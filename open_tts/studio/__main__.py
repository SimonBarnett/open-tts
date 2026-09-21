"""Launch the Open TTS studio wizard."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    from PySide6.QtWidgets import QApplication

    from open_tts.studio.main_window import MainWindow

    app = QApplication(argv or sys.argv)
    app.setApplicationName("Open TTS Studio")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
