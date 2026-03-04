"""
Gate.io Spot WebSocket 호가
- wss://api.gateio.ws/ws/v4/
- channel: spot.order_book (params: [symbol, level, interval)
"""

import asyncio
import json
import logging
from datetime import datetime

import websockets

from crypto_arbitrage_monitor.exchanges.base import ExchangeWsClient, PriceCallback
from crypto_arbitrage_monitor.models import ExchangeId, ExchangePrice, normalize_symbol

logger = logging.getLogger("crypto_arbitrage_monitor.exchanges.gateio")

GATEIO_WS_URL = "wss://api.gateio.ws/ws/v4/"


def _symbol_to_pair(symbol: str) -> str:
    return f"{symbol}_USDT"


class GateIoWsClient(ExchangeWsClient):
    def __init__(self, on_price: PriceCallback, symbols: list[str], **kwargs):
        self._pairs = [_symbol_to_pair(s) for s in (symbols or ["BTC", "ETH", "USDT"])]
        super().__init__(on_price, symbols or ["BTC", "ETH", "USDT"], **kwargs)

    async def _run_ws(self) -> None:
        async with websockets.connect(
            GATEIO_WS_URL,
            ping_interval=self.ping_interval,
            ping_timeout=60,
        ) as ws:
            for pair in self._pairs:
                sub = {
                    "time": int(asyncio.get_event_loop().time()),
                    "channel": "spot.order_book",
                    "event": "subscribe",
                    "payload": [pair, "20", "100ms"],
                }
                await ws.send(json.dumps(sub))
            logger.info("Gate.io 구독: %s", self._pairs)

            while self._running:
                raw = await ws.recv()
                data = json.loads(raw)
                if data.get("event") != "update":
                    continue
                ch = data.get("channel", "")
                if ch != "spot.order_book":
                    continue
                payload = data.get("result", {})
                currency_pair = payload.get("s", "")
                bids = payload.get("bids") or []
                asks = payload.get("asks") or []
                if not bids or not asks:
                    continue
                bid = float(bids[0][0])
                ask = float(asks[0][0])
                if bid <= 0 or ask <= 0:
                    continue
                symbol = normalize_symbol(ExchangeId.GATEIO, currency_pair) or currency_pair.replace("_USDT", "")
                self.on_price(
                    ExchangePrice(
                        exchange=ExchangeId.GATEIO,
                        symbol=symbol,
                        bid_price=bid,
                        ask_price=ask,
                        timestamp=datetime.utcnow(),
                    )
                )
