#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke tests for the Jobcan + PDF lightweight site."""

import os
import sys
import time
from collections import deque
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

KEPT_PATHS = [
    '/', '/autofill', '/tools', '/tools/pdf', '/recommend', '/faq',
    '/privacy', '/terms', '/contact', '/healthz', '/readyz', '/ping',
]
ERROR_PAGE_MARKER = '<title>エラーが発生しました | Jobcan AutoFill</title>'


def run_with_test_client():
    from app import app
    app.config['TESTING'] = True
    client = app.test_client()
    failed = []
    n_per_path = 10
    for path in KEPT_PATHS:
        for i in range(n_per_path):
            response = client.get(path)
            body = response.data.decode('utf-8', errors='replace')
            if response.status_code != 200:
                failed.append(f"path={path} run={i+1} status={response.status_code}")
            elif path not in ('/healthz', '/readyz', '/ping') and ERROR_PAGE_MARKER in body:
                failed.append(f"path={path} run={i+1} body contains error page")
    if failed:
        for item in failed:
            print(f"FAIL: {item}")
        print(f"Total failures: {len(failed)}")
        return 1
    print(f"OK: {len(KEPT_PATHS)} paths x {n_per_path} requests = all 200, no error page")
    return 0


def run_deploy_verification():
    from app import app
    app.config['TESTING'] = True
    client = app.test_client()
    failed = []

    for path in KEPT_PATHS:
        resp = client.get(path, follow_redirects=False)
        body = resp.data.decode('utf-8', errors='replace')
        if resp.status_code != 200:
            failed.append(f"path={path} expected 200 got {resp.status_code}")
        elif path not in ('/healthz', '/readyz', '/ping') and ERROR_PAGE_MARKER in body:
            failed.append(f"path={path} body contains error page")

    redirects = [
        ('/tools/csv', '/tools'),
        ('/tools/csv/', '/tools'),
        ('/guide/csv', '/tools'),
        ('/guide/excel-format', '/tools'),
        ('/guide/autofill', '/autofill'),
        ('/tools/seo', '/tools'),
        ('/tools/image-batch', '/tools'),
        ('/tools/image-cleanup', '/tools'),
        ('/blog/automation-roadmap', '/'),
        ('/case-studies', '/'),
        ('/glossary', '/faq'),
        ('/best-practices', '/faq'),
        ('/sitemap.html', '/sitemap.xml'),
    ]
    for path, expect_suffix in redirects:
        resp = client.get(path, follow_redirects=False)
        loc = (resp.headers.get('Location') or '').strip()
        if resp.status_code != 301:
            failed.append(f"path={path} expected 301 got {resp.status_code}")
        elif not loc.endswith(expect_suffix) and expect_suffix not in loc:
            failed.append(f"path={path} expected Location...{expect_suffix} got {loc}")

    for path in ['/api/seo/crawl-urls', '/api/minutes/format', '/api/pdf/unlock']:
        resp = client.post(path)
        if resp.status_code != 404:
            failed.append(f"path={path} expected 404 got {resp.status_code}")

    resp = client.post('/api/pdf/lock')
    if resp.status_code == 404:
        failed.append('path=/api/pdf/lock expected enabled API got 404')

    saved_enable_a8 = os.environ.get('ENABLE_A8_AFFILIATE')
    saved_a8_links = os.environ.get('A8_AFFILIATE_LINKS_JSON')
    try:
        os.environ['ENABLE_A8_AFFILIATE'] = 'false'
        os.environ.pop('A8_AFFILIATE_LINKS_JSON', None)
        home_html = client.get('/').data.decode('utf-8', errors='replace')
        if 'data-affiliate-network="amazon"' not in home_html:
            failed.append('home page missing Amazon affiliate tracking attributes')
        if 'data-affiliate-placement="top"' not in home_html:
            failed.append('home page missing top affiliate placement attribute')
        if 'a8-lite-section' in home_html:
            failed.append('A8 block rendered while ENABLE_A8_AFFILIATE=false')

        os.environ['ENABLE_A8_AFFILIATE'] = 'true'
        os.environ['A8_AFFILIATE_LINKS_JSON'] = '[]'
        a8_empty_html = client.get('/').data.decode('utf-8', errors='replace')
        if 'a8-lite-section' in a8_empty_html:
            failed.append('A8 block rendered with empty approved link data')
    finally:
        if saved_enable_a8 is None:
            os.environ.pop('ENABLE_A8_AFFILIATE', None)
        else:
            os.environ['ENABLE_A8_AFFILIATE'] = saved_enable_a8
        if saved_a8_links is None:
            os.environ.pop('A8_AFFILIATE_LINKS_JSON', None)
        else:
            os.environ['A8_AFFILIATE_LINKS_JSON'] = saved_a8_links

    if failed:
        for item in failed:
            print(f"FAIL: {item}")
        print(f"Total: {len(failed)}")
        return 1
    print('OK: deploy verification (kept routes 200; retired routes 301; disabled APIs 404; pdf lock enabled)')
    return 0


def run_jobcan_guardrail_verification():
    """Exercise queue guardrails without starting Playwright."""
    import importlib

    app_module = importlib.import_module('app')
    app_module.app.config['TESTING'] = True
    client = app_module.app.test_client()
    failed = []
    now = time.time()

    with app_module.jobs_lock:
        saved_jobs = dict(app_module.jobs)
        saved_queue = deque(app_module.job_queue)
        saved_params = dict(app_module.queued_job_params)
        saved_index = dict(app_module.queue_identity_index)
        app_module.jobs.clear()
        app_module.job_queue.clear()
        app_module.queued_job_params.clear()
        app_module.queue_identity_index.clear()

        app_module.jobs['guard-running'] = {
            'status': 'running',
            'queue_key': 'guard-running-key',
            'start_time': now,
            'last_updated': now,
            'last_heartbeat_at': now,
            'lease_expires_at': now + 90,
            'logs': [],
        }
        for i in range(app_module.MAX_QUEUE_SIZE):
            job_id = f'guard-queued-{i}'
            queue_key = f'guard-queued-key-{i}'
            app_module.jobs[job_id] = {
                'status': 'queued',
                'queue_key': queue_key,
                'start_time': now,
                'queued_at': now,
                'last_updated': now,
                'last_heartbeat_at': now,
                'lease_expires_at': now + 90,
                'logs': [],
                'session_id': f'guard-session-{i}',
            }
            app_module.job_queue.append(job_id)
            app_module.queued_job_params[job_id] = {'queue_key': queue_key}
            app_module.queue_identity_index[queue_key] = job_id

    try:
        status_resp = client.get('/status/guard-queued-0')
        if status_resp.status_code != 200:
            failed.append(f"/status/guard-queued-0 expected 200 got {status_resp.status_code}")
        else:
            status_json = status_resp.get_json(silent=True) or {}
            if status_json.get('status') != 'queued':
                failed.append(f"/status/guard-queued-0 expected queued got {status_json.get('status')}")
            if status_json.get('queue_limit') != app_module.MAX_QUEUE_SIZE:
                failed.append('/status did not expose queue_limit')

        detach_resp = client.post('/api/queue/detach/guard-queued-0')
        detach_json = detach_resp.get_json(silent=True) or {}
        if detach_resp.status_code != 200 or detach_json.get('status') != 'queued':
            failed.append(f"/api/queue/detach queued expected queued got status={detach_resp.status_code} body={detach_json}")

        upload_resp = client.post(
            '/upload',
            data={
                'file': (BytesIO(b'not-a-real-xlsx-but-extension-is-allowed'), 'guardrail.xlsx'),
                'email': 'phase6-guard@example.com',
                'company_id': 'phase6-company',
                'password': 'secret',
            },
            content_type='multipart/form-data',
        )
        upload_json = upload_resp.get_json(silent=True) or {}
        if upload_resp.status_code != 503:
            failed.append(f"/upload queue full expected 503 got {upload_resp.status_code}")
        if upload_json.get('error_code') != 'QUEUE_FULL':
            failed.append(f"/upload queue full expected QUEUE_FULL got {upload_json.get('error_code')}")
        if upload_json.get('queue_limit') != app_module.MAX_QUEUE_SIZE:
            failed.append('/upload queue full did not expose queue_limit')
        if upload_json.get('retry_after_sec') is None:
            failed.append('/upload queue full did not expose retry_after_sec')

        cancel_resp = client.post('/cancel/guard-queued-0')
        cancel_json = cancel_resp.get_json(silent=True) or {}
        if cancel_resp.status_code != 200 or cancel_json.get('status') != 'cancelled':
            failed.append(f"/cancel queued expected cancelled got status={cancel_resp.status_code} body={cancel_json}")

        if client.post('/api/pdf/unlock').status_code != 404:
            failed.append('/api/pdf/unlock expected 404')
        csv_resp = client.get('/tools/csv', follow_redirects=False)
        if csv_resp.status_code != 301:
            failed.append(f"/tools/csv expected 301 got {csv_resp.status_code}")
    finally:
        with app_module.jobs_lock:
            app_module.jobs.clear()
            app_module.jobs.update(saved_jobs)
            app_module.job_queue.clear()
            app_module.job_queue.extend(saved_queue)
            app_module.queued_job_params.clear()
            app_module.queued_job_params.update(saved_params)
            app_module.queue_identity_index.clear()
            app_module.queue_identity_index.update(saved_index)

    if failed:
        for item in failed:
            print(f"FAIL: {item}")
        print(f"Total: {len(failed)}")
        return 1
    print('OK: Jobcan queue guardrails (QUEUE_FULL, status, cancel) verified without Playwright')
    return 0


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--deploy', action='store_true', help='Run deploy verification checks')
    parser.add_argument('--jobcan-guardrails', action='store_true', help='Run lightweight Jobcan queue guardrail checks')
    args = parser.parse_args()
    if args.deploy:
        sys.exit(run_deploy_verification())
    if args.jobcan_guardrails:
        sys.exit(run_jobcan_guardrail_verification())
    sys.exit(run_with_test_client())
