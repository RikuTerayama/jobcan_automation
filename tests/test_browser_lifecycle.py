import os

import automation


class _Closable:
    def __init__(self, label, calls):
        self.label = label
        self.calls = calls

    def close(self):
        self.calls.append(self.label)


def test_cleanup_order_closes_page_context_browser(monkeypatch):
    calls = []
    monkeypatch.setattr(automation, "add_job_log", lambda *args, **kwargs: None)
    errors = automation.close_playwright_resources(
        _Closable("page", calls),
        _Closable("context", calls),
        _Closable("browser", calls),
        "job",
        {},
    )
    assert errors == []
    assert calls == ["page", "context", "browser"]


def test_local_browser_prefers_edge_then_falls_back(monkeypatch):
    calls = []

    class Chromium:
        def launch(self, **kwargs):
            calls.append(kwargs)
            if kwargs.get("channel") == "msedge":
                raise RuntimeError("edge unavailable")
            return "fallback-browser"

    class Playwright:
        chromium = Chromium()

    monkeypatch.setenv("JOBCAN_APP_MODE", "local")
    monkeypatch.setenv("JOBCAN_BROWSER_CHANNEL", "msedge")
    result = automation.launch_jobcan_browser(
        Playwright(),
        ["--no-sandbox", "--disable-web-security", "--mute-audio"],
    )
    assert result == "fallback-browser"
    assert calls[0]["channel"] == "msedge"
    assert calls[1].get("channel") is None
    assert "--no-sandbox" not in calls[0]["args"]
    assert "--disable-web-security" not in calls[0]["args"]
    assert "--mute-audio" in calls[0]["args"]
