"""
수익률/코인 필터: 최소 수익률 이상, 모니터링 코인만 통과
"""

from typing import List, Optional

from crypto_arbitrage_monitor.models import ArbitrageOpportunity


def apply_filters(
    opportunity: ArbitrageOpportunity,
    min_spread_percent: float,
    monitor_symbols: Optional[List[str]] = None,
    min_trade_amount_usd: Optional[float] = None,
) -> bool:
    """
    True면 표시/알림 대상, False면 제외.
    """
    if opportunity.spread_percent < min_spread_percent:
        return False
    if monitor_symbols is not None and len(monitor_symbols) > 0:
        if opportunity.symbol not in monitor_symbols:
            return False
    # min_trade_amount_usd는 규모 필터 (선택): 금액 추정 필요 시 확장
    if min_trade_amount_usd is not None and min_trade_amount_usd > 0:
        # bid_price * 수량으로 추정 가능하나, 현재 모델에 수량 없음 → 일단 통과
        pass
    return True
