"""
Bybit Spot WebSocket 호가
- 공개 endpoint: orderbook.50 (또는 orderbook.1 for best bid/ask)
- wss://stream.bybit.com/v5/public/spot
"""

import asyncio
import json
import logging
from datetime import datetime

import websockets

from crypto_arbitrage_monitor.exchanges.base import ExchangeWsClient, PriceCallback
from crypto_arbitrage_monitor.models import ExchangeId, ExchangePrice, normalize_symbol

logger = logging.getLogger("crypto_arbitrage_monitor.exchanges.bybit")

BYBIT_WS_URL = "wss://stream.bybit.com/v5/public/spot"


def _symbol_to_ticker(symbol: str) -> str:
    return f"{symbol}USDT"


class BybitWsClient(ExchangeWsClient):
    def __init__(self, on_price: PriceCallback, symbols: list[str], **kwargs):
        self._tickers = [_symbol_to_ticker(s) for s in (symbols or ["BTC", "ETH", "USDT"])]
        super().__init__(on_price, symbols or ["BTC", "ETH", "USDT"], **kwargs)

    async def _run_ws(self) -> None:
        async with websockets.connect(
            BYBIT_WS_URL,
            ping_interval=self.ping_interval,
            ping_timeout=60,
        ) as ws:
            # subscribe orderbook.1 (best bid/ask)
            subscribe = {
                "op": "subscribe",
                "args": [f"orderbook.1.{t}" for t in self._tickers],
            }
            await ws.send(json.dumps(subscribe))
            logger.info("Bybit 구독: %s", self._tickers)

            while self._running:
                raw = await ws.recv()
                data = json.loads(raw)
                if data.get("topic", "").startswith("orderbook"):
                    topic = data.get("topic", "")
                    # orderbook.1.BTCUSDT
                    parts = topic.split(".")
                    raw_sym = parts[-1] if len(parts) >= 3 else ""
                    d = data.get("data", {})
                    bids = d.get("b") or []
                    asks = d.get("a") or []
                    if not bids or not asks:
                        continue
                    bid = float(bids[0][0])
                    ask = float(asks[0][0])
                    if bid <= 0 or ask <= 0:
                        continue
                    symbol = normalize_symbol(ExchangeId.BYBIT, raw_sym) or raw_sym.replace("USDT", "")
                    self.on_price(
                        ExchangePrice(
                            exchange=ExchangeId.BYBIT,
                            symbol=symbol,
                            bid_price=bid,
                            ask_price=ask,
                            timestamp=datetime.utcnow(),
                        )
                    )
