"""
실행 진입점: python -m crypto_arbitrage_monitor
- 기본: 데스크톱 GUI 실행 (CustomTkinter)
- 환경 변수 USE_CONSOLE=1 이면 콘솔 모드 (기존 동작)
"""

import asyncio
import json
import os
import signal
import threading
from urllib.request import urlopen

from crypto_arbitrage_monitor.alerts import AlertManager
from crypto_arbitrage_monitor.config import get_settings
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
from crypto_arbitrage_monitor.ui.console import ConsoleMonitor
from crypto_arbitrage_monitor.ui.settings_display import print_settings


def _run_backend(settings, monitor, stop_event, shared_state, on_stopped=None):
    """별도 스레드에서 실행. asyncio 루프 + WebSocket/스프레드 계산. 종료 시 on_stopped() 호출."""
    symbols = settings.monitor_symbols or ["BTC", "ETH", "USDT"]
    all_tasks = []

    alert_manager = AlertManager(sound_enabled=settings.alert_sound_enabled)

    def on_opportunity(opp):
        if not apply_filters(
            opp,
            settings.min_spread_percent,
            settings.monitor_symbols if settings.monitor_symbols else None,
            settings.min_trade_amount_usd,
        ):
            return
        monitor.push(opp)
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
        """입출금/네트워크 정보는 더 이상 사용하지 않으므로, 상태 문구만 설정."""
        if hasattr(monitor, "set_status"):
            monitor.set_status("연결됨 · 차익거래 기회 모니터링 중")

    async def _update_usd_krw_rate() -> None:
        if not settings.usd_krw_auto:
            return
        loop = asyncio.get_event_loop()
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
        await _preload_exchange_info()

        tasks = [asyncio.create_task(c.start()) for c in clients]
        last_refresh = 0.0
        interval = 5.0

        async def periodic_refresh():
            nonlocal last_refresh
            while True:
                await asyncio.sleep(1)
                now = asyncio.get_event_loop().time()
                if now - last_refresh >= interval:
                    last_refresh = now
                    monitor.refresh_display()

        print_task = asyncio.create_task(periodic_refresh())
        rate_task = asyncio.create_task(_update_usd_krw_rate())
        all_tasks = tasks + [print_task, rate_task]
        shared_state["loop"] = asyncio.get_event_loop()
        shared_state["all_tasks"] = all_tasks
        try:
            await asyncio.gather(*all_tasks)
        except asyncio.CancelledError:
            pass
        for c in clients:
            c.stop()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_all())
    except Exception:
        pass
    finally:
        loop.close()
        if on_stopped and hasattr(monitor, "_root"):
            monitor._root.after(0, on_stopped)


def run_console(settings) -> None:
    """콘솔 전용 실행 (USE_CONSOLE=1 일 때)."""
    import asyncio as _asyncio

    symbols = settings.monitor_symbols or ["BTC", "ETH", "USDT"]
    all_tasks = []
    console = ConsoleMonitor()
    alert_manager = AlertManager(sound_enabled=settings.alert_sound_enabled)

    def on_opportunity(opp):
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
        """입출금/네트워크 정보는 더 이상 사용하지 않음."""
        return
    async def _update_usd_krw_rate() -> None:
        if not settings.usd_krw_auto:
            return
        loop = _asyncio.get_event_loop()
        rate = await loop.run_in_executor(None, _fetch_usd_krw_from_upbit_sync)
        if rate > 0:
            calculator.set_usd_krw_rate(rate)
        while True:
            await _asyncio.sleep(max(5, settings.usd_krw_refresh_sec))
            rate = await loop.run_in_executor(None, _fetch_usd_krw_from_upbit_sync)
            if rate > 0:
                calculator.set_usd_krw_rate(rate)

    async def run_all() -> None:
        nonlocal all_tasks
        await _preload_exchange_info()
        tasks = [_asyncio.create_task(c.start()) for c in clients]
        last_print = 0.0
        interval = 5.0

        async def periodic_print():
            nonlocal last_print
            while True:
                await _asyncio.sleep(1)
                now = _asyncio.get_event_loop().time()
                if now - last_print >= interval:
                    last_print = now
                    console.refresh_display()

        print_task = _asyncio.create_task(periodic_print())
        rate_task = _asyncio.create_task(_update_usd_krw_rate())
        all_tasks = tasks + [print_task, rate_task]
        try:
            await _asyncio.gather(*all_tasks)
        except _asyncio.CancelledError:
            pass
        for c in clients:
            c.stop()

    loop = _asyncio.new_event_loop()
    _asyncio.set_event_loop(loop)

    def shutdown():
        for c in clients:
            c.stop()
        for t in all_tasks:
            if not t.done():
                t.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown)
        except (NotImplementedError, OSError):
            pass

    try:
        loop.run_until_complete(run_all())
    except KeyboardInterrupt:
        shutdown()
        if all_tasks:
            loop.run_until_complete(_asyncio.gather(*all_tasks, return_exceptions=True))
    finally:
        loop.close()


def main() -> None:
    settings = get_settings()
    setup_logging(
        level=settings.log_level,
        log_dir=settings.log_dir,
    )

    use_console = os.environ.get("USE_CONSOLE", "").strip() == "1"
    if use_console:
        print_settings(settings)
        print("WebSocket 연결 중... (Ctrl+C 종료)\n")
        run_console(settings)
        return

    # 데스크톱 GUI (시작/중지는 창에서 버튼으로 제어)
    import customtkinter as ctk
    from crypto_arbitrage_monitor.ui.desktop import DesktopMonitor

    root = ctk.CTk()
    monitor = DesktopMonitor(root, run_backend=_run_backend)

    def on_closing():
        monitor.request_stop()
        root.quit()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
