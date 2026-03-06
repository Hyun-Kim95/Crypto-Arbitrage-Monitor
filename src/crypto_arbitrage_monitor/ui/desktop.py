"""
데스크톱 GUI: CustomTkinter 기반 모니터링 창
- 조건 설정(최소 수익률, 코인, 알림 등) + 모니터링 시작/중지
- 콘솔과 동일한 Monitor 인터페이스 (push, refresh_display)
"""

import calendar
import logging
import threading
from collections import OrderedDict
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from crypto_arbitrage_monitor.config import RuntimeSettings, get_settings
from crypto_arbitrage_monitor.models import ArbitrageOpportunity

logger = logging.getLogger("crypto_arbitrage_monitor.ui")

MAX_ROWS = 50
# 기본 모니터링 코인 목록 (체크박스로 제공)
DEFAULT_SYMBOLS = ["BTC", "ETH", "USDT", "XRP"]

try:
    import customtkinter as ctk
    from tkinter import ttk
except ImportError:
    ctk = None
    ttk = None


def _format_number(value: float) -> str:
    if value >= 1_000_000:
        return f"{value:,.0f}"
    if value >= 1:
        return f"{value:,.2f}"
    return f"{value:.4f}"


def _format_monitor_time(ts: datetime) -> str:
    """UTC naive datetime → 로컬 시각 문자열 (HH:MM:SS)."""
    try:
        utc_sec = calendar.timegm(ts.timetuple()) + ts.microsecond / 1_000_000
        local_dt = datetime.fromtimestamp(utc_sec)
        return local_dt.strftime("%H:%M:%S")
    except (OSError, ValueError):
        return ts.strftime("%H:%M:%S")


class DesktopMonitor:
    """데스크톱 모니터: 설정 패널 + 시작/중지 + 테이블."""

    def __init__(
        self,
        root: "ctk.CTk",
        run_backend: Optional[Callable[..., None]] = None,
    ) -> None:
        if ctk is None:
            raise RuntimeError("customtkinter가 필요합니다. pip install customtkinter")
        self._root = root
        self._run_backend_fn = run_backend
        self._rows: OrderedDict[tuple, ArbitrageOpportunity] = OrderedDict()
        self._lock = threading.Lock()
        self._pending_refresh = False
        self._backend_thread: Optional[threading.Thread] = None
        self._shared_state: Dict[str, Any] = {}
        self._stop_event: Optional[threading.Event] = None
        self._build_ui()
        self._load_initial_settings()

    def _build_ui(self) -> None:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self._root.title("암호화폐 차익거래 모니터")
        self._root.geometry("1120x560")
        self._root.minsize(900, 450)

        main = ctk.CTkFrame(self._root, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=12, pady=12)

        # 글자색: 다크 배경에서 잘 보이도록
        self._text_color = "#e8e8e8"
        self._text_color_dim = "#b0b0b0"

        # 왼쪽: 설정 + 시작/중지
        left = ctk.CTkFrame(main, width=280, fg_color=("#e8e8e8", "#1e1e1e"), corner_radius=8)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.pack_propagate(False)

        ctk.CTkLabel(
            left, text="조건 설정", font=ctk.CTkFont(size=14, weight="bold"), text_color=self._text_color
        ).pack(anchor="w", pady=(12, 8), padx=12)
        # 최소 수익률(%)
        ctk.CTkLabel(
            left, text="최소 수익률 (%)", font=ctk.CTkFont(size=12), text_color=self._text_color
        ).pack(anchor="w", padx=12)
        self._entry_min_spread = ctk.CTkEntry(
            left, placeholder_text="0.5", width=240, height=28, text_color=self._text_color
        )
        self._entry_min_spread.pack(anchor="w", padx=12, pady=(0, 8))
        # 모니터링 코인: 체크박스 + 기타
        ctk.CTkLabel(
            left, text="모니터링 코인", font=ctk.CTkFont(size=12), text_color=self._text_color
        ).pack(anchor="w", padx=12, pady=(4, 2))
        self._symbol_vars: Dict[str, Any] = {}
        coin_frame = ctk.CTkFrame(left, fg_color="transparent")
        coin_frame.pack(anchor="w", padx=12, pady=(0, 2))
        for sym in DEFAULT_SYMBOLS:
            v = ctk.BooleanVar(value=False)
            self._symbol_vars[sym] = v
            cb = ctk.CTkCheckBox(
                coin_frame,
                text=sym,
                variable=v,
                font=ctk.CTkFont(size=12),
                width=60,
                text_color=self._text_color,
            )
            cb.pack(side="left", padx=(0, 4), pady=0)
        ctk.CTkLabel(
            left, text="기타 (쉼표 구분)", font=ctk.CTkFont(size=11), text_color=self._text_color_dim
        ).pack(anchor="w", padx=12, pady=(4, 0))
        self._entry_symbols_extra = ctk.CTkEntry(
            left,
            placeholder_text="예: SOL, DOGE",
            width=240,
            height=28,
            text_color=self._text_color,
        )
        self._entry_symbols_extra.pack(anchor="w", padx=12, pady=(0, 8))
        # 최소 거래금액 USD (선택)
        ctk.CTkLabel(
            left,
            text="최소 거래금액 USD (비우면 미적용)",
            font=ctk.CTkFont(size=12),
            text_color=self._text_color,
        ).pack(anchor="w", padx=12, pady=(4, 0))
        self._entry_min_usd = ctk.CTkEntry(
            left, placeholder_text="", width=240, height=28, text_color=self._text_color
        )
        self._entry_min_usd.pack(anchor="w", padx=12, pady=(0, 12))

        ctk.CTkLabel(
            left, text="알림", font=ctk.CTkFont(size=14, weight="bold"), text_color=self._text_color
        ).pack(anchor="w", pady=(8, 6), padx=12)
        self._var_sound = ctk.BooleanVar(value=True)
        self._cb_sound = ctk.CTkCheckBox(
            left,
            text="소리 알림",
            variable=self._var_sound,
            font=ctk.CTkFont(size=12),
            text_color=self._text_color,
        )
        self._cb_sound.pack(anchor="w", padx=12, pady=2)

        # 시작 / 중지
        btn_frame = ctk.CTkFrame(left, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=12)
        self._btn_start = ctk.CTkButton(
            btn_frame, text="모니터링 시작", command=self._on_start, width=120, height=36
        )
        self._btn_start.pack(side="left", padx=(0, 8))
        self._btn_stop = ctk.CTkButton(
            btn_frame,
            text="중지",
            command=self._on_stop,
            width=80,
            height=36,
            state="disabled",
            fg_color="#c0392b",
            hover_color="#a93226",
        )
        self._btn_stop.pack(side="left")

        # 오른쪽: 상태 + 테이블
        right = ctk.CTkFrame(main, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)

        self._status_label = ctk.CTkLabel(
            right,
            text="시작 버튼을 눌러 모니터링을 시작하세요.",
            font=ctk.CTkFont(size=14),
            text_color=self._text_color,
        )
        self._status_label.pack(anchor="w", pady=(0, 6))

        table_frame = ctk.CTkFrame(right, fg_color="transparent")
        table_frame.pack(fill="both", expand=True)

        # 테이블 로우 글자색이 보이도록 스타일 적용 (Treeview 생성 전)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background="#2b2b2b",
            foreground="#ffffff",
            fieldbackground="#2b2b2b",
            rowheight=24,
        )
        style.configure("Treeview.Heading", background="#1f538d", foreground="white")
        style.map(
            "Treeview",
            background=[("selected", "#1f538d")],
            foreground=[("selected", "#ffffff")],
        )

        columns = (
            "시간",
            "코인",
            "거래소A",
            "거래소B",
            "매수가",
            "매도가",
            "스프레드",
        )
        self._tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", height=16, selectmode="none"
        )
        # Windows 등에서 스타일 foreground가 무시될 수 있어 태그로 글자색 강제
        self._tree.tag_configure("row", foreground="#ffffff", background="#2b2b2b")
        for col in columns:
            self._tree.heading(col, text=col)
            if col == "시간":
                self._tree.column(col, width=72, minwidth=60)
            elif col in ("매수가", "매도가", "스프레드"):
                self._tree.column(col, width=110, minwidth=80)
            else:
                self._tree.column(col, width=90, minwidth=60)
        # 스크롤바는 사용하지 않고, 테이블 영역 내에서만 표시
        self._tree.pack(fill="both", expand=True)

        # 텔레그램 관련 입력은 제거됨

    def _load_initial_settings(self) -> None:
        s = get_settings()
        self._entry_min_spread.insert(0, str(s.min_spread_percent))
        symbols = s.monitor_symbols or ["BTC", "ETH", "USDT"]
        for sym in DEFAULT_SYMBOLS:
            if sym in symbols and sym in self._symbol_vars:
                self._symbol_vars[sym].set(True)
        extra = [x for x in symbols if x not in DEFAULT_SYMBOLS]
        if extra:
            self._entry_symbols_extra.insert(0, ", ".join(extra))
        if s.min_trade_amount_usd is not None and s.min_trade_amount_usd > 0:
            self._entry_min_usd.insert(0, str(int(s.min_trade_amount_usd)))
        self._var_sound.set(s.alert_sound_enabled)

    def _get_settings_from_ui(self) -> RuntimeSettings:
        try:
            min_spread = float((self._entry_min_spread.get() or "0.5").strip().replace(",", "."))
        except ValueError:
            min_spread = 0.5
        symbols = []
        for sym, var in self._symbol_vars.items():
            if var.get():
                symbols.append(sym)
        extra_str = (self._entry_symbols_extra.get() or "").strip()
        if extra_str:
            for s in extra_str.split(","):
                t = s.strip().upper()
                if t and t not in symbols:
                    symbols.append(t)
        if not symbols:
            symbols = ["BTC", "ETH", "USDT"]
        min_usd = None
        usd_str = (self._entry_min_usd.get() or "").strip()
        if usd_str:
            try:
                min_usd = float(usd_str.replace(",", "."))
                if min_usd <= 0:
                    min_usd = None
            except ValueError:
                pass
        s = get_settings()
        return RuntimeSettings(
            min_spread_percent=min_spread,
            min_trade_amount_usd=min_usd,
            usd_krw_rate=s.usd_krw_rate,
            usd_krw_auto=s.usd_krw_auto,
            usd_krw_refresh_sec=s.usd_krw_refresh_sec,
            monitor_symbols=symbols,
            alert_sound_enabled=self._var_sound.get(),
            log_level=s.log_level,
            log_dir=s.log_dir,
        )

    def _on_start(self) -> None:
        if not self._run_backend_fn:
            self.set_status("오류: run_backend가 연결되지 않았습니다.")
            return
        settings = self._get_settings_from_ui()
        self._stop_event = threading.Event()
        self._shared_state = {}
        self._backend_thread = threading.Thread(
            target=self._run_backend_fn,
            args=(settings, self, self._stop_event, self._shared_state, self._on_backend_stopped),
            daemon=True,
        )
        self._btn_start.configure(state="disabled")
        self._btn_stop.configure(state="normal")
        self.set_status("연결 중...")
        with self._lock:
            self._rows.clear()
        self._refresh_table()
        self._backend_thread.start()

    def _on_stop(self) -> None:
        loop = self._shared_state.get("loop")
        tasks = self._shared_state.get("all_tasks", [])
        if loop and tasks:
            def cancel_all():
                for t in tasks:
                    if not t.done():
                        t.cancel()
            try:
                if not loop.is_closed():
                    loop.call_soon_threadsafe(cancel_all)
            except RuntimeError:
                pass  # 루프가 이미 닫혀 있으면 무시 (창 닫기 직후 등)
        self.set_status("중지 요청 중...")

    def _on_backend_stopped(self) -> None:
        self._btn_start.configure(state="normal")
        self._btn_stop.configure(state="disabled")
        self.set_status("중지됨 · 시작 버튼을 눌러 다시 시작하세요.")

    def request_stop(self) -> None:
        """창 닫기 등으로 종료할 때 백엔드에 중지 요청."""
        self._on_stop()

    def set_status(self, text: str) -> None:
        def _set():
            self._status_label.configure(text=text, text_color=self._text_color)
        self._root.after(0, _set)

    def push(self, opportunity: ArbitrageOpportunity) -> None:
        with self._lock:
            key = (
                opportunity.symbol,
                opportunity.exchange_buy.value,
                opportunity.exchange_sell.value,
            )
            self._rows[key] = opportunity
            if len(self._rows) > MAX_ROWS:
                self._rows.popitem(last=False)
            self._pending_refresh = True
        self._schedule_refresh()

    def refresh_display(self) -> None:
        with self._lock:
            if not self._rows and not self._pending_refresh:
                return
            self._pending_refresh = True
        self._schedule_refresh()

    def _schedule_refresh(self) -> None:
        self._root.after(0, self._refresh_table)

    def _refresh_table(self) -> None:
        with self._lock:
            rows_snapshot = list(self._rows.values())
            self._pending_refresh = False
        for iid in self._tree.get_children():
            self._tree.delete(iid)
        for opp in rows_snapshot:
            self._tree.insert(
                "",
                "end",
                values=(
                    _format_monitor_time(opp.timestamp),
                    opp.symbol,
                    opp.exchange_buy.value,
                    opp.exchange_sell.value,
                    _format_number(opp.bid_price),
                    _format_number(opp.ask_price),
                    f"{opp.spread_percent:.2f}%",
                ),
                tags=("row",),
            )
