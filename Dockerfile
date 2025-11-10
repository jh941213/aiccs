# Python 3.12 베이스 이미지
FROM python:3.12-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치를 위한 requirements.txt 복사
COPY pyproject.toml ./

# UV 설치
RUN pip install --no-cache-dir uv

# 의존성 설치
RUN uv pip install --system -r pyproject.toml

# 애플리케이션 코드 복사
COPY . .

# 데이터 디렉토리 생성
RUN mkdir -p data/input data/output data/processed data/error config logs

# 환경 변수 설정
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 포트 노출 (FastAPI용)
EXPOSE 8000

# 기본 명령어 (docker-compose에서 오버라이드)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
