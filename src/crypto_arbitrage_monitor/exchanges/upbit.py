"""
업비트 WebSocket 호가 스트림
- Endpoint: wss://api.upbit.com/websocket/v1
- type: orderbook, codes: ["KRW-BTC", ...]
"""

import asyncio
import json
import logging
from datetime import datetime

import websockets
from websockets.exceptions import ConnectionClosed

from crypto_arbitrage_monitor.exchanges.base import ExchangeWsClient, PriceCallback
from crypto_arbitrage_monitor.models import ExchangeId, ExchangePrice, normalize_symbol

logger = logging.getLogger("crypto_arbitrage_monitor.exchanges.upbit")

UPBIT_WS_URL = "wss://api.upbit.com/websocket/v1"

# 정규화 심볼 → 업비트 코드
TO_UPBIT_CODE = {"BTC": "KRW-BTC", "ETH": "KRW-ETH", "USDT": "KRW-USDT", "XRP": "KRW-XRP"}


class UpbitWsClient(ExchangeWsClient):
    def __init__(self, on_price: PriceCallback, symbols: list[str], **kwargs):
        codes = [TO_UPBIT_CODE.get(s, f"KRW-{s}") for s in symbols]
        self._codes = codes if codes else list(TO_UPBIT_CODE.values())
        super().__init__(on_price, symbols or list(TO_UPBIT_CODE.keys()), **kwargs)

    async def _run_ws(self) -> None:
        async with websockets.connect(
            UPBIT_WS_URL,
            ping_interval=self.ping_interval,
            ping_timeout=60,
            close_timeout=5,
        ) as ws:
            # 구독 메시지: orderbook
            subscribe = [
                {"ticket": "crypto-arbitrage-monitor"},
                {"type": "orderbook", "codes": self._codes},
                {"format": "DEFAULT"},
            ]
            await ws.send(json.dumps(subscribe))
            logger.info("Upbit 구독: %s", self._codes)

            while self._running:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=120)
                except asyncio.TimeoutError:
                    await ws.ping()
                    continue
                data = json.loads(raw)
                if data.get("type") != "orderbook":
                    continue
                code = data.get("code", "")
                units = data.get("orderbook_units") or []
                if not units:
                    continue
                first = units[0]
                bid = float(first.get("bid_price", 0))
                ask = float(first.get("ask_price", 0))
                if bid <= 0 or ask <= 0:
                    continue
                symbol = normalize_symbol(ExchangeId.UPBIT, code) or code
                ts = data.get("timestamp")
                timestamp = datetime.utcnow()
                if ts:
                    try:
                        timestamp = datetime.utcfromtimestamp(ts / 1000.0)
                    except (TypeError, OSError):
                        pass
                self.on_price(
                    ExchangePrice(
                        exchange=ExchangeId.UPBIT,
                        symbol=symbol,
                        bid_price=bid,
                        ask_price=ask,
                        timestamp=timestamp,
                    )
                )
