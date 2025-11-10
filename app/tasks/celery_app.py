"""
Celery 애플리케이션 설정
"""
from celery import Celery
from app.core.config import settings

# Celery 앱 생성
celery_app = Celery(
    "voicecom_ai",
    broker=settings.get_celery_broker_url(),
    backend=settings.get_celery_result_backend(),
)

# Celery 설정
celery_app.conf.update(
    # 작업 설정
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,

    # Worker 설정
    worker_prefetch_multiplier=1,  # 한 번에 1개 작업만 가져옴 (GPU 메모리 관리)
    worker_max_tasks_per_child=50,  # Worker 재시작 주기 (메모리 누수 방지)

    # 작업 타임아웃 설정
    task_soft_time_limit=600,  # 10분 (소프트 타임아웃)
    task_time_limit=900,  # 15분 (하드 타임아웃)

    # 결과 설정
    result_expires=3600,  # 결과 1시간 후 만료

    # 재시도 설정
    task_acks_late=True,  # 작업 완료 후 ACK
    task_reject_on_worker_lost=True,  # Worker 종료 시 작업 거부
)

# 작업 자동 검색 (include 명시)
celery_app.autodiscover_tasks(["app.tasks"], force=True)

# Task 명시적 등록
celery_app.conf.update(
    imports=["app.tasks.audio_task"],
)
