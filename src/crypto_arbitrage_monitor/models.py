"""
데이터 모델: exchange_price, arbitrage_opportunity, 심볼 정규화
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ExchangeId(str, Enum):
    """지원 거래소 식별자"""

    UPBIT = "upbit"
    BITHUMB = "bithumb"
    BINANCE = "binance"
    BYBIT = "bybit"
    GATEIO = "gateio"


# PRD: exchange_price
class ExchangePrice(BaseModel):
    """거래소별 실시간 호가 (매수 1호가 / 매도 1호가)"""

    exchange: ExchangeId
    symbol: str = Field(..., description="정규화된 심볼, 예: BTC, ETH, USDT")
    bid_price: float = Field(..., gt=0, description="매수 1호가")
    ask_price: float = Field(..., gt=0, description="매도 1호가")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @property
    def mid_price(self) -> float:
        return (self.bid_price + self.ask_price) / 2.0


# PRD: arbitrage_opportunity
class ArbitrageOpportunity(BaseModel):
    """차익거래 기회 한 건"""

    symbol: str
    exchange_buy: ExchangeId = Field(..., description="매수할 거래소")
    exchange_sell: ExchangeId = Field(..., description="매도할 거래소")
    bid_price: float = Field(..., description="매수처 매수 1호가")
    ask_price: float = Field(..., description="매도처 매도 1호가")
    spread_percent: float = Field(..., description="스프레드(%)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @property
    def description_short(self) -> str:
        return f"{self.symbol} {self.exchange_buy.value} → {self.exchange_sell.value} {self.spread_percent:.2f}%"


# 거래소별 원시 심볼 → 통일 심볼 매핑 (예: KRW-BTC → BTC, BTCUSDT → BTC)
# 확장 시 각 거래소 모듈에서 채움
SYMBOL_NORMALIZE: dict[str, dict[str, str]] = {
    "upbit": {"KRW-BTC": "BTC", "KRW-ETH": "ETH", "KRW-USDT": "USDT"},  # 예시
    "bithumb": {"BTC_KRW": "BTC", "ETH_KRW": "ETH", "USDT_KRW": "USDT"},
    "binance": {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "USDTUSDT": "USDT"},
    "bybit": {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "USDTUSDT": "USDT"},
    "gateio": {"BTC_USDT": "BTC", "ETH_USDT": "ETH", "USDT_USDT": "USDT"},
}


def normalize_symbol(exchange: ExchangeId, raw_symbol: str) -> Optional[str]:
    """거래소별 원시 심볼을 통일 심볼(예: BTC)로 변환"""
    key = exchange.value
    if key not in SYMBOL_NORMALIZE:
        return None
    return SYMBOL_NORMALIZE[key].get(raw_symbol, raw_symbol)
