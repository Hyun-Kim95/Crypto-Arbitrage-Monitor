"""스프레드 계산 및 필터 단위 테스트"""

import pytest
from datetime import datetime

from crypto_arbitrage_monitor.models import ArbitrageOpportunity, ExchangeId, ExchangePrice
from crypto_arbitrage_monitor.spread.calculator import spread_percent, SpreadCalculator
from crypto_arbitrage_monitor.filters import apply_filters


def test_spread_percent():
    assert abs(spread_percent(100, 101) - 1.0) < 0.001
    assert abs(spread_percent(100, 100.5) - 0.5) < 0.001
    assert spread_percent(100, 100) == 0.0


def test_spread_calculator_single_opportunity():
    seen = []
    def on_opp(o: ArbitrageOpportunity):
        seen.append(o)
    calc = SpreadCalculator(on_opportunity=on_opp)
    calc.push_price(ExchangePrice(exchange=ExchangeId.UPBIT, symbol="BTC", bid_price=100, ask_price=101))
    calc.push_price(ExchangePrice(exchange=ExchangeId.BINANCE, symbol="BTC", bid_price=102, ask_price=103))
    assert len(seen) >= 2  # UPBIT->BINANCE and BINANCE->UPBIT
    # UPBIT ask 101, BINANCE bid 102 -> spread (102-101)/101*100
    for o in seen:
        if o.exchange_buy == ExchangeId.UPBIT and o.exchange_sell == ExchangeId.BINANCE:
            assert abs(o.spread_percent - (102 - 101) / 101 * 100) < 0.01
            break
    else:
        pytest.fail("Expected UPBIT->BINANCE opportunity")


def test_apply_filters_min_spread():
    opp = ArbitrageOpportunity(
        symbol="BTC", exchange_buy=ExchangeId.UPBIT, exchange_sell=ExchangeId.BINANCE,
        bid_price=100, ask_price=101, spread_percent=0.3,
    )
    assert apply_filters(opp, min_spread_percent=0.5, monitor_symbols=None) is False
    assert apply_filters(opp, min_spread_percent=0.2, monitor_symbols=None) is True


def test_apply_filters_symbol():
    opp = ArbitrageOpportunity(
        symbol="ETH", exchange_buy=ExchangeId.UPBIT, exchange_sell=ExchangeId.BINANCE,
        bid_price=100, ask_price=101, spread_percent=1.0,
    )
    assert apply_filters(opp, min_spread_percent=0.5, monitor_symbols=["BTC"]) is False
    assert apply_filters(opp, min_spread_percent=0.5, monitor_symbols=["ETH", "BTC"]) is True
    assert apply_filters(opp, min_spread_percent=0.5, monitor_symbols=[]) is True
