#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke tests for the Jobcan + PDF lightweight site."""

import os
import sys

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

    if failed:
        for item in failed:
            print(f"FAIL: {item}")
        print(f"Total: {len(failed)}")
        return 1
    print('OK: deploy verification (kept routes 200; retired routes 301; disabled APIs 404; pdf lock enabled)')
    return 0


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--deploy', action='store_true', help='Run deploy verification checks')
    args = parser.parse_args()
    sys.exit(run_deploy_verification() if args.deploy else run_with_test_client())
