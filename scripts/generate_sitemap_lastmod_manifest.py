#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sitemap lastmod マニフェスト生成スクリプト
ビルド/起動前に実行し、data/sitemap_lastmod.json を生成する。
- 優先: git log -1 --format=%cs で最終コミット日 (YYYY-MM-DD)
- fallback: ファイル mtime（本番Dockerでは同一化し得る）
"""
import json
import os
import subprocess
import sys
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(REPO_ROOT, "templates")
OUTPUT_PATH = os.path.join(REPO_ROOT, "data", "sitemap_lastmod.json")


def url_path_to_template_rel(url_path):
    """app.py の _sitemap_lastmod_for_path と同一のマッピング"""
    path = (url_path or "").strip("/") or ""
    special = {
        "": "landing.html",
        "autofill": "autofill.html",
        "guide": "guide/index.html",
        "guide/complete": "guide/complete-guide.html",
        "guide/comprehensive-guide": "guide/comprehensive-guide.html",
        "blog": "blog/index.html",
        "tools": "tools/index.html",
        "sitemap.html": "sitemap.html",
        "case-studies": "case-studies.html",
        "case-study/contact-center": "case-study-contact-center.html",
        "case-study/consulting-firm": "case-study-consulting-firm.html",
        "case-study/remote-startup": "case-study-remote-startup.html",
    }
    if path in special:
        return special[path]
    if path.startswith("guide/"):
        return "guide/" + path.split("/", 1)[1] + ".html"
    if path.startswith("blog/"):
        return "blog/" + path.split("/", 1)[1] + ".html"
    if path.startswith("tools/"):
        return "tools/" + path.split("/", 1)[1] + ".html"
    return (path + ".html") if path else "landing.html"


def get_sitemap_url_paths():
    """sitemap に含まれる URL パスの一覧（固定＋PRODUCTS 相当）"""
    fixed = [
        "/", "/autofill", "/about", "/contact", "/privacy", "/terms", "/faq",
        "/glossary", "/best-practices", "/case-studies", "/sitemap.html",
        "/guide", "/guide/autofill", "/guide/complete", "/guide/comprehensive-guide",
        "/guide/getting-started", "/guide/excel-format", "/guide/troubleshooting",
        "/tools", "/blog",
        "/blog/implementation-checklist", "/blog/automation-roadmap",
        "/blog/workstyle-reform-automation", "/blog/excel-attendance-limits",
        "/blog/playwright-security", "/blog/month-end-closing-hell-and-automation",
        "/blog/excel-format-mistakes-and-design", "/blog/convince-it-and-hr-for-automation",
        "/blog/playwright-jobcan-challenges-and-solutions", "/blog/jobcan-auto-input-tools-overview",
        "/blog/reduce-manual-work-checklist", "/blog/jobcan-month-end-tips",
        "/blog/jobcan-auto-input-dos-and-donts", "/blog/month-end-closing-checklist",
        "/case-study/contact-center", "/case-study/consulting-firm", "/case-study/remote-startup",
    ]
    try:
        sys.path.insert(0, REPO_ROOT)
        from lib.products_catalog import PRODUCTS
        for p in PRODUCTS:
            if p.get("status") == "available":
                if p.get("path") and p["path"] not in fixed:
                    fixed.append(p["path"])
                if p.get("guide_path") and p["guide_path"] not in fixed:
                    fixed.append(p["guide_path"])
    except Exception:
        pass
    return fixed


def get_git_date(filepath):
    """git log -1 --format=%cs で YYYY-MM-DD を取得。失敗時は None"""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", filepath],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()[:10]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def get_mtime_date(filepath):
    """ファイル mtime を YYYY-MM-DD で返す"""
    try:
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
    except (OSError, TypeError):
        return None


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    manifest = {}
    url_paths = get_sitemap_url_paths()
    seen_templates = set()

    for url_path in url_paths:
        rel = url_path_to_template_rel(url_path)
        fpath = os.path.join(TEMPLATES_DIR, rel.replace("/", os.sep))
        if rel in seen_templates:
            continue
        seen_templates.add(rel)
        if not os.path.isfile(fpath):
            continue
        date_str = get_git_date(fpath)
        if not date_str:
            date_str = get_mtime_date(fpath)
        if date_str:
            manifest[rel] = date_str

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"Generated {OUTPUT_PATH} with {len(manifest)} entries", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
