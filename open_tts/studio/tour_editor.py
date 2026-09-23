"""Record microphone takes for widget audio tutorials."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from open_tts.audiotour import (
    apply_take,
    decode_audio_b64,
    has_real_audio,
    list_tours,
    load_tour,
    message_text,
    preferred_tour_file,
    save_processed,
    take_wav_path,
)
from open_tts.characters import repo_root
from open_tts.studio.mic import MicSession


class TourEditor(QWidget):
    COL_NUM = 0
    COL_TEXT = 1
    COL_AUDIO = 2

    def __init__(self) -> None:
        super().__init__()
        self._src: Path | None = None
        self._data: dict | None = None
        self._record_row = -1
        self._mic = MicSession(self)
        self._player = None
        self._player_out = None

        root = QVBoxLayout(self)
        pick = QHBoxLayout()
        pick.addWidget(QLabel("Tutorial"))
        self.tour_combo = QComboBox()
        self.tour_combo.setMinimumWidth(280)
        self.tour_combo.currentIndexChanged.connect(self._on_tour_chosen)
        pick.addWidget(self.tour_combo, stretch=1)
        open_btn = QPushButton("Open…")
        open_btn.clicked.connect(self._open_tour)
        pick.addWidget(open_btn)
        root.addLayout(pick)

        btns = QHBoxLayout()
        self.record_btn = QPushButton("Record")
        self.record_btn.setToolTip("Record the selected tutorial step.")
        self.record_btn.clicked.connect(self._toggle_record)
        play_btn = QPushButton("Play")
        play_btn.clicked.connect(self._play_step)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        for b in (self.record_btn, play_btn, save_btn):
            btns.addWidget(b)
        btns.addStretch()
        root.addLayout(btns)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["#", "Line", "Audio"])
        self.table.horizontalHeader().setSectionResizeMode(
            self.COL_TEXT, QHeaderView.ResizeMode.Stretch
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        root.addWidget(self.table, stretch=1)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(72)
        self.log.setPlaceholderText("Tutorial record log")
        root.addWidget(self.log)

        self._refresh_tours()

    def _refresh_tours(self, selected: Path | None = None) -> None:
        self.tour_combo.blockSignals(True)
        self.tour_combo.clear()
        for path in list_tours():
            self.tour_combo.addItem(path.name, str(path))
        self.tour_combo.blockSignals(False)
        if selected is not None:
            idx = self.tour_combo.findData(str(selected.resolve()))
            if idx < 0:
                self.tour_combo.addItem(selected.name, str(selected.resolve()))
                idx = self.tour_combo.findData(str(selected.resolve()))
            if idx >= 0:
                self.tour_combo.setCurrentIndex(idx)
        elif self.tour_combo.count():
            self.tour_combo.setCurrentIndex(0)
            self._on_tour_chosen(0)

    def _on_tour_chosen(self, _index: int = 0) -> None:
        raw = self.tour_combo.currentData()
        if not raw:
            return
        self._load(Path(str(raw)))

    def _open_tour(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open audio tutorial",
            str(repo_root()),
            "Audiotour JSON (*-audiotour.json *.json)",
        )
        if path:
            self._refresh_tours(Path(path))

    def _load(self, path: Path) -> None:
        try:
            self._data = load_tour(preferred_tour_file(path))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "Tutorial", str(exc))
            return
        self._src = path
        self.table.setRowCount(0)
        for i, msg in enumerate(self._data.get("messages") or []):
            self.table.insertRow(i)
            num = QTableWidgetItem(str(msg.get("id", i)))
            num.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            text = QTableWidgetItem(message_text(msg))
            audio = QTableWidgetItem("yes" if has_real_audio(msg) else "—")
            audio.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(i, self.COL_NUM, num)
            self.table.setItem(i, self.COL_TEXT, text)
            self.table.setItem(i, self.COL_AUDIO, audio)
        if self.table.rowCount():
            self.table.setCurrentCell(0, self.COL_TEXT)
        self.log.append(f"Opened {path.name} ({self.table.rowCount()} steps)")

    def _selected_row(self) -> int:
        return self.table.currentRow()

    def _toggle_record(self) -> None:
        if self._mic.recording:
            self._stop_record()
            return
        self._start_record()

    def _start_record(self) -> None:
        if self._src is None or self._data is None:
            QMessageBox.information(self, "Record", "Open a tutorial first.")
            return
        row = self._selected_row()
        if row < 0:
            QMessageBox.information(self, "Record", "Pick a step.")
            return
        try:
            self._mic.start()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Record", str(exc))
            return
        self._record_row = row
        self.record_btn.setText("Stop")
        self.log.append(f"Recording step {row}…")

    def _stop_record(self) -> None:
        row = self._record_row
        self.record_btn.setText("Record")
        if self._src is None or self._data is None or row < 0:
            if self._mic.recording:
                try:
                    self._mic.stop_to_wav(repo_root() / "processed" / "_discard.wav")
                except Exception:
                    pass
            return
        dest = take_wav_path(self._src, row)
        try:
            wav = self._mic.stop_to_wav(dest)
            apply_take(self._data, row, wav)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Record", str(exc))
            return
        item = self.table.item(row, self.COL_AUDIO)
        if item is None:
            item = QTableWidgetItem()
            self.table.setItem(row, self.COL_AUDIO, item)
        item.setText("yes")
        self.log.append(f"Saved step {row} → {wav.name}")

    def _play_step(self) -> None:
        if self._data is None:
            return
        row = self._selected_row()
        messages = self._data.get("messages") or []
        if row < 0 or row >= len(messages):
            QMessageBox.information(self, "Play", "Pick a step.")
            return
        msg = messages[row]
        if not has_real_audio(msg):
            QMessageBox.information(self, "Play", "No recording on this step yet.")
            return
        dest = take_wav_path(self._src, row) if self._src else repo_root() / "processed" / "_play.wav"
        decode_audio_b64(str(msg["base64"]), dest)
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        except ImportError as exc:
            QMessageBox.warning(self, "Play", str(exc))
            return
        if self._player is None:
            self._player = QMediaPlayer(self)
            self._player_out = QAudioOutput(self)
            self._player.setAudioOutput(self._player_out)
        self._player.setSource(QUrl.fromLocalFile(str(dest.resolve())))
        self._player.play()
        self.log.append(f"Playing step {row}")

    def _save(self) -> None:
        if self._src is None or self._data is None:
            QMessageBox.information(self, "Save", "Open a tutorial first.")
            return
        dest = save_processed(self._src, self._data)
        self.log.append(f"Wrote {dest} (source JSON left untouched)")
        QMessageBox.information(
            self,
            "Saved",
            f"Tutorial audio saved to:\n{dest}\n\nThe original {self._src.name} is unchanged.",
        )

