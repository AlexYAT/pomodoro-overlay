"""
Pomodoro Overlay Timer — entry point.
System tray, notifications on session complete, optional sound.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from overlay_window import OverlayWindow
from settings import load_timer_config
from timer_engine import TimerConfig, TimerEngine, TimerMode


def get_resource_path(relative: str) -> Path:
    """Path to file in resources/ (works with PyInstaller bundle)."""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).resolve().parent
    return base / "resources" / relative


def play_completion_sound() -> None:
    """Play a short beep or optional sound file."""
    try:
        sound_path = get_resource_path("complete.wav")
        if sound_path.exists():
            from PySide6.QtMultimedia import QSoundEffect
            from PySide6.QtCore import QUrl
            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(str(sound_path)))
            effect.play()
            return
    except Exception:
        pass
    # Fallback: no extra deps — use QApplication.beep() if available
    try:
        QApplication.beep()
    except Exception:
        pass


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Pomodoro Overlay Timer")
    app.setQuitOnLastWindowClosed(False)

    config = load_timer_config()
    engine = TimerEngine(config=config)

    overlay = OverlayWindow(engine)

    tray: QSystemTrayIcon | None = None
    tray_menu_show: QAction | None = None

    def show_overlay() -> None:
        overlay.show()
        overlay.raise_()
        overlay.activateWindow()
        if tray_menu_show:
            tray_menu_show.setVisible(False)

    def hide_overlay() -> None:
        overlay.hide()
        if tray_menu_show:
            tray_menu_show.setVisible(True)

    overlay._on_hide_requested = hide_overlay

    def on_mode_complete(mode: TimerMode) -> None:
        play_completion_sound()
        title = "Pomodoro"
        if mode == TimerMode.WORK:
            msg = "Work session finished. Time for a break!"
        elif mode == TimerMode.SHORT_BREAK:
            msg = "Short break over. Back to work?"
        else:
            msg = "Long break over. Ready for next focus block?"
        if tray and tray.isVisible():
            tray.showMessage(title, msg, QSystemTrayIcon.MessageIcon.Information, 3000)
        # Overlay already shows pulse via overlay_window

    engine.on_mode_complete = on_mode_complete
    engine.on_start = play_completion_sound

    # System tray
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray = QSystemTrayIcon(app)
        icon_path = get_resource_path("icon.png")
        if icon_path.exists():
            tray.setIcon(QIcon(str(icon_path)))
        else:
            tray.setIcon(app.style().standardIcon(app.style().StandardPixmap.SP_MediaPlay))
        tray.setToolTip("Pomodoro Overlay Timer — двойной клик или ПКМ → Show чтобы показать окно")
        tray_menu_show = QAction("Show", app)
        tray_menu_show.triggered.connect(show_overlay)
        from PySide6.QtWidgets import QMenu
        menu = QMenu()
        menu.addAction(tray_menu_show)
        menu.addAction("Settings...", overlay._open_settings)
        menu.addAction("Reset all counters", overlay._reset_all_counters)
        menu.addSeparator()
        menu.addAction("Quit", app.quit)
        tray.setContextMenu(menu)
        tray_menu_show.setVisible(False)
        tray.activated.connect(lambda reason: (
            show_overlay() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None
        ))
        tray.show()

    overlay.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
