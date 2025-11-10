"""
화자 분리 서비스 (Speaker Diarization)
"""
from pathlib import Path
from typing import List, Tuple

from pyannote.audio import Pipeline
from loguru import logger
import soundfile as sf
import torch
import numpy as np

from app.core.config import settings


class DiarizationService:
    """화자 분리 서비스"""

    def __init__(self, hf_token: str = None):
        """
        초기화

        Args:
            hf_token: Hugging Face 액세스 토큰
                    (https://huggingface.co/settings/tokens에서 생성)
        """
        self.pipeline = None
        self.hf_token = hf_token or settings.hf_token
        self._pipeline_loaded = False

    def load_pipeline(self):
        """화자 분리 파이프라인 로드"""
        if self._pipeline_loaded:
            return

        if not self.hf_token:
            raise ValueError(
                "Hugging Face 토큰이 필요합니다. "
                "https://huggingface.co/settings/tokens에서 생성 후 "
                ".env 파일에 HF_TOKEN 설정하세요."
            )

        logger.info("🔄 화자 분리 모델 로드 중...")

        try:
            # pyannote community-1: 최신 오픈소스 모델
            # 최신 pyannote.audio는 환경 변수 HF_TOKEN을 자동으로 사용
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-community-1"
            )

            # GPU 사용 설정 (Mac MPS 지원)
            if torch.backends.mps.is_available():
                self.pipeline.to(torch.device("mps"))
                logger.info("✅ MPS(Apple Silicon)로 화자 분리 모델 로드 완료")
            elif torch.cuda.is_available():
                self.pipeline.to(torch.device("cuda"))
                logger.info("✅ CUDA GPU로 화자 분리 모델 로드 완료")
            else:
                logger.info("✅ CPU로 화자 분리 모델 로드 완료")

            self._pipeline_loaded = True

        except Exception as e:
            logger.error(f"❌ 화자 분리 모델 로드 실패: {e}")
            raise

    def unload_pipeline(self):
        """파이프라인 언로드 (GPU 메모리 해제)"""
        if self.pipeline is not None:
            del self.pipeline
            self.pipeline = None
            self._pipeline_loaded = False

            # GPU 메모리 정리
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            logger.info("✅ 화자 분리 모델 언로드 완료")

    def diarize(
        self,
        audio_path: Path,
        num_speakers: int = None,
        min_speakers: int = None,
        max_speakers: int = None,
    ) -> List[Tuple[float, float, str]]:
        """
        화자 분리 수행

        Args:
            audio_path: 오디오 파일 경로
            num_speakers: 정확한 화자 수 (알고 있는 경우)
            min_speakers: 최소 화자 수
            max_speakers: 최대 화자 수

        Returns:
            [(시작시간(초), 종료시간(초), 화자ID), ...]
        """
        if not self._pipeline_loaded:
            self.load_pipeline()

        logger.info(f"🎤 화자 분리 시작: {audio_path.name}")

        try:
            # 화자 수 설정
            kwargs = {}
            if num_speakers is not None:
                kwargs["num_speakers"] = num_speakers
            else:
                if min_speakers is not None:
                    kwargs["min_speakers"] = min_speakers
                if max_speakers is not None:
                    kwargs["max_speakers"] = max_speakers

            # audio_in_memory 형식으로 전달 (torchcodec 문제 우회)
            waveform, sample_rate = sf.read(str(audio_path))
            if waveform.ndim == 1:
                # Mono: (time,) -> (1, time)
                waveform = waveform.reshape(1, -1)
            else:
                # Stereo: (time, channel) -> (channel, time)
                waveform = waveform.T

            audio_in_memory = {
                "waveform": torch.from_numpy(waveform).float(),
                "sample_rate": sample_rate
            }

            # community-1: 화자 분리 실행
            output = self.pipeline(audio_in_memory, **kwargs)

            # community-1 API: 더 간단한 iteration
            segments = []
            for turn, speaker in output.speaker_diarization:
                segments.append((turn.start, turn.end, speaker))

            logger.info(f"✅ 화자 분리 완료: {len(segments)}개 세그먼트")

            # 화자 정보 로깅
            speakers = set(seg[2] for seg in segments)
            logger.info(f"📊 감지된 화자 수: {len(speakers)}")

            return segments

        except Exception as e:
            logger.error(f"❌ 화자 분리 실패: {e}")
            raise

    def merge_with_transcript(
        self,
        diarization_segments: List[Tuple[float, float, str]],
        whisper_segments: List[Tuple[str, str, str]],
    ) -> List[Tuple[str, str, str, str]]:
        """
        화자 분리 결과와 Whisper STT 결과 병합

        Args:
            diarization_segments: [(시작(초), 종료(초), 화자), ...]
            whisper_segments: [(시작시각, 종료시각, 텍스트), ...]

        Returns:
            [(시작시각, 종료시각, 화자, 텍스트), ...]
        """
        logger.info("🔄 화자 정보와 STT 결과 병합 중...")

        merged_segments = []

        for srt_start, srt_end, text in whisper_segments:
            # SRT 타임스탬프를 초 단위로 변환
            start_sec = self._timestamp_to_seconds(srt_start)
            end_sec = self._timestamp_to_seconds(srt_end)

            # 해당 시간대의 화자 찾기 (중간 지점 기준)
            mid_sec = (start_sec + end_sec) / 2
            speaker = self._find_speaker_at_time(diarization_segments, mid_sec)

            # 화자 라벨 추가
            speaker_label = f"[{speaker}]" if speaker else "[알 수 없음]"

            merged_segments.append((srt_start, srt_end, speaker_label, text))

        logger.info(f"✅ 병합 완료: {len(merged_segments)}개 세그먼트")

        return merged_segments

    @staticmethod
    def _timestamp_to_seconds(timestamp: str) -> float:
        """
        SRT 타임스탬프를 초 단위로 변환

        Args:
            timestamp: SRT 타임스탬프 (HH:MM:SS,mmm)

        Returns:
            초 단위 시간
        """
        time_part, ms_part = timestamp.split(",")
        hours, minutes, seconds = map(int, time_part.split(":"))
        milliseconds = int(ms_part)

        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000

    @staticmethod
    def _find_speaker_at_time(
        diarization_segments: List[Tuple[float, float, str]], time_sec: float
    ) -> str:
        """
        특정 시각의 화자 찾기

        Args:
            diarization_segments: [(시작, 종료, 화자), ...]
            time_sec: 찾을 시각 (초)

        Returns:
            화자 ID
        """
        for start, end, speaker in diarization_segments:
            if start <= time_sec <= end:
                return speaker

        return "UNKNOWN"


# 전역 인스턴스
diarization_service = DiarizationService()
