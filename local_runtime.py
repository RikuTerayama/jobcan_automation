"""Windows-local runtime helpers kept separate from the public web entry point."""

from __future__ import annotations

import ctypes
import os
import socket
import sys
import time
import urllib.request
from ctypes import wintypes


MUTEX_NAME = "Local\\OshigotoJobcanTool"
ERROR_ALREADY_EXISTS = 183


class SingleInstance:
    """A named Windows mutex that prevents duplicate desktop instances."""

    def __init__(self, name: str = MUTEX_NAME):
        self.name = name
        self.handle = None

    def acquire(self) -> bool:
        if os.name != "nt":
            return True
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        ctypes.set_last_error(0)
        self.handle = kernel32.CreateMutexW(None, False, self.name)
        if not self.handle:
            raise OSError(ctypes.get_last_error(), "single-instance mutex creation failed")
        return ctypes.get_last_error() != ERROR_ALREADY_EXISTS

    def release(self) -> None:
        if self.handle and os.name == "nt":
            ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(self.handle)
        self.handle = None


def choose_loopback_port(preferred: int | None = None) -> int:
    """Reserve a currently free loopback port long enough to discover its number."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        sock.bind(("127.0.0.1", preferred or 0))
        return int(sock.getsockname()[1])


def wait_until_ready(url: str, timeout_sec: float = 15.0) -> None:
    deadline = time.monotonic() + timeout_sec
    last_error = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if response.status == 200:
                    return
        except Exception as exc:
            last_error = exc
            time.sleep(0.1)
    raise RuntimeError("ローカル画面の起動を確認できませんでした。") from last_error


def show_error(message: str, title: str = "Jobcan Tool") -> None:
    """Show a usable error in noconsole builds, with stderr as a fallback."""
    if os.name == "nt":
        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
    else:
        print(f"{title}: {message}", file=sys.stderr)
