"""Main studio window: character wizard + script editor tabs."""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QTabWidget

from open_tts.studio.character_wizard import CharacterWizard
from open_tts.studio.script_editor import ScriptEditor


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Open TTS Studio")
        self.resize(1100, 720)

        tabs = QTabWidget()
        tabs.addTab(CharacterWizard(), "Character")
        tabs.addTab(ScriptEditor(), "Script")
        self.setCentralWidget(tabs)
