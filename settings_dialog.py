"""
Settings dialog: timer durations, opacity, size preset, click-through.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSlider,
    QSpinBox,
    QWidget,
)

from settings import (
    load_click_through,
    load_opacity,
    load_size_preset,
    save_click_through,
    save_opacity,
    save_size_preset,
    SIZE_PRESETS,
)
from timer_engine import TimerConfig

from settings import is_click_through_supported


class SettingsDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None,
        current_config: TimerConfig,
        current_opacity: float,
        current_size_preset: str,
        current_click_through: bool,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pomodoro Settings")
        self._overlay = parent
        self._initial_opacity = current_opacity
        self._current_config = current_config
        self._current_opacity = current_opacity
        self._current_size_preset = current_size_preset
        self._current_click_through = current_click_through

        layout = QFormLayout(self)

        self.work_spin = QSpinBox()
        self.work_spin.setRange(1, 120)
        self.work_spin.setValue(current_config.work_minutes)
        self.work_spin.setSuffix(" min")
        layout.addRow("Work duration:", self.work_spin)

        self.short_break_spin = QSpinBox()
        self.short_break_spin.setRange(1, 60)
        self.short_break_spin.setValue(current_config.short_break_minutes)
        self.short_break_spin.setSuffix(" min")
        layout.addRow("Short break:", self.short_break_spin)

        self.long_break_spin = QSpinBox()
        self.long_break_spin.setRange(1, 60)
        self.long_break_spin.setValue(current_config.long_break_minutes)
        self.long_break_spin.setSuffix(" min")
        layout.addRow("Long break:", self.long_break_spin)

        self.sessions_spin = QSpinBox()
        self.sessions_spin.setRange(1, 20)
        self.sessions_spin.setValue(current_config.sessions_before_long_break)
        layout.addRow("Work sessions before long break:", self.sessions_spin)

        self.auto_advance_cb = QCheckBox("Auto-advance to next mode when session ends")
        self.auto_advance_cb.setChecked(current_config.auto_advance)
        layout.addRow(self.auto_advance_cb)

        # Opacity — при движении слайдера сразу меняем прозрачность окна (превью)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(50, 100)
        self.opacity_slider.setValue(int(current_opacity * 100))
        self.opacity_label = QLabel(f"{current_opacity * 100:.0f}%")
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        layout.addRow("Window opacity:", self.opacity_slider)
        layout.addRow("", self.opacity_label)

        # Size preset
        self.size_combo = QComboBox()
        for key in ("S", "M", "L"):
            self.size_combo.addItem(f"{key} ({SIZE_PRESETS[key]}px)", key)
        idx = self.size_combo.findData(current_size_preset)
        if idx >= 0:
            self.size_combo.setCurrentIndex(idx)
        layout.addRow("Window size:", self.size_combo)

        # Click-through
        if is_click_through_supported():
            self.click_through_cb = QCheckBox("Click-through (mouse passes to windows below)")
            self.click_through_cb.setChecked(current_click_through)
            layout.addRow(self.click_through_cb)
        else:
            self.click_through_cb = None
            layout.addRow("", QLabel("Click-through: not supported on this OS"))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_opacity_changed(self, value: int) -> None:
        self.opacity_label.setText(f"{value}%")
        if self._overlay is not None:
            self._overlay.setWindowOpacity(value / 100.0)

    def reject(self) -> None:
        if self._overlay is not None:
            self._overlay.setWindowOpacity(self._initial_opacity)
        super().reject()

    def get_config(self) -> TimerConfig:
        return TimerConfig(
            work_minutes=self.work_spin.value(),
            short_break_minutes=self.short_break_spin.value(),
            long_break_minutes=self.long_break_spin.value(),
            sessions_before_long_break=self.sessions_spin.value(),
            auto_advance=self.auto_advance_cb.isChecked(),
        )

    def get_opacity(self) -> float:
        return self.opacity_slider.value() / 100.0

    def get_size_preset(self) -> str:
        return self.size_combo.currentData()

    def get_click_through(self) -> bool:
        if self.click_through_cb:
            return self.click_through_cb.isChecked()
        return False
