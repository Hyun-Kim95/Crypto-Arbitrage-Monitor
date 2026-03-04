"""
Gate.io 차익거래용 코인 대출 가능 여부 및 대출 금리
- 간단한 HTTP GET (urllib + run_in_executor) 로 조회
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional
from urllib.request import urlopen

from pydantic import BaseModel

logger = logging.getLogger("crypto_arbitrage_monitor.exchange_info.gateio_lending")


class GateIoLoanInfo(BaseModel):
    """Gate.io 대출 정보"""

    symbol: str = ""
    loanable: bool = False
    rate: Optional[float] = None  # 대출 금리


# Gate.io Margin Loan API (공개)
GATEIO_LOAN_API = "https://api.gateio.ws/api/v4/margin/loanable"


def _fetch_loanable_sync() -> list:
    """동기 HTTP로 loanable 리스트 조회 (executor에서 실행)."""
    try:
        with urlopen(GATEIO_LOAN_API, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        logger.warning("Gate.io loanable 조회 실패: %s", exc)
        return []


async def fetch_gateio_loan_info(symbols: Optional[List[str]] = None) -> Dict[str, GateIoLoanInfo]:
    """
    Gate.io 대출 가능 여부 및 금리 조회.
    symbols가 있으면 해당 코인만, 없으면 전체(또는 일부) 반환.
    """
    loop = asyncio.get_event_loop()
    raw = await loop.run_in_executor(None, _fetch_loanable_sync)

    result: Dict[str, GateIoLoanInfo] = {}
    if not isinstance(raw, list):
        return result

    for item in raw:
        cur = str(item.get("currency", "")).upper()
        if not cur:
            continue
        if symbols and cur not in symbols:
            continue
        loanable = bool(item.get("loanable", False))
        rate_val = item.get("rate")
        try:
            rate = float(rate_val) if rate_val is not None else None
        except (TypeError, ValueError):
            rate = None
        result[cur] = GateIoLoanInfo(symbol=cur, loanable=loanable, rate=rate)

    return result
