"""Flow B: table script editor with suggested animation cues."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
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

from open_tts.characters import load_registry, repo_root
from open_tts.cues import ANIMATION_CHOICES, AUTO, cue_from_yaml, cue_to_yaml_value, suggest_cue
from open_tts.script import interview_document, load_interview, save_interview


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
        self.host_edit = QLineEdit("leo")
        self.guest_edit = QLineEdit("eve")
        self.dual_start = QSpinBox()
        self.dual_start.setRange(0, 99)
        self.dual_start.setValue(4)
        self.dual_end = QSpinBox()
        self.dual_end.setRange(0, 99)
        self.dual_end.setValue(5)
        meta_form.addRow("Title", self.title_edit)
        meta_form.addRow("Host id", self.host_edit)
        meta_form.addRow("Guest id", self.guest_edit)
        meta_form.addRow("Dual start turns", self.dual_start)
        meta_form.addRow("Dual end turns", self.dual_end)
        root.addWidget(meta)

        btn_row = QHBoxLayout()
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
        for b in (load_btn, save_btn, add_btn, del_btn, up_btn, down_btn, render_btn):
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

        default = repo_root() / "interviews" / "partner-smart-catalogue.yaml"
        if default.is_file():
            self.load_path(default)

    def _speaker_choices(self) -> list[str]:
        reg = load_registry()
        ids = sorted(reg.keys())
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
        self.host_edit.setText(str(chars.get("host", "leo")))
        self.guest_edit.setText(str(chars.get("guest", "eve")))
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
        self.log.append(f"Loaded {path}")

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
        doc = interview_document(
            title=self.title_edit.text().strip() or "Interview",
            characters={
                "host": self.host_edit.text().strip() or "leo",
                "guest": self.guest_edit.text().strip() or "eve",
            },
            layout={
                "dual_start_turns": self.dual_start.value(),
                "dual_end_turns": self.dual_end.value(),
            },
            script_rows=rows,
        )
        save_interview(doc, path)

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
            proc = subprocess.run(
                cmd,
                cwd=repo_root(),
                capture_output=True,
                text=True,
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
