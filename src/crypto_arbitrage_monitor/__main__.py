"""
실행 진입점: python -m crypto_arbitrage_monitor
"""

import asyncio
import json
import signal
from urllib.request import urlopen

from crypto_arbitrage_monitor.alerts import AlertManager
from crypto_arbitrage_monitor.config import get_settings
from crypto_arbitrage_monitor.exchange_info import ExchangeInfoService
from crypto_arbitrage_monitor.exchanges import (
    BinanceWsClient,
    BithumbWsClient,
    BybitWsClient,
    GateIoWsClient,
    UpbitWsClient,
)
from crypto_arbitrage_monitor.filters import apply_filters
from crypto_arbitrage_monitor.logging_config import setup_logging
from crypto_arbitrage_monitor.models import ExchangeId
from crypto_arbitrage_monitor.spread import SpreadCalculator
from crypto_arbitrage_monitor.ui import ConsoleMonitor
from crypto_arbitrage_monitor.ui.settings_display import print_settings


def run_loop(settings) -> None:
    symbols = settings.monitor_symbols or ["BTC", "ETH", "USDT"]
    all_tasks: list = []
    console = ConsoleMonitor()
    info_service = ExchangeInfoService()
    # (ExchangeId, symbol) -> 출금 가능 여부
    withdraw_ok: dict = {}

    alert_manager = AlertManager(
        sound_enabled=settings.alert_sound_enabled,
        telegram_enabled=settings.telegram_enabled,
        telegram_token=settings.telegram_bot_token or "",
        telegram_chat_id=settings.telegram_chat_id or "",
    )

    def on_opportunity(opp):
        # 출금 불가 코인은 자동 제외 (양쪽 거래소 모두 출금 가능해야 함)
        if withdraw_ok:
            kb = (opp.exchange_buy, opp.symbol)
            ks = (opp.exchange_sell, opp.symbol)
            if not withdraw_ok.get(kb, True) or not withdraw_ok.get(ks, True):
                return
        if not apply_filters(
            opp,
            settings.min_spread_percent,
            settings.monitor_symbols if settings.monitor_symbols else None,
            settings.min_trade_amount_usd,
        ):
            return
        console.push(opp)
        alert_manager.trigger_sync(opp)

    calculator = SpreadCalculator(
        on_opportunity=on_opportunity,
        usd_krw_rate=settings.usd_krw_rate,
    )

    def on_price(price):
        calculator.push_price(price)

    clients = [
        UpbitWsClient(on_price, symbols),
        BithumbWsClient(on_price, symbols),
        BinanceWsClient(on_price, symbols),
        BybitWsClient(on_price, symbols),
        GateIoWsClient(on_price, symbols),
    ]

    def _fetch_usd_krw_from_upbit_sync() -> float:
        """
        업비트 KRW-USDT 시세를 이용해 USD/KRW 환율을 추정.
        /v1/ticker?markets=KRW-USDT 의 trade_price 사용.
        """
        url = "https://api.upbit.com/v1/ticker?markets=KRW-USDT"
        try:
            with urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list) and data:
                price = float(data[0].get("trade_price", 0.0))
                return price if price > 0 else 0.0
        except Exception:
            return 0.0
        return 0.0

    async def _preload_exchange_info() -> None:
        """ccxt로 입출금/네트워크 정보를 미리 불러와 콘솔에 반영."""
        target_exchanges = [
            ExchangeId.UPBIT,
            ExchangeId.BITHUMB,
            ExchangeId.BINANCE,
            ExchangeId.BYBIT,
            ExchangeId.GATEIO,
        ]
        for ex in target_exchanges:
            try:
                status_list = await info_service.get_withdraw_deposit_status(ex, symbols)
                for s in status_list:
                    withdraw_ok[(ex, s.symbol)] = s.withdraw_enabled
                    console.set_withdraw_status(
                        ex.value,
                        s.symbol,
                        "가능" if s.withdraw_enabled else "불가",
                    )
                # 네트워크 정보는 심볼별 대표 네트워크 하나만 표시
                for sym in symbols:
                    nets = await info_service.get_network_info(ex, sym)
                    if not nets:
                        continue
                    main_net = nets[0]
                    console.set_network(ex.value, sym, main_net.network)
            except Exception:
                # ccxt 오류가 나도 전체 흐름은 유지
                continue

    async def _update_usd_krw_rate() -> None:
        """USD/KRW 환율을 업비트 시세로 주기적으로 갱신."""
        if not settings.usd_krw_auto:
            return
        loop = asyncio.get_event_loop()
        # 최초 1회 즉시 갱신 시도
        rate = await loop.run_in_executor(None, _fetch_usd_krw_from_upbit_sync)
        if rate > 0:
            calculator.set_usd_krw_rate(rate)
        while True:
            await asyncio.sleep(max(5, settings.usd_krw_refresh_sec))
            rate = await loop.run_in_executor(None, _fetch_usd_krw_from_upbit_sync)
            if rate > 0:
                calculator.set_usd_krw_rate(rate)

    async def run_all() -> None:
        nonlocal all_tasks
        # 입출금/네트워크 정보 선조회
        await _preload_exchange_info()

        tasks = [asyncio.create_task(c.start()) for c in clients]
        last_print = 0.0
        interval = 5.0

        async def periodic_print():
            nonlocal last_print
            while True:
                await asyncio.sleep(1)
                now = asyncio.get_event_loop().time()
                if now - last_print >= interval:
                    last_print = now
                    console.print_table()

        print_task = asyncio.create_task(periodic_print())
        rate_task = asyncio.create_task(_update_usd_krw_rate())
        all_tasks = tasks + [print_task, rate_task]
        try:
            await asyncio.gather(*all_tasks)
        except asyncio.CancelledError:
            pass
        for c in clients:
            c.stop()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def shutdown() -> None:
        """Ctrl+C 또는 SIGTERM 시 그레이스풀하게 태스크를 취소."""
        for c in clients:
            c.stop()
        for t in all_tasks:
            if not t.done():
                t.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown)
        except (NotImplementedError, OSError):
            # Windows 등에서 signal handler 지원이 제한될 수 있음
            pass

    try:
        loop.run_until_complete(run_all())
    except KeyboardInterrupt:
        # 수동 Ctrl+C 시 태스크를 취소하고 정리까지 기다린 뒤 종료
        shutdown()
        if all_tasks:
            loop.run_until_complete(
                asyncio.gather(*all_tasks, return_exceptions=True)
            )
    finally:
        loop.close()


def main() -> None:
    settings = get_settings()
    setup_logging(
        level=settings.log_level,
        log_dir=settings.log_dir,
    )
    print_settings(settings)
    print("WebSocket 연결 중... (Ctrl+C 종료)\n")
    run_loop(settings)


if __name__ == "__main__":
    main()
