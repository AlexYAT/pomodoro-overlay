"""
Frameless overlay window: circular progress, time display, drag, resize.
"""
from __future__ import annotations

import math
import sys
from typing import TYPE_CHECKING


from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QGuiApplication,
    QPainter,
    QPainterPath,
    QPen,
    QScreen,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QMenu,
    QWidget,
)

from settings import (
    is_click_through_supported,
    save_timer_config,
    load_click_through,
    load_opacity,
    load_size_preset,
    load_window_geometry,
    save_click_through,
    save_opacity,
    save_size_preset,
    save_window_geometry,
    SIZE_PRESETS,
)
from settings_dialog import SettingsDialog
from timer_engine import TimerConfig, TimerEngine, TimerMode, TimerState

if TYPE_CHECKING:
    from typing import Callable

# --- Platform click-through ---


def apply_click_through(widget: QWidget, enable: bool) -> None:
    if not is_click_through_supported():
        return
    if enable:
        widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)
    else:
        widget.setAttribute(Qt.WA_TransparentForMouseEvents, False)


# --- Colors per mode ---

MODE_COLORS = {
    TimerMode.WORK: QColor(220, 80, 60),       # tomato
    TimerMode.SHORT_BREAK: QColor(70, 160, 100),
    TimerMode.LONG_BREAK: QColor(60, 120, 180),
}

MODE_LABELS = {
    TimerMode.WORK: "Work",
    TimerMode.SHORT_BREAK: "Short Break",
    TimerMode.LONG_BREAK: "Long Break",
}


def _paint_ring_and_text(
    painter: QPainter,
    w: int,
    h: int,
    progress: float,
    remaining_sec: float,
    mode: TimerMode,
    state: TimerState,
    pulse_phase: float,
    session_count: int = 0,
    total_pomodoros_since_start: int = 0,
) -> None:
    """Draw base ring + progress arc + time; в Work: N (всего за сеанс); в перерывах номер не показывать."""
    side = min(w, h)
    cx, cy = w / 2, h / 2
    margin = 12
    ring_radius = (side / 2) - margin
    ring_width = max(8, ring_radius * 0.12)

    # Base ring (background)
    base_color = QColor(60, 60, 65)
    painter.setPen(QPen(base_color, ring_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(QPointF(cx, cy), ring_radius - ring_width / 2, ring_radius - ring_width / 2)

    # Progress arc (from 12 o'clock, clockwise; progress = how much passed)
    progress_color = MODE_COLORS.get(mode, MODE_COLORS[TimerMode.WORK])
    if state == TimerState.RUNNING and remaining_sec <= 0:
        alpha = int(180 + 75 * math.sin(pulse_phase))
        progress_color = QColor(progress_color.red(), progress_color.green(), progress_color.blue())
        progress_color.setAlpha(min(255, max(0, alpha)))
    painter.setPen(QPen(progress_color, ring_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    span = 360 * progress
    start_angle = 90
    painter.drawArc(
        QRectF(cx - ring_radius, cy - ring_radius, ring_radius * 2, ring_radius * 2),
        int(16 * start_angle),
        int(-16 * span),
    )

    # Время MM:SS (верхний блок по центру)
    m = int(remaining_sec // 60)
    s = int(remaining_sec % 60)
    time_text = f"{m:02d}:{s:02d}"
    font = QFont()
    font.setPointSizeF(max(10, ring_radius * 0.35))
    font.setWeight(QFont.Weight.Medium)
    painter.setFont(font)
    painter.setPen(QColor(240, 240, 240))
    time_rect = QRectF(0, cy - ring_radius * 0.55, w, ring_radius * 0.45)
    painter.drawText(time_rect, Qt.AlignmentFlag.AlignCenter, time_text)

    small_font = QFont()
    small_font.setPointSizeF(max(8, ring_radius * 0.12))
    painter.setFont(small_font)
    painter.setPen(QColor(180, 180, 185))
    mode_text = MODE_LABELS.get(mode, "Work")

    if mode == TimerMode.WORK:
        # Только в Work: номер в цикле (в скобках — всего за сеанс)
        pomodoro_in_cycle = session_count + 1
        pomodoro_in_run = total_pomodoros_since_start + 1
        pomodoro_text = f"{pomodoro_in_cycle} ({pomodoro_in_run})"
        painter.setPen(QColor(220, 220, 225))
        small_font.setPointSizeF(max(9, ring_radius * 0.14))
        painter.setFont(small_font)
        pomodoro_rect = QRectF(0, cy - ring_radius * 0.08, w, ring_radius * 0.28)
        painter.drawText(pomodoro_rect, Qt.AlignmentFlag.AlignCenter, pomodoro_text)
        painter.setPen(QColor(180, 180, 185))
        small_font.setPointSizeF(max(8, ring_radius * 0.12))
        painter.setFont(small_font)
        mode_rect = QRectF(0, cy + ring_radius * 0.22, w, ring_radius * 0.5)
    else:
        # В перерывах: только режим, без номера и скобок
        mode_rect = QRectF(0, cy - ring_radius * 0.05, w, ring_radius * 0.55)
    painter.drawText(mode_rect, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter, mode_text)


class OverlayWindow(QWidget):
    """Frameless, always-on-top overlay with drag, resize, and circular timer."""

    def __init__(self, engine: TimerEngine, on_hide_requested: Callable[[], None] | None = None) -> None:
        super().__init__()
        self._engine = engine
        self._on_hide_requested = on_hide_requested
        self._drag_pos: QPoint | None = None
        self._press_global_pos: QPoint | None = None
        self._resize_edge: int = 0  # 0 = none, 1 = bottom-right corner
        self._min_size = 160
        self._click_threshold_px = 6
        self._max_size = 480

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)

        # Opacity (настройка пользователя; при паузе/ожидании — полностью видимое окно)
        self._saved_opacity = min(1.0, max(0.5, load_opacity()))

        # Size from preset
        preset = load_size_preset()
        side = SIZE_PRESETS.get(preset, SIZE_PRESETS["M"])
        self.resize(side, side)

        # Restore position
        pos, size = load_window_geometry()
        if pos is not None and size is not None:
            self.move(pos)
            self.resize(size)
        else:
            self._center_on_screen()

        # Click-through
        self._click_through = load_click_through()
        apply_click_through(self, self._click_through)

        # Display state (updated each tick; drawn in paintEvent)
        self._display_remaining = float(engine.config.duration_seconds(engine.mode))
        self._display_progress = 0.0
        self._display_mode = engine.mode
        self._display_state = engine.state
        self._pulse_phase = 0.0

        # UI update timer (~15 fps enough for smooth ring)
        self._ui_timer = QTimer(self)
        self._ui_timer.timeout.connect(self._on_ui_tick)
        self._ui_timer.start(66)

        # Pulse for completion
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._on_pulse_tick)
        self._pulse_phase = 0.0

        # Моргание окна при завершении перерыва
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._on_blink_tick)
        self._blink_count = 0
        self._opacity_before_blink = self.windowOpacity()

        engine.on_tick = lambda rem, prog: None  # we poll via tick() in _on_ui_tick
        engine.on_mode_complete = self._on_mode_complete

        self._apply_opacity_for_state()

    def _apply_opacity_for_state(self) -> None:
        """На паузе / ожидании старта — непрозрачное окно поверх всех (напоминание после перерыва)."""
        if self._blink_timer.isActive():
            return
        if self._engine.state in (TimerState.IDLE, TimerState.PAUSED):
            self.setWindowOpacity(1.0)
            self.raise_()
        else:
            self.setWindowOpacity(self._saved_opacity)

    def _center_on_screen(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)

    def _on_ui_tick(self) -> None:
        prev_state = self._display_state
        remaining, progress = self._engine.tick()
        self._display_remaining = remaining
        self._display_progress = progress
        self._display_mode = self._engine.mode
        self._display_state = self._engine.state
        if self._display_state != prev_state:
            self._apply_opacity_for_state()
        self.update()

    def _on_pulse_tick(self) -> None:
        self._pulse_phase += 0.2
        self.update()

    def _on_mode_complete(self, mode: TimerMode) -> None:
        self._pulse_phase = 0.0
        if not self._pulse_timer.isActive():
            self._pulse_timer.start(50)
        # При завершении перерыва — сразу показать время следующего помодоро и моргание
        if mode in (TimerMode.SHORT_BREAK, TimerMode.LONG_BREAK):
            self._on_ui_tick()
            self._start_blink()
        QTimer.singleShot(3000, self._stop_pulse)

    def _start_blink(self) -> None:
        if self._blink_timer.isActive():
            return
        self._apply_opacity_for_state()
        self._opacity_before_blink = 1.0
        self._blink_count = 0
        self._blink_timer.start(280)

    def _on_blink_tick(self) -> None:
        self._blink_count += 1
        if self._blink_count >= 10:
            self._blink_timer.stop()
            self._apply_opacity_for_state()
            self.raise_()
            return
        if self._blink_count % 2 == 1:
            self.setWindowOpacity(0.35)
        else:
            self.setWindowOpacity(1.0)

    def _stop_pulse(self) -> None:
        self._pulse_timer.stop()
        self._pulse_phase = 0.0
        self._on_ui_tick()

    def paintEvent(self, event: object) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        w, h = self.width(), self.height()
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 14, 14)
        painter.fillPath(path, QColor(45, 45, 50, 250))
        _paint_ring_and_text(
            painter, w, h,
            self._display_progress,
            self._display_remaining,
            self._display_mode,
            self._display_state,
            self._pulse_phase,
            self._engine.session_count,
            self._engine.total_pomodoros_since_start,
        )

    def _in_resize_zone(self, pos: QPoint) -> bool:
        r = 20
        return pos.x() >= self.width() - r and pos.y() >= self.height() - r

    def mousePressEvent(self, event: object) -> None:
        e = event
        if e.button() == Qt.MouseButton.LeftButton:
            if self._in_resize_zone(e.position().toPoint()):
                self._resize_edge = 1
                self._resize_start_pos = e.globalPosition().toPoint()
                self._resize_start_geo = self.geometry()
                self._press_global_pos = None
            else:
                self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self._press_global_pos = e.globalPosition().toPoint()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, event: object) -> None:
        e = event
        if self._resize_edge == 1:
            delta = e.globalPosition().toPoint() - self._resize_start_pos
            new_w = max(self._min_size, min(self._max_size, self._resize_start_geo.width() + delta.x()))
            new_h = max(self._min_size, min(self._max_size, self._resize_start_geo.height() + delta.y()))
            side = int(min(new_w, new_h))
            self.resize(side, side)
            return
        if self._drag_pos is not None:
            self.move(e.globalPosition().toPoint() - self._drag_pos)
            return
        if self._in_resize_zone(e.position().toPoint()):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, event: object) -> None:
        e = event
        if e.button() == Qt.MouseButton.LeftButton:
            was_resize = self._resize_edge == 1
            release_pos = e.globalPosition().toPoint()
            if not was_resize and self._press_global_pos is not None:
                dx = release_pos.x() - self._press_global_pos.x()
                dy = release_pos.y() - self._press_global_pos.y()
                if dx * dx + dy * dy <= self._click_threshold_px * self._click_threshold_px:
                    self._engine.toggle_start_pause()
            self._press_global_pos = None
            self._drag_pos = None
            self._resize_edge = 0
            save_window_geometry(self.pos(), self.size())
        super().mouseReleaseEvent(e)

    def closeEvent(self, event: object) -> None:
        save_window_geometry(self.pos(), self.size())
        self._ui_timer.stop()
        self._pulse_timer.stop()
        super().closeEvent(event)

    def keyPressEvent(self, event: object) -> None:
        k = event.key()
        if k == Qt.Key.Key_Space:
            self._engine.toggle_start_pause()
            event.accept()
            return
        if k == Qt.Key.Key_R:
            self._engine.reset()
            event.accept()
            return
        if k == Qt.Key.Key_S:
            self._engine.skip()
            event.accept()
            return
        if k == Qt.Key.Key_Escape:
            if self._on_hide_requested:
                self._on_hide_requested()
            event.accept()
            return
        super().keyPressEvent(event)

    def _reset_all_counters(self) -> None:
        self._engine.reset_all_counters()
        self._on_ui_tick()
        self._apply_opacity_for_state()

    def contextMenuEvent(self, event: object) -> None:
        menu = QMenu(self)
        act_start = QAction("Start / Pause (Space)", self)
        act_start.triggered.connect(self._engine.toggle_start_pause)
        menu.addAction(act_start)
        menu.addAction("Reset (R)", self._engine.reset)
        menu.addAction("Skip (S)", self._engine.skip)
        menu.addSeparator()
        menu.addAction("Work", lambda: self._engine.set_mode(TimerMode.WORK))
        menu.addAction("Short Break", lambda: self._engine.set_mode(TimerMode.SHORT_BREAK))
        menu.addAction("Long Break", lambda: self._engine.set_mode(TimerMode.LONG_BREAK))
        menu.addSeparator()
        menu.addAction("Reset all counters", self._reset_all_counters)
        menu.addSeparator()
        menu.addAction("Settings...", self._open_settings)
        menu.addSeparator()
        if self._on_hide_requested:
            menu.addAction("Hide (Esc)", self._on_hide_requested)
        menu.addAction("Quit", QApplication.instance().quit)
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        menu.exec(self.mapToGlobal(pos))

    def _open_settings(self) -> None:
        dialog = SettingsDialog(
            self,
            self._engine.config,
            self._saved_opacity,
            load_size_preset(),
            self._click_through,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            cfg = dialog.get_config()
            save_timer_config(cfg)
            self.set_engine_config(cfg)
            self.set_opacity(dialog.get_opacity())
            self.set_size_preset(dialog.get_size_preset())
            self.set_click_through(dialog.get_click_through())

    # --- Public API for main/settings ---

    def set_opacity(self, value: float) -> None:
        self._saved_opacity = min(1.0, max(0.5, value))
        save_opacity(self._saved_opacity)
        if self._engine.state == TimerState.RUNNING:
            self.setWindowOpacity(self._saved_opacity)
        else:
            self.setWindowOpacity(1.0)

    def set_size_preset(self, preset: str) -> None:
        side = SIZE_PRESETS.get(preset, SIZE_PRESETS["M"])
        self.resize(side, side)
        save_size_preset(preset)

    def set_click_through(self, enable: bool) -> None:
        self._click_through = enable
        apply_click_through(self, enable)
        save_click_through(enable)

    def click_through_enabled(self) -> bool:
        return self._click_through

    def set_engine_config(self, config: TimerConfig) -> None:
        self._engine.set_config(config)
        self._on_ui_tick()

    def get_engine(self) -> TimerEngine:
        return self._engine
