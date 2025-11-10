"""
설정 관리
Pydantic Settings를 사용한 환경 변수 관리
"""
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


# 프로젝트 루트 경로
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # Redis 설정
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")

    # Celery 설정 (환경 변수로 오버라이드 가능)
    celery_broker_url: str | None = Field(default=None, alias="CELERY_BROKER_URL")
    celery_result_backend: str | None = Field(default=None, alias="CELERY_RESULT_BACKEND")

    # Ollama 설정
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="midm-2.0:base", alias="OLLAMA_MODEL")
    ollama_timeout: int = Field(default=120, alias="OLLAMA_TIMEOUT")

    # Whisper 설정
    whisper_model: str = Field(default="dropbox-dash/faster-whisper-large-v3-turbo", alias="WHISPER_MODEL")
    whisper_device: str = Field(default="cuda", alias="WHISPER_DEVICE")
    whisper_compute_type: str = Field(default="float16", alias="WHISPER_COMPUTE_TYPE")

    # Pyannote (화자 분리) 설정
    hf_token: str = Field(default="", alias="HF_TOKEN")

    # 경로 설정
    input_dir: Path = Field(default=BASE_DIR / "data" / "input", alias="INPUT_DIR")
    output_dir: Path = Field(default=BASE_DIR / "data" / "output", alias="OUTPUT_DIR")
    processed_dir: Path = Field(default=BASE_DIR / "data" / "processed", alias="PROCESSED_DIR")
    error_dir: Path = Field(default=BASE_DIR / "data" / "error", alias="ERROR_DIR")
    config_dir: Path = Field(default=BASE_DIR / "config", alias="CONFIG_DIR")
    log_dir: Path = Field(default=BASE_DIR / "logs", alias="LOG_DIR")

    # GPU 설정
    gpu_memory_reserve_mb: int = Field(default=1024, alias="GPU_MEMORY_RESERVE_MB")

    # 로그 설정
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    def get_celery_broker_url(self) -> str:
        """Celery 브로커 URL (환경 변수 우선)"""
        if self.celery_broker_url:
            return self.celery_broker_url
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def get_celery_result_backend(self) -> str:
        """Celery 결과 백엔드 URL (환경 변수 우선)"""
        if self.celery_result_backend:
            return self.celery_result_backend
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def get_redis_url(self) -> str:
        """Redis URL (환경 변수 우선)"""
        if self.redis_url:
            return self.redis_url
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    class Config:
        env_file = BASE_DIR / ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 전역 설정 인스턴스
settings = Settings()


# 필요한 디렉토리 생성
def ensure_directories():
    """필수 디렉토리 생성"""
    directories = [
        settings.input_dir,
        settings.output_dir,
        settings.processed_dir,
        settings.error_dir,
        settings.config_dir,
        settings.log_dir,
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


# 초기화 시 디렉토리 생성
ensure_directories()
