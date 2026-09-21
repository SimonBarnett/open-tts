"""Studio main window and player UI."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

from open_tts.audio import media_duration
from open_tts.render import (
    invalidate_sentence_audio,
    render_cues_only,
    render_full,
    render_line,
)
from open_tts.script import apply_line_to_script, load_interview, save_interview
from open_tts.studio.project import StudioProject

CUE_CHOICES = ("", "auto", "pause", "laugh", "surprise")


def run_edit_app(project: StudioProject) -> int:
    try:
        from PySide6.QtCore import QTimer, Qt, QUrl
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        from PySide6.QtMultimediaWidgets import QVideoWidget
        from PySide6.QtWidgets import (
            QApplication,
            QComboBox,
            QFormLayout,
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QListWidget,
            QListWidgetItem,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QPlainTextEdit,
            QSlider,
            QSplitter,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print(
            "PySide6 is required for the studio UI. Install with: pip install PySide6",
            file=sys.stderr,
        )
        return 1

    app = QApplication(sys.argv)

    class MainWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.project = project
            self.data = load_interview(project.yaml_path)
            self.segments = project.load_segments()
            self.layout_opts = project.layout(self.data)
            self._audio_duration = media_duration(project.audio_path)
            self._current_line_id = 1
            self._dirty = False
            self._baseline: dict[int, tuple[str, str, str]] = {}
            self._rebuild_baseline()

            self.setWindowTitle(f"open-tts studio — {project.yaml_path.name}")
            self.resize(1200, 720)

            central = QWidget()
            self.setCentralWidget(central)
            root = QVBoxLayout(central)

            splitter = QSplitter(Qt.Horizontal)

            left = QWidget()
            left_l = QVBoxLayout(left)
            self.video_widget = QVideoWidget()
            left_l.addWidget(self.video_widget, stretch=3)

            self.player = QMediaPlayer()
            self.audio_out = QAudioOutput()
            self.player.setAudioOutput(self.audio_out)
            self.player.setVideoOutput(self.video_widget)
            if project.video_path.is_file():
                self.player.setSource(QUrl.fromLocalFile(str(project.video_path)))
            else:
                self.player.setSource(QUrl.fromLocalFile(str(project.audio_path)))

            transport = QHBoxLayout()
            self.btn_play = QPushButton("Play")
            self.btn_pause = QPushButton("Pause")
            self.btn_prev = QPushButton("Prev line")
            self.btn_next = QPushButton("Next line")
            self.btn_loop = QPushButton("Loop line")
            self.loop_line = False
            transport.addWidget(self.btn_play)
            transport.addWidget(self.btn_pause)
            transport.addWidget(self.btn_prev)
            transport.addWidget(self.btn_next)
            transport.addWidget(self.btn_loop)
            left_l.addLayout(transport)

            self.slider = QSlider(Qt.Horizontal)
            self.slider.setMinimum(0)
            self.slider.setMaximum(max(1, int(self._audio_duration * 1000)))
            left_l.addWidget(self.slider)

            self.overlay = QLabel("")
            left_l.addWidget(self.overlay)

            splitter.addWidget(left)

            right = QWidget()
            right_l = QVBoxLayout(right)

            self.line_list = QListWidget()
            for seg in self.segments:
                cue = seg.get("cue") or ""
                item = QListWidgetItem(
                    f"{seg['id']:03d} {seg['speaker']}: {seg['text'][:60]}"
                    + (f" [{cue}]" if cue else "")
                )
                item.setData(Qt.UserRole, seg["id"])
                self.line_list.addItem(item)
            right_l.addWidget(self.line_list)

            insp = QGroupBox("Line inspector")
            form = QFormLayout(insp)
            self.field_speaker = QComboBox()
            chars = sorted({seg["speaker"] for seg in self.segments})
            self.field_speaker.addItems(chars)
            self.field_text = QLineEdit()
            self.field_cue = QComboBox()
            self.field_cue.addItems(CUE_CHOICES)
            form.addRow("Speaker", self.field_speaker)
            form.addRow("Text", self.field_text)
            form.addRow("Cue", self.field_cue)
            right_l.addWidget(insp)

            actions = QHBoxLayout()
            self.btn_save = QPushButton("Save YAML")
            self.btn_reload = QPushButton("Reload YAML")
            self.btn_render_line = QPushButton("Render line")
            self.btn_render_cues = QPushButton("Render cues / layout")
            self.btn_render_full = QPushButton("Render full")
            actions.addWidget(self.btn_save)
            actions.addWidget(self.btn_reload)
            actions.addWidget(self.btn_render_line)
            actions.addWidget(self.btn_render_cues)
            actions.addWidget(self.btn_render_full)
            right_l.addLayout(actions)

            self.log = QPlainTextEdit()
            self.log.setReadOnly(True)
            self.log.setMaximumBlockCount(500)
            right_l.addWidget(self.log)

            splitter.addWidget(right)
            splitter.setStretchFactor(0, 2)
            splitter.setStretchFactor(1, 1)
            root.addWidget(splitter)

            self.btn_play.clicked.connect(self.player.play)
            self.btn_pause.clicked.connect(self.player.pause)
            self.btn_prev.clicked.connect(self._prev_line)
            self.btn_next.clicked.connect(self._next_line)
            self.btn_loop.clicked.connect(self._toggle_loop)
            self.btn_save.clicked.connect(self._save_yaml)
            self.btn_reload.clicked.connect(self._reload_yaml)
            self.btn_render_line.clicked.connect(self._render_line)
            self.btn_render_cues.clicked.connect(self._render_cues)
            self.btn_render_full.clicked.connect(self._render_full)
            self.line_list.currentRowChanged.connect(self._on_list_row)
            self.slider.sliderMoved.connect(self._seek_ms)
            self.player.positionChanged.connect(self._on_position)
            self.field_speaker.currentTextChanged.connect(self._mark_dirty)
            self.field_text.textChanged.connect(self._mark_dirty)
            self.field_cue.currentTextChanged.connect(self._mark_dirty)

            self._timer = QTimer(self)
            self._timer.timeout.connect(self._sync_playhead_line)
            self._timer.start(200)

            self._select_line(1)
            self._log(f"Opened {project.yaml_path} → {project.output_dir}")

        def _rebuild_baseline(self) -> None:
            lines = self.project.lines(self.data)
            self._baseline = {
                i + 1: (
                    ln["speaker"],
                    ln["text"],
                    str(ln.get("cue") or ""),
                )
                for i, ln in enumerate(lines)
            }

        def _log(self, msg: str) -> None:
            self.log.appendPlainText(msg)

        def _mark_dirty(self) -> None:
            self._dirty = True

        def _segment_for_id(self, line_id: int) -> dict | None:
            for seg in self.segments:
                if seg["id"] == line_id:
                    return seg
            return None

        def _select_line(self, line_id: int) -> None:
            self._current_line_id = line_id
            seg = self._segment_for_id(line_id)
            if not seg:
                return
            lines = self.project.lines(self.data)
            ln = lines[line_id - 1]
            self.line_list.blockSignals(True)
            self.line_list.setCurrentRow(line_id - 1)
            self.line_list.blockSignals(False)
            self.field_speaker.blockSignals(True)
            self.field_text.blockSignals(True)
            self.field_cue.blockSignals(True)
            idx = self.field_speaker.findText(ln["speaker"])
            if idx >= 0:
                self.field_speaker.setCurrentIndex(idx)
            else:
                self.field_speaker.addItem(ln["speaker"])
                self.field_speaker.setCurrentText(ln["speaker"])
            self.field_text.setText(ln["text"])
            cue = str(ln.get("cue") or "")
            ci = self.field_cue.findText(cue)
            if ci < 0 and cue:
                self.field_cue.addItem(cue)
                ci = self.field_cue.findText(cue)
            self.field_cue.setCurrentIndex(ci if ci >= 0 else 0)
            self.field_speaker.blockSignals(False)
            self.field_text.blockSignals(False)
            self.field_cue.blockSignals(False)
            self._dirty = False
            self._update_overlay(seg)

        def _update_overlay(self, seg: dict) -> None:
            cue = seg.get("cue") or "auto"
            self.overlay.setText(
                f"Line {seg['id']} · {seg['speaker']} · cue={cue} · "
                f"{seg['start']:.2f}s – {seg['end']:.2f}s"
            )

        def _on_list_row(self, row: int) -> None:
            if row < 0:
                return
            line_id = row + 1
            self._select_line(line_id)
            self._seek_to_line(line_id)

        def _seek_to_line(self, line_id: int, *, bound: str = "start") -> None:
            seg = self._segment_for_id(line_id)
            if not seg:
                return
            key = "start" if bound == "start" else "end"
            ms = int(float(seg[key]) * 1000)
            self.player.setPosition(ms)
            self.slider.setValue(ms)

        def _prev_line(self) -> None:
            if self._current_line_id <= 1:
                self._select_line(1)
                self._seek_to_line(1, bound="start")
                return
            lid = self._current_line_id - 1
            self._select_line(lid)
            self._seek_to_line(lid, bound="end")

        def _next_line(self) -> None:
            lid = min(len(self.segments), self._current_line_id + 1)
            self._select_line(lid)
            self._seek_to_line(lid, bound="start")

        def _toggle_loop(self) -> None:
            self.loop_line = not self.loop_line
            self.btn_loop.setText("Loop line *" if self.loop_line else "Loop line")

        def _seek_ms(self, ms: int) -> None:
            self.player.setPosition(ms)

        def _on_position(self, ms: int) -> None:
            self.slider.blockSignals(True)
            self.slider.setValue(ms)
            self.slider.blockSignals(False)
            if self.loop_line:
                seg = self._segment_for_id(self._current_line_id)
                if seg and ms >= int(float(seg["end"]) * 1000):
                    self._seek_to_line(self._current_line_id)

        def _sync_playhead_line(self) -> None:
            ms = self.player.position()
            t = ms / 1000.0
            for seg in self.segments:
                if float(seg["start"]) <= t < float(seg["end"]):
                    if seg["id"] != self._current_line_id and not self._dirty:
                        self._select_line(seg["id"])
                    break

        def _apply_inspector_to_data(self) -> tuple[str, str, str]:
            line_index = self._current_line_id - 1
            speaker = self.field_speaker.currentText()
            text = self.field_text.text()
            cue_raw = self.field_cue.currentText()
            cue = cue_raw if cue_raw else None
            apply_line_to_script(
                self.data,
                line_index,
                speaker=speaker,
                text=text,
                cue=cue,
            )
            return speaker, text, cue_raw

        def _save_yaml(self) -> None:
            prev = self._baseline.get(self._current_line_id)
            speaker, text, cue = self._apply_inspector_to_data()
            save_interview(self.data, self.project.yaml_path)
            if prev and (prev[0] != speaker or prev[1] != text):
                invalidate_sentence_audio(
                    self.project.output_dir,
                    self._current_line_id,
                    prev[0],
                    speaker,
                )
            self._rebuild_baseline()
            self._dirty = False
            self._log(f"Saved {self.project.yaml_path}")
            self._reload_yaml(silent=True)

        def _reload_yaml(self, silent: bool = False) -> None:
            import json

            self.data = load_interview(self.project.yaml_path)
            if self.project.timings_path.is_file():
                self.segments = json.loads(
                    self.project.timings_path.read_text(encoding="utf-8")
                )
            self._audio_duration = media_duration(self.project.audio_path)
            self.slider.setMaximum(max(1, int(self._audio_duration * 1000)))
            self.line_list.clear()
            for seg in self.segments:
                cue = seg.get("cue") or ""
                item = QListWidgetItem(
                    f"{seg['id']:03d} {seg['speaker']}: {seg['text'][:60]}"
                    + (f" [{cue}]" if cue else "")
                )
                item.setData(Qt.UserRole, seg["id"])
                self.line_list.addItem(item)
            self._rebuild_baseline()
            self._select_line(min(self._current_line_id, len(self.segments)))
            if not silent:
                self._log("Reloaded YAML and timings from disk")

        def _run_render(self, label: str, fn) -> None:
            try:
                self._log(f"{label}…")
                QApplication.processEvents()
                out = fn()
                self._log(f"{label} done → {out}")
                self._reload_yaml(silent=True)
                if self.project.video_path.is_file():
                    self.player.setSource(
                        QUrl.fromLocalFile(str(self.project.video_path))
                    )
            except Exception as exc:
                self._log(f"{label} failed: {exc}")
                self._log(traceback.format_exc())

        def _render_line(self) -> None:
            if self._dirty:
                self._save_yaml()
            lid = self._current_line_id
            prev = self._baseline.get(lid)
            prev_sp = prev[0] if prev else None

            def job():
                return render_line(
                    self.project.yaml_path,
                    self.project.output_dir,
                    lid,
                    previous_speaker=prev_sp,
                )

            self._run_render("Render line", job)

        def _render_cues(self) -> None:
            if self._dirty:
                self._save_yaml()

            def job():
                return render_cues_only(
                    self.project.yaml_path, self.project.output_dir
                )

            self._run_render("Render cues", job)

        def _render_full(self) -> None:
            if self._dirty:
                self._save_yaml()

            def job():
                return render_full(self.project.yaml_path, self.project.output_dir)

            self._run_render("Render full", job)

        def closeEvent(self, event) -> None:
            if self._dirty:
                r = QMessageBox.question(
                    self,
                    "Unsaved changes",
                    "Discard unsaved line edits?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if r != QMessageBox.Yes:
                    event.ignore()
                    return
            super().closeEvent(event)

    win = MainWindow()
    win.show()
    return app.exec()
