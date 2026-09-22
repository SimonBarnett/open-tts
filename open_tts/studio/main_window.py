"""Main studio window: character wizard + script editor tabs."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QStyle, QTabWidget, QToolBar

from open_tts.studio.character_wizard import CharacterWizard
from open_tts.studio.script_editor import ScriptEditor


class MainWindow(QMainWindow):
    def __init__(self, yaml_path: Path | str | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Open TTS Studio")
        self.resize(1100, 720)

        tabs = QTabWidget()
        models = CharacterWizard()
        script = ScriptEditor()
        models.registry_changed.connect(script.refresh_models)
        tabs.addTab(models, "Models")
        tabs.addTab(script, "Interview")
        self.setCentralWidget(tabs)
        self._tabs = tabs
        self._script = script

        bar = QToolBar("Folder")
        bar.setObjectName("folderToolbar")
        bar.setMovable(False)
        bar.setFloatable(False)
        bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
        open_act = QAction(icon, "Open / Create folder", self)
        open_act.setObjectName("openCreateFolder")
        open_act.setToolTip("Pick a folder: open an existing interview, or create a full new project there.")
        open_act.triggered.connect(self._open_create_folder)
        bar.addAction(open_act)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, bar)
        self._folder_toolbar = bar
        self._open_folder_action = open_act

        if yaml_path is not None:
            path = Path(yaml_path)
            if path.is_file():
                script.load_path(path)
        if script._path is not None:
            tabs.setCurrentWidget(script)

    def _open_create_folder(self) -> None:
        self._script._open_folder()
        if self._script._path is not None:
            self._tabs.setCurrentWidget(self._script)
