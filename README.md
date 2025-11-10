# Voicecom AI - 음성 파일 자동 처리 시스템

WAV 음성 파일을 자동으로 텍스트 변환(STT) 후 LLM 기반 요약 생성 시스템

## 📋 시스템 개요

**기능**: Whisper STT → SRT 생성 → LLM 요약 → 자동 파일 관리

**처리 흐름**:
```
input/
  ↓ (자동 감지)
WAV 파일 → STT (Whisper) → SRT 생성
  ↓
LLM 요약 (Ollama midm-2.0)
  ↓
output/ (SRT + 요약.txt)
  ↓
processed/ (원본 이동)
```

## 🛠️ 기술 스택

| 계층 | 기술 | 용도 |
|------|------|------|
| Web API | FastAPI + Uvicorn | REST API 서버 |
| Task Queue | Celery + Redis | 비동기 작업 처리 |
| STT | faster-whisper | Whisper large-v3-turbo |
| LLM | Ollama | midm-2.0:base |
| DB | SQLite | 작업 상태 관리 |
| GPU | CUDA 12.x | GPU 가속 |

## 📦 설치 방법

### 1. 사전 요구사항

- Windows 10/11 또는 Windows Server 2019/2022
- NVIDIA GPU (VRAM 12GB 이상)
- CUDA 12.x 설치
- Python 3.10 이상

### 2. 환경 설정

```bash
# 1. 가상환경 생성
python -m venv venv

# 2. 가상환경 활성화 (Windows)
venv\Scripts\activate

# 3. 패키지 설치
pip install -r requirements.txt
```

### 3. Redis 설치

**Windows Redis 다운로드**:
```bash
# Redis for Windows (Memurai 또는 Redis Windows Port)
# https://github.com/redis-windows/redis-windows/releases
```

또는 Docker 사용:
```bash
docker run -d -p 6379:6379 redis:latest
```

### 4. Ollama 설치 및 모델 다운로드

```bash
# Ollama 설치 (https://ollama.ai)

# midm-2.0:base 모델 다운로드
ollama pull midm-2.0:base
```

### 5. 환경 변수 설정

`.env.example`을 `.env`로 복사하고 필요시 수정:
```bash
cp .env.example .env
```

## 🚀 실행 방법

### Windows에서 모든 서비스 실행

`run_services.bat` 파일 실행:
```batch
run_services.bat
```

또는 개별 실행:

**1. Redis 시작** (별도 터미널)
```bash
redis-server
```

**2. Ollama 시작** (별도 터미널)
```bash
ollama serve
```

**3. Celery Worker 시작** (별도 터미널)
```bash
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo
```

**4. FastAPI 서버 시작** (별도 터미널)
```bash
python app/main.py
```

## 📁 디렉토리 구조

```
voicecom_ai/
├── app/
│   ├── api/              # REST API
│   ├── core/             # 설정
│   ├── tasks/            # Celery 태스크
│   ├── services/         # Whisper, Ollama 서비스
│   └── utils/            # 유틸리티
├── config/               # 프롬프트, 용어 사전
├── data/
│   ├── input/           # WAV 입력 (여기에 파일 넣기)
│   ├── output/          # SRT + 요약 출력
│   ├── processed/       # 처리 완료 WAV
│   └── error/           # 에러 파일
└── logs/                # 로그
```

## 💻 API 사용법

### 서버 실행 후 접속

- **API 문서**: http://localhost:8000/docs
- **기본 URL**: http://localhost:8000/api/v1

### 주요 엔드포인트

#### 1. 파일 업로드
```bash
POST /api/v1/upload
Content-Type: multipart/form-data

파라미터:
  file: WAV 파일

응답:
{
  "task_id": "uuid",
  "filename": "example.wav",
  "status": "pending"
}
```

#### 2. 작업 상태 조회
```bash
GET /api/v1/tasks/{task_id}

응답:
{
  "task_id": "uuid",
  "filename": "example.wav",
  "status": "in_progress",
  "progress": 50
}
```

#### 3. 프롬프트 수정
```bash
PUT /api/v1/config/prompt
Content-Type: application/json

{
  "prompt_content": "새 프롬프트 내용..."
}
```

## 🎯 처리 흐름 상세

### Mono 파일 처리

```
mono.wav (input/)
  ↓
Whisper STT → mono.srt
  ↓
LLM 요약 → mono_요약.txt
  ↓
output/ 저장 + processed/ 이동
```

### Stereo 파일 처리

```
stereo.wav (input/)
  ↓
채널 분리 → stereo_1ch.wav + stereo_2ch.wav
  ↓
각 채널 STT → [화자1], [화자2] 라벨링
  ↓
통합 SRT 생성 → stereo.srt
  ↓
LLM 요약 → stereo_요약.txt
  ↓
output/ 저장 + processed/ 이동
```

## 🔧 설정 파일

### config/default_prompt.txt
LLM 요약에 사용되는 프롬프트 템플릿

### config/dictionary.txt
용어 사전 (지역명, 병원명, 전문용어)

## ⚙️ GPU 메모리 관리

**VRAM 12GB 환경**:
- Whisper: 2-4GB
- Ollama: 4-6GB
- 여유 공간: 2-4GB

**처리 전략**:
1. Whisper 처리 → GPU 메모리 해제
2. Ollama 요약 시작
3. 순차 처리로 메모리 안정성 확보

## 🐛 트러블슈팅

### 1. Redis 연결 실패
```bash
# Redis 실행 확인
redis-cli ping
# 응답: PONG
```

### 2. Ollama 연결 실패
```bash
# Ollama 상태 확인
ollama list
```

### 3. GPU 메모리 부족
```python
# settings 수정
GPU_MEMORY_RESERVE_MB=2048  # 더 많은 여유 공간 확보
```

### 4. Celery Worker 에러 (Windows)
```bash
# --pool=solo 옵션 필수 (Windows gevent 이슈)
celery -A app.tasks.celery_app worker --pool=solo
```

## 📝 로그 확인

```bash
# 로그 파일 위치
logs/app.log

# 실시간 로그 확인 (Linux/Mac)
tail -f logs/app.log

# Windows PowerShell
Get-Content logs/app.log -Wait
```

## 🧪 테스트

```bash
# 테스트 실행
pytest tests/
```

## 📊 Phase 1 완료 상태

✅ 프로젝트 구조 생성
✅ FastAPI REST API
✅ Celery + Redis 설정
✅ Whisper STT 서비스
✅ Ollama LLM 요약
✅ Mono 파일 처리
✅ Stereo 파일 처리 (채널 분리)
✅ 에러 핸들링

## 🚀 다음 단계 (Phase 2-4)

- [ ] Watchdog 파일 자동 감지
- [ ] Tkinter GUI
- [ ] 병렬 처리 최적화
- [ ] PyInstaller EXE 빌드
- [ ] 설치 패키지 생성

## 📄 라이선스

내부 프로젝트 (비공개)
# aicc
