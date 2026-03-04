"""
설정 스키마 및 로드
- 최소 수익률, 알림 설정, 모니터링 코인 등
"""

from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """앱 전역 설정"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 수익률 필터
    min_spread_percent: float = Field(default=0.5, description="최소 수익률(%) - 이 이상만 표시")
    min_trade_amount_usd: Optional[float] = Field(default=None, description="최소 거래금액(USD), None이면 미적용")
    # 환율 (USDT ≒ USD 로 가정하고 KRW로 변환할 때 사용)
    usd_krw_rate: float = Field(default=1300.0, description="USDT→KRW 환산에 사용할 기본 USD/KRW 환율")
    usd_krw_auto: bool = Field(default=True, description="True면 거래소 시세로 USD/KRW 환율을 자동 갱신")
    usd_krw_refresh_sec: int = Field(default=30, description="환율 자동 갱신 주기(초)")

    # 모니터링 코인 (비어 있으면 전체, 있으면 해당 코인만)
    monitor_symbols: List[str] = Field(default_factory=list, description="모니터링할 심볼 목록, 빈 리스트=전체")

    # 알림
    alert_sound_enabled: bool = Field(default=True, description="소리 알림 사용 여부")
    telegram_enabled: bool = Field(default=False, description="텔레그램 알림 사용 여부")
    telegram_bot_token: str = Field(default="", description="텔레그램 봇 토큰")
    telegram_chat_id: str = Field(default="", description="텔레그램 채팅 ID")

    # 로깅
    log_level: str = Field(default="INFO", description="로그 레벨")
    log_dir: Optional[Path] = Field(default=None, description="로그 파일 디렉터리, None이면 콘솔만")


def get_settings() -> Settings:
    """설정 싱글톤 로드"""
    return Settings()
