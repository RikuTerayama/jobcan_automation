import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run_local_probe(source):
    env = os.environ.copy()
    env.update({
        "JOBCAN_APP_MODE": "local",
        "JOBCAN_LOCAL_PORT": "18765",
        "MAX_ACTIVE_SESSIONS": "1",
        "MAX_QUEUE_SIZE": "0",
    })
    result = subprocess.run(
        [sys.executable, "-c", source],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return json.loads(result.stdout.strip().splitlines()[-1]), result


def test_local_ui_security_affiliate_and_template_download():
    data, process = _run_local_probe(r'''
import json, re
from app import app
base = "http://127.0.0.1:18765"
app.config["TESTING"] = True
with app.test_client() as client:
    page = client.get("/autofill", base_url=base)
    html = page.get_data(as_text=True)
    token = re.search(r'name="local-csrf-token" content="([^"]+)"', html).group(1)
    template = client.get("/download-template", base_url=base)
    bad_host = client.get("/autofill", base_url="http://localhost:18765")
    forbidden = client.get("/recommend", base_url=base)
    bad_origin = client.post("/local/shutdown", base_url=base, headers={"Origin": "https://example.com", "X-CSRF-Token": token})
    bad_csrf = client.post("/local/shutdown", base_url=base, headers={"Origin": base, "X-CSRF-Token": "wrong"})
print(json.dumps({
    "status": page.status_code,
    "template_status": template.status_code,
    "template_zip": template.data[:4] == b"PK\x03\x04",
    "bad_host": bad_host.status_code,
    "forbidden": forbidden.status_code,
    "bad_origin": bad_origin.status_code,
    "bad_csrf": bad_csrf.status_code,
    "affiliate_count": html.count("tag=jobcanauto-22") + html.count("tag=ieltsconsult-22"),
    "a8_count": html.lower().count("a8.net"),
    "adsense_count": html.count("pagead2.googlesyndication.com"),
    "ga_count": html.count("googletagmanager.com"),
    "remote_font_count": html.count("fonts.googleapis.com"),
    "privacy_copy": "このPC上" in html and "Renderへ送信しません" in html,
}))
''')
    assert data == {
        "status": 200,
        "template_status": 200,
        "template_zip": True,
        "bad_host": 403,
        "forbidden": 404,
        "bad_origin": 403,
        "bad_csrf": 403,
        "affiliate_count": 0,
        "a8_count": 0,
        "adsense_count": 0,
        "ga_count": 0,
        "remote_font_count": 0,
        "privacy_copy": True,
    }
    assert "super-secret-password" not in process.stderr


def test_local_rejects_invalid_excel_and_second_job_without_logging_credentials():
    data, process = _run_local_probe(r'''
import io, json, re, time
from app import app, jobs
base = "http://127.0.0.1:18765"
app.config["TESTING"] = True
with app.test_client() as client:
    html = client.get("/autofill", base_url=base).get_data(as_text=True)
    token = re.search(r'name="local-csrf-token" content="([^"]+)"', html).group(1)
    headers = {"Origin": base, "X-CSRF-Token": token}
    invalid = client.post("/upload", base_url=base, headers=headers, data={
        "email": "local@example.com", "password": "super-secret-password",
        "file": (io.BytesIO(b"not an excel file"), "input.xlsx"),
    }, content_type="multipart/form-data")
    template_bytes = client.get("/download-template", base_url=base).data
    jobs["busy"] = {"status": "running", "start_time": time.time(), "queue_key": "other", "logs": []}
    busy = client.post("/upload", base_url=base, headers=headers, data={
        "email": "local@example.com", "password": "super-secret-password",
        "file": (io.BytesIO(template_bytes), "input.xlsx"),
    }, content_type="multipart/form-data")
print(json.dumps({"invalid": invalid.status_code, "invalid_code": invalid.json.get("error_code"), "busy": busy.status_code, "busy_code": busy.json.get("error_code"), "queue_limit": busy.json.get("queue_limit")}))
''')
    assert data == {"invalid": 400, "invalid_code": "INVALID_EXCEL_SIGNATURE", "busy": 503, "busy_code": "QUEUE_FULL", "queue_limit": 0}
    assert "super-secret-password" not in process.stdout
    assert "super-secret-password" not in process.stderr
