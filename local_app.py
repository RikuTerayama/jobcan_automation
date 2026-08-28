"""Launcher entry point for the Windows-local Jobcan desktop application."""

from __future__ import annotations

import argparse
import os
import shutil
import threading
import webbrowser

from werkzeug.serving import make_server

from local_runtime import SingleInstance, choose_loopback_port, show_error, wait_until_ready


def configure_local_environment(port: int) -> None:
    origin = f"http://127.0.0.1:{port}"
    values = {
        "JOBCAN_APP_MODE": "local",
        "JOBCAN_LOCAL_PORT": str(port),
        "BASE_URL": origin,
        "MAX_ACTIVE_SESSIONS": "1",
        "MAX_QUEUE_SIZE": "0",
        "ADSENSE_ENABLED": "false",
        "AFFILIATE_ENABLED": "false",
        "AMAZON_AFFILIATE_ENABLED": "false",
        "GA_MEASUREMENT_ID": "",
    }
    for key, value in values.items():
        os.environ[key] = value


def run_local_app(port: int | None = None, open_browser: bool = True) -> int:
    instance = SingleInstance()
    if not instance.acquire():
        show_error("Jobcan Toolはすでに起動しています。開いているブラウザ画面を確認してください。")
        return 2

    server = None
    try:
        selected_port = choose_loopback_port(port)
        configure_local_environment(selected_port)

        from app import UPLOAD_FOLDER, app, jobs, queued_job_params

        server = make_server("127.0.0.1", selected_port, app, threaded=True)

        def request_shutdown() -> None:
            threading.Thread(target=server.shutdown, name="local-server-shutdown", daemon=True).start()

        app.config["LOCAL_SHUTDOWN_CALLBACK"] = request_shutdown
        url = f"http://127.0.0.1:{selected_port}/autofill"
        ready_thread = threading.Thread(target=server.serve_forever, name="local-flask-server", daemon=True)
        ready_thread.start()
        wait_until_ready(url)
        if open_browser:
            webbrowser.open(url, new=1, autoraise=True)
        ready_thread.join()

        # Credentials are held only in these in-memory job dictionaries.
        for job in jobs.values():
            for key in ("email", "password", "company_id"):
                job.pop(key, None)
        queued_job_params.clear()
        shutil.rmtree(UPLOAD_FOLDER, ignore_errors=True)
        return 0
    except OSError as exc:
        show_error(f"ローカルポートを使用できませんでした。\n\n{exc}")
        return 3
    except Exception as exc:
        show_error(f"Jobcan Toolを起動できませんでした。\n\n{exc}")
        return 1
    finally:
        if server is not None:
            server.server_close()
        instance.release()


def main() -> int:
    parser = argparse.ArgumentParser(description="Jobcan Tool Windows local launcher")
    parser.add_argument("--port", type=int, default=None, help="development smoke-test port")
    parser.add_argument("--no-browser", action="store_true", help="do not open the default browser")
    args = parser.parse_args()
    return run_local_app(port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    raise SystemExit(main())
