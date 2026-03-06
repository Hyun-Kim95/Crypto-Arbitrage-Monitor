"""
설정 화면: 현재 설정 출력 및 안내
- 최소 수익률, 알림 설정, 모니터링 코인
"""

from crypto_arbitrage_monitor.config import Settings


def print_settings(settings: Settings) -> None:
    """현재 설정을 콘솔에 출력"""
    print("=== 설정 ===")
    print(f"  최소 수익률: {settings.min_spread_percent}%")
    print(f"  최소 거래금액(USD): {settings.min_trade_amount_usd or '미적용'}")
    print(f"  모니터링 코인: {settings.monitor_symbols or '전체'}")
    print(f"  소리 알림: {'ON' if settings.alert_sound_enabled else 'OFF'}")
    print("  (변경 시 .env 파일 수정 또는 환경 변수 설정)")
    print()
