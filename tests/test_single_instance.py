"""
Single-instance guard (needs Qt).
"""
from __future__ import annotations

import unittest
import uuid

from PySide6.QtWidgets import QApplication

from single_instance import SingleInstanceGuard


def _app() -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return QApplication([])


class TestSingleInstanceGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _app()

    def test_second_acquire_activates_first(self) -> None:
        key = f"PomodoroOverlay-test-{uuid.uuid4().hex}"
        primary = SingleInstanceGuard(key)
        self.addCleanup(primary.release)
        self.assertTrue(primary.acquire())

        activated: list[bool] = []
        primary.activated.connect(lambda: activated.append(True))

        secondary = SingleInstanceGuard(key)
        self.addCleanup(secondary.release)
        self.assertFalse(secondary.acquire())

        self.app.processEvents()
        self.assertEqual(activated, [True])

    def test_acquire_after_release(self) -> None:
        key = f"PomodoroOverlay-test-{uuid.uuid4().hex}"
        first = SingleInstanceGuard(key)
        self.assertTrue(first.acquire())
        first.release()

        second = SingleInstanceGuard(key)
        self.addCleanup(second.release)
        self.assertTrue(second.acquire())


if __name__ == "__main__":
    unittest.main()
