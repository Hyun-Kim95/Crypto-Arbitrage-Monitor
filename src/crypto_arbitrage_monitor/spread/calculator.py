"""
PRD: Spread (%) = (해외 매도가 - 국내 매수가) / 국내 매수가 x 100
매수처 ask로 매수, 매도처 bid로 매도 시 수익률.
"""

import logging
from datetime import datetime
from typing import Callable, Dict, Tuple

from crypto_arbitrage_monitor.models import ArbitrageOpportunity, ExchangeId, ExchangePrice

logger = logging.getLogger("crypto_arbitrage_monitor.spread")

# 국내 거래소 (원화 매수 → 해외 매도 시 매수처)
DOMESTIC = {ExchangeId.UPBIT, ExchangeId.BITHUMB}
# 해외 거래소 (USDT 등)
OVERSEAS = {ExchangeId.BINANCE, ExchangeId.BYBIT, ExchangeId.GATEIO}


def spread_percent(bid_price: float, ask_price: float) -> float:
    """
    매수처 bid(매수 1호가)로 사서, 매도처 ask(매도 1호가)로 팔 때 수익률(%).
    spread = (매도가 - 매수가) / 매수가 * 100
    """
    if bid_price <= 0:
        return 0.0
    return ((ask_price - bid_price) / bid_price) * 100.0


class SpreadCalculator:
    """
    거래소별 최신 호가를 저장하고, 모든 거래소 쌍에 대해 스프레드를 계산해 콜백으로 전달.
    """

    def __init__(
        self,
        on_opportunity: Callable[[ArbitrageOpportunity], None],
        usd_krw_rate: float = 1.0,
    ):
        self.on_opportunity = on_opportunity
        self._usd_krw_rate = usd_krw_rate
        # (exchange, symbol) -> ExchangePrice
        self._latest: Dict[Tuple[str, str], ExchangePrice] = {}

    def set_usd_krw_rate(self, rate: float) -> None:
        """외부에서 환율을 주기적으로 갱신할 때 사용."""
        if rate > 0:
            self._usd_krw_rate = rate

    def push_price(self, price: ExchangePrice) -> None:
        """호가 갱신 시 호출. 저장 후 해당 심볼에 대해 모든 쌍 스프레드 재계산."""
        key = (price.exchange.value, price.symbol)
        self._latest[key] = price
        self._recompute_pairs(price.symbol)

    def _recompute_pairs(self, symbol: str) -> None:
        """해당 심볼에 대해 (exchange_buy, exchange_sell) 모든 쌍 계산."""
        prices_by_exchange: Dict[ExchangeId, ExchangePrice] = {}
        for (ex, sym), p in self._latest.items():
            if sym != symbol:
                continue
            prices_by_exchange[p.exchange] = p

        if len(prices_by_exchange) < 2:
            return

        for buy_ex in list(prices_by_exchange.keys()):
            for sell_ex in list(prices_by_exchange.keys()):
                if buy_ex == sell_ex:
                    continue
                buy_p = prices_by_exchange.get(buy_ex)
                sell_p = prices_by_exchange.get(sell_ex)
                if not buy_p or not sell_p:
                    continue

                # 매수 거래소에서 실제로 사는 가격 = 매도 1호가(ask)
                # 매도 거래소에서 실제로 파는 가격 = 매수 1호가(bid)
                buy_ask = buy_p.ask_price
                sell_bid = sell_p.bid_price

                # 통화 정규화
                # - 국내↔국내: KRW끼리, 해외↔해외: USDT끼리 → 그대로 비교
                # - 국내↔해외: USDT 쪽을 USD/KRW 환율로 KRW로 환산 후 비교
                if (buy_ex in DOMESTIC and sell_ex in DOMESTIC) or (
                    buy_ex in OVERSEAS and sell_ex in OVERSEAS
                ):
                    buy_price = buy_ask
                    sell_price = sell_bid
                else:
                    # 교차 통화 쌍 (KRW↔USDT)
                    if self._usd_krw_rate <= 0:
                        # 환율 설정이 잘못되어 있으면 해당 쌍은 건너뜀
                        continue
                    if buy_ex in DOMESTIC and sell_ex in OVERSEAS:
                        # 국내(KRW)에서 매수, 해외(USDT)에서 매도 → 해외 bid를 KRW로 변환
                        buy_price = buy_ask
                        sell_price = sell_bid * self._usd_krw_rate
                    elif buy_ex in OVERSEAS and sell_ex in DOMESTIC:
                        # 해외(USDT)에서 매수, 국내(KRW)에서 매도 → 해외 ask를 KRW로 변환
                        buy_price = buy_ask * self._usd_krw_rate
                        sell_price = sell_bid
                    else:
                        buy_price = buy_ask
                        sell_price = sell_bid

                pct = spread_percent(buy_price, sell_price)
                self.on_opportunity(
                    ArbitrageOpportunity(
                        symbol=symbol,
                        exchange_buy=buy_ex,
                        exchange_sell=sell_ex,
                        bid_price=buy_price,
                        ask_price=sell_price,
                        spread_percent=pct,
                        timestamp=datetime.utcnow(),
                    )
                )
