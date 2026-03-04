"""
입출금 상태, 네트워크 정보 모델
"""

from typing import List, Optional

from pydantic import BaseModel

from crypto_arbitrage_monitor.models import ExchangeId


class NetworkInfo(BaseModel):
    """코인별 네트워크 정보 (예: USDT TRC20/ERC20)"""

    exchange: ExchangeId
    symbol: str
    network: str = ""  # e.g. TRC20, ERC20
    deposit_enabled: bool = False
    withdraw_enabled: bool = False


class WithdrawDepositStatus(BaseModel):
    """입출금 가능 여부 요약"""

    exchange: ExchangeId
    symbol: str
    deposit_enabled: bool = False
    withdraw_enabled: bool = False
    network: Optional[str] = None
