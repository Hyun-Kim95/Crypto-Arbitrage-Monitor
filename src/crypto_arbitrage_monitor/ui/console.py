"""
메인 모니터링 화면: 콘솔 테이블
표시 컬럼: 시간, 코인, 거래소A, 거래소B, 매수가, 매도가, 스프레드
"""

import calendar
import logging
from collections import OrderedDict
from datetime import datetime
from typing import Optional

from crypto_arbitrage_monitor.models import ArbitrageOpportunity


def _format_monitor_time(ts: datetime) -> str:
    """UTC naive datetime → 로컬 시각 문자열 (HH:MM:SS)."""
    try:
        utc_sec = calendar.timegm(ts.timetuple()) + ts.microsecond / 1_000_000
        local_dt = datetime.fromtimestamp(utc_sec)
        return local_dt.strftime("%H:%M:%S")
    except (OSError, ValueError):
        return ts.strftime("%H:%M:%S")

logger = logging.getLogger("crypto_arbitrage_monitor.ui")

# 최근 N건 유지 (중복 제거: symbol + exchange_buy + exchange_sell)
MAX_ROWS = 50


class ConsoleMonitor:
    """필터 통과한 기회를 콘솔 테이블로 출력. 최근 건만 유지."""

    def __init__(self) -> None:
        # (symbol, exchange_buy, exchange_sell) -> opportunity
        self._rows: OrderedDict[tuple, ArbitrageOpportunity] = OrderedDict()

    def push(self, opportunity: ArbitrageOpportunity) -> None:
        key = (opportunity.symbol, opportunity.exchange_buy.value, opportunity.exchange_sell.value)
        self._rows[key] = opportunity
        if len(self._rows) > MAX_ROWS:
            self._rows.popitem(last=False)

    def _header(self) -> str:
        return (
            f"{'시간':<8} | {'코인':<6} | {'거래소A':<10} | {'거래소B':<10} | "
            f"{'매수가':>14} | {'매도가':>14} | {'스프레드':>8}"
        )

    def _sep(self) -> str:
        return "-" * (8 + 6 + 10 + 10 + 14 + 14 + 8 + 7 * 4)

    def _row(self, opp: ArbitrageOpportunity) -> str:
        # 네트워크/출금 상태/대출 정보는 현재 표시하지 않음
        tstr = _format_monitor_time(opp.timestamp)
        return (
            f"{tstr:<8} | {opp.symbol:<6} | {opp.exchange_buy.value:<10} | {opp.exchange_sell.value:<10} | "
            f"{opp.bid_price:>14,.0f} | {opp.ask_price:>14,.0f} | {opp.spread_percent:>7.2f}%"
        )

    def print_table(self) -> None:
        """현재 보유한 기회 목록을 테이블로 출력"""
        if not self._rows:
            return
        lines = [self._header(), self._sep()]
        for opp in self._rows.values():
            lines.append(self._row(opp))
        print("\n".join(lines))

    def refresh_display(self) -> None:
        """주기 갱신용. 콘솔에서는 print_table과 동일."""
        self.print_table()
