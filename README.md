#AICC - 음성 파일 자동 처리 시스템

음성 파일 자동 처리 시스템

## 📋 시스템 개요

**배포 환경**: Windows 온프레미스 폐쇄망 (인터넷 불가)

**처리 흐름**:
```
input/
  ↓ (자동 감지)
WAV 파일 → STT (Whisper) → 화자 분리 (Pyannote) → SRT 생성
  ↓
LLM 요약 (Ollama)
  ↓
output/ (SRT + 요약.txt)
  ↓
processed/ (원본 이동)
```

**파일 타입별 처리**:
- **Mono**: Whisper STT → SRT 생성 → LLM 요약
- **Stereo**: Pyannote 화자 분리 + Whisper STT → 화자 라벨링 SRT → LLM 요약

## 🛠️ 기술 스택

| 계층 | 기술 | 버전 | 용도 |
|------|------|------|------|
| Web API | FastAPI + Uvicorn | 0.121+ | REST API 서버 |
| Task Queue | Celery + Redis | 5.5+ | 비동기 작업 처리 |
| STT | faster-whisper | 1.2+ | Whisper large-v3-turbo |
| Speaker Diarization | pyannote.audio | 4.0.1 | 화자 분리 |
| LLM | Ollama | - | HyperCLOVAX-SEED-1.5B |
| Deep Learning | PyTorch | 2.9.0 | GPU 가속 |
| Python | 3.11+ | - | 런타임 |

## 📦 설치 방법

### 1. 사전 요구사항

**Windows**:
- Windows 10/11 또는 Windows Server 2019/2022
- NVIDIA GPU (VRAM 12GB 이상 권장)
- CUDA 12.x 설치

**Mac**:
- macOS 11+ (Apple Silicon 또는 Intel)
- 16GB+ RAM 권장

**Linux**:
- Ubuntu 20.04+ / CentOS 8+
- NVIDIA GPU (선택사항)

### 2. 환경 설정

```bash
# 1. 프로젝트 클론
git clone <repository>
cd aicc

# 2. 가상환경 생성 및 활성화
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate

# 3. 패키지 설치
pip install -r requirements.txt

# 또는 uv 사용 (더 빠름)
uv pip install -r requirements.txt
```

### 3. Redis 설치

**Mac (Homebrew)**:
```bash
brew install redis
brew services start redis
```

**Windows**:
- [Redis for Windows](https://github.com/redis-windows/redis-windows/releases) 다운로드
- 또는 WSL2에서 Redis 실행

**Linux**:
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

**Docker** (모든 플랫폼):
```bash
docker run -d -p 6379:6379 redis:latest
```

### 4. Ollama 설치 및 모델 다운로드

```bash
# 1. Ollama 설치 (https://ollama.ai)

# 2. 모델 다운로드
ollama pull joonoh/HyperCLOVAX-SEED-Text-Instruct-1.5B:latest

# 3. Ollama 서버 시작
ollama serve
```

### 5. Hugging Face 토큰 설정

Pyannote 화자 분리 모델 사용을 위해 Hugging Face 토큰이 필요합니다:

1. https://huggingface.co/settings/tokens 에서 토큰 생성
2. `.env` 파일에 추가:

```bash
cp .env.example .env
# .env 파일 편집
HF_TOKEN=your_huggingface_token_here
```

### 6. 필수 디렉토리 생성

자동으로 생성되지만 수동으로도 가능:
```bash
mkdir -p data/input data/output data/processed data/error logs
```

## 🚀 실행 방법

### 통합 실행 스크립트

**Mac/Linux**:
```bash
chmod +x run_services.sh
./run_services.sh
```

**Windows**:
```batch
run_services.bat
```

### 개별 서비스 실행

**1. Redis 시작** (별도 터미널)
```bash
redis-server
# 또는 Mac: brew services start redis
```

**2. Ollama 시작** (별도 터미널)
```bash
ollama serve
```

**3. Celery Worker 시작** (별도 터미널)
```bash
# 가상환경 활성화 필수
source .venv/bin/activate  # Mac/Linux
# .venv\Scripts\activate   # Windows

celery -A app.tasks.celery_app worker --loglevel=info --pool=solo
```

**4. FastAPI 서버 시작** (별도 터미널)
```bash
# 가상환경 활성화 필수
source .venv/bin/activate  # Mac/Linux
# .venv\Scripts\activate   # Windows

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 서비스 확인

```bash
# Redis 확인
redis-cli ping  # 응답: PONG

# Ollama 확인
ollama list

# API 확인
curl http://localhost:8000/
curl http://localhost:8000/api/v1/health
```

## 📁 디렉토리 구조

```
aicc/
├── app/
│   ├── api/              # REST API 엔드포인트
│   │   └── routes.py     # 파일 업로드, 상태 조회
│   ├── core/             # 설정 및 환경 변수
│   │   └── config.py     # Pydantic Settings
│   ├── tasks/            # Celery 태스크
│   │   ├── celery_app.py # Celery 설정
│   │   └── audio_task.py # 오디오 처리 태스크
│   ├── services/         # 비즈니스 로직
│   │   ├── whisper_service.py     # STT
│   │   ├── diarization_service.py # 화자 분리
│   │   └── ollama_service.py      # LLM 요약
│   └── utils/            # 유틸리티
│       └── audio_utils.py # 오디오 처리
├── config/               # 설정 파일
│   ├── default_prompt.txt # LLM 프롬프트 템플릿
│   └── dictionary.txt    # 용어 사전
├── data/
│   ├── input/           # WAV 입력 (여기에 파일 넣기)
│   ├── output/          # SRT + 요약 출력
│   ├── processed/       # 처리 완료 WAV
│   └── error/           # 에러 파일 + 로그
├── logs/                # 애플리케이션 로그
├── tests/               # 테스트 스크립트
├── .env                 # 환경 변수 (gitignore)
├── pyproject.toml       # 프로젝트 설정
└── README.md
```

## 💻 API 사용법

### API 문서

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Base URL**: http://localhost:8000/api/v1

### 주요 엔드포인트

#### 1. Health Check
```bash
GET /api/v1/health

응답:
{
  "status": "ok",
  "redis_connected": true,
  "ollama_available": true,
  "gpu_available": true,
  "gpu_memory_free_mb": 8192
}
```

#### 2. 파일 업로드
```bash
POST /api/v1/upload
Content-Type: multipart/form-data

파라미터:
  file: WAV 파일 (Mono 또는 Stereo)

응답:
{
  "task_id": "uuid",
  "filename": "example.wav",
  "status": "pending",
  "message": "파일이 업로드되어 처리 대기 중입니다."
}
```

**curl 예제**:
```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -F "file=@data/교통약자음성파일_테스트용/Mono_example.wav"
```

#### 3. 작업 상태 조회
```bash
GET /api/v1/task/{task_id}

응답:
{
  "task_id": "uuid",
  "filename": "example.wav",
  "status": "completed",  # pending, processing, completed, failed
  "result": {
    "srt_path": "output/example.srt",
    "summary_path": "output/example_요약.txt"
  }
}
```

## 🎯 처리 흐름 상세

### Mono 파일 처리

```
mono.wav (input/)
  ↓
Whisper STT
  ↓ (GPU 메모리 해제)
mono.srt 생성
  ↓
텍스트 추출
  ↓
LLM 요약 (Ollama)
  ↓
output/mono.srt
output/mono_요약.txt
  ↓
processed/mono.wav (원본 이동)
```

### Stereo 파일 처리 (화자 분리)

```
stereo.wav (input/)
  ↓
Pyannote 화자 분리 (SPEAKER_00, SPEAKER_01, ...)
  ↓ (GPU 메모리 해제)
Whisper STT
  ↓ (GPU 메모리 해제)
화자 정보 + STT 결과 병합
  ↓
[SPEAKER_00] 텍스트
[SPEAKER_01] 텍스트
  ↓
LLM 요약 (Ollama)
  ↓
output/stereo.srt
output/stereo_요약.txt
  ↓
processed/stereo.wav (원본 이동)
```

**화자 라벨링 예시**:
```srt
1
00:00:01,940 --> 00:00:09,060
[SPEAKER_00] 팀장님 안 바쁘시면 잠깐 오시면 안 돼요?

2
00:00:09,100 --> 00:00:12,340
[SPEAKER_01] 네, 지금 가겠습니다.
```

## 🔧 설정 파일

### .env 환경 변수

```bash
# Redis 설정
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Ollama 설정
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=joonoh/HyperCLOVAX-SEED-Text-Instruct-1.5B:latest
OLLAMA_TIMEOUT=120

# Whisper 설정
WHISPER_MODEL=dropbox-dash/faster-whisper-large-v3-turbo
WHISPER_DEVICE=cpu  # cpu, cuda, mps (Apple Silicon)
WHISPER_COMPUTE_TYPE=int8

# Pyannote (화자 분리) 설정
HF_TOKEN=your_huggingface_token_here

# GPU 설정
GPU_MEMORY_RESERVE_MB=1024

# 로그 설정
LOG_LEVEL=INFO
```

### config/default_prompt.txt

LLM 요약에 사용되는 프롬프트 템플릿:

```
아래 대화 내용을 한두 문장으로 간단히 요약해주세요.
대화 내용 그대로를 정확히 요약하세요.

{dictionary_section}
대화 내용:
{transcript_text}

위 대화의 핵심 내용 요약:
```

### config/dictionary.txt

용어 사전 (지역명, 병원명, 전문용어):

```
# 지역명
용문 - 경기도 양평군 용문면
양동 - 경기도 양평군 양평읍 양동리

# 병원/시설명
양동고려의원 - 양평군 양평읍 소재 의료기관

# 서비스 관련 용어
교통약자이동지원센터 - 장애인, 고령자 등을 위한 차량 배차 서비스
행복콜 - 교통약자 차량 배차 서비스 콜센터명
당일콜 - 예약 없이 당일 즉시 배차 요청
```

## ⚙️ GPU 메모리 관리

**VRAM 12GB 환경 예시**:
- Whisper: 2-4GB
- Pyannote: 2-3GB
- Ollama (1.5B 모델): 2-3GB
- 여유 공간: 2-4GB

**처리 전략** (순차 처리로 메모리 안정성 확보):
1. Pyannote 화자 분리 실행
2. GPU 메모리 해제
3. Whisper STT 실행
4. GPU 메모리 해제
5. Ollama LLM 요약 실행

**CPU 전용 환경**:
```bash
# .env 파일 수정
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

## 🐛 트러블슈팅

### 1. Redis 연결 실패

```bash
# Redis 실행 확인
redis-cli ping
# 응답: PONG

# Redis 시작 (Mac)
brew services start redis

# Redis 시작 (Linux)
sudo systemctl start redis
```

### 2. Ollama 연결 실패

```bash
# Ollama 상태 확인
ollama list

# Ollama 서버 시작
ollama serve

# 모델 다운로드 확인
ollama pull joonoh/HyperCLOVAX-SEED-Text-Instruct-1.5B:latest
```

### 3. Pyannote HF_TOKEN 에러

```
ValueError: Hugging Face 토큰이 필요합니다.
```

**해결 방법**:
1. https://huggingface.co/settings/tokens 에서 토큰 생성
2. `.env` 파일에 `HF_TOKEN=your_token` 추가
3. Celery Worker 재시작

### 4. GPU 메모리 부족

```bash
# .env 파일 수정
GPU_MEMORY_RESERVE_MB=2048  # 더 많은 여유 공간 확보

# 또는 CPU 사용
WHISPER_DEVICE=cpu
```

### 5. Celery Worker 에러 (Windows)

```bash
# --pool=solo 옵션 필수 (Windows gevent 이슈)
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo
```

### 6. Apple Silicon (M1/M2) MPS 사용

```bash
# .env 파일 수정
WHISPER_DEVICE=mps
WHISPER_COMPUTE_TYPE=float16
```

## 📝 로그 확인

```bash
# 로그 파일 위치
logs/app.log

# 실시간 로그 확인 (Mac/Linux)
tail -f logs/app.log

# Windows PowerShell
Get-Content logs/app.log -Wait -Tail 50

# Celery Worker 로그 (별도 터미널에서 실행 시)
# 터미널에 직접 출력됨
```

## 🧪 테스트

### 개발 환경 테스트

```bash
# 가상환경 활성화
source .venv/bin/activate

# 개별 컴포넌트 테스트
python test_whisper.py
python test_diarization.py
python test_memory.py

# 전체 파이프라인 테스트
python test_full_pipeline.py
```

### API 테스트

```bash
# Health check
curl http://localhost:8000/api/v1/health

# 파일 업로드
curl -X POST "http://localhost:8000/api/v1/upload" \
  -F "file=@data/교통약자음성파일_테스트용/Mono_example.wav"
```

## 📊 현재 완료 상태

### ✅ Phase 1 완료
- 프로젝트 구조 생성
- FastAPI REST API
- Celery + Redis 비동기 작업 처리
- Whisper STT 서비스 (faster-whisper)
- Pyannote 화자 분리 (Speaker Diarization)
- Ollama LLM 요약
- Mono 파일 처리
- Stereo 파일 처리 (화자 라벨링)
- 에러 핸들링 및 로그
- 로컬 환경 테스트 완료

### 🚀 다음 단계 (Phase 2-4)

- [ ] Watchdog 파일 자동 감지
- [ ] Docker 이미지 최적화
- [ ] Tkinter GUI 애플리케이션
- [ ] 병렬 처리 최적화 (GPU 사용률 극대화)
- [ ] PyInstaller EXE 빌드 (Windows 배포용)
- [ ] 오프라인 설치 패키지 생성 (폐쇄망 대응)
- [ ] Windows 자동 실행 설정

## 📈 성능 벤치마크

**테스트 환경**: Mac M1 Pro, 16GB RAM

| 파일 타입 | 파일 크기 | 길이 | 처리 시간 | 비고 |
|----------|---------|------|----------|------|
| Mono | 477KB | 30초 | ~44초 | Whisper + LLM |
| Stereo | 4.4MB | 2분 30초 | ~60초 | Pyannote + Whisper + LLM |

## 🔒 보안 고려사항

- `.env` 파일은 Git에 커밋하지 않음 (gitignore)
- HF_TOKEN은 환경 변수로 관리
- API 인증은 추후 추가 예정
- 폐쇄망 환경에서는 외부 네트워크 접근 불필요

## 📄 라이선스

내부 프로젝트 (비공개)

## 🙏 기술 스택 크레딧

- [FastAPI](https://fastapi.tiangolo.com/)
- [Celery](https://docs.celeryq.dev/)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [pyannote.audio](https://github.com/pyannote/pyannote-audio)
- [Ollama](https://ollama.ai/)
