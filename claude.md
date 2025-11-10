# Voicecom 음성 파일 자동 처리 시스템

## 📋 프로젝트 개요

**목적**: WAV 음성 파일을 자동으로 텍스트 변환(STT) 후 LLM 기반 요약 생성

**배포 환경**: Windows 온프레미스 폐쇄망 (인터넷 불가)

**핵심 기능**: Whisper → SRT 생성 → LLM 요약 → 자동 파일 관리

---

## 🎯 핵심 처리 흐름

### 1. 기본 프로세스

```
WAV 파일 입력 (input/)
    ↓
Whisper STT → SRT 생성
    ↓
LLM 분석 → 요약 TXT 생성
    ↓
결과물 저장 (output/) + 원본 이동 (processed/)

```

### 2. 파일 타입별 분기 처리

### **Case 1: Mono 파일**

```
mono.wav (input/)
    ↓
mono.srt 생성
    ↓
LLM 요약
    ↓
output/mono.srt
output/mono_요약.txt
processed/mono.wav (원본 이동)

```

### **Case 2: Stereo 파일 (최대 2채널)**

```
stereo.wav (input/)
    ↓
채널 분리: stereo_1ch.wav + stereo_2ch.wav
    ↓
각 채널별 SRT 생성
    ├─ stereo_1ch.srt (화자1)
    └─ stereo_2ch.srt (화자2)
    ↓
시간 정보 기반으로 통합
    ↓
stereo.srt 생성 (화자 라벨링: [화자1], [화자2])
    ↓
LLM 요약
    ↓
output/stereo.srt
output/stereo_요약.txt
processed/stereo.wav (원본 이동)
임시 파일 삭제 (stereo_1ch.srt, stereo_2ch.srt)

```

### 3. 에러 처리

- 처리 실패 시: 원본 WAV + 에러 로그를 `error/` 폴더로 이동

---

## 🤖 AI 모델 구성

### STT 모델

- **사용 모델**: `openai/whisper-large-v3-turbo`
- **출력 형식**: SRT (시간 정보 포함)

### LLM 요약 모델

| 용도 | 모델 | 파라미터 크기 | 비고 |
| --- | --- | --- | --- |
| 현재 사용 중 | `konantech/Konan-LLM-OND` | 4B | - |
| 경량 후보 | `LFM2` | 350M~2.6B | 성능 검증 필요 |
| 최대 고려 | `skt a.x 4.0-light` | 7B | 최대 허용 크기 |
| 제외 | `EXAONE` | - | 라이센스 이슈 |

---

## 📝 프롬프트 시스템

### 기본 프롬프트 템플릿

```
다음은 차량 배차 서비스 콜센터 상담원과 고객 간의 전화 대화입니다.
상담원 관점에서 핵심 내용만 간단히 정리해주세요.

{dictionary_section}

대화 내용:
{transcript_text}

정리 요구사항:
- 불필요한 디테일 제외
- 한두 문장으로 간단히 요약
- 실제 사람이 메모하듯 짧고 깔끔하게
- 문맥에 맞게 어색한 표현이나 단어는 자연스럽게 보정
- 위 용어사전에 있는 지역명이나 전문용어가 대화에 나오면 정확한 표현으로 수정하여 요약

요약:

```

### 용어 사전 기능

- **위치**: `dictionary_section` 변수에 TXT 파일 내용 삽입
- **목적**:
    - 지역명 정확도 향상 (예: "양동고려의원", "용문")
    - 도메인 특화 용어 보정
    - Whisper STT 오류 보완

### 프롬프트 관리 기능

- 고객사 관리자가 GUI를 통해 프롬프트 수정 가능
- 수정 후 서비스 재시작 시 새 프롬프트 적용
- 용어 사전 파일도 별도 관리 가능

---

## 🖥️ GUI 애플리케이션 설계

### 기술 스택

- **빌드 도구**: PyInstaller
- **UI 프레임워크**: Tkinter
- **실행 파일**: `voicecom_ai.exe`

### UI 구성 (미니멀리즘)

```
┌─────────────────────────────────┐
│  음성 처리 시스템 v1.0          │
├─────────────────────────────────┤
│  [●] 서비스 실행 중              │
│                                 │
│  처리 현황:                     │
│  - 대기 중: 2개                 │
│  - 처리 완료: 15개              │
│                                 │
│  [프롬프트 수정]  [서비스 재시작] │
└─────────────────────────────────┘

```

### 주요 기능

1. **프롬프트 편집기**: 별도 창으로 멀티라인 텍스트 편집
2. **용어 사전 관리**: TXT 파일 직접 편집 인터페이스
3. **상태 모니터링**: 실시간 처리 현황 표시
4. **로그 최소화**: 상세 로그는 별도 파일로 관리

---

## ⚡ 성능 최적화

### 병렬 처리 설계

- **목표**: GPU 리소스 효율적 활용
- **고려 사항**:
    - Whisper 최대 GPU 사용량 측정
    - LLM 최대 GPU 사용량 측정
    - 동시 처리 가능한 파일 수 계산 (VRAM 12GB 기준)
    - 큐 시스템 구현 (대기열 관리)

### 처리 우선순위

```
input/ 폴더 모니터링
    ↓
새 파일 감지
    ↓
GPU 가용 메모리 확인
    ↓
병렬 처리 슬롯 할당
    ↓
처리 시작

```

---

## 📦 배포 및 설치

### 시스템 요구사항

| 항목 | 사양 |
| --- | --- |
| **OS** | Windows 10/11, Windows Server 2019/2022 |
| **GPU** | NVIDIA RTX / A시리즈 (CUDA 12.x 지원) |
| **VRAM** | 최소 12GB (테스트 환경 기준) |
| **인터넷** | 불필요 (완전 폐쇄망 대응) |

### 설치 패키지 구성

```
voicecom_ai_installer/
├── voicecom_ai.exe              # 메인 실행 파일
├── install.bat                  # 자동 설치 스크립트
├── requirements/
│   ├── nvidia_driver.exe        # NVIDIA 드라이버
│   ├── docker_desktop.exe       # Docker Desktop
│   └── cuda_toolkit.exe         # CUDA 12.x
├── docker_images/
│   ├── whisper_service.tar      # Whisper 서비스 이미지
│   └── llm_service.tar          # LLM 서비스 이미지
├── config/
│   ├── default_prompt.txt       # 기본 프롬프트
│   └── dictionary.txt           # 기본 용어 사전
└── docs/
    ├── 설치_가이드.pdf
    └── 사용자_매뉴얼.pdf

```

### 자동 실행 설정

**방법 1: 시작 프로그램 등록**

```
C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp\
→ voicecom_ai.exe 바로가기 생성

```

**방법 2: 작업 스케줄러**

- 트리거: 시스템 시작 시
- 동작: `voicecom_ai.exe` 실행
- 권한: 시스템 계정으로 실행

### 설치 프로세스

1. NVIDIA 드라이버 설치 확인/설치
2. Docker Desktop 설치
3. Docker 이미지 로드 (`docker load < whisper_service.tar`)
4. 폴더 구조 자동 생성 (input, output, processed, error)
5. 서비스 자동 시작 설정
6. 초기 구성 테스트

---

## 📂 폴더 구조

```
voicecom_ai/
├── input/          # WAV 파일 입력 (자동 감지)
├── output/         # SRT + 요약 TXT 출력
├── processed/      # 처리 완료된 WAV 보관
├── error/          # 에러 발생 파일 + 로그
├── config/         # 프롬프트 + 용어 사전
└── logs/           # 시스템 로그

```

---

## 📊 출력 예시

### Stereo 파일 처리 결과

**Input**: `stereo.wav`

**Output 1**: `stereo.srt`

```
[화자1] 안녕하세요. 행복콜입니다. 네 안녕하세요. 오늘 예약 좀 하려고 하는데요.
김순엽. 말씀드리면 돼요?

[화자2] 네 어디 가시는지 알려주시면 돼요. 양동고려의원. 양동고려의원인데
저희가 예약은 안 되시고 콜센터 부르는 것처럼 당일로 지금 즉시 콜로 되고
있는 거거든요...

```

**Output 2**: `stereo_요약.txt`

```
고객이 김순엽 씨의 예약을 요청했으나, 현재 예약은 불가능하고 당일 콜택시
서비스만 제공됨. 배차가 용문과 양동 지역에 가능하며, 도착 시간은 차량 위치에
따라 달라짐. 고객은 30분 후에 다시 전화할 예정이며, 현재 상황에 대한 이해를 구함.

```

### Mono 파일 처리 결과

**Input**: `mono.wav`

**Output 1**: `mono.srt`

```
여보세요. 여기 양평에 용문맨에 사는데요.
교통약자이동지원센터라고 해가지고 전화하라고 그래서 뭐 뭐 필요한지 나 83세인데요.
네 저희 쪽 차량 그니까 저희 쪽에 등록 원하시는 거예요? 이용하고 계시는 거예요?...

```

**Output 2**: `mono_요약.txt`

```
상담원은 고객이 83세 교통약자로서 차량 배차 서비스를 등록하기 위해 필요한
서류와 절차를 안내합니다. 고객은 5급 장애 진단서를 발급받아야 하며, 진단서에는
'대중교통이 어렵다'는 내용과 치료 기간이 명시되어야 합니다. 서류는 읍면사무소에서
받을 수 있으며, 등록 신청서와 진단서를 팩스나 메일로 제출해야 합니다.
팩스 번호는 031-774-5809입니다.

```

---

## 🔧 기술 구현 핵심 사항

### 1. Docker 기반 서비스 구조

```yaml
services:
  whisper:
    image: whisper_service
    volumes:
      - ./input:/input
      - ./output:/output
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]

  llm:
    image: llm_service
    volumes:
      - ./output:/output
      - ./config:/config
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]

```

### 2. 파일 감지 및 처리 로직

```python
# 의사 코드
while True:
    wav_files = scan_input_folder()
    for wav_file in wav_files:
        if is_mono(wav_file):
            process_mono(wav_file)
        else:
            process_stereo(wav_file)

```

### 3. 에러 핸들링

- 모든 예외는 로그 파일에 기록
- 실패한 파일은 `error/` 폴더로 격리
- 에러 타입별 분류 (STT 실패, LLM 실패, 파일 손상 등)

---

## 🚀 개발 우선순위

### Phase 1: 기본 기능 (MVP)

- [ ]  Mono WAV 처리 파이프라인
- [ ]  Stereo WAV 채널 분리 및 병합
- [ ]  LLM 요약 기능
- [ ]  기본 폴더 구조 및 파일 관리

### Phase 2: GUI 및 설정

- [ ]  Tkinter GUI 개발
- [ ]  프롬프트 편집 기능
- [ ]  용어 사전 관리 인터페이스
- [ ]  서비스 제어 (시작/중지/재시작)

### Phase 3: 최적화

- [ ]  병렬 처리 구현
- [ ]  GPU 메모리 효율 관리
- [ ]  처리 대기열 시스템

### Phase 4: 배포 준비

- [ ]  PyInstaller 빌드 설정
- [ ]  오프라인 설치 패키지 구성
- [ ]  자동 시작 스크립트
- [ ]  사용자 문서 작성

---

## 📝 테스트 데이터

- **제공된 샘플**: 교통약자음성파일_테스트용.zip
    
    [교통약자음성파일_테스트용.zip](attachment:a983941f-de14-49d1-be24-4a427946b40e:교통약자음성파일_테스트용.zip)
    
    - Mono 파일: 3개
    - Stereo 파일: 3개

---

## ✅ 체크리스트

### 설치 시

- [ ]  NVIDIA 드라이버 설치 확인
- [ ]  Docker Desktop 설치 및 실행
- [ ]  Docker 이미지 로드 완료
- [ ]  폴더 구조 생성 확인
- [ ]  자동 시작 설정 완료
- [ ]  테스트 파일로 검증

### 운영 시

- [ ]  Input 폴더 자동 감지 작동
- [ ]  Mono/Stereo 자동 분기 처리
- [ ]  SRT 파일 정상 생성
- [ ]  요약 품질 확인
- [ ]  에러 핸들링 정상 작동
- [ ]  GPU 사용률 모니터링