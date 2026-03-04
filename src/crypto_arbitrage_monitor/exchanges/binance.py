"""
Binance Spot WebSocket 호가
- 스트림: wss://stream.binance.com:9443/ws/<symbol>@depth@100ms
- 응답: bids/asks 배열, 첫 번째가 best bid/ask
"""

import asyncio
import json
import logging
from datetime import datetime

import websockets

from crypto_arbitrage_monitor.exchanges.base import ExchangeWsClient, PriceCallback
from crypto_arbitrage_monitor.models import ExchangeId, ExchangePrice, normalize_symbol

logger = logging.getLogger("crypto_arbitrage_monitor.exchanges.binance")

# 복수 스트림: /stream + SUBSCRIBE 메시지
BINANCE_WS_URL = "wss://stream.binance.com:9443/stream"


def _symbol_to_stream(symbol: str) -> str:
    return f"{symbol}USDT".lower()


class BinanceWsClient(ExchangeWsClient):
    def __init__(self, on_price: PriceCallback, symbols: list[str], **kwargs):
        self._streams = [_symbol_to_stream(s) for s in (symbols or ["BTC", "ETH", "USDT"])]
        super().__init__(on_price, symbols or ["BTC", "ETH", "USDT"], **kwargs)

    async def _run_ws(self) -> None:
        async with websockets.connect(
            BINANCE_WS_URL,
            ping_interval=self.ping_interval,
            ping_timeout=60,
        ) as ws:
            # SUBSCRIBE로 복수 심볼 구독
            await ws.send(
                json.dumps(
                    {
                        "method": "SUBSCRIBE",
                        "params": [f"{s}@depth@100ms" for s in self._streams],
                        "id": 1,
                    }
                )
            )
            logger.info("Binance 구독: %s", self._streams)
            while self._running:
                raw = await ws.recv()
                data = json.loads(raw)
                # combined stream: { "stream": "btcusdt@depth@100ms", "data": { "bids": [...], "asks": [...] } }
                payload = data.get("data", data)
                stream = data.get("stream", "")
                raw_sym = stream.split("@")[0] if stream else ""
                bids = payload.get("bids") or []
                asks = payload.get("asks") or []
                if not bids or not asks:
                    continue
                bid = float(bids[0][0])
                ask = float(asks[0][0])
                if bid <= 0 or ask <= 0:
                    continue
                symbol = normalize_symbol(ExchangeId.BINANCE, raw_sym.upper()) or raw_sym.upper().replace("USDT", "")
                self.on_price(
                    ExchangePrice(
                        exchange=ExchangeId.BINANCE,
                        symbol=symbol,
                        bid_price=bid,
                        ask_price=ask,
                        timestamp=datetime.utcnow(),
                    )
                )
