"""Main studio window: character wizard + script editor tabs."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QStyle, QTabWidget, QToolBar

from open_tts.studio.character_wizard import CharacterWizard
from open_tts.studio.script_editor import ScriptEditor
from open_tts.studio.tour_editor import TourEditor


class MainWindow(QMainWindow):
    def __init__(self, yaml_path: Path | str | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Open TTS Studio")
        self.resize(1100, 720)

        tabs = QTabWidget()
        models = CharacterWizard()
        script = ScriptEditor()
        tours = TourEditor()
        models.registry_changed.connect(script.refresh_models)
        tabs.addTab(models, "Models")
        tabs.addTab(script, "Interview")
        tabs.addTab(tours, "Tutorials")
        self._tours = tours
        self.setCentralWidget(tabs)
        self._tabs = tabs
        self._script = script

        bar = QToolBar("File")
        bar.setObjectName("fileToolbar")
        bar.setMovable(False)
        bar.setFloatable(False)
        bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        style = self.style()
        create_act = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder),
            "Create",
            self,
        )
        create_act.setObjectName("createFolder")
        create_act.setToolTip("Create a new interview in a folder.")
        create_act.triggered.connect(self._create_folder)
        open_act = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon),
            "Open",
            self,
        )
        open_act.setObjectName("openFolder")
        open_act.setToolTip("Open an existing interview folder.")
        open_act.triggered.connect(self._open_folder)
        save_act = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton),
            "Save",
            self,
        )
        save_act.setObjectName("saveInterview")
        save_act.setToolTip("Save the current interview.")
        save_act.triggered.connect(self._save)
        bar.addAction(create_act)
        bar.addAction(open_act)
        bar.addAction(save_act)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, bar)
        self._folder_toolbar = bar
        self._create_folder_action = create_act
        self._open_folder_action = open_act
        self._save_action = save_act

        if yaml_path is not None:
            path = Path(yaml_path)
            if path.is_file():
                script.load_path(path)
        tabs.setCurrentWidget(script)

    def _show_interview(self) -> None:
        if self._script._path is not None:
            self._tabs.setCurrentWidget(self._script)

    def _create_folder(self) -> None:
        self._script._create_folder()
        self._show_interview()

    def _open_folder(self) -> None:
        self._script._open_folder()
        self._show_interview()

    def _save(self) -> None:
        self._script._save()
        self._show_interview()
