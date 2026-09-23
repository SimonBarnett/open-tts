"""Flow B: table script editor with suggested animation cues."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QInputDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from open_tts.characters import (
    ensure_original_sheets,
    load_registry,
    repo_root,
    resolve_hero,
    resolve_stage_still,
)
from open_tts.prefs import hero_pref_for, last_cast, last_project, remember_cast, remember_project
from open_tts.cues import ANIMATION_CHOICES, AUTO, cue_from_yaml, cue_to_yaml_value, suggest_cue
from open_tts.overlays import (
    OverlaySpec,
    import_drop,
    overlay_spec,
    overlays_to_yaml,
)
from open_tts.script import (
    SCREEN_AUTO,
    SCREEN_CHOICES,
    STAGE_AUTO,
    interview_document,
    load_interview,
    save_interview,
    screen_from_entry,
    side_override,
    split_yaml_value,
)
from open_tts.record import output_dir_for_script, save_line_recording, write_pcm_wav
from open_tts.viseme_sets import NONE_MODEL, characters_to_sides, sides_to_characters


class DropWell(QLabel):
    """Drop an image, video, or text file into the interview."""

    path_changed = Signal(object)

    def __init__(self, kind: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.kind = kind
        self._path: Path | None = None
        self._dest_dir = repo_root() / "interviews" / "assets"
        self.setAcceptDrops(True)
        self.setMinimumHeight(56)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background: #2a2a32; color: #bbb; border: 1px dashed #666;")
        self._reset_caption()

    def _reset_caption(self) -> None:
        self.setText(f"Drop {self.kind} here")

    def set_dest_dir(self, path: Path) -> None:
        self._dest_dir = path

    def path(self) -> Path | None:
        return self._path

    def set_path(self, path: Path | None) -> None:
        self._path = path
        if path and path.is_file():
            self.setText(path.name)
        else:
            self._reset_caption()
        self.path_changed.emit(self._path)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if not urls:
            return
        src = Path(urls[0].toLocalFile())
        if not src.is_file():
            return
        dest_dir = self._dest_dir
        self.set_path(import_drop(src, dest_dir))
        event.acceptProposedAction()


class ScriptEditor(QWidget):
    COL_NUM = 0
    COL_SPEAKER = 1
    COL_TEXT = 2
    COL_SCREEN = 3
    COL_LEFT = 4
    COL_RIGHT = 5
    COL_ANIM = 6
    COL_NOTES = 7

    def __init__(self) -> None:
        super().__init__()
        self._path: Path | None = None
        self._suppress_suggest = False
        self._mic = None
        self._mic_io = None
        self._mic_chunks: list[bytes] = []
        self._mic_fmt = None
        self._mic_timer: QTimer | None = None
        self._record_row = -1
        self._player = None
        self._player_out = None
        ensure_original_sheets()

        root = QVBoxLayout(self)

        cast = QHBoxLayout()
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Title")
        self.left_combo = QComboBox()
        self.right_combo = QComboBox()
        self.left_face = QLabel()
        self.right_face = QLabel()
        for face in (self.left_face, self.right_face):
            face.setFixedSize(72, 72)
            face.setScaledContents(True)
            face.setStyleSheet("background: #222; border: 1px solid #555;")
        self.host_edit = QLineEdit("leo")
        self.guest_edit = QLineEdit("eve")
        self.host_edit.hide()
        self.guest_edit.hide()
        self.dual_start = QSpinBox()
        self.dual_start.setRange(0, 99)
        self.dual_start.setValue(4)
        self.dual_start.setPrefix("first ")
        self.dual_end = QSpinBox()
        self.dual_end.setRange(0, 99)
        self.dual_end.setValue(5)
        self.dual_end.setPrefix("last ")
        cast.addWidget(QLabel("Title"))
        cast.addWidget(self.title_edit, stretch=2)
        cast.addWidget(self.left_face)
        cast.addWidget(QLabel("Left"))
        cast.addWidget(self.left_combo, stretch=1)
        cast.addWidget(self.right_face)
        cast.addWidget(QLabel("Right"))
        cast.addWidget(self.right_combo, stretch=1)
        self._fill_side_combos()
        self.left_combo.currentTextChanged.connect(self._sync_hidden_roles)
        self.right_combo.currentTextChanged.connect(self._sync_hidden_roles)
        root.addLayout(cast)

        extras = QHBoxLayout()
        extras.addWidget(QLabel("Auto-split"))
        extras.addWidget(self.dual_start)
        extras.addWidget(self.dual_end)
        extras.addStretch()
        self.extras_row = QWidget()
        self.extras_row.setLayout(extras)
        self.extras_row.setVisible(False)
        root.addWidget(self.extras_row)

        plate = QGroupBox("Background, title, scrolling text")
        plate_l = QVBoxLayout(plate)
        self.bg_well = DropWell("background image")
        self.title_well = DropWell("title card image")
        self.scroll_file_well = DropWell("scroll .txt")
        self.title_card_edit = QLineEdit()
        self.title_card_edit.setPlaceholderText("Title card text")
        self.scroll_edit = QTextEdit()
        self.scroll_edit.setPlaceholderText("Scrolling credits / crawl — or drop a .txt")
        self.scroll_edit.setMaximumHeight(70)
        wells = QHBoxLayout()
        wells.addWidget(self.bg_well)
        wells.addWidget(self.title_well)
        wells.addWidget(self.scroll_file_well)
        plate_l.addLayout(wells)
        plate_l.addWidget(self.title_card_edit)
        plate_l.addWidget(self.scroll_edit)
        self.scroll_file_well.path_changed.connect(self._load_dropped_scroll)
        plate.setVisible(False)
        self.plate_box = plate
        root.addWidget(plate)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add line")
        add_btn.clicked.connect(self._add_line)
        del_btn = QPushButton("Remove")
        del_btn.clicked.connect(self._delete_line)
        swap_btn = QPushButton("Swap sides")
        swap_btn.setToolTip("From this line on, left and right swap places.")
        swap_btn.clicked.connect(self._swap_sides_on_current)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        self.record_btn = QPushButton("Record")
        self.record_btn.setToolTip("Record the selected line with the microphone.")
        self.record_btn.clicked.connect(self._toggle_record)
        play_btn = QPushButton("Play")
        play_btn.setToolTip("Play the recorded or generated audio for this line.")
        play_btn.clicked.connect(self._play_line)
        render_btn = QPushButton("Make audio")
        render_btn.setToolTip("TTS any missing lines and write full_interview.wav / .mp3.")
        render_btn.clicked.connect(self._render)
        review_btn = QPushButton("Review")
        review_btn.clicked.connect(self._review)
        more = QToolButton()
        more.setText("More")
        more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(more)
        menu.addAction("New project…", self._new_project)
        menu.addAction("Open folder…", self._open_folder)
        menu.addAction("Load YAML…", self._load_dialog)
        menu.addAction("Move line up", lambda: self._move_line(-1))
        menu.addAction("Move line down", lambda: self._move_line(1))
        menu.addAction("Auto-split counts", self._toggle_extras)
        menu.addAction("Background & titles", self._toggle_plate)
        menu.addAction("Make video", self._render_video)
        more.setMenu(menu)
        for b in (
            add_btn,
            del_btn,
            swap_btn,
            save_btn,
            self.record_btn,
            play_btn,
            render_btn,
            review_btn,
            more,
        ):
            btn_row.addWidget(b)
        btn_row.addStretch()
        root.addLayout(btn_row)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["#", "Who", "Line", "Screen", "Left", "Right", "Mood", "Notes"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            self.COL_TEXT, QHeaderView.ResizeMode.Stretch
        )
        self.table.cellChanged.connect(self._on_cell_changed)
        root.addWidget(self.table, stretch=1)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(72)
        self.log.setPlaceholderText("Render log")
        root.addWidget(self.log)

        self._apply_last_cast_defaults()
        self._refresh_faces()
        last = last_project()
        if last and Path(last).is_file():
            self.load_path(Path(last))
        else:
            default = repo_root() / "interviews" / "partner-smart-catalogue.yaml"
            if default.is_file():
                self.load_path(default)

    def _model_ids(self) -> list[str]:
        return sorted(load_registry()) or ["leo", "eve"]

    def _fill_side_combos(self) -> None:
        ids = [NONE_MODEL, *self._model_ids()]
        for box in (self.left_combo, self.right_combo):
            current = box.currentText()
            box.blockSignals(True)
            box.clear()
            box.addItems(ids)
            idx = box.findText(current)
            box.setCurrentIndex(idx if idx >= 0 else 0)
            box.blockSignals(False)
        if self.left_combo.currentText() == NONE_MODEL and self.left_combo.count() > 1:
            self.left_combo.setCurrentText("leo" if "leo" in ids else ids[1])
        if self.right_combo.currentText() == NONE_MODEL and "eve" in ids:
            self.right_combo.setCurrentText("eve")
        self._sync_hidden_roles()

    def _model_pick_row(self, combo: QComboBox, face: QLabel) -> QWidget:
        wrap = QWidget()
        row = QHBoxLayout(wrap)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(combo, stretch=1)
        row.addWidget(face)
        return wrap

    def _set_face(self, label: QLabel, char_id: str) -> None:
        if not char_id or char_id == NONE_MODEL:
            label.clear()
            return
        kind = "left" if label is self.left_face else "right"
        entry = load_registry().get(char_id)
        extra = hero_pref_for(char_id)
        path = resolve_stage_still(char_id, kind, entry, extra=extra) or resolve_hero(
            char_id, entry, extra=extra
        )
        if path is None:
            label.clear()
            return
        pix = QPixmap(str(path))
        if pix.isNull():
            label.clear()
            return
        label.setPixmap(pix)

    def _refresh_faces(self) -> None:
        self._set_face(self.left_face, self.left_combo.currentText())
        self._set_face(self.right_face, self.right_combo.currentText())

    def refresh_models(self) -> None:
        self._fill_side_combos()
        self._refresh_faces()

    def _toggle_extras(self) -> None:
        self.extras_row.setVisible(not self.extras_row.isVisible())

    def _toggle_plate(self) -> None:
        self.plate_box.setVisible(not self.plate_box.isVisible())

    def _apply_last_cast_defaults(self) -> None:
        host, guest = last_cast()
        ids = self._model_ids()
        if host in ids or host == NONE_MODEL:
            self.left_combo.setCurrentText(host)
        if guest in ids or guest == NONE_MODEL:
            self.right_combo.setCurrentText(guest)
        self._sync_hidden_roles()

    def _sync_hidden_roles(self) -> None:
        roles = sides_to_characters(self.left_combo.currentText(), self.right_combo.currentText())
        self.host_edit.setText(roles["host"])
        self.guest_edit.setText(roles["guest"])
        if roles["host"] and roles["guest"]:
            remember_cast(roles["host"], roles["guest"])
        self._refresh_faces()

    def _speaker_choices(self) -> list[str]:
        ids = self._model_ids()
        host = self.host_edit.text().strip()
        guest = self.guest_edit.text().strip()
        for extra in (host, guest):
            if extra and extra not in ids:
                ids.append(extra)
        return ids or ["leo", "eve"]

    def load_path(self, path: Path) -> None:
        data = load_interview(path)
        self._path = path
        self._suppress_suggest = True
        self.title_edit.setText(str(data.get("title", "")))
        chars = data.get("characters") or {}
        self._fill_side_combos()
        left, right = characters_to_sides(chars, data.get("layout") or {})
        if self.left_combo.findText(left) < 0:
            self.left_combo.addItem(left)
        if self.right_combo.findText(right) < 0:
            self.right_combo.addItem(right)
        self.left_combo.setCurrentText(left)
        self.right_combo.setCurrentText(right)
        self._sync_hidden_roles()
        layout = data.get("layout") or {}
        self.dual_start.setValue(int(layout.get("dual_start_turns", 4)))
        self.dual_end.setValue(int(layout.get("dual_end_turns", 5)))

        self.table.setRowCount(0)
        for entry in data["script"]:
            speaker = str(entry["speaker"])
            text = str(entry["text"])
            anim = cue_from_yaml(entry)
            if anim == AUTO:
                anim = suggest_cue(text)
            left_side = side_override(entry, "left")
            right_side = side_override(entry, "right")
            if entry.get("swap") and left_side is None and right_side is None:
                prev_l, prev_r = self._resolved_sides_at(self.table.rowCount())
                left_side, right_side = prev_r, prev_l

            def _side_combo_value(side: str | None) -> str:
                if side is None:
                    return STAGE_AUTO
                return NONE_MODEL if side == "" else side

            self._append_row(
                speaker,
                text,
                anim,
                "",
                screen_from_entry(entry),
                _side_combo_value(left_side),
                _side_combo_value(right_side),
            )
        self._renumber()
        self._suppress_suggest = False
        spec = overlay_spec(data, path)
        self.bg_well.set_path(spec.background)
        self.title_well.set_path(spec.title_image)
        self.title_card_edit.setText(spec.title_text)
        self.scroll_edit.setPlainText(spec.scroll_text)
        self._set_drop_dest(path)
        remember_project(path)
        self.log.append(f"Loaded {path}")

    def _set_drop_dest(self, path: Path) -> None:
        from open_tts.project import interview_yaml_in_project

        dest = path.parent / "assets" if interview_yaml_in_project(path) else (
            repo_root() / "interviews" / "assets"
        )
        dest.mkdir(parents=True, exist_ok=True)
        for well in (self.bg_well, self.title_well, self.scroll_file_well):
            well.set_dest_dir(dest)

    def _new_project(self) -> None:
        from open_tts.project import create_project, project_dir, slug_from_title

        title, ok = QInputDialog.getText(self, "New interview", "Title:")
        if not ok:
            return
        title = title.strip() or "New interview"
        slug = slug_from_title(title)
        dest = project_dir(slug)
        n = 2
        while dest.exists():
            dest = project_dir(f"{slug}-{n}")
            n += 1
            slug = dest.name
        host, guest = last_cast()
        try:
            root = create_project(slug, host=host, guest=guest, title=title)
        except (ValueError, FileExistsError) as exc:
            QMessageBox.warning(self, "New interview", str(exc))
            return
        yaml_path = root / "interview.yaml"
        self.load_path(yaml_path)
        self.log.append(f"Created {root}")

    def _create_folder(self) -> None:
        from open_tts.project import INTERVIEW_YAML, ensure_project_in_folder, projects_root

        start = str(projects_root())
        folder = QFileDialog.getExistingDirectory(self, "Create interview folder", start)
        if not folder:
            return
        try:
            root = ensure_project_in_folder(Path(folder))
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Create", str(exc))
            return
        yaml_path = root / INTERVIEW_YAML
        self.load_path(yaml_path)
        self.log.append(f"Created {root}")

    def _open_folder(self) -> None:
        from open_tts.project import INTERVIEW_YAML, projects_root

        start = str(projects_root())
        folder = QFileDialog.getExistingDirectory(self, "Open interview folder", start)
        if not folder:
            return
        yaml_path = Path(folder) / INTERVIEW_YAML
        if not yaml_path.is_file():
            QMessageBox.warning(
                self,
                "Open",
                f"No {INTERVIEW_YAML} in that folder. Use Create for a new interview.",
            )
            return
        self.load_path(yaml_path)
        self.log.append(f"Opened folder {yaml_path.parent}")

    def _load_dialog(self) -> None:
        start = str(repo_root() / "interviews")
        path, _ = QFileDialog.getOpenFileName(
            self, "Open interview YAML", start, "YAML (*.yaml *.yml)"
        )
        if path:
            self.load_path(Path(path))

    def _save(self) -> None:
        if self._path is not None:
            self._write_yaml(self._path)
            self.log.append(f"Saved {self._path}")
            return
        self._save_dialog()

    def _save_dialog(self) -> None:
        start = str(self._path or repo_root() / "interviews")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save interview YAML", start, "YAML (*.yaml *.yml)"
        )
        if path:
            self._path = Path(path)
            self._write_yaml(self._path)
            self.log.append(f"Saved {self._path}")

    def _write_yaml(self, path: Path) -> None:
        rows: list[dict[str, str]] = []
        for r in range(self.table.rowCount()):
            speaker = self._cell_text(r, self.COL_SPEAKER)
            text = self._cell_text(r, self.COL_TEXT)
            anim = self._cell_text(r, self.COL_ANIM) or AUTO
            cue = cue_to_yaml_value(anim)
            row: dict = {"speaker": speaker, "text": text}
            if cue:
                row["cue"] = cue
            split = split_yaml_value(self._cell_text(r, self.COL_SCREEN) or SCREEN_AUTO)
            if split is not None:
                row["split"] = split
            left_side = self._cell_text(r, self.COL_LEFT) or STAGE_AUTO
            right_side = self._cell_text(r, self.COL_RIGHT) or STAGE_AUTO
            if left_side not in (STAGE_AUTO, ""):
                row["left"] = "" if left_side == NONE_MODEL else left_side
            if right_side not in (STAGE_AUTO, ""):
                row["right"] = "" if right_side == NONE_MODEL else right_side
            rows.append(row)
        left = self.left_combo.currentText()
        right = self.right_combo.currentText()
        roles = sides_to_characters(left, right)
        self.host_edit.setText(roles["host"])
        self.guest_edit.setText(roles["guest"])
        layout: dict = {
            "dual_start_turns": self.dual_start.value(),
            "dual_end_turns": self.dual_end.value(),
        }
        if left and left != NONE_MODEL:
            layout["left"] = left
        if right and right != NONE_MODEL:
            layout["right"] = right
        if (not left or left == NONE_MODEL) or (not right or right == NONE_MODEL) or left == right:
            layout["dual_start_turns"] = 0
            layout["dual_end_turns"] = 0
        spec = OverlaySpec(
            background=self.bg_well.path(),
            title_text=self.title_card_edit.text(),
            title_image=self.title_well.path(),
            title_duration=3.0,
            scroll_text=self.scroll_edit.toPlainText(),
            scroll_duration=6.0,
        )
        doc = interview_document(
            title=self.title_edit.text().strip() or "Interview",
            characters=roles,
            layout=layout,
            script_rows=rows,
            overlays=overlays_to_yaml(spec, path),
        )
        save_interview(doc, path)

    def _load_dropped_scroll(self, path) -> None:
        if path is None:
            return
        p = Path(path)
        if p.suffix.lower() == ".txt" and p.is_file():
            self.scroll_edit.setPlainText(p.read_text(encoding="utf-8"))

    def _append_row(
        self,
        speaker: str,
        text: str,
        animation: str,
        notes: str,
        screen: str = SCREEN_AUTO,
        left: str = STAGE_AUTO,
        right: str = STAGE_AUTO,
    ) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, self.COL_NUM, QTableWidgetItem(str(r + 1)))
        self.table.setCellWidget(r, self.COL_SPEAKER, self._speaker_combo(speaker))
        self.table.setItem(r, self.COL_TEXT, QTableWidgetItem(text))
        self.table.setCellWidget(r, self.COL_SCREEN, self._screen_combo(screen))
        self.table.setCellWidget(r, self.COL_LEFT, self._stage_combo(left))
        self.table.setCellWidget(r, self.COL_RIGHT, self._stage_combo(right))
        self.table.setCellWidget(r, self.COL_ANIM, self._anim_combo(animation))
        self.table.setItem(r, self.COL_NOTES, QTableWidgetItem(notes))

    def _speaker_combo(self, value: str) -> QComboBox:
        box = QComboBox()
        for sp in self._speaker_choices():
            box.addItem(sp)
        idx = box.findText(value)
        if idx >= 0:
            box.setCurrentIndex(idx)
        elif value:
            box.addItem(value)
            box.setCurrentText(value)
        return box

    def _stage_combo(self, value: str) -> QComboBox:
        box = QComboBox()
        box.addItem(STAGE_AUTO)
        box.addItem(NONE_MODEL)
        for sp in self._model_ids():
            box.addItem(sp)
        idx = box.findText(value or STAGE_AUTO)
        if idx >= 0:
            box.setCurrentIndex(idx)
        elif value:
            box.addItem(value)
            box.setCurrentText(value)
        else:
            box.setCurrentIndex(0)
        return box

    def _screen_combo(self, value: str) -> QComboBox:
        box = QComboBox()
        for choice in SCREEN_CHOICES:
            box.addItem(choice)
        idx = box.findText(value or SCREEN_AUTO)
        box.setCurrentIndex(idx if idx >= 0 else 0)
        return box

    def _anim_combo(self, value: str) -> QComboBox:
        box = QComboBox()
        for choice in ANIMATION_CHOICES:
            box.addItem(choice)
        idx = box.findText(value)
        box.setCurrentIndex(idx if idx >= 0 else 0)
        box.currentTextChanged.connect(lambda _t, row=box: self._on_anim_changed(row))
        return box

    def _on_anim_changed(self, combo: QComboBox) -> None:
        if self._suppress_suggest:
            return
        _ = combo

    def _cell_text(self, row: int, col: int) -> str:
        if col == self.COL_SPEAKER:
            w = self.table.cellWidget(row, col)
            return w.currentText() if isinstance(w, QComboBox) else ""
        if col == self.COL_SCREEN:
            w = self.table.cellWidget(row, col)
            return w.currentText() if isinstance(w, QComboBox) else SCREEN_AUTO
        if col in (self.COL_LEFT, self.COL_RIGHT):
            w = self.table.cellWidget(row, col)
            return w.currentText() if isinstance(w, QComboBox) else STAGE_AUTO
        if col == self.COL_ANIM:
            w = self.table.cellWidget(row, col)
            return w.currentText() if isinstance(w, QComboBox) else AUTO
        item = self.table.item(row, col)
        return item.text() if item else ""

    def _on_cell_changed(self, row: int, col: int) -> None:
        if self._suppress_suggest or col != self.COL_TEXT:
            return
        anim_w = self.table.cellWidget(row, self.COL_ANIM)
        if isinstance(anim_w, QComboBox) and anim_w.currentText() != AUTO:
            return
        text = self._cell_text(row, self.COL_TEXT)
        suggested = suggest_cue(text)
        if isinstance(anim_w, QComboBox):
            self._suppress_suggest = True
            idx = anim_w.findText(suggested)
            if idx >= 0:
                anim_w.setCurrentIndex(idx)
            self._suppress_suggest = False

    def _resolved_sides_at(self, row: int) -> tuple[str, str]:
        left = self.left_combo.currentText()
        right = self.right_combo.currentText()
        if left == NONE_MODEL:
            left = ""
        if right == NONE_MODEL:
            right = ""
        for r in range(max(0, row)):
            lval = self._cell_text(r, self.COL_LEFT) or STAGE_AUTO
            rval = self._cell_text(r, self.COL_RIGHT) or STAGE_AUTO
            if lval not in (STAGE_AUTO, ""):
                left = "" if lval == NONE_MODEL else lval
            if rval not in (STAGE_AUTO, ""):
                right = "" if rval == NONE_MODEL else rval
        return left, right

    def _set_stage_combo(self, row: int, col: int, value: str) -> None:
        box = self.table.cellWidget(row, col)
        if not isinstance(box, QComboBox):
            return
        if box.findText(value) < 0 and value:
            box.addItem(value)
        box.setCurrentText(value or STAGE_AUTO)

    def _swap_sides_on_current(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(
                self, "Swap sides", "Select the line where the swap should start."
            )
            return
        left, right = self._resolved_sides_at(row)
        self._set_stage_combo(row, self.COL_LEFT, right or NONE_MODEL)
        self._set_stage_combo(row, self.COL_RIGHT, left or NONE_MODEL)

    def _add_line(self) -> None:
        speakers = self._speaker_choices()
        self._append_row(speakers[0], "", AUTO, "")
        self._renumber()

    def _delete_line(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self._renumber()

    def _move_line(self, delta: int) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        new_row = row + delta
        if new_row < 0 or new_row >= self.table.rowCount():
            return
        self._suppress_suggest = True
        cols = self.table.columnCount()
        row_data = []
        for c in range(cols):
            if c in (
                self.COL_SPEAKER,
                self.COL_SCREEN,
                self.COL_LEFT,
                self.COL_RIGHT,
                self.COL_ANIM,
            ):
                w = self.table.cellWidget(row, c)
                row_data.append(w)
                self.table.removeCellWidget(row, c)
            else:
                row_data.append(self.table.takeItem(row, c))
        self.table.removeRow(row)
        self.table.insertRow(new_row)
        for c, data in enumerate(row_data):
            if c in (
                self.COL_SPEAKER,
                self.COL_SCREEN,
                self.COL_LEFT,
                self.COL_RIGHT,
                self.COL_ANIM,
            ):
                self.table.setCellWidget(new_row, c, data)
            elif data is not None:
                self.table.setItem(new_row, c, data)
        self.table.setCurrentCell(new_row, self.COL_TEXT)
        self._renumber()
        self._suppress_suggest = False

    def _renumber(self) -> None:
        for r in range(self.table.rowCount()):
            item = self.table.item(r, self.COL_NUM)
            if item is None:
                item = QTableWidgetItem()
                self.table.setItem(r, self.COL_NUM, item)
            item.setText(str(r + 1))
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)

    def _ensure_script_path(self) -> Path | None:
        if self._path:
            self._write_yaml(self._path)
            return self._path
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save interview",
            str(repo_root() / "interviews" / "draft.yaml"),
            "YAML (*.yaml *.yml)",
        )
        if not path:
            return None
        self._path = Path(path)
        self._write_yaml(self._path)
        return self._path

    def _output_dir(self) -> Path | None:
        yaml_path = self._ensure_script_path()
        if yaml_path is None:
            return None
        return output_dir_for_script(yaml_path)

    def _current_speaker(self) -> str:
        row = self.table.currentRow()
        if row < 0:
            return ""
        return self._cell_text(row, self.COL_SPEAKER).strip()

    def _toggle_record(self) -> None:
        if self._mic is not None:
            self._stop_record()
            return
        self._start_record()

    def _start_record(self) -> None:
        if self.table.currentRow() < 0:
            if self.table.rowCount() == 0:
                self._add_line()
            self.table.setCurrentCell(0, self.COL_TEXT)
        row = self.table.currentRow()
        speaker = self._current_speaker()
        if not speaker:
            QMessageBox.information(self, "Record", "Pick a line and a speaker first.")
            return
        if self._output_dir() is None:
            return
        try:
            from PySide6.QtMultimedia import QAudioFormat, QAudioSource, QMediaDevices
        except ImportError as exc:
            QMessageBox.warning(self, "Record", f"Qt multimedia is missing: {exc}")
            return
        device = QMediaDevices.defaultAudioInput()
        if device.isNull():
            QMessageBox.warning(self, "Record", "No microphone found.")
            return
        fmt = QAudioFormat()
        fmt.setSampleRate(24000)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if not device.isFormatSupported(fmt):
            fmt = device.preferredFormat()
        source = QAudioSource(device, fmt)
        io = source.start()
        if io is None:
            QMessageBox.warning(self, "Record", "Could not open the microphone.")
            return
        self._mic = source
        self._mic_io = io
        self._mic_fmt = fmt
        self._mic_chunks = []
        self._record_row = row
        self._mic_timer = QTimer(self)
        self._mic_timer.timeout.connect(self._pump_mic)
        self._mic_timer.start(40)
        self.record_btn.setText("Stop")
        self.log.append(f"Recording line {row + 1} ({speaker})…")

    def _pump_mic(self) -> None:
        if self._mic_io is None:
            return
        data = self._mic_io.readAll()
        if data:
            self._mic_chunks.append(bytes(data))

    def _stop_record(self) -> None:
        if self._mic_timer is not None:
            self._mic_timer.stop()
            self._mic_timer = None
        self._pump_mic()
        source = self._mic
        self._mic = None
        self._mic_io = None
        if source is not None:
            source.stop()
        self.record_btn.setText("Record")
        raw = b"".join(self._mic_chunks)
        self._mic_chunks = []
        row = self._record_row
        speaker = (
            self._cell_text(row, self.COL_SPEAKER).strip() if row >= 0 else ""
        )
        out = self._output_dir()
        if not raw or not speaker or out is None:
            self.log.append("Recording discarded (empty).")
            return
        fmt = self._mic_fmt
        width = 2
        rate = 24000
        channels = 1
        if fmt is not None:
            rate = int(fmt.sampleRate() or rate)
            channels = int(fmt.channelCount() or channels)
            try:
                from PySide6.QtMultimedia import QAudioFormat

                kind = fmt.sampleFormat()
                width = {
                    QAudioFormat.SampleFormat.UInt8: 1,
                    QAudioFormat.SampleFormat.Int16: 2,
                    QAudioFormat.SampleFormat.Int32: 4,
                }.get(kind, 2)
            except Exception:
                width = 2
        scratch = out / "_work" / "mic_take.wav"
        write_pcm_wav(
            scratch,
            raw,
            sample_rate=rate,
            channels=channels,
            sample_width=width,
        )
        try:
            mp3, wav = save_line_recording(scratch, out, speaker, row + 1)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Record", str(exc))
            return
        self.log.append(f"Saved {wav.relative_to(out) if wav.is_relative_to(out) else wav}")
        if mp3.is_file():
            self.log.append(f"Also {mp3.name} for other tools.")

    def _play_line(self) -> None:
        row = self.table.currentRow()
        speaker = self._current_speaker()
        out = self._output_dir()
        if row < 0 or not speaker or out is None:
            QMessageBox.information(self, "Play", "Pick a line that has audio.")
            return
        from open_tts.render import sentence_audio_paths

        mp3, wav = sentence_audio_paths(out, speaker, row + 1)
        path = wav if wav.is_file() else mp3
        if not path.is_file():
            QMessageBox.information(
                self,
                "Play",
                "No audio for this line yet. Record it, or Make audio.",
            )
            return
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        except ImportError as exc:
            QMessageBox.warning(self, "Play", str(exc))
            return
        if self._player is None:
            self._player = QMediaPlayer(self)
            self._player_out = QAudioOutput(self)
            self._player.setAudioOutput(self._player_out)
        self._player.setSource(QUrl.fromLocalFile(str(path.resolve())))
        self._player.play()
        self.log.append(f"Playing {path.name}")

    def _render_video(self) -> None:
        self._render(video=True)

    def _render(self, video: bool = False) -> None:
        if not self._ensure_script_path():
            return
        cmd = [sys.executable, "-m", "open_tts", "render", str(self._path)]
        if not video:
            cmd.append("--no-video")
        self.log.append("$ " + " ".join(cmd))
        try:
            env = os.environ.copy()
            env.setdefault("PYTHONIOENCODING", "utf-8")
            proc = subprocess.run(
                cmd,
                cwd=repo_root(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                check=False,
            )
        except OSError as exc:
            QMessageBox.warning(self, "Render failed", str(exc))
            return
        if proc.stdout:
            self.log.append(proc.stdout.rstrip())
        if proc.stderr:
            self.log.append(proc.stderr.rstrip())
        if proc.returncode != 0:
            QMessageBox.warning(self, "Render failed", f"Exit code {proc.returncode}")
        else:
            self.log.append("Render finished.")

    def _review(self) -> None:
        if not self._path:
            self._save_dialog()
        if not self._path:
            return
        self._write_yaml(self._path)
        from open_tts.studio.app import run_edit_app
        from open_tts.studio.project import resolve_edit_target

        try:
            project = resolve_edit_target(self._path)
        except ValueError as exc:
            QMessageBox.warning(self, "Review", str(exc))
            return
        if not project.timings_path.is_file():
            QMessageBox.information(
                self,
                "Review",
                "Render this interview first so timings.json exists.",
            )
            return
        editor = self.window()
        def back() -> None:
            if editor is not None:
                editor.show()
                editor.raise_()
            self.load_path(self._path)
        if editor is not None:
            editor.hide()
        self.log.append(f"Review {project.yaml_path}")
        try:
            run_edit_app(project, on_back=back)
        except Exception as exc:
            if editor is not None:
                editor.show()
                editor.raise_()
            QMessageBox.warning(self, "Review", str(exc))
