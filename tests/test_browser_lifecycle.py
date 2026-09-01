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


def test_server_browser_uses_playwright_chromium_without_channel():
    calls = []

    class Chromium:
        def launch(self, **kwargs):
            calls.append(kwargs)
            return "server-browser"

    class Playwright:
        chromium = Chromium()

    result = automation.launch_jobcan_browser(
        Playwright(),
        ["--no-sandbox", "--disable-web-security", "--mute-audio"],
    )
    assert result == "server-browser"
    assert calls == [{
        "headless": True,
        "args": ["--no-sandbox", "--disable-web-security", "--mute-audio"],
        "timeout": 60000,
    }]
    assert "channel" not in calls[0]
