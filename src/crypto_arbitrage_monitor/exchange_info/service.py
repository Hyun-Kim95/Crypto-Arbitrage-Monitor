"""
거래소별 입출금/네트워크 정보 조회 (ccxt 활용)
- fetch_currencies() 결과를 캐시해서 입출금 여부/네트워크 정보를 제공
"""

import asyncio
import logging
from typing import Dict, List, Optional

from crypto_arbitrage_monitor.exchange_info.types import NetworkInfo, WithdrawDepositStatus
from crypto_arbitrage_monitor.models import ExchangeId

logger = logging.getLogger("crypto_arbitrage_monitor.exchange_info")

try:
    import ccxt  # type: ignore
except Exception as exc:  # ImportError, DLL 문제 등 모두 포함
    ccxt = None  # type: ignore
    err_str = str(exc)
    if "_rust" in err_str or "DLL" in err_str or "프로시저" in err_str:
        logger.info(
            "이 PC에서는 입출금/네트워크 정보 기능을 사용할 수 없습니다. "
            "호가·스프레드·알림은 정상 동작합니다."
        )
    else:
        logger.info("ccxt 미사용. 입출금/네트워크 정보 기능 비활성화: %s", exc)


EXCHANGE_CCXT_ID = {
    ExchangeId.UPBIT: "upbit",
    ExchangeId.BITHUMB: "bithumb",
    ExchangeId.BINANCE: "binance",
    ExchangeId.BYBIT: "bybit",
    ExchangeId.GATEIO: "gateio",
}


def _load_currencies_sync(exchange: ExchangeId) -> Dict[str, dict]:
    """동기 ccxt 클라이언트로 통화 정보(fetch_currencies) 조회."""
    if ccxt is None:
        # ccxt를 사용할 수 없는 환경이면 빈 결과 반환 (기능 비활성화)
        return {}
    ccxt_id = EXCHANGE_CCXT_ID.get(exchange)
    if not ccxt_id or not hasattr(ccxt, ccxt_id):
        logger.debug("지원되지 않는 ccxt 거래소: %s", exchange)
        return {}
    ex_class = getattr(ccxt, ccxt_id)
    ex = ex_class()
    try:
        return ex.fetch_currencies()
    except Exception as exc:
        logger.warning("ccxt fetch_currencies 실패 (%s): %s", exchange, exc)
        return {}


class ExchangeInfoService:
    """
    입출금 가능 여부, 네트워크 정보 캐시 및 조회.
    출금 불가 코인 제외, UI 네트워크/출금상태 표시 시 사용.
    """

    def __init__(self) -> None:
        self._cache: Dict[ExchangeId, List[WithdrawDepositStatus]] = {}
        self._network_cache: Dict[ExchangeId, List[NetworkInfo]] = {}

    async def _ensure_loaded(self, exchange: ExchangeId) -> None:
        """해당 거래소의 통화 정보를 한 번만 불러와 캐시에 채운다."""
        if exchange in self._cache and exchange in self._network_cache:
            return

        loop = asyncio.get_event_loop()
        currencies = await loop.run_in_executor(None, _load_currencies_sync, exchange)
        status_list: List[WithdrawDepositStatus] = []
        networks: List[NetworkInfo] = []

        for code, info in currencies.items():
            deposit = bool(info.get("deposit", False))
            withdraw = bool(info.get("withdraw", False))
            status_list.append(
                WithdrawDepositStatus(
                    exchange=exchange,
                    symbol=code,
                    deposit_enabled=deposit,
                    withdraw_enabled=withdraw,
                    network=None,
                )
            )

            nets = info.get("networks") or {}
            for net_name, net in nets.items():
                networks.append(
                    NetworkInfo(
                        exchange=exchange,
                        symbol=code,
                        network=net_name,
                        deposit_enabled=bool(net.get("deposit", False)),
                        withdraw_enabled=bool(net.get("withdraw", False)),
                    )
                )

        self._cache[exchange] = status_list
        self._network_cache[exchange] = networks

    async def get_withdraw_deposit_status(
        self, exchange: ExchangeId, symbols: Optional[List[str]] = None
    ) -> List[WithdrawDepositStatus]:
        """거래소별 입출금 상태 (캐시 있으면 반환, 없으면 ccxt로 채움)."""
        await self._ensure_loaded(exchange)
        status_list = self._cache.get(exchange, [])
        if symbols is None:
            return status_list
        return [s for s in status_list if s.symbol in symbols]

    async def get_network_info(self, exchange: ExchangeId, symbol: str) -> List[NetworkInfo]:
        """같은 코인이라도 거래소별 네트워크가 다를 수 있음 (예: USDT TRC20 vs ERC20)."""
        await self._ensure_loaded(exchange)
        return [n for n in self._network_cache.get(exchange, []) if n.symbol == symbol]

    def set_cached_status(self, exchange: ExchangeId, status_list: List[WithdrawDepositStatus]) -> None:
        """테스트/수동 설정용 캐시 저장"""
        self._cache[exchange] = status_list

    def set_cached_networks(self, exchange: ExchangeId, networks: List[NetworkInfo]) -> None:
        self._network_cache[exchange] = networks
