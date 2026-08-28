import sys
import os
from pathlib import Path

import app


def test_resource_path_uses_pyinstaller_bundle(monkeypatch):
    bundle_root = Path.cwd() / "packaged-probe"
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_root), raising=False)
    assert Path(app.resource_path("templates")) == bundle_root / "templates"


def test_local_launcher_never_binds_all_interfaces():
    source = (Path(__file__).resolve().parents[1] / "local_app.py").read_text(encoding="utf-8")
    assert 'make_server("127.0.0.1"' in source
    assert 'make_server("0.0.0.0"' not in source


def test_windows_single_instance_mutex():
    if os.name != "nt":
        return
    from local_runtime import SingleInstance

    first = SingleInstance("Local\\OshigotoJobcanToolTest")
    second = SingleInstance("Local\\OshigotoJobcanToolTest")
    try:
        assert first.acquire() is True
        assert second.acquire() is False
    finally:
        second.release()
        first.release()
