"""
FastAPI 라우터
"""
import uuid
from pathlib import Path
from datetime import datetime
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse
from loguru import logger

from app.api.schemas import (
    AudioFileUploadResponse,
    TaskStatusResponse,
    TaskResultResponse,
    PromptUpdateRequest,
    PromptResponse,
    DictionaryUpdateRequest,
    DictionaryResponse,
    HealthCheckResponse,
    TaskStatus,
)
from app.core.config import settings

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse, tags=["시스템"])
async def health_check():
    """
    시스템 헬스 체크
    - Redis 연결 상태
    - Ollama 가용 상태
    - GPU 상태
    """
    # TODO: 실제 헬스 체크 로직 구현
    return HealthCheckResponse(
        status="ok",
        redis_connected=True,
        ollama_available=True,
        gpu_available=True,
        gpu_memory_free_mb=8192,
    )


@router.post("/upload", response_model=AudioFileUploadResponse, tags=["파일 처리"])
async def upload_audio_file(file: UploadFile = File(...)):
    """
    WAV 파일 업로드
    - 파일을 input/ 폴더에 저장
    - Celery 작업 큐에 추가
    """
    # 파일 확장자 검증
    if not file.filename.lower().endswith(".wav"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="WAV 파일만 업로드 가능합니다.",
        )

    # 고유 작업 ID 생성
    task_id = str(uuid.uuid4())

    # 파일 저장
    file_path = settings.input_dir / file.filename

    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 저장 실패: {str(e)}",
        )

    # Celery 작업 큐에 추가
    from app.tasks.audio_task import process_audio_file
    celery_task = process_audio_file.delay(str(file_path), task_id)

    logger.info(f"📋 작업 추가됨: {task_id} (Celery Task: {celery_task.id})")

    return AudioFileUploadResponse(
        task_id=celery_task.id,  # Celery task ID 사용
        filename=file.filename,
        status=TaskStatus.PENDING,
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse, tags=["작업 관리"])
async def get_task_status(task_id: str):
    """
    작업 상태 조회
    """
    from app.tasks.audio_task import process_audio_file
    from celery.result import AsyncResult

    # Celery 작업 결과 조회
    result = AsyncResult(task_id, app=process_audio_file.app)

    # 상태 매핑
    status_mapping = {
        "PENDING": TaskStatus.PENDING,
        "STARTED": TaskStatus.IN_PROGRESS,
        "SUCCESS": TaskStatus.COMPLETED,
        "FAILURE": TaskStatus.FAILED,
        "RETRY": TaskStatus.IN_PROGRESS,
    }

    task_status = status_mapping.get(result.state, TaskStatus.PENDING)

    # 진행률 계산 (임시)
    progress = 0
    if result.state == "STARTED":
        progress = 50
    elif result.state == "SUCCESS":
        progress = 100

    return TaskStatusResponse(
        task_id=task_id,
        filename="",  # TODO: 파일명 조회
        status=task_status,
        progress=progress,
        created_at=datetime.now(),  # TODO: 실제 생성 시간
        updated_at=datetime.now(),
    )


@router.get("/results/{task_id}", response_model=TaskResultResponse, tags=["작업 관리"])
async def get_task_result(task_id: str):
    """
    작업 결과 조회
    """
    from app.tasks.audio_task import process_audio_file
    from celery.result import AsyncResult

    # Celery 작업 결과 조회
    result = AsyncResult(task_id, app=process_audio_file.app)

    if result.state != "SUCCESS":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"작업이 완료되지 않았습니다. 현재 상태: {result.state}",
        )

    # 작업 결과에서 파일명 가져오기
    task_result = result.result
    filename = task_result.get("filename", "")
    base_name = Path(filename).stem

    # 파일 읽기
    srt_path = settings.output_dir / f"{base_name}.srt"
    summary_path = settings.output_dir / f"{base_name}_요약.txt"

    if not srt_path.exists() or not summary_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="결과 파일을 찾을 수 없습니다.",
        )

    srt_content = srt_path.read_text(encoding="utf-8")
    summary = summary_path.read_text(encoding="utf-8")

    return TaskResultResponse(
        task_id=task_id,
        filename=filename,
        srt_content=srt_content,
        summary=summary,
    )


@router.get("/download/srt/{filename}", tags=["파일 다운로드"])
async def download_srt(filename: str):
    """
    SRT 파일 다운로드
    """
    file_path = settings.output_dir / filename

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="파일을 찾을 수 없습니다.",
        )

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="text/plain",
    )


@router.get("/config/prompt", response_model=PromptResponse, tags=["설정 관리"])
async def get_prompt():
    """
    현재 프롬프트 조회
    """
    prompt_file = settings.config_dir / "default_prompt.txt"

    try:
        prompt_content = prompt_file.read_text(encoding="utf-8")
        stat = prompt_file.stat()
        updated_at = datetime.fromtimestamp(stat.st_mtime)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"프롬프트 읽기 실패: {str(e)}",
        )

    return PromptResponse(
        prompt_content=prompt_content,
        updated_at=updated_at,
    )


@router.put("/config/prompt", response_model=PromptResponse, tags=["설정 관리"])
async def update_prompt(request: PromptUpdateRequest):
    """
    프롬프트 수정
    """
    prompt_file = settings.config_dir / "default_prompt.txt"

    try:
        prompt_file.write_text(request.prompt_content, encoding="utf-8")
        updated_at = datetime.now()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"프롬프트 저장 실패: {str(e)}",
        )

    return PromptResponse(
        prompt_content=request.prompt_content,
        updated_at=updated_at,
    )


@router.get("/config/dictionary", response_model=DictionaryResponse, tags=["설정 관리"])
async def get_dictionary():
    """
    용어 사전 조회
    """
    dict_file = settings.config_dir / "dictionary.txt"

    try:
        dictionary_content = dict_file.read_text(encoding="utf-8")
        stat = dict_file.stat()
        updated_at = datetime.fromtimestamp(stat.st_mtime)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"용어 사전 읽기 실패: {str(e)}",
        )

    return DictionaryResponse(
        dictionary_content=dictionary_content,
        updated_at=updated_at,
    )


@router.put("/config/dictionary", response_model=DictionaryResponse, tags=["설정 관리"])
async def update_dictionary(request: DictionaryUpdateRequest):
    """
    용어 사전 수정
    """
    dict_file = settings.config_dir / "dictionary.txt"

    try:
        dict_file.write_text(request.dictionary_content, encoding="utf-8")
        updated_at = datetime.now()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"용어 사전 저장 실패: {str(e)}",
        )

    return DictionaryResponse(
        dictionary_content=request.dictionary_content,
        updated_at=updated_at,
    )
