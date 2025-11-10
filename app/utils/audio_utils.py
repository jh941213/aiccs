"""
오디오 처리 유틸리티
"""
from pathlib import Path
from typing import Tuple

import soundfile as sf
from loguru import logger


def get_audio_info(audio_path: Path) -> Tuple[int, int, float]:
    """
    오디오 파일 정보 가져오기

    Args:
        audio_path: 오디오 파일 경로

    Returns:
        (채널 수, 샘플레이트, 길이(초))
    """
    try:
        with sf.SoundFile(audio_path) as f:
            channels = f.channels
            samplerate = f.samplerate
            duration = len(f) / f.samplerate

        logger.debug(
            f"오디오 정보 - 채널: {channels}, 샘플레이트: {samplerate}Hz, 길이: {duration:.2f}초"
        )

        return channels, samplerate, duration

    except Exception as e:
        logger.error(f"❌ 오디오 정보 읽기 실패: {e}")
        raise


def is_mono(audio_path: Path) -> bool:
    """
    모노 파일 여부 확인

    Args:
        audio_path: 오디오 파일 경로

    Returns:
        모노 파일 여부
    """
    channels, _, _ = get_audio_info(audio_path)
    return channels == 1


def is_stereo(audio_path: Path) -> bool:
    """
    스테레오 파일 여부 확인

    Args:
        audio_path: 오디오 파일 경로

    Returns:
        스테레오 파일 여부
    """
    channels, _, _ = get_audio_info(audio_path)
    return channels == 2


def split_stereo_channels(audio_path: Path, output_dir: Path) -> Tuple[Path, Path]:
    """
    스테레오 파일을 좌우 채널로 분리

    Args:
        audio_path: 스테레오 WAV 파일 경로
        output_dir: 출력 디렉토리

    Returns:
        (왼쪽 채널 파일, 오른쪽 채널 파일)
    """
    logger.info(f"🔊 스테레오 채널 분리 시작: {audio_path.name}")

    try:
        # 오디오 읽기
        data, samplerate = sf.read(audio_path)

        # 채널 수 확인
        if data.ndim != 2 or data.shape[1] != 2:
            raise ValueError("스테레오 파일이 아닙니다.")

        # 파일명 생성
        base_name = audio_path.stem
        left_path = output_dir / f"{base_name}_1ch.wav"
        right_path = output_dir / f"{base_name}_2ch.wav"

        # 채널 분리 및 저장
        sf.write(left_path, data[:, 0], samplerate)  # 왼쪽 채널 (화자1)
        sf.write(right_path, data[:, 1], samplerate)  # 오른쪽 채널 (화자2)

        logger.info(f"✅ 채널 분리 완료: {left_path.name}, {right_path.name}")

        return left_path, right_path

    except Exception as e:
        logger.error(f"❌ 채널 분리 실패: {e}")
        raise


def merge_transcripts_with_speaker_labels(
    left_segments: list, right_segments: list
) -> str:
    """
    좌우 채널 STT 결과를 시간 순서대로 병합하여 화자 라벨링

    Args:
        left_segments: 왼쪽 채널 세그먼트 [(start, end, text), ...]
        right_segments: 오른쪽 채널 세그먼트 [(start, end, text), ...]

    Returns:
        병합된 SRT 형식 문자열 (화자 라벨 포함)
    """
    logger.info("🔄 채널 병합 및 화자 라벨링 시작")

    # 모든 세그먼트를 시간 순서로 정렬
    all_segments = []

    for start, end, text in left_segments:
        all_segments.append((start, end, "[화자1] " + text))

    for start, end, text in right_segments:
        all_segments.append((start, end, "[화자2] " + text))

    # 시작 시간 기준으로 정렬
    all_segments.sort(key=lambda x: _timestamp_to_seconds(x[0]))

    # SRT 형식으로 변환
    srt_content = []
    for idx, (start, end, text) in enumerate(all_segments, start=1):
        srt_content.append(f"{idx}")
        srt_content.append(f"{start} --> {end}")
        srt_content.append(text)
        srt_content.append("")  # 빈 줄

    logger.info(f"✅ 채널 병합 완료: {len(all_segments)}개 세그먼트")

    return "\n".join(srt_content)


def _timestamp_to_seconds(timestamp: str) -> float:
    """
    SRT 타임스탬프를 초 단위로 변환

    Args:
        timestamp: SRT 타임스탬프 (HH:MM:SS,mmm)

    Returns:
        초 단위 시간
    """
    # HH:MM:SS,mmm 형식 파싱
    time_part, ms_part = timestamp.split(",")
    hours, minutes, seconds = map(int, time_part.split(":"))
    milliseconds = int(ms_part)

    total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000

    return total_seconds
