"""
QSettings-based persistence for window geometry and Pomodoro config.
"""
from __future__ import annotations

import sys
from typing import Any

from PySide6.QtCore import QByteArray, QPoint, QSettings, QSize

from timer_engine import TimerConfig, TimerMode


def _settings_organization() -> str:
    return "PomodoroOverlay"


def _settings_app() -> str:
    return "PomodoroOverlayTimer"


def get_settings() -> QSettings:
    return QSettings(_settings_organization(), _settings_app())


# --- Window state ---

GEOM_KEY = "window/geometry"
STATE_KEY = "window/state"
POS_KEY = "window/pos"
SIZE_KEY = "window/size"
OPACITY_KEY = "window/opacity"
SIZE_PRESET_KEY = "window/size_preset"
CLICK_THROUGH_KEY = "window/click_through"
ALWAYS_ON_TOP_KEY = "window/always_on_top"


def load_window_geometry() -> tuple[QPoint | None, QSize | None]:
    s = get_settings()
    pos_data = s.value(POS_KEY)
    size_data = s.value(SIZE_KEY)
    pos = None
    if pos_data and len(pos_data) == 2:
        try:
            pos = QPoint(int(pos_data[0]), int(pos_data[1]))
        except (TypeError, ValueError):
            pos = None
    size = None
    if size_data and len(size_data) == 2:
        try:
            size = QSize(int(size_data[0]), int(size_data[1]))
        except (TypeError, ValueError):
            size = None
    return pos, size


def save_window_geometry(pos: QPoint, size: QSize) -> None:
    s = get_settings()
    s.setValue(POS_KEY, [pos.x(), pos.y()])
    s.setValue(SIZE_KEY, [size.width(), size.height()])
    s.sync()


def load_window_state() -> QByteArray | None:
    return get_settings().value(STATE_KEY)


def save_window_state(state: QByteArray) -> None:
    s = get_settings()
    s.setValue(STATE_KEY, state)
    s.sync()


def load_opacity() -> float:
    v = get_settings().value(OPACITY_KEY, 0.82)
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.82


def save_opacity(value: float) -> None:
    get_settings().setValue(OPACITY_KEY, value)
    get_settings().sync()


def load_size_preset() -> str:
    v = get_settings().value(SIZE_PRESET_KEY, "M")
    return str(v) if v else "M"


def save_size_preset(value: str) -> None:
    get_settings().setValue(SIZE_PRESET_KEY, value)
    get_settings().sync()


def load_click_through() -> bool:
    v = get_settings().value(CLICK_THROUGH_KEY, False)
    return bool(v)


def save_click_through(value: bool) -> None:
    get_settings().setValue(CLICK_THROUGH_KEY, value)
    get_settings().sync()


def load_always_on_top() -> bool:
    v = get_settings().value(ALWAYS_ON_TOP_KEY, True)
    return bool(v)


def save_always_on_top(value: bool) -> None:
    get_settings().setValue(ALWAYS_ON_TOP_KEY, value)
    get_settings().sync()


# --- Timer config keys ---

WORK_MIN_KEY = "timer/work_minutes"
SHORT_BREAK_MIN_KEY = "timer/short_break_minutes"
LONG_BREAK_MIN_KEY = "timer/long_break_minutes"
SESSIONS_BEFORE_LONG_KEY = "timer/sessions_before_long_break"
AUTO_ADVANCE_KEY = "timer/auto_advance"


def load_timer_config() -> TimerConfig:
    s = get_settings()
    return TimerConfig(
        work_minutes=_int(s.value(WORK_MIN_KEY, 25), 25),
        short_break_minutes=_int(s.value(SHORT_BREAK_MIN_KEY, 5), 5),
        long_break_minutes=_int(s.value(LONG_BREAK_MIN_KEY, 15), 15),
        sessions_before_long_break=_int(s.value(SESSIONS_BEFORE_LONG_KEY, 4), 4),
        auto_advance=_bool(s.value(AUTO_ADVANCE_KEY, True)),
    )


def save_timer_config(config: TimerConfig) -> None:
    s = get_settings()
    s.setValue(WORK_MIN_KEY, config.work_minutes)
    s.setValue(SHORT_BREAK_MIN_KEY, config.short_break_minutes)
    s.setValue(LONG_BREAK_MIN_KEY, config.long_break_minutes)
    s.setValue(SESSIONS_BEFORE_LONG_KEY, config.sessions_before_long_break)
    s.setValue(AUTO_ADVANCE_KEY, config.auto_advance)
    s.sync()


def _int(v: Any, default: int) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def is_click_through_supported() -> bool:
    """Click-through is supported on Windows via WA_TransparentForMouseEvents."""
    return sys.platform == "win32"


def _bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() in ("true", "1", "yes")
    return bool(v)


# --- Size presets (width = height) ---

SIZE_S = 200
SIZE_M = 260
SIZE_L = 320

SIZE_PRESETS: dict[str, int] = {
    "S": SIZE_S,
    "M": SIZE_M,
    "L": SIZE_L,
}
