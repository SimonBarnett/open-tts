"""Model library: pick an existing model or start another; visemes are central."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QObject, QSize, QTimer, Qt, QThread, Signal
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from open_tts.characters import (
    ensure_original_sheets,
    load_registry,
    native_stage_kind,
    persist_hero,
    repo_root,
    resolve_hero,
    resolve_stage_still,
    save_registry,
    set_character_hero,
    slug_character_id,
    stage_source_image,
    upsert_character,
)
from open_tts.prefs import (
    hero_pref_for,
    last_hero,
    last_model,
    remember_hero_for,
    remember_model,
)
from open_tts.imagine import LocalImageProvider, get_image_provider
from open_tts.loops import (
    frame_at,
    install_generated_video,
    list_character_clips,
    resolve_clip,
    resolve_loop,
)
from open_tts.tts import list_tts_voices
from open_tts.framing import (
    STAGE_SIZE,
    Placement,
    apply_placement,
    compose_split_pair,
    frame_monologue,
    is_stage_aspect,
    load_placement,
    save_placement,
)
from open_tts.studio.placement_view import StillPlacementPanel
from open_tts.viseme_sets import DEFAULT_VISEME_SET, ensure_default_viseme_set, viseme_set_path


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


class _VideoWorker(QObject):
    done = Signal(object)
    fail = Signal(str)

    def __init__(self, provider, prompt: str, ref: Path | None, slot: str) -> None:
        super().__init__()
        self._provider = provider
        self._prompt = prompt
        self._ref = ref
        self._slot = slot

    def run(self) -> None:
        try:
            self.done.emit(
                self._provider.generate_video(self._prompt, self._ref, self._slot)
            )
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
        self._locked_video: Path | None = None
        self._face_approved: bool = False
        self._pending_slot: str = "full"
        self._placement: Placement = Placement()
        self._gen_thread: QThread | None = None
        self._gen_worker: _VideoWorker | None = None
        self._player = None
        self._player_out = None
        self.play_clip_btn = None
        self.stop_clip_btn = None
        ensure_default_viseme_set()
        ensure_original_sheets()

        root = QVBoxLayout(self)
        self.stack = QStackedWidget()
        root.addWidget(self.stack)

        page = QWidget()
        page_l = QHBoxLayout(page)

        lib = QVBoxLayout()
        lib.addWidget(QLabel("People"))
        self.model_list = QListWidget()
        self.model_list.setIconSize(QSize(72, 72))
        self.model_list.setMinimumWidth(160)
        self.model_list.itemActivated.connect(self._on_model_activated)
        self.model_list.itemClicked.connect(self._on_model_activated)
        lib.addWidget(self.model_list, stretch=1)
        self.new_btn = QPushButton("New person")
        self.new_btn.clicked.connect(self._on_new_model)
        lib.addWidget(self.new_btn)
        page_l.addLayout(lib, stretch=0)

        detail = QVBoxLayout()
        self.current_model_label = QLabel("Pick someone on the left")
        self.current_model_label.setStyleSheet("font-size: 16px; font-weight: 600;")
        detail.addWidget(self.current_model_label)

        frames = QHBoxLayout()
        self.full_frame_label = QLabel("Full")
        self.split_left_label = QLabel("Left")
        self.split_right_label = QLabel("Right")
        self.split_frame_label = self.split_left_label
        for lbl, caption in (
            (self.full_frame_label, "Full screen"),
            (self.split_left_label, "Left half"),
            (self.split_right_label, "Right half"),
        ):
            col = QVBoxLayout()
            caption_l = QLabel(caption)
            caption_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if lbl is self.full_frame_label:
                lbl.setFixedSize(276, 150)
            else:
                lbl.setFixedSize(138, 150)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setScaledContents(True)
            lbl.setStyleSheet("background: #1a1a20; color: #aaa; border: 1px solid #444;")
            col.addWidget(caption_l)
            col.addWidget(lbl)
            frames.addLayout(col)
        frames.addStretch()
        detail.addLayout(frames)

        self.placement_panel = StillPlacementPanel()
        self.placement_panel.placement_changed.connect(self._on_placement_changed)
        detail.addWidget(self.placement_panel)

        voice_row = QHBoxLayout()
        voice_row.addWidget(QLabel("Voice"))
        self.voice_combo = QComboBox()
        self.voice_combo.setEditable(False)
        self.voice_combo.setMinimumWidth(220)
        self._fill_voice_combo("eve")
        self.voice_combo.currentIndexChanged.connect(self._on_voice_changed)
        voice_row.addWidget(self.voice_combo, stretch=1)
        self.customize_btn = QToolButton()
        self.customize_btn.setText("Customize…")
        self.customize_btn.setCheckable(True)
        self.customize_btn.toggled.connect(self._set_customize)
        voice_row.addWidget(self.customize_btn)
        detail.addLayout(voice_row)

        self.customize_box = QGroupBox("Customize")
        custom = QVBoxLayout(self.customize_box)
        form = QFormLayout()
        self.id_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText(
            "required look: navy jacket, red hair, glasses — becomes a cartoon"
        )
        self.prompt_edit.setMaximumHeight(70)
        form.addRow("Id", self.id_edit)
        form.addRow("Name", self.name_edit)
        form.addRow("Look", self.prompt_edit)
        custom.addLayout(form)

        btn_row = QHBoxLayout()
        self.face_btn = QPushButton("New face")
        self.face_btn.clicked.connect(self._on_generate_still)
        self.again_btn = QPushButton("Again")
        self.again_btn.clicked.connect(self._on_generate_still)
        self.keep_btn = QPushButton("Approve face")
        self.keep_btn.clicked.connect(self._on_keep)
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._on_save)
        for btn in (self.face_btn, self.again_btn, self.keep_btn, self.save_btn):
            btn_row.addWidget(btn)
        custom.addLayout(btn_row)

        using_local = isinstance(self._provider, LocalImageProvider)
        self.status_label = QLabel(
            "New faces show in Full / Left / Right. Right-click a phoneme clip to update it."
        )
        self.status_label.setStyleSheet("color: #c90;" if using_local else "color: #8c8;")
        custom.addWidget(self.status_label)

        custom.addWidget(QLabel("Phoneme clips — right-click to update one. Preview uses Full / Left / Right."))
        self.clip_list = QListWidget()
        self.clip_list.setIconSize(QSize(84, 46))
        self.clip_list.setMaximumHeight(220)
        self.clip_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.clip_list.customContextMenuRequested.connect(self._on_clip_menu)
        self.clip_list.itemClicked.connect(self._on_clip_picked)
        custom.addWidget(self.clip_list)
        self.video_widget = None
        self.history_list = QListWidget()
        self.history_list.setMaximumHeight(56)
        self.history_list.itemClicked.connect(self._on_history_pick)
        custom.addWidget(self.history_list)
        self.customize_box.setVisible(False)
        detail.addWidget(self.customize_box, stretch=1)
        detail.addStretch()
        page_l.addLayout(detail, stretch=1)

        self.back_btn = QPushButton("People")
        self.back_btn.clicked.connect(self._show_picker)
        self.back_btn.hide()
        self.picker_page = page
        self.editor_page = page
        self.stack.addWidget(page)

        self._refresh_model_list()
        saved = last_model()
        ids = load_registry()
        if saved and saved in ids:
            self._enter_model(saved)
        elif "leo" in ids:
            self._enter_model("leo")
        else:
            self._show_picker()
        self._sync_video_enabled()
        QTimer.singleShot(0, self._refresh_still)

    def _fill_voice_combo(self, selected: str | None = None) -> None:
        selected = (selected or "").strip() or "eve"
        self.voice_combo.blockSignals(True)
        self.voice_combo.clear()
        seen: set[str] = set()
        for voice in list_tts_voices():
            voice_id = voice["voice_id"]
            if voice_id in seen:
                continue
            seen.add(voice_id)
            name = voice.get("name") or voice_id
            self.voice_combo.addItem(f"{name} ({voice_id})", voice_id)
        if selected and self.voice_combo.findData(selected) < 0:
            self.voice_combo.addItem(selected, selected)
        idx = self.voice_combo.findData(selected)
        self.voice_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.voice_combo.blockSignals(False)

    def _selected_voice_id(self) -> str:
        data = self.voice_combo.currentData()
        if data:
            return str(data)
        text = self.voice_combo.currentText().strip()
        if text.endswith(")") and "(" in text:
            return text[text.rfind("(") + 1 : -1].strip()
        return text

    def _refresh_model_list(self, selected: str | None = None) -> None:
        selected = selected or self.id_edit.text().strip()
        registry = load_registry()
        self.model_list.blockSignals(True)
        self.model_list.clear()
        for char_id in sorted(registry):
            item = QListWidgetItem(char_id)
            path = resolve_stage_still(
                char_id,
                native_stage_kind(char_id),
                registry.get(char_id),
                extra=hero_pref_for(char_id),
            ) or resolve_hero(
                char_id, registry.get(char_id), extra=hero_pref_for(char_id)
            )
            if path is not None:
                pix = QPixmap(str(path))
                if not pix.isNull():
                    item.setIcon(
                        QIcon(
                            pix.scaled(
                                56,
                                56,
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation,
                            )
                        )
                    )
            self.model_list.addItem(item)
        self.model_list.blockSignals(False)
        if selected:
            matches = self.model_list.findItems(selected, Qt.MatchFlag.MatchExactly)
            if matches:
                self.model_list.setCurrentItem(matches[0])

    def _set_customize(self, open_it: bool) -> None:
        self.customize_btn.blockSignals(True)
        self.customize_btn.setChecked(open_it)
        self.customize_btn.blockSignals(False)
        self.customize_box.setVisible(bool(open_it))
        self.customize_btn.setText("Done" if open_it else "Customize…")

    def _on_voice_changed(self, _index: int = 0) -> None:
        char_id = self.id_edit.text().strip()
        if not char_id:
            return
        registry = load_registry()
        if char_id not in registry:
            return
        registry[char_id]["voice_id"] = self._selected_voice_id()
        save_registry(registry)

    def _show_picker(self) -> None:
        self._refresh_model_list(self.id_edit.text().strip() or last_model())
        self._set_customize(False)
        self.stack.setCurrentWidget(self.picker_page)

    def _show_editor(self) -> None:
        self.stack.setCurrentWidget(self.editor_page)

    def _enter_model(self, char_id: str) -> None:
        self._on_model_picked(char_id)
        remember_model(char_id)
        self.current_model_label.setText(char_id)
        self._show_editor()

    def _on_model_activated(self, item) -> None:
        char_id = item.text().strip() if item is not None else ""
        if char_id:
            self._enter_model(char_id)

    def _on_new_model(self) -> None:
        self.model_list.clearSelection()
        self.id_edit.clear()
        self.name_edit.clear()
        self._fill_voice_combo("eve")
        self.prompt_edit.clear()
        self._history.clear()
        self.history_list.clear()
        self._stop_video()
        self._locked_hero = None
        self._locked_video = None
        self._face_approved = False
        self._still_path = None
        self._preview_sheet = None
        self._placement = Placement()
        self.placement_panel.set_placement(self._placement)
        self.placement_panel.set_pixmap(None)
        self._sync_video_enabled()
        self.current_model_label.setText("New person")
        self._set_customize(True)
        self._show_editor()
        self.name_edit.setFocus()
        self._refresh_clip_list("")
        self.status_label.setText(
            "New face first. Move/size it, then Approve face before any video clip."
        )

    def _on_model_picked(self, char_id: str) -> None:
        if not char_id:
            return
        entry = load_registry().get(char_id) or {}
        self.id_edit.setText(char_id)
        self.name_edit.setText(str(entry.get("display_name") or char_id))
        self._fill_voice_combo(str(entry.get("voice_id") or char_id or "eve"))
        self.prompt_edit.setPlainText(str(entry.get("prompt") or ""))
        self._load_hero_for(char_id, entry)
        self._stop_video()
        loop = resolve_loop(char_id, "full")
        if loop is not None:
            self._locked_video = loop
        self._refresh_clip_list(char_id)
        QTimer.singleShot(0, self._refresh_still)

    def _load_hero_for(self, char_id: str, entry: dict | None = None) -> None:
        path = resolve_hero(char_id, entry, extra=hero_pref_for(char_id), root=repo_root())
        if path is None and last_hero() and last_model() == char_id:
            listed = Path(str(last_hero()))
            if listed.is_file():
                path = listed
        if path is not None:
            self._locked_hero = path
            self._placement = load_placement(path)
            self.placement_panel.set_placement(self._placement)
            display = path
            if "heroes" not in Path(path).parts:
                staged = resolve_stage_still(
                    char_id, native_stage_kind(char_id), entry or {}
                )
                if staged is not None:
                    display = staged
            self._show_still(display)
            self._face_approved = True
            self._sync_video_enabled()
            return
        self._locked_hero = None
        self._still_path = None
        self._face_approved = False
        self._placement = Placement()
        self.placement_panel.set_placement(self._placement)
        self.placement_panel.set_pixmap(None)
        self._sync_video_enabled()

    def _prompt_text(self) -> str:
        name = self.name_edit.text().strip()
        body = self.prompt_edit.toPlainText().strip()
        if name and body:
            return f"{name}: {body}"
        return body or name or "friendly studio presenter"

    def _ensure_id(self) -> str:
        char_id = self.id_edit.text().strip()
        if char_id:
            return char_id
        seed = self.name_edit.text().strip() or self.prompt_edit.toPlainText().strip()
        char_id = slug_character_id(seed)
        self.id_edit.setText(char_id)
        if not self.name_edit.text().strip():
            self.name_edit.setText(seed.split(":")[0].strip() or char_id)
        return char_id

    def _preview_image(self, path: Path | None) -> Path | None:
        if path is None or not path.is_file():
            return None
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            return path
        try:
            frame = frame_at(path, 0, repo_root())
        except FileNotFoundError:
            return None
        return frame if frame.is_file() else None

    def _show_still(self, path: Path) -> None:
        preview = self._preview_image(path) or path
        self._still_path = preview
        pix = QPixmap(str(preview)) if preview.is_file() else QPixmap()
        self.placement_panel.set_pixmap(pix if not pix.isNull() else None)
        self.placement_panel.set_placement(self._placement)
        self._show_frame_versions()

    def _on_placement_changed(self, placement: Placement) -> None:
        self._placement = placement.clamped()
        self._show_frame_versions()

    def _placed_still_image(self):
        from PIL import Image

        if not (self._still_path and self._still_path.is_file()):
            return None
        img = Image.open(self._still_path).convert("RGBA")
        return apply_placement(img, self._placement)

    def _write_placed_hero(self, dest: Path) -> Path:
        """Write the pan/zoomed still used as the I2V / clip reference."""
        from PIL import Image

        src = self._locked_hero or self._still_path
        if src is None or not Path(src).is_file():
            raise FileNotFoundError("No still to place")
        with Image.open(src) as img:
            placed = apply_placement(img, self._placement)
            dest.parent.mkdir(parents=True, exist_ok=True)
            placed.save(dest)
        return dest

    def _show_frame_versions(self) -> None:
        from PIL import Image

        img = self._placed_still_image()
        if img is None:
            char_id = self.id_edit.text().strip()
            raw = stage_source_image(
                char_id,
                load_registry().get(char_id),
                extra=hero_pref_for(char_id),
            )
            img = apply_placement(raw, self._placement) if raw is not None else None
        if img is None:
            return
        preview = (STAGE_SIZE[0] // 2, STAGE_SIZE[1] // 2)
        # Dual = two halves of the screen. No separate "split talking" mode.
        if is_stage_aspect(img.size):
            full = img.resize(preview, Image.Resampling.LANCZOS)
            left = full.crop((0, 0, preview[0] // 2, preview[1]))
            right = full.crop((preview[0] // 2, 0, preview[0], preview[1]))
        else:
            full = frame_monologue(img, preview)
            pair = compose_split_pair(img, img, preview)
            left = pair.crop((0, 0, preview[0] // 2, preview[1]))
            right = pair.crop((preview[0] // 2, 0, preview[0], preview[1]))
        self.full_frame_label.setPixmap(_pil_to_qpixmap(full))
        self.split_left_label.setPixmap(_pil_to_qpixmap(left))
        self.split_right_label.setPixmap(_pil_to_qpixmap(right))
        img.close()

    def _refresh_still(self) -> None:
        if self._still_path and self._still_path.is_file():
            self._show_still(self._still_path)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_still()

    def _refresh_clip_list(self, char_id: str | None = None, selected: str | None = None) -> None:
        char_id = (char_id or self.id_edit.text()).strip()
        selected = selected or self._selected_slot()
        self.clip_list.blockSignals(True)
        self.clip_list.clear()
        for clip in list_character_clips(char_id or "_"):
            mark = "ready" if clip["ready"] else "missing"
            item = QListWidgetItem(f"{clip['label']}  —  {mark}")
            item.setData(Qt.ItemDataRole.UserRole, clip["slot"])
            thumb = self._preview_image(clip.get("path"))
            if thumb is not None:
                pix = QPixmap(str(thumb))
                if not pix.isNull():
                    item.setIcon(
                        QIcon(
                            pix.scaled(
                                84,
                                46,
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation,
                            )
                        )
                    )
            self.clip_list.addItem(item)
        self.clip_list.blockSignals(False)
        if selected:
            for i in range(self.clip_list.count()):
                item = self.clip_list.item(i)
                if item and item.data(Qt.ItemDataRole.UserRole) == selected:
                    self.clip_list.setCurrentItem(item)
                    break
        elif self.clip_list.count():
            self.clip_list.setCurrentRow(0)

    def _selected_slot(self) -> str:
        item = self.clip_list.currentItem() if hasattr(self, "clip_list") else None
        if item is not None:
            slot = item.data(Qt.ItemDataRole.UserRole)
            if slot:
                return str(slot)
        return "full"

    def _on_clip_picked(self, item) -> None:
        slot = str(item.data(Qt.ItemDataRole.UserRole) or "full")
        char_id = self.id_edit.text().strip()
        path = resolve_clip(char_id, slot) if char_id else None
        self._stop_video()
        if path is not None:
            self._locked_video = path
            self._show_still(path)
            self.status_label.setText(f"{slot}: {path.name}")
        else:
            self.status_label.setText(f"{slot}: no image yet — right-click to update")

    def _on_clip_menu(self, pos) -> None:
        item = self.clip_list.itemAt(pos)
        if item is not None:
            self.clip_list.setCurrentItem(item)
            self._on_clip_picked(item)
        menu = QMenu(self)
        update = menu.addAction("Update this clip")
        update.setEnabled(bool(self._face_approved and self._gen_thread is None))
        play = menu.addAction("Play clip")
        stop = menu.addAction("Stop")
        chosen = menu.exec(self.clip_list.mapToGlobal(pos))
        if chosen == update:
            self._on_generate()
        elif chosen == play:
            self._on_play_clip()
        elif chosen == stop:
            self._stop_video()

    def _sync_video_enabled(self) -> None:
        if hasattr(self, "clip_list"):
            self.clip_list.setEnabled(self._gen_thread is None)

    def _set_gen_busy(self, busy: bool, kind: str = "still") -> None:
        self.face_btn.setEnabled(not busy)
        self.again_btn.setEnabled(not busy)
        self.keep_btn.setEnabled(not busy)
        if hasattr(self, "clip_list"):
            self.clip_list.setEnabled(not busy)
        if kind != "video":
            self.face_btn.setText("Drawing face…" if busy else "New face")
        if not busy:
            self.face_btn.setText("New face")
        self._sync_video_enabled()

    def _on_generate_still(self) -> None:
        if self._gen_thread is not None:
            return
        self._ensure_id()
        if not self.prompt_edit.toPlainText().strip() and not self.name_edit.text().strip():
            QMessageBox.information(
                self,
                "New face",
                "Describe the look (navy jacket, red hair…) so the cartoon still matches.",
            )
            self.prompt_edit.setFocus()
            return
        self._set_gen_busy(True, "still")
        self.status_label.setText("Drawing cartoon still…")
        self._face_approved = False
        self._sync_video_enabled()
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

    def _on_still_ready(self, still) -> None:
        path = Path(still)
        if not path.is_file():
            QMessageBox.warning(self, "New face", "Generator returned no image.")
            return
        self._history.append(path)
        self.history_list.addItem(str(path))
        self._face_approved = False
        self._placement = Placement()
        self.placement_panel.set_placement(self._placement)
        self._sync_video_enabled()
        self._show_still(path)
        self.status_label.setText(
            "Still ready. Drag to move, Size to zoom, then Approve face before any video."
        )

    def _on_generate(self) -> None:
        if self._gen_thread is not None:
            return
        if not self._face_approved or not (
            self._locked_hero and self._locked_hero.is_file()
        ):
            QMessageBox.information(
                self,
                "Approve face first",
                "Generate a still with New face, then Approve face. Video comes after that.",
            )
            return
        self._ensure_id()
        slot = self._selected_slot()
        self._pending_slot = slot
        self._placement = self.placement_panel.placement()
        if self._locked_hero and self._locked_hero.is_file():
            save_placement(self._locked_hero, self._placement)
            placed = repo_root() / "characters" / "heroes" / "_placed" / f"{self._ensure_id()}.png"
            try:
                ref = self._write_placed_hero(placed)
            except Exception as exc:  # noqa: BLE001
                QMessageBox.warning(self, "Placement", str(exc))
                return
        else:
            ref = self._locked_hero
        self._set_gen_busy(True, "video")
        self.status_label.setText(f"Generating VIDEO clip: {slot}…")
        thread = QThread(self)
        worker = _VideoWorker(
            self._provider,
            self._prompt_text(),
            ref,
            slot,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.done.connect(self._on_video_ready)
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

    def _on_video_ready(self, video) -> None:
        path = Path(video)
        char_id = self._ensure_id()
        slot = self._pending_slot or self._selected_slot()
        if not (char_id and path.is_file()):
            QMessageBox.warning(self, "Update this clip", "Generator returned no MP4.")
            return
        try:
            loops = install_generated_video(
                path, char_id, repo_root(), slots=[slot]
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Video clip", str(exc))
            return
        installed = loops.get(slot) or path
        self._locked_video = installed if installed.is_file() else path
        self._show_still(self._locked_video)
        if slot == "full":
            thumb = self._thumb_from_video(self._locked_video, char_id)
            if thumb is not None:
                dest = persist_hero(thumb, char_id, repo_root())
                self._locked_hero = dest
                remember_hero_for(char_id, dest)
        registry = load_registry()
        if self._locked_hero:
            set_character_hero(registry, char_id, self._locked_hero, repo_root())
        else:
            registry.setdefault(char_id, {"voice_id": char_id})
        entry = registry[char_id]
        entry["voice_id"] = self._selected_voice_id() or char_id
        entry["prompt"] = self.prompt_edit.toPlainText().strip()
        if self.name_edit.text().strip():
            entry["display_name"] = self.name_edit.text().strip()
        clips = dict(entry.get("clips") or {})
        clips[slot] = str(installed)
        entry["clips"] = clips
        if slot == "full":
            entry["loop"] = str(installed)
        save_registry(registry)
        remember_model(char_id)
        self.registry_changed.emit()
        self._history.append(self._locked_video)
        self.history_list.addItem(str(self._locked_video))
        self.status_label.setText(f"Updated {slot} only: {installed.name}")
        self._refresh_clip_list(char_id, slot)
        self._refresh_model_list(char_id)
        self.current_model_label.setText(char_id)

    def _thumb_from_video(self, video: Path, char_id: str) -> Path | None:
        try:
            frame = frame_at(video, 0, repo_root())
        except FileNotFoundError:
            return None
        return frame if frame.is_file() else None

    def _on_play_clip(self) -> None:
        path = self._locked_video
        if path is None:
            char_id = self.id_edit.text().strip()
            path = resolve_clip(char_id, self._selected_slot()) if char_id else None
        if path is not None:
            self._play_video(path)

    def _ensure_player(self) -> None:
        if self._player is not None or os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            return
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

            self._player = QMediaPlayer(self)
            self._player_out = QAudioOutput(self)
            self._player_out.setVolume(0.0)
            self._player.setAudioOutput(self._player_out)
            if hasattr(self._player, "setLoops"):
                self._player.setLoops(QMediaPlayer.Loops.Infinite)
        except Exception:
            self._player = None

    def _play_video(self, path: Path) -> None:
        self._ensure_player()
        if self._player is None or not path.is_file():
            return
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            return
        from PySide6.QtCore import QUrl

        if self._player_out is not None:
            self._player_out.setVolume(0.0)
        self._player.setSource(QUrl.fromLocalFile(str(path.resolve())))
        self._player.play()

    def _stop_video(self) -> None:
        if self._player is None:
            return
        self._player.stop()

    def _on_still_fail(self, message: str) -> None:
        self.status_label.setText("Face preview failed")
        QMessageBox.warning(self, "Generation failed", message)

    def _on_keep(self) -> None:
        src = None
        for path in reversed(self._history):
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} and path.is_file():
                src = path
                break
        if src is None and self._still_path and self._still_path.is_file():
            src = self._still_path
        if src is None:
            QMessageBox.information(self, "Approve face", "New face first — approve a still, then video.")
            return
        char_id = self._ensure_id() or last_model() or "draft"
        if not self.id_edit.text().strip():
            self.id_edit.setText(char_id)
        dest = persist_hero(src, char_id, repo_root())
        self._locked_hero = dest
        self._placement = self.placement_panel.placement()
        save_placement(dest, self._placement)
        self._face_approved = True
        self._sync_video_enabled()
        registry = load_registry()
        set_character_hero(registry, char_id, dest, repo_root())
        entry = registry[char_id]
        entry["voice_id"] = self._selected_voice_id() or char_id
        entry["prompt"] = self.prompt_edit.toPlainText().strip()
        entry["placement"] = {
            "zoom": self._placement.zoom,
            "pan_x": self._placement.pan_x,
            "pan_y": self._placement.pan_y,
        }
        if self.name_edit.text().strip():
            entry["display_name"] = self.name_edit.text().strip()
        save_registry(registry)
        remember_model(char_id)
        remember_hero_for(char_id, dest)
        self.current_model_label.setText(char_id)
        self._show_still(dest)
        self._refresh_model_list(char_id)
        self.registry_changed.emit()
        self.status_label.setText(
            "Face approved with current size/position. Right-click a phoneme clip to update it."
        )
        QMessageBox.information(
            self,
            "Approved",
            f"Face locked for {char_id} (including move/size). Video clips can be generated now.",
        )

    def _on_history_pick(self, item) -> None:
        path = Path(item.text())
        if path.is_file():
            self._show_still(path)

    def _on_save(self) -> None:
        char_id = self.id_edit.text().strip()
        voice_id = self._selected_voice_id() or char_id
        if not char_id:
            QMessageBox.warning(self, "Save", "Character id is required.")
            return
        if self._locked_hero and self._locked_hero.is_file():
            self._locked_hero = persist_hero(self._locked_hero, char_id, repo_root())
            remember_hero_for(char_id, self._locked_hero)
        set_id = char_id or DEFAULT_VISEME_SET
        sheet_path = viseme_set_path(set_id, repo_root())
        if not sheet_path.is_file():
            ensure_default_viseme_set(repo_root())
            sheet_path = viseme_set_path(DEFAULT_VISEME_SET, repo_root())
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
            f"Model '{char_id}' saved. Phoneme clips update from the clip list.",
        )
