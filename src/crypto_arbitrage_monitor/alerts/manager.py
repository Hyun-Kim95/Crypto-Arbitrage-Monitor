"""
수익률 조건 충족 시 소리 + 텔레그램 알림
"""

import asyncio
import logging
import platform
import sys
from typing import Optional

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


def _format_telegram_message(opp: ArbitrageOpportunity) -> str:
    """PRD 예시 형식"""
    return (
        "[차익 거래 기회 발생]\n\n"
        f"코인: {opp.symbol}\n"
        f"거래소: {opp.exchange_buy.value} → {opp.exchange_sell.value}\n"
        f"수익률: {opp.spread_percent:.2f}%\n\n"
        f"{opp.exchange_buy.value} 매수가: {opp.bid_price:,.0f}\n"
        f"{opp.exchange_sell.value} 매도가: {opp.ask_price:,.0f}"
    )


async def _send_telegram(token: str, chat_id: str, text: str) -> bool:
    try:
        from telegram import Bot
        bot = Bot(token=token)
        await bot.send_message(chat_id=chat_id, text=text)
        return True
    except Exception as e:
        logger.warning("텔레그램 전송 실패: %s", e)
        return False


class AlertManager:
    def __init__(
        self,
        sound_enabled: bool = True,
        telegram_enabled: bool = False,
        telegram_token: str = "",
        telegram_chat_id: str = "",
    ) -> None:
        self.sound_enabled = sound_enabled
        self.telegram_enabled = telegram_enabled and bool(telegram_token and telegram_chat_id)
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id

    def trigger_sync(self, opportunity: ArbitrageOpportunity) -> None:
        """필터 통과한 기회 발생 시 호출 (소리). 텔레그램은 비동기로 실행."""
        if self.sound_enabled:
            _beep_sound()
        if self.telegram_enabled:
            text = _format_telegram_message(opportunity)
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_send_telegram(self.telegram_token, self.telegram_chat_id, text))
            except RuntimeError:
                asyncio.run(_send_telegram(self.telegram_token, self.telegram_chat_id, text))

    async def trigger(self, opportunity: ArbitrageOpportunity) -> None:
        """비동기 컨텍스트에서 알림 (소리 + 텔레그램)"""
        if self.sound_enabled:
            _beep_sound()
        if self.telegram_enabled:
            text = _format_telegram_message(opportunity)
            await _send_telegram(self.telegram_token, self.telegram_chat_id, text)
