"""Central Serial — entry point.

Bootstraps logging (one file per day under logs/) and launches the PySide6
application.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow

LOGS_DIR = Path(__file__).resolve().parent / "logs"


def setup_logging():
    LOGS_DIR.mkdir(exist_ok=True)
    log_file = LOGS_DIR / f"central_serial_{datetime.now():%Y%m%d}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
    )


def main():
    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("Central Serial")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
