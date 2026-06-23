"""
Basic tests for timer_engine (no Qt).
"""
from __future__ import annotations

import time
import unittest

from timer_engine import TimerConfig, TimerEngine, TimerMode, TimerState


class TestTimerConfig(unittest.TestCase):
    def test_duration_seconds(self) -> None:
        cfg = TimerConfig(work_minutes=25, short_break_minutes=5, long_break_minutes=15)
        self.assertEqual(cfg.duration_seconds(TimerMode.WORK), 25 * 60)
        self.assertEqual(cfg.duration_seconds(TimerMode.SHORT_BREAK), 5 * 60)
        self.assertEqual(cfg.duration_seconds(TimerMode.LONG_BREAK), 15 * 60)


class TestTimerEngine(unittest.TestCase):
    def test_initial_state(self) -> None:
        engine = TimerEngine()
        self.assertEqual(engine.state, TimerState.IDLE)
        self.assertEqual(engine.mode, TimerMode.WORK)
        self.assertEqual(engine.remaining_seconds(), 25 * 60)
        self.assertEqual(engine.progress_0_1(), 0.0)

    def test_start_pause(self) -> None:
        cfg = TimerConfig(work_minutes=1)
        engine = TimerEngine(config=cfg)
        engine.start()
        self.assertEqual(engine.state, TimerState.RUNNING)
        engine.tick()
        engine.pause()
        self.assertEqual(engine.state, TimerState.PAUSED)
        r1 = engine.remaining_seconds()
        time.sleep(0.05)
        r2 = engine.remaining_seconds()
        self.assertAlmostEqual(r1, r2, delta=0.1)

    def test_reset(self) -> None:
        engine = TimerEngine(config=TimerConfig(work_minutes=25))
        engine.start()
        engine.tick()
        engine.reset()
        self.assertEqual(engine.state, TimerState.IDLE)
        self.assertAlmostEqual(engine.remaining_seconds(), 25 * 60, delta=1)

    def test_skip_cycles_mode(self) -> None:
        engine = TimerEngine(config=TimerConfig(work_minutes=1, auto_advance=False))
        engine.start()
        engine.skip()
        self.assertEqual(engine.mode, TimerMode.SHORT_BREAK)
        engine.skip()
        self.assertEqual(engine.mode, TimerMode.LONG_BREAK)
        engine.skip()
        self.assertEqual(engine.mode, TimerMode.WORK)

    def test_progress_increases_when_running(self) -> None:
        cfg = TimerConfig(work_minutes=1)
        engine = TimerEngine(config=cfg)
        engine.start()
        p0 = engine.progress_0_1()
        time.sleep(0.15)
        engine.tick()
        p1 = engine.progress_0_1()
        self.assertGreater(p1, p0)

    def test_reset_all_counters(self) -> None:
        engine = TimerEngine(config=TimerConfig(work_minutes=25))
        engine.start()
        engine._session_count = 3
        engine._total_pomodoros_since_start = 7
        engine._mode = TimerMode.SHORT_BREAK
        engine.reset_all_counters()
        self.assertEqual(engine.state, TimerState.IDLE)
        self.assertEqual(engine.mode, TimerMode.WORK)
        self.assertEqual(engine.session_count, 0)
        self.assertEqual(engine.total_pomodoros_since_start, 0)
        self.assertAlmostEqual(engine.remaining_seconds(), 25 * 60, delta=1)


if __name__ == "__main__":
    unittest.main()
