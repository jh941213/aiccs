@echo off
chcp 65001 >nul
echo ========================================
echo Voicecom AI 서비스 시작
echo ========================================
echo.

REM 가상환경 활성화
echo [1/4] 가상환경 활성화...
call venv\Scripts\activate
echo ✓ 가상환경 활성화 완료
echo.

REM Redis 실행 확인
echo [2/4] Redis 연결 확인...
redis-cli ping >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ Redis가 실행되지 않았습니다.
    echo   Redis를 먼저 실행해주세요: redis-server
    pause
    exit /b 1
)
echo ✓ Redis 연결 확인 완료
echo.

REM Ollama 실행 확인
echo [3/4] Ollama 연결 확인...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ Ollama가 실행되지 않았습니다.
    echo   Ollama를 먼저 실행해주세요: ollama serve
    pause
    exit /b 1
)
echo ✓ Ollama 연결 확인 완료
echo.

REM 새 터미널에서 Celery Worker 시작
echo [4/4] Celery Worker 시작...
start "Celery Worker" cmd /k "venv\Scripts\activate && celery -A app.tasks.celery_app worker --loglevel=info --pool=solo"
timeout /t 3 /nobreak >nul
echo ✓ Celery Worker 시작 완료
echo.

REM FastAPI 서버 시작 (현재 터미널)
echo FastAPI 서버 시작 중...
echo.
echo ========================================
echo 서비스 실행 중
echo ========================================
echo API 문서: http://localhost:8000/docs
echo 헬스 체크: http://localhost:8000/api/v1/health
echo.
echo Ctrl+C 를 눌러 종료할 수 있습니다.
echo ========================================
echo.

python app/main.py
