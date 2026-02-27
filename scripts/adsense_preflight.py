#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AdSense 再申請前ゲート: 不承認要因ゼロを自動チェック。
- テストクライアント使用（サーバ不要）: デフォルト
- 本番確認: --live https://jobcan-automation.onrender.com

NG があれば exit 1 で終了。
使用例:
  python scripts/adsense_preflight.py
  python scripts/adsense_preflight.py --live https://jobcan-automation.onrender.com
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL_DEFAULT = 'https://jobcan-automation.onrender.com'

# 主要ページ（GSC 404 解消対象含む）
MAJOR_PATHS = ['/', '/autofill', '/tools', '/privacy', '/contact', '/about', '/best-practices']

# sitemap.xml に含まれるべき重要URL（完全一致：末尾スラッシュなし）
SITEMAP_REQUIRED_URLS = ['/', '/autofill', '/tools', '/privacy', '/blog', '/glossary', '/guide/excel-format', '/best-practices']

# インデックス対象ページ（noindex なし・canonical 自己参照の確認用）
INDEXABLE_PATHS = ['/', '/privacy', '/blog', '/glossary', '/guide/excel-format']

# 不整合文字列（ヒット0が必須）
DISALLOWED_STRINGS = [
    'github.com/your-repo',
    'example.com',
    'ローカル処理優先',
    'ファイルやテキストはアップロードせず、ブラウザ内で処理します。サーバーには保存されません。',
    '検索条件に一致するツールが見つかりませんでした。',
]

# /tools サーバ返却HTMLに含まれてはいけない文言（本文・script 含む）
NO_RESULTS_FORBIDDEN = '検索条件に一致するツールが見つかりませんでした。'

# Googlebot UA
GOOGLEBOT_UA = 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'

# 本文テキストの最小長（Googlebot 取得想定）
MIN_BODY_CHARS = 1000


def run_local():
    """Flask test client でチェック"""
    from app import app
    app.config['TESTING'] = True
    client = app.test_client()

    def get_fn(path, headers=None):
        if headers:
            return client.get(path, headers=headers)
        return client.get(path)

    return _run_checks(get_fn, 'http://test', use_headers=True)


def _run_checks(get_fn, base_url, use_headers=True):
    """共通チェックロジック。get_fn(path, headers?) -> (status, body, headers_dict)"""
    rows = []
    all_ok = True

    def get(path, headers=None):
        if use_headers and headers:
            return get_fn(path, headers=headers)
        return get_fn(path)

    # 1) 主要ページ 200
    for path in MAJOR_PATHS:
        try:
            resp = get(path)
            status = resp.status_code if hasattr(resp, 'status_code') else resp[0]
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            ok = status == 200
            rows.append(('1_page_200', path, 'OK' if ok else f'FAIL status={status}', ok))
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('1_page_200', path, f'ERROR {e}', False))
            all_ok = False

    # 1b) /best-practices と /best-practices/ が 404 でないこと（200 または 301）
    for path in ('/best-practices', '/best-practices/'):
        try:
            resp = get(path)
            status = resp.status_code if hasattr(resp, 'status_code') else resp[0]
            ok = status in (200, 301)
            rows.append(('1b_best_practices', path, f'OK {status}' if ok else f'FAIL {status} (404)', ok))
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('1b_best_practices', path, f'ERROR {e}', False))
            all_ok = False

    # 2) Googlebot UA で 200 かつ本文長
    try:
        h = {'User-Agent': GOOGLEBOT_UA} if use_headers else None
        resp = get('/', h) if h else get('/')
        status = resp.status_code if hasattr(resp, 'status_code') else resp[0]
        body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
        ok = status == 200 and len(body) >= MIN_BODY_CHARS
        rows.append(('2_googlebot', '/', f'OK status={status} len={len(body)}' if ok else f'FAIL status={status} len={len(body)}', ok))
        if not ok:
            all_ok = False
    except Exception as e:
        rows.append(('2_googlebot', '/', f'ERROR {e}', False))
        all_ok = False

    # 3a) /tools サーバ返却HTMLに no-results 日本語文言が含まれないこと（必須）
    try:
        resp = get('/tools')
        body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
        found = NO_RESULTS_FORBIDDEN in body
        rows.append(('3a_tools_no_results', '/tools', 'OK HTML has no no-results text' if not found else 'FAIL no-results text in server HTML', not found))
        if found:
            all_ok = False
    except Exception as e:
        rows.append(('3a_tools_no_results', '/tools', f'ERROR {e}', False))
        all_ok = False

    # 3b) 不整合文字列 0 件（/tools, /, /privacy）
    disallow_found = []
    for path in ['/tools', '/', '/privacy']:
        try:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            for s in DISALLOWED_STRINGS:
                if s in body:
                    disallow_found.append((path, s[:40]))
        except Exception as e:
            disallow_found.append((path, str(e)))
    if disallow_found:
        for path, msg in disallow_found[:5]:
            rows.append(('3b_disallowed', path, f'FAIL found: {msg}...', False))
        all_ok = False
    else:
        rows.append(('3b_disallowed', '/, /tools, /privacy', 'OK 0 disallowed strings', True))

    # 4) Cache-Control
    try:
        resp = get('/tools')
        headers = resp.headers if hasattr(resp, 'headers') else {}
        cc = headers.get('Cache-Control') or headers.get('cache-control', '')
        ok = 'no-store' in cc.lower() or 'max-age=0' in cc
        rows.append(('4_cache_control', '/tools', f'OK {cc}' if ok else f'FAIL missing no-store {cc}', ok))
        if not ok:
            all_ok = False
    except Exception as e:
        rows.append(('4_cache_control', '/tools', f'ERROR {e}', False))
        all_ok = False

    # 5) ads.txt は 200 必須。Google AdSense publisher 行（pub-）を含むこと
    try:
        resp = get('/ads.txt')
        status = resp.status_code if hasattr(resp, 'status_code') else resp[0]
        body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
        has_pub = 'pub-' in body or 'google.com' in body
        ok = status == 200 and has_pub
        rows.append(('5_ads_txt', '/ads.txt', f'OK 200 pub_id' if ok else f'FAIL status={status} (200 required) pub={has_pub}', ok))
        if not ok:
            all_ok = False
    except Exception as e:
        rows.append(('5_ads_txt', '/ads.txt', f'FAIL ERROR {e}', False))
        all_ok = False

    # 6) robots.txt は 200 必須。主要ページをブロックしていないこと
    try:
        resp = get('/robots.txt')
        status = resp.status_code if hasattr(resp, 'status_code') else resp[0]
        body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
        blocks_main = 'Disallow: /' in body and 'Allow: /' not in body.split('Disallow: /')[0]
        ok = status == 200 and not blocks_main
        rows.append(('6_robots_txt', '/robots.txt', f'OK 200 allow /' if ok else f'FAIL status={status} (200 required)', ok))
        if not ok:
            all_ok = False
    except Exception as e:
        rows.append(('6_robots_txt', '/robots.txt', f'FAIL ERROR {e}', False))
        all_ok = False

    # 7) sitemap.xml に重要URLが含まれること（完全一致）+ lastmod ユニーク数
    import re
    try:
        resp = get('/sitemap.xml')
        status = resp.status_code if hasattr(resp, 'status_code') else resp[0]
        body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
        if status != 200:
            rows.append(('7_sitemap', '/sitemap.xml', f'FAIL status={status}', False))
            all_ok = False
        else:
            base = BASE_URL_DEFAULT.rstrip('/')
            missing = []
            for u in SITEMAP_REQUIRED_URLS:
                loc_url = base + (u if u != '/' else '/')
                if f'<loc>{loc_url}</loc>' not in body:
                    missing.append(u)
            if missing:
                rows.append(('7_sitemap', '/sitemap.xml', f'FAIL missing in sitemap: {missing[:3]}', False))
                all_ok = False
            else:
                rows.append(('7_sitemap', '/sitemap.xml', 'OK required URLs in sitemap', True))
            lastmods = re.findall(r'<lastmod>([^<]+)</lastmod>', body)
            lastmods_unique = len(set(lastmods)) if lastmods else 0
            ok_lastmod = lastmods_unique >= 2
            rows.append(('7b_sitemap_lastmod', '/sitemap.xml', f'OK lastmod unique={lastmods_unique}' if ok_lastmod else f'FAIL lastmod unique={lastmods_unique} (need >=2)', ok_lastmod))
            if not ok_lastmod:
                all_ok = False
    except Exception as e:
        rows.append(('7_sitemap', '/sitemap.xml', f'FAIL ERROR {e}', False))
        all_ok = False

    # 8) robots.txt が複数行形式で Sitemap が改行付きで含まれること
    try:
        resp = get('/robots.txt')
        body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
        has_newlines = '\n' in body
        # Sitemap 行が独立した行で存在（\nSitemap: または Sitemap:\n）
        has_sitemap_line = '\nSitemap:' in body or body.strip().startswith('Sitemap:') or 'Sitemap:' in body
        ok = has_newlines and has_sitemap_line
        rows.append(('8_robots_format', '/robots.txt', f'OK multiline+Sitemap' if ok else f'FAIL multiline={has_newlines} Sitemap={has_sitemap_line}', ok))
        if not ok:
            all_ok = False
    except Exception as e:
        rows.append(('8_robots_format', '/robots.txt', f'FAIL ERROR {e}', False))
        all_ok = False

    # 9) インデックス対象ページに noindex が無く canonical が自己参照であること
    for path in INDEXABLE_PATHS:
        try:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            has_noindex = 'noindex, nofollow' in body or ('name="robots"' in body and 'noindex' in body)
            # canonical 自己参照: BASE_URL + path が含まれる（path が / のときは base/ または base/）
            base = BASE_URL_DEFAULT.rstrip('/')
            expected_canonical = base + (path if path != '/' else '') or '/'
            if path == '/':
                expected_canonical = base + '/'
            has_canonical_self = expected_canonical in body and 'rel="canonical"' in body
            ok = not has_noindex and has_canonical_self
            rows.append(('9_indexable', path, 'OK no noindex, canonical self' if ok else f'FAIL noindex={has_noindex} canonical={has_canonical_self}', ok))
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('9_indexable', path, f'ERROR {e}', False))
            all_ok = False

    return rows, all_ok


def run_live(base_url):
    """実サーバでチェック（urllib）"""
    import urllib.request
    import urllib.error

    def get(path, headers=None):
        url = base_url.rstrip('/') + path
        req = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(req) as r:
                body = r.read().decode('utf-8', errors='replace')
                h = dict(r.headers)
                return r.status, body, h
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            return e.code, body, dict(e.headers) if e.headers else {}

    # アダプタ: (status, body, headers) を返す形に
    def get_fn(path, headers=None):
        status, body, h = get(path, headers)
        class Resp:
            status_code = status
            data = body.encode('utf-8') if isinstance(body, str) else body
            headers = h
        return Resp()

    return _run_checks(lambda path, headers=None: get_fn(path, headers), base_url, use_headers=True)


def print_table(rows):
    """表形式で出力"""
    w1, w2, w3 = 16, 20, 50
    print(f"{'Check':<{w1}} {'Path':<{w2}} {'Result':<{w3}}")
    print('-' * (w1 + w2 + w3))
    for r in rows:
        status = 'OK' if r[3] else 'NG'
        print(f"{r[0]:<{w1}} {r[1]:<{w2}} [{status}] {r[2]}")


def main():
    parser = argparse.ArgumentParser(description='AdSense preflight check')
    parser.add_argument('--live', metavar='BASE_URL', default=None,
                        help=f'Use live server (default: {BASE_URL_DEFAULT})')
    args = parser.parse_args()

    base_url = args.live or 'http://test'
    if args.live:
        print(f"(live: {args.live})\n")
        rows, all_ok = run_live(args.live)
    else:
        print("(Flask test client)\n")
        rows, all_ok = run_local()

    print_table(rows)
    print()
    if all_ok:
        print("ALL CHECKS PASSED")
        return 0
    print("SOME CHECKS FAILED - fix before AdSense re-application")
    return 1


if __name__ == '__main__':
    sys.exit(main())
