"""
오디오 파일 처리 Celery 태스크
"""
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

from loguru import logger

from app.tasks.celery_app import celery_app
from app.core.config import settings


@celery_app.task(bind=True, name="process_audio_file")
def process_audio_file(self, file_path: str, task_id: str):
    """
    오디오 파일 처리 메인 태스크

    Args:
        file_path: 오디오 파일 경로
        task_id: 작업 ID

    처리 흐름:
        1. 파일 타입 감지 (Mono/Stereo)
        2. STT 처리
        3. LLM 요약
        4. 결과 저장
        5. 원본 파일 이동
    """
    # Lazy imports (모델 로딩 지연)
    from app.utils.audio_utils import is_mono, is_stereo
    from app.services.ollama_service import ollama_service

    audio_path = Path(file_path)
    logger.info(f"📥 작업 시작 [{task_id}]: {audio_path.name}")

    try:
        # 1. 파일 타입 감지
        if is_mono(audio_path):
            logger.info("🎤 Mono 파일 감지")
            srt_content, transcript_text = process_mono_file(audio_path)

        elif is_stereo(audio_path):
            logger.info("🎤 Stereo 파일 감지")
            srt_content, transcript_text = process_stereo_file(audio_path)

        else:
            raise ValueError("지원하지 않는 오디오 형식입니다 (Mono 또는 Stereo만 가능).")

        # 2. LLM 요약 생성
        logger.info("🤖 LLM 요약 생성 중...")
        summary = ollama_service.summarize_sync(transcript_text)

        # 3. 결과 저장
        save_results(audio_path, srt_content, summary)

        # 4. 원본 파일을 processed/ 폴더로 이동
        move_to_processed(audio_path)

        logger.info(f"✅ 작업 완료 [{task_id}]: {audio_path.name}")

        return {
            "task_id": task_id,
            "status": "success",
            "filename": audio_path.name,
            "completed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ 작업 실패 [{task_id}]: {e}")

        # 에러 파일 처리
        handle_error(audio_path, task_id, e)

        raise


def process_mono_file(audio_path: Path) -> tuple[str, str]:
    """
    Mono 파일 처리

    Args:
        audio_path: 오디오 파일 경로

    Returns:
        (SRT 내용, 플레인 텍스트)
    """
    from app.services.whisper_service import whisper_service

    logger.info("🎤 Mono 파일 STT 시작")

    # Whisper STT
    srt_content = whisper_service.transcribe_to_srt(audio_path, language="ko")

    # GPU 메모리 해제
    whisper_service.unload_model()

    # SRT에서 텍스트만 추출
    transcript_text = extract_text_from_srt(srt_content)

    return srt_content, transcript_text


def process_stereo_file(audio_path: Path) -> tuple[str, str]:
    """
    Stereo 파일 처리 (pyannote 화자 분리 + Whisper STT)

    Args:
        audio_path: 오디오 파일 경로

    Returns:
        (SRT 내용, 플레인 텍스트)
    """
    from app.services.whisper_service import whisper_service
    from app.services.diarization_service import diarization_service

    logger.info("🎤 Stereo 파일 처리 시작 (pyannote 화자 분리)")

    # 1. 화자 분리 (pyannote)
    logger.info("🎤 화자 분리 수행 중...")
    diarization_segments = diarization_service.diarize(
        audio_path,
        min_speakers=1,
        max_speakers=3,  # 최대 3명까지 감지
    )

    # 화자 분리 모델 언로드 (GPU 메모리 해제)
    diarization_service.unload_pipeline()

    # 2. Whisper STT
    logger.info("🎤 Whisper STT 수행 중...")
    whisper_segments = whisper_service.transcribe(audio_path, language="ko")

    # Whisper 모델 언로드 (GPU 메모리 해제)
    whisper_service.unload_model()

    # 3. 화자 정보와 STT 결과 병합
    merged_segments = diarization_service.merge_with_transcript(
        diarization_segments, whisper_segments
    )

    # 4. SRT 형식으로 변환
    srt_content = convert_merged_to_srt(merged_segments)

    # SRT에서 텍스트만 추출
    transcript_text = extract_text_from_srt(srt_content)

    return srt_content, transcript_text


def convert_merged_to_srt(merged_segments: List[Tuple[str, str, str, str]]) -> str:
    """
    병합된 세그먼트를 SRT 형식으로 변환

    Args:
        merged_segments: [(시작시각, 종료시각, 화자, 텍스트), ...]

    Returns:
        SRT 형식 문자열
    """
    srt_lines = []

    for idx, (start, end, speaker, text) in enumerate(merged_segments, start=1):
        srt_lines.append(f"{idx}")
        srt_lines.append(f"{start} --> {end}")
        srt_lines.append(f"{speaker} {text}")
        srt_lines.append("")  # 빈 줄

    return "\n".join(srt_lines)


def extract_text_from_srt(srt_content: str) -> str:
    """
    SRT 형식에서 텍스트만 추출

    Args:
        srt_content: SRT 형식 문자열

    Returns:
        플레인 텍스트
    """
    lines = srt_content.strip().split("\n")
    text_lines = []

    for line in lines:
        line = line.strip()

        # 번호, 타임스탬프, 빈 줄 제외
        if line and not line.isdigit() and "-->" not in line:
            text_lines.append(line)

    return " ".join(text_lines)


def save_results(audio_path: Path, srt_content: str, summary: str):
    """
    결과 파일 저장

    Args:
        audio_path: 원본 오디오 파일 경로
        srt_content: SRT 내용
        summary: 요약 내용
    """
    base_name = audio_path.stem

    # SRT 파일 저장
    srt_path = settings.output_dir / f"{base_name}.srt"
    srt_path.write_text(srt_content, encoding="utf-8")
    logger.info(f"💾 SRT 저장: {srt_path.name}")

    # 요약 파일 저장
    summary_path = settings.output_dir / f"{base_name}_요약.txt"
    summary_path.write_text(summary, encoding="utf-8")
    logger.info(f"💾 요약 저장: {summary_path.name}")


def move_to_processed(audio_path: Path):
    """
    원본 파일을 processed/ 폴더로 이동

    Args:
        audio_path: 원본 오디오 파일 경로
    """
    processed_path = settings.processed_dir / audio_path.name

    shutil.move(str(audio_path), str(processed_path))
    logger.info(f"📦 원본 이동: {processed_path}")


def handle_error(audio_path: Path, task_id: str, error: Exception):
    """
    에러 발생 시 파일 및 로그 관리

    Args:
        audio_path: 원본 오디오 파일 경로
        task_id: 작업 ID
        error: 발생한 에러
    """
    # 에러 로그 파일 생성
    error_log_path = settings.error_dir / f"{audio_path.stem}_error.log"

    error_log = f"""
작업 ID: {task_id}
파일명: {audio_path.name}
에러 발생 시각: {datetime.now().isoformat()}
에러 유형: {type(error).__name__}
에러 메시지: {str(error)}
"""

    error_log_path.write_text(error_log.strip(), encoding="utf-8")
    logger.info(f"📝 에러 로그 저장: {error_log_path.name}")

    # 원본 파일을 error/ 폴더로 이동
    if audio_path.exists():
        error_audio_path = settings.error_dir / audio_path.name
        shutil.move(str(audio_path), str(error_audio_path))
        logger.info(f"⚠️ 에러 파일 이동: {error_audio_path}")
