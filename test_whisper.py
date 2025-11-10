"""
Whisper STT 테스트 스크립트
"""
from faster_whisper import WhisperModel
import time

# 모델 크기 (tiny, base, small, medium, large-v3 등)
model_size = "tiny"  # 빠른 테스트를 위해 tiny 모델 사용

print(f"🔄 Whisper {model_size} 모델 로드 중...")
start = time.time()

# CPU 모드로 로드 (faster-whisper는 MPS 미지원)
model = WhisperModel(
    model_size,
    device="cpu",
    compute_type="int8"  # Mac에서 int8 사용
)

load_time = time.time() - start
print(f"✅ 모델 로드 완료 ({load_time:.2f}초)")

# 테스트 문장 (한글)
print("\n🎤 음성 인식 테스트를 위해서는 WAV 파일이 필요합니다.")
print("테스트용 WAV 파일을 data/input/ 폴더에 넣어주세요.")
print("\n모델 로드는 성공했습니다!")
