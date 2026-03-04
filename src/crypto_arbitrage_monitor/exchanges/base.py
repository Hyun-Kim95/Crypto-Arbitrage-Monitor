"""
거래소 WebSocket 공통 인터페이스 및 재연결 로직
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Callable, Optional

from crypto_arbitrage_monitor.models import ExchangePrice

PriceCallback = Callable[[ExchangePrice], None]

logger = logging.getLogger("crypto_arbitrage_monitor.exchanges")


class ExchangeWsClient(ABC):
    """거래소 WebSocket 클라이언트 공통 베이스"""

    def __init__(
        self,
        on_price: PriceCallback,
        symbols: list[str],
        reconnect_delay: float = 5.0,
        ping_interval: float = 30.0,
    ):
        self.on_price = on_price
        self.symbols = symbols
        self.reconnect_delay = reconnect_delay
        self.ping_interval = ping_interval
        self._task: Optional[asyncio.Task] = None
        self._running = False

    @abstractmethod
    async def _run_ws(self) -> None:
        """WebSocket 연결 및 메시지 수신 루프 (구현체에서 정의)"""
        ...

    async def start(self) -> None:
        """백그라운드에서 WebSocket 실행 (재연결 포함)"""
        self._running = True
        while self._running:
            try:
                await self._run_ws()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("WebSocket 오류, %s초 후 재연결: %s", self.reconnect_delay, e)
            if self._running:
                await asyncio.sleep(self.reconnect_delay)

    def stop(self) -> None:
        self._running = False
