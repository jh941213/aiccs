"""
FastAPI 메인 애플리케이션
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 라이프사이클 관리
    """
    # 시작 시
    logger.info("🚀 Voicecom AI 서비스 시작")
    logger.info(f"📁 Input 디렉토리: {settings.input_dir}")
    logger.info(f"📁 Output 디렉토리: {settings.output_dir}")
    logger.info(f"🔧 Whisper 모델: {settings.whisper_model}")
    logger.info(f"🤖 Ollama 모델: {settings.ollama_model}")

    yield

    # 종료 시
    logger.info("🛑 Voicecom AI 서비스 종료")


# FastAPI 앱 생성
app = FastAPI(
    title="Voicecom AI API",
    description="음성 파일 자동 처리 시스템 - STT + LLM 요약",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "Voicecom AI",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower(),
    )
