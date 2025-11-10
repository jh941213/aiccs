"""
Whisper STT 서비스
faster-whisper를 사용한 음성 인식
"""
from pathlib import Path
from typing import List, Tuple
from datetime import timedelta

from faster_whisper import WhisperModel
from loguru import logger

from app.core.config import settings


class WhisperService:
    """Whisper STT 서비스"""

    def __init__(self):
        """초기화"""
        self.model = None
        self._model_loaded = False

    def load_model(self):
        """모델 로드"""
        if self._model_loaded:
            return

        logger.info(f"🔄 Whisper 모델 로드 중: {settings.whisper_model}")

        try:
            self.model = WhisperModel(
                settings.whisper_model,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
            )
            self._model_loaded = True
            logger.info("✅ Whisper 모델 로드 완료")

        except Exception as e:
            logger.error(f"❌ Whisper 모델 로드 실패: {e}")
            raise

    def unload_model(self):
        """모델 언로드 (GPU 메모리 해제)"""
        if self.model is not None:
            del self.model
            self.model = None
            self._model_loaded = False

            # GPU 메모리 정리
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            logger.info("✅ Whisper 모델 언로드 완료")

    def transcribe(self, audio_path: Path, language: str = "ko") -> List[Tuple[str, str, str]]:
        """
        음성 파일을 텍스트로 변환

        Args:
            audio_path: 음성 파일 경로
            language: 언어 코드 (기본값: ko)

        Returns:
            [(시작시간, 종료시간, 텍스트), ...]
        """
        if not self._model_loaded:
            self.load_model()

        logger.info(f"🎤 STT 시작: {audio_path.name}")

        try:
            segments, info = self.model.transcribe(
                str(audio_path),
                language=language,
                beam_size=5,
                vad_filter=True,  # VAD (Voice Activity Detection) 필터
                vad_parameters={
                    "threshold": 0.5,
                    "min_speech_duration_ms": 250,
                    "max_speech_duration_s": float("inf"),
                    "min_silence_duration_ms": 2000,
                    "speech_pad_ms": 400,
                },
            )

            results = []
            for segment in segments:
                start_time = self._format_timestamp(segment.start)
                end_time = self._format_timestamp(segment.end)
                text = segment.text.strip()

                results.append((start_time, end_time, text))

                logger.debug(f"[{start_time} -> {end_time}] {text}")

            logger.info(f"✅ STT 완료: {len(results)}개 세그먼트")
            return results

        except Exception as e:
            logger.error(f"❌ STT 실패: {e}")
            raise

    def transcribe_to_srt(self, audio_path: Path, language: str = "ko") -> str:
        """
        음성 파일을 SRT 형식으로 변환

        Args:
            audio_path: 음성 파일 경로
            language: 언어 코드

        Returns:
            SRT 형식 문자열
        """
        segments = self.transcribe(audio_path, language)

        srt_content = []
        for idx, (start_time, end_time, text) in enumerate(segments, start=1):
            srt_content.append(f"{idx}")
            srt_content.append(f"{start_time} --> {end_time}")
            srt_content.append(text)
            srt_content.append("")  # 빈 줄

        return "\n".join(srt_content)

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """
        초를 SRT 타임스탬프 형식으로 변환

        Args:
            seconds: 초 단위 시간

        Returns:
            SRT 타임스탬프 (HH:MM:SS,mmm)
        """
        td = timedelta(seconds=seconds)
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int(td.microseconds / 1000)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


# 전역 인스턴스
whisper_service = WhisperService()
