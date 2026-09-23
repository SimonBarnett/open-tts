"""Shared microphone capture for interview lines and audiotour steps."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QTimer

from open_tts.record import write_pcm_wav


class MicSession(QObject):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._source = None
        self._io = None
        self._fmt = None
        self._chunks: list[bytes] = []
        self._timer: QTimer | None = None

    @property
    def recording(self) -> bool:
        return self._source is not None

    def start(self) -> None:
        if self.recording:
            raise RuntimeError("Already recording")
        from PySide6.QtMultimedia import QAudioFormat, QAudioSource, QMediaDevices

        device = QMediaDevices.defaultAudioInput()
        if device.isNull():
            raise RuntimeError("No microphone found.")
        fmt = QAudioFormat()
        fmt.setSampleRate(24000)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if not device.isFormatSupported(fmt):
            fmt = device.preferredFormat()
        source = QAudioSource(device, fmt)
        io = source.start()
        if io is None:
            raise RuntimeError("Could not open the microphone.")
        self._source = source
        self._io = io
        self._fmt = fmt
        self._chunks = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._pump)
        self._timer.start(40)

    def _pump(self) -> None:
        if self._io is None:
            return
        data = self._io.readAll()
        if data:
            self._chunks.append(bytes(data))

    def stop_to_wav(self, dest: Path) -> Path:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        self._pump()
        source = self._source
        self._source = None
        self._io = None
        if source is not None:
            source.stop()
        raw = b"".join(self._chunks)
        self._chunks = []
        if not raw:
            raise ValueError("Recording was empty.")
        rate, channels, width = 24000, 1, 2
        fmt = self._fmt
        if fmt is not None:
            rate = int(fmt.sampleRate() or rate)
            channels = int(fmt.channelCount() or channels)
            from PySide6.QtMultimedia import QAudioFormat

            width = {
                QAudioFormat.SampleFormat.UInt8: 1,
                QAudioFormat.SampleFormat.Int16: 2,
                QAudioFormat.SampleFormat.Int32: 4,
            }.get(fmt.sampleFormat(), 2)
        return write_pcm_wav(
            dest, raw, sample_rate=rate, channels=channels, sample_width=width
        )
