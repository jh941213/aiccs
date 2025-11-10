"""
Ollama LLM 서비스
Ollama REST API를 사용한 요약 생성
"""
from pathlib import Path
from typing import Optional

import httpx
from loguru import logger

from app.core.config import settings


class OllamaService:
    """Ollama LLM 서비스"""

    def __init__(self):
        """초기화"""
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout

    async def check_health(self) -> bool:
        """
        Ollama 서버 상태 확인

        Returns:
            서버 가용 여부
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"❌ Ollama 서버 연결 실패: {e}")
            return False

    async def summarize(
        self,
        transcript: str,
        prompt_template: Optional[str] = None,
        dictionary_content: Optional[str] = None,
    ) -> str:
        """
        대화 내용 요약

        Args:
            transcript: 대화 전문 (SRT 형식 또는 텍스트)
            prompt_template: 프롬프트 템플릿 (None이면 기본값 사용)
            dictionary_content: 용어 사전 내용

        Returns:
            요약 텍스트
        """
        # 기본 프롬프트 로드
        if prompt_template is None:
            prompt_file = settings.config_dir / "default_prompt.txt"
            prompt_template = prompt_file.read_text(encoding="utf-8")

        # 용어 사전 로드
        if dictionary_content is None:
            dict_file = settings.config_dir / "dictionary.txt"
            if dict_file.exists():
                dictionary_content = dict_file.read_text(encoding="utf-8")
            else:
                dictionary_content = ""

        # 용어 사전 섹션 생성
        if dictionary_content.strip():
            dictionary_section = f"용어사전:\n{dictionary_content}\n"
        else:
            dictionary_section = ""

        # 프롬프트 포맷팅
        full_prompt = prompt_template.format(
            dictionary_section=dictionary_section,
            transcript_text=transcript,
        )

        logger.info("🤖 LLM 요약 시작")
        logger.debug(f"프롬프트 길이: {len(full_prompt)} 문자")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,  # 낮은 온도로 일관된 요약 생성
                            "top_p": 0.9,
                            "num_predict": 512,  # 최대 토큰 수
                        },
                    },
                )

                response.raise_for_status()
                result = response.json()

                summary = result.get("response", "").strip()

                logger.info(f"✅ LLM 요약 완료: {len(summary)} 문자")
                logger.debug(f"요약 내용: {summary[:100]}...")

                return summary

        except httpx.TimeoutException:
            logger.error(f"❌ LLM 요약 타임아웃 ({self.timeout}초)")
            raise

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ LLM API 에러: {e.response.status_code} - {e.response.text}")
            raise

        except Exception as e:
            logger.error(f"❌ LLM 요약 실패: {e}")
            raise

    def summarize_sync(
        self,
        transcript: str,
        prompt_template: Optional[str] = None,
        dictionary_content: Optional[str] = None,
    ) -> str:
        """
        대화 내용 요약 (동기 버전, Celery 태스크용)

        Args:
            transcript: 대화 전문
            prompt_template: 프롬프트 템플릿
            dictionary_content: 용어 사전 내용

        Returns:
            요약 텍스트
        """
        import asyncio

        # 이벤트 루프 생성 및 실행
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.summarize(transcript, prompt_template, dictionary_content)
        )


# 전역 인스턴스
ollama_service = OllamaService()
