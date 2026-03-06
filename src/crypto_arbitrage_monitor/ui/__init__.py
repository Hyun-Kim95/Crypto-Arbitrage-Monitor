"""
UI: 데스크톱 GUI(기본) 및 콘솔 모드
"""

from crypto_arbitrage_monitor.ui.console import ConsoleMonitor

__all__ = ["ConsoleMonitor", "DesktopMonitor"]

# DesktopMonitor는 customtkinter 의존으로 필요 시 로드
def __getattr__(name):
    if name == "DesktopMonitor":
        from crypto_arbitrage_monitor.ui.desktop import DesktopMonitor
        return DesktopMonitor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
