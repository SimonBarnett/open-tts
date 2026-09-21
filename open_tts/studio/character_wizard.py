"""Flow A: describe character, generate still, bake sheet, save registry."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from open_tts.characters import load_registry, repo_root, save_registry, upsert_character
from open_tts.imagine import get_image_provider
from open_tts.sprite import CharacterSheet


class CharacterWizard(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._provider = get_image_provider()
        self._history: list[Path] = []
        self._locked_hero: Path | None = None
        self._preview_sheet: Path | None = None
        self._sheet_preview: CharacterSheet | None = None

        root = QVBoxLayout(self)

        form_box = QGroupBox("Describe character")
        form = QFormLayout(form_box)
        self.id_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.voice_edit = QLineEdit()
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText(
            "mid-40s presenter, navy jacket, studio lighting, facing camera"
        )
        self.prompt_edit.setMaximumHeight(90)
        form.addRow("Character id", self.id_edit)
        form.addRow("Display name", self.name_edit)
        form.addRow("Voice id", self.voice_edit)
        form.addRow("Look", self.prompt_edit)
        root.addWidget(form_box)

        btn_row = QHBoxLayout()
        self.gen_btn = QPushButton("Generate still")
        self.gen_btn.clicked.connect(self._on_generate)
        self.keep_btn = QPushButton("Keep")
        self.keep_btn.clicked.connect(self._on_keep)
        self.again_btn = QPushButton("Again")
        self.again_btn.clicked.connect(self._on_generate)
        self.bake_btn = QPushButton("Bake sheet")
        self.bake_btn.clicked.connect(self._on_bake)
        self.save_btn = QPushButton("Save to registry")
        self.save_btn.clicked.connect(self._on_save)
        for btn in (
            self.gen_btn,
            self.keep_btn,
            self.again_btn,
            self.bake_btn,
            self.save_btn,
        ):
            btn_row.addWidget(btn)
        root.addLayout(btn_row)

        self.still_label = QLabel("Hero still preview")
        self.still_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.still_label.setMinimumHeight(240)
        self.still_label.setStyleSheet("background: #222; color: #ccc;")
        root.addWidget(self.still_label)

        self.history_list = QListWidget()
        self.history_list.setMaximumHeight(80)
        self.history_list.itemClicked.connect(self._on_history_pick)
        root.addWidget(QLabel("Still history (click to preview)"))
        root.addWidget(self.history_list)

        preview_row = QHBoxLayout()
        self.viseme_label = QLabel("Viseme O")
        self.laugh_label = QLabel("Laugh strip")
        for lbl in (self.viseme_label, self.laugh_label):
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setMinimumSize(140, 140)
            lbl.setStyleSheet("background: #333;")
            preview_row.addWidget(lbl)
        root.addLayout(preview_row)

    def _prompt_text(self) -> str:
        name = self.name_edit.text().strip()
        body = self.prompt_edit.toPlainText().strip()
        if name and body:
            return f"{name}: {body}"
        return body or name or "portrait character facing camera"

    def _show_still(self, path: Path) -> None:
        pix = QPixmap(str(path))
        if not pix.isNull():
            self.still_label.setPixmap(
                pix.scaled(
                    self.still_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def _on_generate(self) -> None:
        try:
            still = self._provider.generate_still(
                self._prompt_text(),
                self._locked_hero,
            )
        except Exception as exc:  # noqa: BLE001 — surface provider errors in UI
            QMessageBox.warning(self, "Generation failed", str(exc))
            return
        self._history.append(still)
        self.history_list.addItem(str(still))
        self._show_still(still)

    def _on_keep(self) -> None:
        if not self._history:
            QMessageBox.information(self, "Keep", "Generate a still first.")
            return
        self._locked_hero = self._history[-1]
        QMessageBox.information(self, "Locked", f"Hero locked: {self._locked_hero.name}")

    def _on_history_pick(self, item) -> None:
        path = Path(item.text())
        if path.is_file():
            self._show_still(path)

    def _on_bake(self) -> None:
        if not self._locked_hero:
            QMessageBox.information(
                self,
                "Bake sheet",
                "Keep a hero still before baking the sheet.",
            )
            return
        hero = self._locked_hero
        char_id = self.id_edit.text().strip() or "character"
        dest = repo_root() / "characters" / f"{char_id}.png"
        try:
            self._preview_sheet = self._provider.generate_sheet(hero, dest)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Bake failed", str(exc))
            return
        sheet = CharacterSheet(dest)
        self._sheet_preview = sheet
        self._set_cell_preview(self.viseme_label, sheet.viseme("o"))
        frames = sheet.expression_frames("laugh")
        if frames:
            self._set_cell_preview(self.laugh_label, frames[0])

    def _set_cell_preview(self, label: QLabel, img) -> None:
        tmp = repo_root() / "_frame_cache" / "studio_preview.png"
        tmp.parent.mkdir(exist_ok=True)
        img.save(tmp)
        pix = QPixmap(str(tmp))
        label.setPixmap(
            pix.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )

    def _on_save(self) -> None:
        char_id = self.id_edit.text().strip()
        voice_id = self.voice_edit.text().strip() or char_id
        if not char_id:
            QMessageBox.warning(self, "Save", "Character id is required.")
            return
        sheet_path = repo_root() / "characters" / f"{char_id}.png"
        if not sheet_path.is_file():
            QMessageBox.warning(self, "Save", "Bake a sheet before saving.")
            return
        registry = load_registry()
        upsert_character(
            registry,
            char_id,
            voice_id=voice_id,
            sheet=sheet_path,
            prompt=self.prompt_edit.toPlainText().strip() or None,
            hero=self._locked_hero,
        )
        save_registry(registry)
        QMessageBox.information(
            self,
            "Saved",
            f"Updated characters/registry.yaml with '{char_id}'.",
        )
