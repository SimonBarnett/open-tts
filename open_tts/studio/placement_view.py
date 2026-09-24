"""Interactive pan/zoom of the hero still before generating clips."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent, QPainter, QPixmap, QWheelEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from open_tts.framing import Placement


class StillPlacementView(QWidget):
    """Drag to pan, wheel or slider to size the model in the initial still."""

    placement_changed = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pix: QPixmap | None = None
        self._placement = Placement()
        self._drag_origin: QPoint | None = None
        self._pan_at_press = (0.0, 0.0)
        self.setMinimumHeight(220)
        self.setStyleSheet("background: #1a1a20; border: 1px solid #444;")
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip("Drag to move. Mouse wheel or Size slider to zoom.")

    def set_pixmap(self, pix: QPixmap | None) -> None:
        self._pix = pix
        self.update()

    def placement(self) -> Placement:
        return self._placement.clamped()

    def set_placement(self, placement: Placement | None) -> None:
        self._placement = (placement or Placement()).clamped()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().window().color())
        if self._pix is None or self._pix.isNull():
            painter.setPen(self.palette().text().color())
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Hero still")
            return
        p = self._placement.clamped()
        target = self.rect().adjusted(4, 4, -4, -4)
        scaled = self._pix.scaled(
            target.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        zw = max(1, int(round(scaled.width() * p.zoom)))
        zh = max(1, int(round(scaled.height() * p.zoom)))
        zoomed = scaled.scaled(
            zw,
            zh,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        max_ox = max(0, (zoomed.width() - target.width()) / 2)
        max_oy = max(0, (zoomed.height() - target.height()) / 2)
        ox = int(round(p.pan_x * max_ox))
        oy = int(round(p.pan_y * max_oy))
        x = target.center().x() - zoomed.width() // 2 + ox
        y = target.center().y() - zoomed.height() // 2 + oy
        painter.setClipRect(target)
        painter.drawPixmap(x, y, zoomed)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.position().toPoint()
            self._pan_at_press = (self._placement.pan_x, self._placement.pan_y)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_origin is None or self._pix is None:
            return
        delta = event.position().toPoint() - self._drag_origin
        # Drag right moves the model right (positive pan).
        span = max(40.0, float(min(self.width(), self.height())))
        pan_x = self._pan_at_press[0] + (delta.x() / span) * 2.0
        pan_y = self._pan_at_press[1] + (delta.y() / span) * 2.0
        self._placement = Placement(
            zoom=self._placement.zoom, pan_x=pan_x, pan_y=pan_y
        ).clamped()
        self.update()
        self.placement_changed.emit(self._placement)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        steps = event.angleDelta().y() / 120.0
        zoom = self._placement.zoom * (1.0 + 0.08 * steps)
        self._placement = Placement(
            zoom=zoom, pan_x=self._placement.pan_x, pan_y=self._placement.pan_y
        ).clamped()
        self.update()
        self.placement_changed.emit(self._placement)


class StillPlacementPanel(QWidget):
    """Placement view + Size slider + Reset."""

    placement_changed = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        hint = QLabel("Move / size the model here before Approve face (then generate clips).")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.view = StillPlacementView()
        self.view.placement_changed.connect(self._on_view_changed)
        layout.addWidget(self.view, stretch=1)
        row = QHBoxLayout()
        row.addWidget(QLabel("Size"))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(100, 400)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self._on_slider)
        row.addWidget(self.zoom_slider, stretch=1)
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.reset)
        row.addWidget(self.reset_btn)
        layout.addLayout(row)

    def set_pixmap(self, pix: QPixmap | None) -> None:
        self.view.set_pixmap(pix)

    def placement(self) -> Placement:
        return self.view.placement()

    def set_placement(self, placement: Placement | None) -> None:
        p = (placement or Placement()).clamped()
        self.view.set_placement(p)
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(int(round(p.zoom * 100)))
        self.zoom_slider.blockSignals(False)

    def reset(self) -> None:
        self.set_placement(Placement())
        self.placement_changed.emit(self.placement())

    def _on_slider(self, value: int) -> None:
        cur = self.view.placement()
        self.view.set_placement(
            Placement(zoom=value / 100.0, pan_x=cur.pan_x, pan_y=cur.pan_y)
        )
        self.placement_changed.emit(self.view.placement())

    def _on_view_changed(self, placement: Placement) -> None:
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(int(round(placement.zoom * 100)))
        self.zoom_slider.blockSignals(False)
        self.placement_changed.emit(placement)
