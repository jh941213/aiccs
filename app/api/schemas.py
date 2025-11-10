"""
API 요청/응답 스키마 정의
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """작업 상태"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AudioFileUploadResponse(BaseModel):
    """파일 업로드 응답"""
    task_id: str = Field(..., description="작업 ID")
    filename: str = Field(..., description="업로드된 파일명")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="작업 상태")
    message: str = Field(default="파일이 업로드되어 처리 대기 중입니다.")


class TaskStatusResponse(BaseModel):
    """작업 상태 조회 응답"""
    task_id: str = Field(..., description="작업 ID")
    filename: str = Field(..., description="파일명")
    status: TaskStatus = Field(..., description="작업 상태")
    progress: int = Field(default=0, ge=0, le=100, description="진행률 (%)")
    created_at: datetime = Field(..., description="생성 시간")
    updated_at: Optional[datetime] = Field(None, description="업데이트 시간")
    error_message: Optional[str] = Field(None, description="에러 메시지 (실패 시)")


class TaskResultResponse(BaseModel):
    """작업 결과 응답"""
    task_id: str = Field(..., description="작업 ID")
    filename: str = Field(..., description="파일명")
    srt_content: Optional[str] = Field(None, description="SRT 자막 내용")
    summary: Optional[str] = Field(None, description="요약 내용")
    srt_file_path: Optional[str] = Field(None, description="SRT 파일 경로")
    summary_file_path: Optional[str] = Field(None, description="요약 파일 경로")


class PromptUpdateRequest(BaseModel):
    """프롬프트 수정 요청"""
    prompt_content: str = Field(..., description="새 프롬프트 내용", min_length=10)


class PromptResponse(BaseModel):
    """프롬프트 조회/수정 응답"""
    prompt_content: str = Field(..., description="현재 프롬프트 내용")
    updated_at: Optional[datetime] = Field(None, description="마지막 수정 시간")


class DictionaryUpdateRequest(BaseModel):
    """용어 사전 수정 요청"""
    dictionary_content: str = Field(..., description="용어 사전 내용")


class DictionaryResponse(BaseModel):
    """용어 사전 조회/수정 응답"""
    dictionary_content: str = Field(..., description="현재 용어 사전 내용")
    updated_at: Optional[datetime] = Field(None, description="마지막 수정 시간")


class HealthCheckResponse(BaseModel):
    """헬스 체크 응답"""
    status: str = Field(default="ok")
    redis_connected: bool = Field(..., description="Redis 연결 상태")
    ollama_available: bool = Field(..., description="Ollama 가용 상태")
    gpu_available: bool = Field(..., description="GPU 가용 상태")
    gpu_memory_free_mb: Optional[int] = Field(None, description="GPU 여유 메모리 (MB)")
