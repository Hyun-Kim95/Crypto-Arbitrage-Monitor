"""
로깅 설정
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_dir: Optional[Path] = None,
    log_filename: str = "crypto_arbitrage_monitor.log",
) -> None:
    """
    로거 설정.
    - level: DEBUG, INFO, WARNING, ERROR
    - log_dir: 지정 시 해당 디렉터리에 파일 로그 추가
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger("crypto_arbitrage_monitor")
    root.setLevel(log_level)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 콘솔
    if not root.handlers:
        h_console = logging.StreamHandler(sys.stdout)
        h_console.setFormatter(fmt)
        root.addHandler(h_console)

    # 파일 (선택)
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / log_filename
        h_file = logging.FileHandler(path, encoding="utf-8")
        h_file.setFormatter(fmt)
        root.addHandler(h_file)
