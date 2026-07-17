#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate/check sitemap lastmod manifest for the lightweight site."""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(REPO_ROOT, 'templates')
OUTPUT_PATH = os.path.join(REPO_ROOT, 'data', 'sitemap_lastmod.json')


def url_path_to_template_rel(url_path):
    path = (url_path or '').strip('/') or ''
    special = {
        '': 'landing.html',
        'autofill': 'autofill_flow.html',
        'tools': 'tools/index.html',
        'tools/pdf': 'tools/pdf_flow.html',
        'faq': 'faq_lite.html',
        'about': 'about.html',
    }
    if path in special:
        return special[path]
    if path.startswith('tools/'):
        return 'tools/' + path.split('/', 1)[1] + '.html'
    return (path + '.html') if path else 'landing.html'


def get_sitemap_url_paths():
    return ['/', '/autofill', '/tools', '/tools/pdf', '/faq', '/about']


def get_git_date(filepath):
    try:
        relpath = os.path.relpath(filepath, REPO_ROOT).replace(os.sep, '/')
        result = subprocess.run(['git', 'log', '-1', '--format=%cs', '--', relpath], cwd=REPO_ROOT, capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()[:10]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def get_mtime_date(filepath):
    try:
        return datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d')
    except (OSError, TypeError):
        return None


def has_git():
    if not os.path.isdir(os.path.join(REPO_ROOT, '.git')):
        return False
    try:
        result = subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], cwd=REPO_ROOT, capture_output=True, text=True, timeout=3)
        return result.returncode == 0 and result.stdout.strip() == 'true'
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def generate_manifest(use_git=True):
    manifest = {}
    seen_templates = set()
    for url_path in get_sitemap_url_paths():
        rel = url_path_to_template_rel(url_path)
        fpath = os.path.join(TEMPLATES_DIR, rel.replace('/', os.sep))
        if rel in seen_templates:
            continue
        seen_templates.add(rel)
        if not os.path.isfile(fpath):
            continue
        date_str = get_git_date(fpath) if use_git else None
        if not date_str:
            date_str = get_mtime_date(fpath)
        if date_str:
            manifest[rel] = date_str
    return dict(sorted(manifest.items()))


def manifest_to_json(manifest):
    return json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)


def run_check():
    if not has_git():
        print('ERROR: .git not found or git unavailable. --check requires git.', file=sys.stderr)
        return 2
    expected_json = manifest_to_json(generate_manifest(use_git=True))
    try:
        with open(OUTPUT_PATH, 'r', encoding='utf-8') as f:
            current = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f'ERROR: Cannot read {OUTPUT_PATH}: {exc}', file=sys.stderr)
        return 1
    current_json = manifest_to_json(dict(sorted(current.items())))
    if expected_json != current_json:
        print('ERROR: data/sitemap_lastmod.json is outdated or differs from expected.', file=sys.stderr)
        print('Run: python scripts/generate_sitemap_lastmod_manifest.py --write', file=sys.stderr)
        return 1
    return 0


def run_write():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(manifest_to_json(generate_manifest(use_git=has_git())) + '\n')
    print(f'Generated {OUTPUT_PATH}', file=sys.stderr)
    return 0


def main():
    parser = argparse.ArgumentParser(description='sitemap lastmod manifest generator')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    return run_check() if args.check else run_write()


if __name__ == '__main__':
    sys.exit(main())
