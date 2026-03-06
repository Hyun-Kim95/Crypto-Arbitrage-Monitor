"""
수익률 조건 충족 시 소리 알림만 수행
- 소리는 최대 1초에 한 번만 재생
"""

import logging
import platform
import sys
import time

from crypto_arbitrage_monitor.models import ArbitrageOpportunity

logger = logging.getLogger("crypto_arbitrage_monitor.alerts")


def _beep_sound() -> None:
    """시스템 비프 (Windows: \x07, 그 외: bell)"""
    try:
        if platform.system() == "Windows":
            import ctypes

            ctypes.windll.kernel32.Beep(750, 200)  # 750Hz, 200ms
        else:
            sys.stdout.write("\a")
            sys.stdout.flush()
    except Exception as e:
        logger.debug("소리 알림 실패: %s", e)


SOUND_COOLDOWN_SEC = 1.0  # 소리 알림 최소 간격(초)


class AlertManager:
    def __init__(self, sound_enabled: bool = True) -> None:
        self.sound_enabled = sound_enabled
        self._last_sound_time: float = 0.0

    def _maybe_beep(self) -> None:
        if not self.sound_enabled:
            return
        now = time.monotonic()
        if now - self._last_sound_time >= SOUND_COOLDOWN_SEC:
            self._last_sound_time = now
            _beep_sound()

    def trigger_sync(self, opportunity: ArbitrageOpportunity) -> None:  # noqa: ARG002
        """필터 통과한 기회 발생 시 호출 (소리)."""
        self._maybe_beep()

    async def trigger(self, opportunity: ArbitrageOpportunity) -> None:  # noqa: ARG002
        """비동기 컨텍스트에서 알림 (소리만)."""
        self._maybe_beep()
