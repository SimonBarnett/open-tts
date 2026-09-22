"""Flow B: table script editor with suggested animation cues."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal
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
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from open_tts.characters import load_registry, repo_root, resolve_hero
from open_tts.prefs import hero_pref_for, last_cast, last_project, remember_cast, remember_project
from open_tts.cues import ANIMATION_CHOICES, AUTO, cue_from_yaml, cue_to_yaml_value, suggest_cue
from open_tts.overlays import (
    OverlaySpec,
    import_drop,
    overlay_spec,
    overlays_to_yaml,
)
from open_tts.script import interview_document, load_interview, save_interview
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
    COL_ANIM = 3
    COL_NOTES = 4

    def __init__(self) -> None:
        super().__init__()
        self._path: Path | None = None
        self._suppress_suggest = False

        root = QVBoxLayout(self)

        meta = QGroupBox("Interview header")
        meta_form = QFormLayout(meta)
        self.title_edit = QLineEdit()
        self.left_combo = QComboBox()
        self.right_combo = QComboBox()
        self.left_face = QLabel()
        self.right_face = QLabel()
        for face in (self.left_face, self.right_face):
            face.setFixedSize(56, 56)
            face.setScaledContents(True)
            face.setStyleSheet("background: #222; border: 1px solid #555;")
        self.host_edit = QLineEdit("leo")
        self.guest_edit = QLineEdit("eve")
        self.host_edit.hide()
        self.guest_edit.hide()
        self.dual_start = QSpinBox()
        self.dual_start.setRange(0, 99)
        self.dual_start.setValue(4)
        self.dual_end = QSpinBox()
        self.dual_end.setRange(0, 99)
        self.dual_end.setValue(5)
        meta_form.addRow("Title", self.title_edit)
        meta_form.addRow("Left model", self._model_pick_row(self.left_combo, self.left_face))
        meta_form.addRow("Right model", self._model_pick_row(self.right_combo, self.right_face))
        meta_form.addRow("Dual start turns", self.dual_start)
        meta_form.addRow("Dual end turns", self.dual_end)
        self._fill_side_combos()
        self.left_combo.currentTextChanged.connect(self._sync_hidden_roles)
        self.right_combo.currentTextChanged.connect(self._sync_hidden_roles)
        root.addWidget(meta)

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
        root.addWidget(plate)

        btn_row = QHBoxLayout()
        new_btn = QPushButton("New…")
        new_btn.clicked.connect(self._new_project)
        open_btn = QPushButton("Open folder…")
        open_btn.clicked.connect(self._open_folder)
        load_btn = QPushButton("Load YAML…")
        load_btn.clicked.connect(self._load_dialog)
        save_btn = QPushButton("Save YAML…")
        save_btn.clicked.connect(self._save_dialog)
        add_btn = QPushButton("Add line")
        add_btn.clicked.connect(self._add_line)
        del_btn = QPushButton("Delete line")
        del_btn.clicked.connect(self._delete_line)
        up_btn = QPushButton("Move up")
        up_btn.clicked.connect(lambda: self._move_line(-1))
        down_btn = QPushButton("Move down")
        down_btn.clicked.connect(lambda: self._move_line(1))
        render_btn = QPushButton("Render")
        render_btn.clicked.connect(self._render)
        review_btn = QPushButton("Review")
        review_btn.clicked.connect(self._review)
        for b in (
            new_btn,
            open_btn,
            load_btn,
            save_btn,
            add_btn,
            del_btn,
            up_btn,
            down_btn,
            render_btn,
            review_btn,
        ):
            btn_row.addWidget(b)
        root.addLayout(btn_row)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["#", "Speaker", "Text", "Animation", "Notes"])
        self.table.horizontalHeader().setSectionResizeMode(
            self.COL_TEXT, QHeaderView.ResizeMode.Stretch
        )
        self.table.cellChanged.connect(self._on_cell_changed)
        root.addWidget(self.table)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(120)
        root.addWidget(self.log)

        self._apply_last_cast_defaults()
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
        path = resolve_hero(
            char_id,
            load_registry().get(char_id),
            extra=hero_pref_for(char_id),
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
            self._append_row(speaker, text, anim, "")
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

    def _open_folder(self) -> None:
        from open_tts.project import INTERVIEW_YAML, ensure_project_in_folder, projects_root

        start = str(projects_root())
        folder = QFileDialog.getExistingDirectory(self, "Open folder", start)
        if not folder:
            return
        try:
            root = ensure_project_in_folder(Path(folder))
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Open folder", str(exc))
            return
        yaml_path = root / INTERVIEW_YAML
        self.load_path(yaml_path)
        self.log.append(f"Opened folder {root}")

    def _load_dialog(self) -> None:
        start = str(repo_root() / "interviews")
        path, _ = QFileDialog.getOpenFileName(
            self, "Open interview YAML", start, "YAML (*.yaml *.yml)"
        )
        if path:
            self.load_path(Path(path))

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
            row: dict[str, str] = {"speaker": speaker, "text": text}
            if cue:
                row["cue"] = cue
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
        self, speaker: str, text: str, animation: str, notes: str
    ) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, self.COL_NUM, QTableWidgetItem(str(r + 1)))
        self.table.setCellWidget(r, self.COL_SPEAKER, self._speaker_combo(speaker))
        self.table.setItem(r, self.COL_TEXT, QTableWidgetItem(text))
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
            if c in (self.COL_SPEAKER, self.COL_ANIM):
                w = self.table.cellWidget(row, c)
                row_data.append(w)
                self.table.removeCellWidget(row, c)
            else:
                row_data.append(self.table.takeItem(row, c))
        self.table.removeRow(row)
        self.table.insertRow(new_row)
        for c, data in enumerate(row_data):
            if c in (self.COL_SPEAKER, self.COL_ANIM):
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

    def _render(self) -> None:
        if not self._path:
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Save before render",
                str(repo_root() / "interviews" / "draft.yaml"),
                "YAML (*.yaml *.yml)",
            )
            if not path:
                return
            self._path = Path(path)
        self._write_yaml(self._path)
        cmd = [sys.executable, "-m", "open_tts", "render", str(self._path), "--no-video"]
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
