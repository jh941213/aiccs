#!/bin/bash

echo "========================================"
echo "Voicecom AI 서비스 시작 (Mac/Linux)"
echo "========================================"
echo ""

# 가상환경 활성화
echo "[1/4] 가상환경 활성화..."
if [ ! -d "venv" ]; then
    echo "✗ 가상환경이 없습니다. 먼저 생성해주세요:"
    echo "  python3 -m venv venv"
    exit 1
fi

source venv/bin/activate
echo "✓ 가상환경 활성화 완료"
echo ""

# Redis 실행 확인
echo "[2/4] Redis 연결 확인..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "✗ Redis가 실행되지 않았습니다."
    echo "  Redis를 먼저 실행해주세요:"
    echo "    brew install redis  # Redis 설치 (처음)"
    echo "    redis-server         # Redis 실행"
    exit 1
fi
echo "✓ Redis 연결 확인 완료"
echo ""

# Ollama 실행 확인
echo "[3/4] Ollama 연결 확인..."
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✗ Ollama가 실행되지 않았습니다."
    echo "  Ollama를 먼저 실행해주세요:"
    echo "    ollama serve          # Ollama 서버 실행"
    echo ""
    echo "  midm-2.0:base 모델 다운로드:"
    echo "    ollama pull midm-2.0:base"
    exit 1
fi
echo "✓ Ollama 연결 확인 완료"
echo ""

# 새 터미널에서 Celery Worker 시작
echo "[4/4] Celery Worker 시작..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"' && source venv/bin/activate && celery -A app.tasks.celery_app worker --loglevel=info"'
else
    # Linux
    gnome-terminal -- bash -c "source venv/bin/activate && celery -A app.tasks.celery_app worker --loglevel=info; exec bash"
fi

sleep 3
echo "✓ Celery Worker 시작 완료"
echo ""

# FastAPI 서버 시작 (현재 터미널)
echo "FastAPI 서버 시작 중..."
echo ""
echo "========================================"
echo "서비스 실행 중"
echo "========================================"
echo "API 문서: http://localhost:8000/docs"
echo "헬스 체크: http://localhost:8000/api/v1/health"
echo ""
echo "Ctrl+C 를 눌러 종료할 수 있습니다."
echo "========================================"
echo ""

python app/main.py
