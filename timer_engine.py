"""
Pure Pomodoro timer logic (no Qt).
Uses time.monotonic() for drift-resistant timing.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

# --- Callback types ---
# on_tick(remaining_sec, progress_0_1), on_mode_complete(mode), on_start()
# --- Enums ---


class TimerState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"


class TimerMode(Enum):
    WORK = "work"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"


# --- Config ---


@dataclass
class TimerConfig:
    """Pomodoro durations and cycle settings."""

    work_minutes: int = 25
    short_break_minutes: int = 5
    long_break_minutes: int = 15
    sessions_before_long_break: int = 4
    auto_advance: bool = True

    def duration_seconds(self, mode: TimerMode) -> int:
        if mode == TimerMode.WORK:
            return self.work_minutes * 60
        if mode == TimerMode.SHORT_BREAK:
            return self.short_break_minutes * 60
        if mode == TimerMode.LONG_BREAK:
            return self.long_break_minutes * 60
        return self.work_minutes * 60


# --- Engine ---


@dataclass
class TimerEngine:
    """
    Stateless-style engine: elapsed is computed from monotonic timestamps.
    No drift from QTimer ticks; pause/resume is exact.
    """

    config: TimerConfig = field(default_factory=TimerConfig)
    on_tick: Callable[[float, float], None] | None = None  # (remaining_sec, progress_0_1)
    on_mode_complete: Callable[[TimerMode], None] | None = None
    on_start: Callable[[], None] | None = None

    def __post_init__(self) -> None:
        self._state = TimerState.IDLE
        self._mode = TimerMode.WORK
        self._session_count = 0  # work sessions completed in current cycle
        self._total_pomodoros_since_start = 0  # всего помодоро за сеанс (не сбрасывается)
        self._duration_sec = float(self.config.duration_seconds(self._mode))
        self._start_monotonic: float = 0.0
        self._elapsed_before_pause: float = 0.0

    @property
    def total_pomodoros_since_start(self) -> int:
        return self._total_pomodoros_since_start

    @property
    def state(self) -> TimerState:
        return self._state

    @property
    def mode(self) -> TimerMode:
        return self._mode

    @property
    def session_count(self) -> int:
        return self._session_count

    def _now(self) -> float:
        return time.monotonic()

    def _remaining_seconds(self) -> float:
        if self._state == TimerState.IDLE:
            return self._duration_sec
        if self._state == TimerState.PAUSED:
            return max(0.0, self._duration_sec - self._elapsed_before_pause)
        # RUNNING
        elapsed = self._elapsed_before_pause + (self._now() - self._start_monotonic)
        return max(0.0, self._duration_sec - elapsed)

    def _elapsed_seconds(self) -> float:
        return self._duration_sec - self._remaining_seconds()

    def progress_0_1(self) -> float:
        """Progress as 0..1 (how much time has passed)."""
        if self._duration_sec <= 0:
            return 0.0
        return min(1.0, self._elapsed_seconds() / self._duration_sec)

    def remaining_seconds(self) -> float:
        """Current remaining time in seconds (for display)."""
        return self._remaining_seconds()

    def current_mode_duration_seconds(self) -> float:
        return self._duration_sec

    def tick(self) -> tuple[float, float]:
        """
        Call periodically from UI (e.g. 10–20 Hz).
        Returns (remaining_sec, progress_0_1).
        Handles completion and mode transition.
        """
        remaining = self._remaining_seconds()
        progress = self.progress_0_1()

        if self._state == TimerState.RUNNING and remaining <= 0:
            self._on_complete()

        if self.on_tick:
            self.on_tick(remaining, progress)
        return remaining, progress

    def _on_complete(self) -> None:
        completed_mode = self._mode
        if self.on_mode_complete:
            self.on_mode_complete(completed_mode)
        self._state = TimerState.IDLE
        if completed_mode == TimerMode.WORK:
            self._session_count += 1
            self._total_pomodoros_since_start += 1
        self._advance_mode_if_auto(completed_mode)

    def _advance_mode_if_auto(self, completed: TimerMode) -> None:
        if not self.config.auto_advance:
            return
        if completed == TimerMode.WORK:
            n = self.config.sessions_before_long_break
            if self._session_count >= n:
                self._session_count = 0
                self._mode = TimerMode.LONG_BREAK
            else:
                self._mode = TimerMode.SHORT_BREAK
            self.start()
        elif completed in (TimerMode.SHORT_BREAK, TimerMode.LONG_BREAK):
            self._mode = TimerMode.WORK
            self._duration_sec = float(self.config.duration_seconds(self._mode))
            # Work не автозапускаем — сразу показываем время следующего помодоро

    def start(self) -> None:
        """Start or resume current mode."""
        if self._state == TimerState.RUNNING:
            return
        if self._state == TimerState.IDLE:
            self._duration_sec = float(self.config.duration_seconds(self._mode))
            self._elapsed_before_pause = 0.0
            self._start_monotonic = self._now()
        else:
            # PAUSED -> resume
            self._elapsed_before_pause = self._duration_sec - self._remaining_seconds()
            self._start_monotonic = self._now()
        self._state = TimerState.RUNNING
        if self.on_start:
            self.on_start()

    def pause(self) -> None:
        if self._state != TimerState.RUNNING:
            return
        self._elapsed_before_pause = self._duration_sec - self._remaining_seconds()
        self._state = TimerState.PAUSED

    def toggle_start_pause(self) -> None:
        if self._state == TimerState.RUNNING:
            self.pause()
        else:
            self.start()

    def reset(self) -> None:
        """Reset current session to full duration, stay in same mode."""
        self._state = TimerState.IDLE
        self._duration_sec = float(self.config.duration_seconds(self._mode))
        self._elapsed_before_pause = 0.0
        if self.on_tick:
            self.on_tick(self._duration_sec, 0.0)

    def reset_all_counters(self) -> None:
        """Сброс счётчиков и режима Work (как при новом запуске программы)."""
        self._session_count = 0
        self._total_pomodoros_since_start = 0
        self._mode = TimerMode.WORK
        self._state = TimerState.IDLE
        self._duration_sec = float(self.config.duration_seconds(TimerMode.WORK))
        self._elapsed_before_pause = 0.0
        if self.on_tick:
            self.on_tick(self._duration_sec, 0.0)

    def skip(self) -> None:
        """Finish current session and advance to next mode (with auto logic)."""
        completed = self._mode
        was_running = self._state == TimerState.RUNNING
        self._state = TimerState.IDLE
        if completed == TimerMode.WORK:
            self._session_count += 1
        self._advance_mode_if_auto(completed)
        if not self.config.auto_advance:
            # Manual skip: cycle work -> short -> long -> work
            if completed == TimerMode.WORK:
                self._mode = TimerMode.SHORT_BREAK
            elif completed == TimerMode.SHORT_BREAK:
                self._mode = TimerMode.LONG_BREAK
            else:
                self._mode = TimerMode.WORK
            if was_running and self._mode != TimerMode.WORK:
                self.start()

    def set_mode(self, mode: TimerMode) -> None:
        self._mode = mode
        if self._state != TimerState.IDLE:
            self._state = TimerState.IDLE
        self._duration_sec = float(self.config.duration_seconds(self._mode))
        self._elapsed_before_pause = 0.0
        if self.on_tick:
            self.on_tick(self._duration_sec, 0.0)

    def set_config(self, config: TimerConfig) -> None:
        self.config = config
        if self._state == TimerState.IDLE:
            self._duration_sec = float(self.config.duration_seconds(self._mode))
            if self.on_tick:
                self.on_tick(self._duration_sec, 0.0)
