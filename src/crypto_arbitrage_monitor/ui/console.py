"""
메인 모니터링 화면: 콘솔 테이블
PRD: | 코인 | 거래소A | 거래소B | 매수가 | 매도가 | 스프레드 | 네트워크 | 출금상태 |
"""

import logging
from collections import OrderedDict
from typing import Dict, Optional

from crypto_arbitrage_monitor.models import ArbitrageOpportunity

logger = logging.getLogger("crypto_arbitrage_monitor.ui")

# 최근 N건 유지 (중복 제거: symbol + exchange_buy + exchange_sell)
MAX_ROWS = 50


class ConsoleMonitor:
    """필터 통과한 기회를 콘솔 테이블로 출력. 최근 건만 유지."""

    def __init__(self) -> None:
        # (symbol, exchange_buy, exchange_sell) -> opportunity
        self._rows: OrderedDict[tuple, ArbitrageOpportunity] = OrderedDict()
        self._network: Dict[tuple, str] = {}  # (exchange, symbol) -> "TRC20" 등
        self._withdraw: Dict[tuple, str] = {}  # (exchange, symbol) -> "가능"/"불가"

    def set_network(self, exchange: str, symbol: str, network: str) -> None:
        self._network[(exchange, symbol)] = network

    def set_withdraw_status(self, exchange: str, symbol: str, status: str) -> None:
        self._withdraw[(exchange, symbol)] = status

    def push(self, opportunity: ArbitrageOpportunity) -> None:
        key = (opportunity.symbol, opportunity.exchange_buy.value, opportunity.exchange_sell.value)
        self._rows[key] = opportunity
        if len(self._rows) > MAX_ROWS:
            self._rows.popitem(last=False)

    def _header(self) -> str:
        return (
            f"{'코인':<6} | {'거래소A':<10} | {'거래소B':<10} | {'매수가':>14} | {'매도가':>14} | {'스프레드':>8} | {'네트워크':<8} | {'출금상태':<8}"
        )

    def _sep(self) -> str:
        return "-" * (6 + 10 + 10 + 14 + 14 + 8 + 8 + 8 + 8 * 4)

    def _row(self, opp: ArbitrageOpportunity) -> str:
        net_buy = self._network.get((opp.exchange_buy.value, opp.symbol), "-")
        net_sell = self._network.get((opp.exchange_sell.value, opp.symbol), "-")
        net = f"{net_buy}/{net_sell}"
        wd_buy = self._withdraw.get((opp.exchange_buy.value, opp.symbol), "-")
        wd_sell = self._withdraw.get((opp.exchange_sell.value, opp.symbol), "-")
        wd = f"{wd_buy}/{wd_sell}"
        return (
            f"{opp.symbol:<6} | {opp.exchange_buy.value:<10} | {opp.exchange_sell.value:<10} | "
            f"{opp.bid_price:>14,.0f} | {opp.ask_price:>14,.0f} | {opp.spread_percent:>7.2f}% | "
            f"{net:<8} | {wd:<8}"
        )

    def print_table(self) -> None:
        """현재 보유한 기회 목록을 테이블로 출력"""
        if not self._rows:
            return
        lines = [self._header(), self._sep()]
        for opp in self._rows.values():
            lines.append(self._row(opp))
        print("\n".join(lines))
