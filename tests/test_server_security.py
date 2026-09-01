import io

import app as app_module
import automation


def test_web_upload_rejects_invalid_excel_signature():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        response = client.post(
            "/upload",
            data={
                "email": "security@example.com",
                "password": "super-secret-password",
                "company_id": "secret-company-id",
                "file": (io.BytesIO(b"not an excel file"), "input.xlsx"),
            },
            content_type="multipart/form-data",
        )

    assert response.status_code == 400
    assert response.get_json()["error_code"] == "INVALID_EXCEL_SIGNATURE"


def test_removed_local_mode_env_cannot_suppress_web_runtime(monkeypatch):
    monkeypatch.setenv("JOBCAN_APP_MODE", "local")
    monkeypatch.setenv("GA_MEASUREMENT_ID", "G-SERVER-TEST")
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        response = client.get("/autofill")
        shutdown = client.post("/local/shutdown")

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert shutdown.status_code == 404
    assert app_module.MAX_QUEUE_SIZE > 0
    assert "G-SERVER-TEST" in body
    assert "fonts.googleapis.com" in body
    assert 'rel="canonical"' in body


def test_company_id_value_is_not_written_to_login_logs(monkeypatch):
    logs = []
    secret_company_id = "secret-company-id-12345"

    class Page:
        def goto(self, *args, **kwargs):
            return None

        def wait_for_load_state(self, *args, **kwargs):
            return None

        def wait_for_selector(self, *args, **kwargs):
            return None

        def click(self, *args, **kwargs):
            return None

    monkeypatch.setattr(automation, "add_job_log", lambda _job_id, message, _jobs: logs.append(str(message)))
    monkeypatch.setattr(automation, "clear_session", lambda *args, **kwargs: True)
    monkeypatch.setattr(automation, "human_like_wait", lambda *args, **kwargs: None)
    monkeypatch.setattr(automation, "human_like_mouse_movement", lambda *args, **kwargs: None)
    monkeypatch.setattr(automation, "reliable_fill", lambda *args, **kwargs: True)
    monkeypatch.setattr(automation, "human_like_typing", lambda *args, **kwargs: False)

    jobs = {"job": {}}
    result = automation.perform_login(
        Page(),
        "security@example.com",
        "super-secret-password",
        "job",
        jobs,
        company_id=secret_company_id,
    )

    assert result[0] is False
    assert any("会社IDが指定されています" in message for message in logs)
    assert any("会社IDを入力しました" in message for message in logs)
    assert all(secret_company_id not in message for message in logs)
