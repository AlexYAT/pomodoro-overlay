"""
One running copy of the app: a second launch activates the first and exits.
Uses a per-user lock file plus a local socket (no extra dependencies).
"""
from __future__ import annotations

import getpass
from pathlib import Path

from PySide6.QtCore import QDir, QLockFile, QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

ACTIVATE_MSG = b"activate\n"
CONNECT_TIMEOUT_MS = 200
WRITE_TIMEOUT_MS = 200


def default_instance_key() -> str:
    user = "".join(c if c.isalnum() or c in "-_" else "_" for c in getpass.getuser())
    return f"PomodoroOverlayTimer-{user}"


class SingleInstanceGuard(QObject):
    """Holds the primary lock or notifies the already running instance."""

    activated = Signal()

    def __init__(self, key: str | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._key = key or default_instance_key()
        lock_path = str(Path(QDir.tempPath()) / f"{self._key}.lock")
        self._lock = QLockFile(lock_path)
        self._lock.setStaleLockTime(30_000)
        self._server: QLocalServer | None = None

    def acquire(self) -> bool:
        """True if this process is primary; False if another instance was signaled."""
        if not self._lock.tryLock(100):
            self._notify_running()
            return False
        self._start_server()
        return True

    def release(self) -> None:
        if self._server is not None:
            self._server.close()
            QLocalServer.removeServer(self._key)
            self._server = None
        if self._lock.isLocked():
            self._lock.unlock()

    def _notify_running(self) -> bool:
        socket = QLocalSocket(self)
        if not self._connect(socket):
            return False
        socket.write(ACTIVATE_MSG)
        socket.flush()
        socket.waitForBytesWritten(WRITE_TIMEOUT_MS)
        socket.disconnectFromServer()
        return True

    def _connect(self, socket: QLocalSocket) -> bool:
        for _ in range(5):
            socket.connectToServer(self._key)
            if socket.waitForConnected(CONNECT_TIMEOUT_MS):
                return True
        return False

    def _start_server(self) -> None:
        QLocalServer.removeServer(self._key)
        server = QLocalServer(self)
        server.newConnection.connect(self._on_new_connection)
        if not server.listen(self._key):
            QLocalServer.removeServer(self._key)
            server.listen(self._key)
        self._server = server

    def _on_new_connection(self) -> None:
        if self._server is None:
            return
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            if socket is not None:
                socket.close()
        self.activated.emit()
