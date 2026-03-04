"""
빗썸 호가 수집
- 공개 WebSocket 호가 스트림이 없어 REST orderbook 주기 폴링으로 1호가 수집
- aiohttp 미사용 (Python 3.9 + 구버전 aiohttp 호환 이슈 회피)
"""

import asyncio
import json
import logging
from datetime import datetime
from urllib.request import urlopen

from crypto_arbitrage_monitor.exchanges.base import ExchangeWsClient, PriceCallback
from crypto_arbitrage_monitor.models import ExchangeId, ExchangePrice, normalize_symbol

logger = logging.getLogger("crypto_arbitrage_monitor.exchanges.bithumb")

# 빗썸 공개 REST: orderbook
BITHUMB_ORDERBOOK_URL = "https://api.bithumb.com/public/orderbook/{pair}"

TO_BITHUMB_PAIR = {"BTC": "BTC_KRW", "ETH": "ETH_KRW", "USDT": "USDT_KRW", "XRP": "XRP_KRW"}


def _fetch_orderbook_sync(url: str) -> dict:
    """동기 HTTP 요청 (executor에서 실행)"""
    with urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


class BithumbWsClient(ExchangeWsClient):
    """
    빗썸 REST orderbook 주기 폴링으로 1호가 수집
    """

    def __init__(self, on_price: PriceCallback, symbols: list, poll_interval: float = 2.0, **kwargs):
        super().__init__(on_price, symbols or list(TO_BITHUMB_PAIR.keys()), **kwargs)
        self._pairs = [TO_BITHUMB_PAIR.get(s, f"{s}_KRW") for s in self.symbols]
        self._poll_interval = poll_interval

    async def _run_ws(self) -> None:
        loop = asyncio.get_event_loop()
        while self._running:
            for pair in self._pairs:
                try:
                    url = BITHUMB_ORDERBOOK_URL.format(pair=pair)
                    data = await loop.run_in_executor(None, _fetch_orderbook_sync, url)
                    if data.get("status") != "0000":
                        continue
                    item = data.get("data", {})
                    bids = item.get("bids") or []
                    asks = item.get("asks") or []
                    if not bids or not asks:
                        continue
                    bid = float(bids[0].get("price", 0))
                    ask = float(asks[0].get("price", 0))
                    if bid <= 0 or ask <= 0:
                        continue
                    symbol = normalize_symbol(ExchangeId.BITHUMB, pair) or pair.split("_")[0]
                    self.on_price(
                        ExchangePrice(
                            exchange=ExchangeId.BITHUMB,
                            symbol=symbol,
                            bid_price=bid,
                            ask_price=ask,
                            timestamp=datetime.utcnow(),
                        )
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.debug("Bithumb orderbook 요청 실패 %s: %s", pair, e)
            await asyncio.sleep(self._poll_interval)
