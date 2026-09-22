"""Model library: pick an existing model or start another; visemes are central."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from open_tts.characters import (
    load_registry,
    persist_hero,
    repo_root,
    resolve_hero,
    save_registry,
    set_character_hero,
    upsert_character,
)
from open_tts.prefs import (
    hero_pref_for,
    last_hero,
    last_model,
    remember_hero,
    remember_hero_for,
    remember_model,
)
from open_tts.imagine import LocalImageProvider, get_image_provider
from open_tts.sprite import COLS, PREVIEW_ROWS, CharacterSheet
from open_tts.viseme_sets import (
    DEFAULT_VISEME_SET,
    ensure_default_viseme_set,
    list_viseme_sets,
    viseme_set_path,
)


def _pil_to_qpixmap(img) -> QPixmap:
    rgba = img.convert("RGBA")
    qimg = QImage(
        rgba.tobytes("raw", "RGBA"),
        rgba.width,
        rgba.height,
        QImage.Format.Format_RGBA8888,
    )
    return QPixmap.fromImage(qimg.copy())


class _StillWorker(QObject):
    done = Signal(object)
    fail = Signal(str)

    def __init__(self, provider, prompt: str, ref: Path | None) -> None:
        super().__init__()
        self._provider = provider
        self._prompt = prompt
        self._ref = ref

    def run(self) -> None:
        try:
            self.done.emit(self._provider.generate_still(self._prompt, self._ref))
        except Exception as exc:  # noqa: BLE001 — surfaced on the UI thread
            self.fail.emit(str(exc))


class CharacterWizard(QWidget):
    registry_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._provider = get_image_provider()
        self._history: list[Path] = []
        self._locked_hero: Path | None = None
        self._still_path: Path | None = None
        self._preview_sheet: Path | None = None
        self._sheet_preview: CharacterSheet | None = None
        self._gen_thread: QThread | None = None
        self._gen_worker: _StillWorker | None = None
        ensure_default_viseme_set()

        root = QVBoxLayout(self)
        self.stack = QStackedWidget()
        root.addWidget(self.stack)

        picker = QWidget()
        picker_l = QVBoxLayout(picker)
        lib_box = QGroupBox("Models (left / right library)")
        lib_l = QVBoxLayout(lib_box)
        self.model_list = QListWidget()
        self.model_list.itemActivated.connect(self._on_model_activated)
        self.model_list.itemClicked.connect(self._on_model_activated)
        lib_btns = QHBoxLayout()
        self.new_btn = QPushButton("New model")
        self.new_btn.clicked.connect(self._on_new_model)
        lib_btns.addWidget(self.new_btn)
        lib_btns.addStretch()
        lib_l.addWidget(QLabel("Select a model, or New model. Last pick reloads next time."))
        lib_l.addWidget(self.model_list)
        lib_l.addLayout(lib_btns)
        picker_l.addWidget(lib_box)
        picker_l.addStretch()
        self.picker_page = picker
        self.stack.addWidget(picker)

        editor = QWidget()
        editor_l = QVBoxLayout(editor)
        nav = QHBoxLayout()
        self.back_btn = QPushButton("Back")
        self.back_btn.clicked.connect(self._show_picker)
        self.current_model_label = QLabel("Model")
        nav.addWidget(self.back_btn)
        nav.addWidget(self.current_model_label, stretch=1)
        editor_l.addLayout(nav)

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
        self.viseme_combo = QComboBox()
        self.viseme_combo.setEditable(True)
        self.viseme_combo.currentTextChanged.connect(self._on_viseme_set_changed)
        form.addRow("Character id", self.id_edit)
        form.addRow("Display name", self.name_edit)
        form.addRow("Voice id", self.voice_edit)
        form.addRow("Look", self.prompt_edit)
        form.addRow("Viseme set", self.viseme_combo)
        editor_l.addWidget(form_box)

        btn_row = QHBoxLayout()
        self.gen_btn = QPushButton("Generate still")
        self.gen_btn.clicked.connect(self._on_generate)
        self.keep_btn = QPushButton("Keep")
        self.keep_btn.clicked.connect(self._on_keep)
        self.again_btn = QPushButton("Again")
        self.again_btn.clicked.connect(self._on_generate)
        self.bake_btn = QPushButton("New viseme set")
        self.bake_btn.clicked.connect(self._on_bake)
        self.save_btn = QPushButton("Save model")
        self.save_btn.clicked.connect(self._on_save)
        for btn in (
            self.gen_btn,
            self.keep_btn,
            self.again_btn,
            self.bake_btn,
            self.save_btn,
        ):
            btn_row.addWidget(btn)
        editor_l.addLayout(btn_row)

        using_local = isinstance(self._provider, LocalImageProvider)
        self.status_label = QLabel(
            "Still provider: local placeholder (no XAI_API_KEY in environment or .env)"
            if using_local
            else "Still provider: xAI Grok Imagine"
        )
        self.status_label.setStyleSheet("color: #c90;" if using_local else "color: #8c8;")
        editor_l.addWidget(self.status_label)

        self.still_label = QLabel("Hero still preview")
        self.still_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.still_label.setMinimumHeight(200)
        self.still_label.setStyleSheet("background: #222; color: #ccc;")
        editor_l.addWidget(self.still_label)

        self.history_list = QListWidget()
        self.history_list.setMaximumHeight(70)
        self.history_list.itemClicked.connect(self._on_history_pick)
        editor_l.addWidget(QLabel("Still history (click to preview)"))
        editor_l.addWidget(self.history_list)

        grid_box = QGroupBox("Viseme set (6 columns: vowels, consonants, expressions)")
        grid_l = QGridLayout(grid_box)
        grid_l.setSpacing(3)
        self._sheet_cells: list[QLabel] = []
        for row in range(PREVIEW_ROWS):
            for col in range(COLS):
                lbl = QLabel()
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setMinimumSize(72, 72)
                lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                lbl.setScaledContents(True)
                lbl.setStyleSheet("background: #1a1a20; border: 1px solid #444;")
                grid_l.addWidget(lbl, row, col)
                self._sheet_cells.append(lbl)
        editor_l.addWidget(grid_box, stretch=1)
        self.editor_page = editor
        self.stack.addWidget(editor)

        self._refresh_viseme_combo()
        self._refresh_model_list()
        self._preview_selected_viseme_set()
        saved = last_model()
        if saved and saved in load_registry():
            self._enter_model(saved)
        else:
            self._show_picker()
            self._load_hero_for(last_model() or "", {})
        QTimer.singleShot(0, self._refresh_still)

    def _refresh_viseme_combo(self, selected: str | None = None) -> None:
        current = selected or self.viseme_combo.currentText() or DEFAULT_VISEME_SET
        self.viseme_combo.blockSignals(True)
        self.viseme_combo.clear()
        for name in list_viseme_sets():
            self.viseme_combo.addItem(name)
        idx = self.viseme_combo.findText(current)
        self.viseme_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.viseme_combo.blockSignals(False)

    def _refresh_model_list(self, selected: str | None = None) -> None:
        selected = selected or self.id_edit.text().strip()
        self.model_list.blockSignals(True)
        self.model_list.clear()
        for char_id in sorted(load_registry()):
            self.model_list.addItem(char_id)
        self.model_list.blockSignals(False)
        if selected:
            matches = self.model_list.findItems(selected, Qt.MatchFlag.MatchExactly)
            if matches:
                self.model_list.setCurrentItem(matches[0])

    def _show_picker(self) -> None:
        self._refresh_model_list(self.id_edit.text().strip() or last_model())
        self.stack.setCurrentWidget(self.picker_page)

    def _show_editor(self) -> None:
        self.stack.setCurrentWidget(self.editor_page)

    def _enter_model(self, char_id: str) -> None:
        self._on_model_picked(char_id)
        remember_model(char_id)
        self.current_model_label.setText(f"Model: {char_id}")
        self._show_editor()

    def _on_model_activated(self, item) -> None:
        char_id = item.text().strip() if item is not None else ""
        if char_id:
            self._enter_model(char_id)

    def _on_new_model(self) -> None:
        self.model_list.clearSelection()
        self.id_edit.clear()
        self.name_edit.clear()
        self.voice_edit.clear()
        self.prompt_edit.clear()
        self._history.clear()
        self.history_list.clear()
        self._locked_hero = None
        self._preview_sheet = None
        self.still_label.setText("Hero still preview")
        self.current_model_label.setText("Model: (new)")
        self._refresh_viseme_combo(DEFAULT_VISEME_SET)
        self._preview_selected_viseme_set()
        self._show_editor()

    def _on_model_picked(self, char_id: str) -> None:
        if not char_id:
            return
        entry = load_registry().get(char_id) or {}
        self.id_edit.setText(char_id)
        self.name_edit.setText(str(entry.get("display_name") or char_id))
        self.voice_edit.setText(str(entry.get("voice_id") or char_id))
        self.prompt_edit.setPlainText(str(entry.get("prompt") or ""))
        viseme = str(entry.get("viseme_set") or DEFAULT_VISEME_SET)
        self._refresh_viseme_combo(viseme)
        self._load_hero_for(char_id, entry)
        self._preview_selected_viseme_set()
        QTimer.singleShot(0, self._refresh_still)

    def _load_hero_for(self, char_id: str, entry: dict | None = None) -> None:
        path = resolve_hero(char_id, entry, extra=hero_pref_for(char_id), root=repo_root())
        if path is None and last_hero() and last_model() == char_id:
            listed = Path(str(last_hero()))
            if listed.is_file():
                path = listed
        if path is not None:
            self._locked_hero = path
            self._show_still(path)
            return
        self._locked_hero = None
        self._still_path = None
        self.still_label.clear()
        self.still_label.setText("Hero still preview")

    def _prompt_text(self) -> str:
        name = self.name_edit.text().strip()
        body = self.prompt_edit.toPlainText().strip()
        if name and body:
            return f"{name}: {body}"
        return body or name or "portrait character facing camera"

    def _show_still(self, path: Path) -> None:
        self._still_path = path
        pix = QPixmap(str(path))
        if pix.isNull():
            return
        target = self.still_label.size()
        if target.width() < 32 or target.height() < 32:
            target.setWidth(max(target.width(), 320))
            target.setHeight(max(target.height(), 200))
        self.still_label.setPixmap(
            pix.scaled(
                target,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _refresh_still(self) -> None:
        if self._still_path and self._still_path.is_file():
            self._show_still(self._still_path)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_still()

    def _set_gen_busy(self, busy: bool) -> None:
        self.gen_btn.setEnabled(not busy)
        self.again_btn.setEnabled(not busy)
        self.gen_btn.setText("Generating…" if busy else "Generate still")

    def _on_generate(self) -> None:
        if self._gen_thread is not None:
            return
        self._set_gen_busy(True)
        self.still_label.setText("Generating still…")
        thread = QThread(self)
        worker = _StillWorker(self._provider, self._prompt_text(), self._locked_hero)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.done.connect(self._on_still_ready)
        worker.fail.connect(self._on_still_fail)
        worker.done.connect(thread.quit)
        worker.fail.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._clear_gen_thread)
        self._gen_thread = thread
        self._gen_worker = worker
        thread.start()

    def _clear_gen_thread(self) -> None:
        self._gen_thread = None
        self._gen_worker = None
        self._set_gen_busy(False)

    def _on_still_ready(self, still) -> None:
        path = Path(still)
        char_id = self.id_edit.text().strip()
        if char_id and path.is_file():
            dest = persist_hero(path, char_id, repo_root())
            registry = load_registry()
            set_character_hero(registry, char_id, dest, repo_root())
            save_registry(registry)
            remember_model(char_id)
            remember_hero_for(char_id, dest)
            self.registry_changed.emit()
            path = dest
            self._locked_hero = dest
        self._history.append(path)
        self.history_list.addItem(str(path))
        self._show_still(path)

    def _on_still_fail(self, message: str) -> None:
        self.still_label.setText("Hero still preview")
        QMessageBox.warning(self, "Generation failed", message)

    def _on_keep(self) -> None:
        if not self._history:
            QMessageBox.information(self, "Keep", "Generate a still first.")
            return
        src = self._history[-1]
        if not src.is_file():
            QMessageBox.warning(self, "Keep", "The last still is gone. Generate again.")
            return
        char_id = self.id_edit.text().strip() or last_model() or "draft"
        if not self.id_edit.text().strip():
            self.id_edit.setText(char_id)
        dest = persist_hero(src, char_id, repo_root())
        self._locked_hero = dest
        registry = load_registry()
        set_character_hero(registry, char_id, dest, repo_root())
        save_registry(registry)
        remember_model(char_id)
        remember_hero_for(char_id, dest)
        self.current_model_label.setText(f"Model: {char_id}")
        self._show_still(dest)
        self.registry_changed.emit()
        QMessageBox.information(self, "Kept", f"Face saved for {char_id}: {dest.name}")

    def _on_history_pick(self, item) -> None:
        path = Path(item.text())
        if path.is_file():
            self._show_still(path)

    def _on_bake(self) -> None:
        if not self._locked_hero:
            QMessageBox.information(
                self,
                "New viseme set",
                "Keep a hero still before baking a new viseme set.",
            )
            return
        hero = self._locked_hero
        set_id = self.viseme_combo.currentText().strip()
        if set_id in (DEFAULT_VISEME_SET, ""):
            set_id = self.id_edit.text().strip() or "character"
        dest = viseme_set_path(set_id, repo_root())
        try:
            self._preview_sheet = self._provider.generate_sheet(hero, dest)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Bake failed", str(exc))
            return
        self._refresh_viseme_combo(set_id)
        self._preview_viseme_cells(CharacterSheet(dest))

    def _on_viseme_set_changed(self, _name: str = "") -> None:
        self._preview_selected_viseme_set()

    def _preview_selected_viseme_set(self) -> None:
        set_id = self.viseme_combo.currentText().strip() or DEFAULT_VISEME_SET
        sheet_path = viseme_set_path(set_id)
        if not sheet_path.is_file():
            return
        self._preview_viseme_cells(CharacterSheet(sheet_path))

    def _preview_viseme_cells(self, sheet: CharacterSheet) -> None:
        self._sheet_preview = sheet
        idx = 0
        for row in range(PREVIEW_ROWS):
            for col in range(COLS):
                self._set_cell_preview(self._sheet_cells[idx], sheet.cell(col, row))
                idx += 1

    def _set_cell_preview(self, label: QLabel, img) -> None:
        label.setPixmap(_pil_to_qpixmap(img))

    def _on_save(self) -> None:
        char_id = self.id_edit.text().strip()
        voice_id = self.voice_edit.text().strip() or char_id
        if not char_id:
            QMessageBox.warning(self, "Save", "Character id is required.")
            return
        if self._locked_hero and self._locked_hero.is_file():
            self._locked_hero = persist_hero(self._locked_hero, char_id, repo_root())
            remember_hero_for(char_id, self._locked_hero)
        set_id = self.viseme_combo.currentText().strip() or DEFAULT_VISEME_SET
        sheet_path = viseme_set_path(set_id, repo_root())
        if not sheet_path.is_file():
            ensure_default_viseme_set(repo_root())
            sheet_path = viseme_set_path(set_id, repo_root())
            if not sheet_path.is_file():
                QMessageBox.warning(
                    self,
                    "Save",
                    "Select an existing viseme set, or Keep a still and click New viseme set.",
                )
                return
        registry = load_registry()
        upsert_character(
            registry,
            char_id,
            voice_id=voice_id,
            sheet=sheet_path,
            prompt=self.prompt_edit.toPlainText().strip() or None,
            hero=self._locked_hero,
            viseme_set=set_id,
            display_name=self.name_edit.text().strip() or None,
        )
        save_registry(registry)
        remember_model(char_id)
        self.current_model_label.setText(f"Model: {char_id}")
        self._refresh_model_list(char_id)
        self.registry_changed.emit()
        QMessageBox.information(
            self,
            "Saved",
            f"Model '{char_id}' uses viseme set '{set_id}'.",
        )
