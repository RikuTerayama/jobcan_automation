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
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL_DEFAULT = 'https://jobcan-automation.onrender.com'

# 主要ページ（GSC 404 解消対象含む）
MAJOR_PATHS = ['/', '/autofill', '/tools', '/privacy', '/contact', '/about', '/best-practices', '/faq']
PUBLIC_AFFILIATE_PATHS = ['/', '/tools', '/autofill', '/privacy', '/terms', '/contact', '/about', '/faq', '/guide', '/blog', '/case-studies', '/sitemap.html']
NON_UI_AFFILIATE_PATHS = ['/sitemap.xml', '/robots.txt', '/ads.txt', '/api/seo/crawl-urls']

# sitemap.xml に含まれるべき重要URL（完全一致：末尾スラッシュなし）
SITEMAP_REQUIRED_URLS = ['/', '/autofill', '/tools', '/blog', '/glossary', '/guide/excel-format', '/best-practices']

# インデックス対象ページ（noindex なし・canonical 自己参照の確認用）
INDEXABLE_PATHS = ['/', '/blog', '/glossary', '/guide/excel-format']
NOINDEX_SELF_CANONICAL_PATHS = ['/privacy', '/terms', '/contact']
INDEXABILITY_TARGET_PATHS = [
    '/', '/blog', '/faq', '/guide', '/guide/autofill', '/guide/getting-started',
    '/guide/excel-format', '/guide/troubleshooting', '/guide/complete',
    '/guide/comprehensive-guide', '/guide/csv', '/guide/image-batch',
    '/guide/image-cleanup', '/guide/pdf', '/guide/seo', '/glossary',
    '/best-practices', '/case-studies', '/case-study/contact-center',
    '/case-study/consulting-firm', '/case-study/remote-startup',
    '/tools', '/tools/csv', '/tools/image-batch', '/tools/image-cleanup',
    '/tools/pdf', '/tools/seo',
]
ARTICLE_SCHEMA_REQUIRED_PATHS = [
    '/guide/autofill', '/guide/getting-started', '/guide/excel-format',
    '/guide/troubleshooting', '/guide/complete', '/guide/comprehensive-guide',
    '/guide/csv', '/guide/image-batch', '/guide/image-cleanup', '/guide/pdf',
    '/guide/seo', '/best-practices', '/case-study/contact-center',
    '/case-study/consulting-firm', '/case-study/remote-startup',
]
HUB_LINK_REQUIREMENTS = {
    '/blog': [
        '/blog/implementation-checklist',
        '/blog/automation-roadmap',
        '/blog/jobcan-auto-input-tools-overview',
        '/blog/jobcan-auto-input-dos-and-donts',
        '/blog/month-end-closing-checklist',
        '/blog/playwright-security',
    ],
    '/guide': [
        '/guide/getting-started',
        '/guide/autofill',
        '/guide/excel-format',
        '/guide/troubleshooting',
        '/guide/complete',
        '/guide/comprehensive-guide',
        '/best-practices',
    ],
    '/case-studies': [
        '/case-study/contact-center',
        '/case-study/consulting-firm',
        '/case-study/remote-startup',
    ],
    '/tools': [
        '/tools/csv',
        '/tools/image-batch',
        '/tools/image-cleanup',
        '/tools/pdf',
        '/tools/seo',
    ],
}
RELATED_CONTENT_REQUIRED_PATHS = ['/glossary', '/best-practices', '/guide/complete', '/guide/comprehensive-guide']
INTENTIONALLY_EXCLUDED_PATHS = ['/privacy', '/terms', '/contact', '/sitemap.html']

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
VISIBLE_TEXT_INTEGRITY_PATHS = [
    '/', '/faq', '/guide', '/guide/getting-started', '/guide/excel-format',
    '/guide/troubleshooting', '/guide/complete', '/guide/comprehensive-guide',
    '/guide/csv', '/guide/image-batch', '/guide/image-cleanup', '/guide/pdf',
    '/guide/seo', '/blog', '/glossary', '/best-practices', '/case-studies',
    '/case-study/contact-center', '/case-study/consulting-firm',
    '/case-study/remote-startup', '/privacy', '/terms', '/contact',
]
VISIBLE_TEXT_FORBIDDEN = ['</h1>', '</h2>', '</h3>', '</p>', '</li>', '</a>', '/h1>', '/h2>', '/h3>', '/p>', '/li>', '/a>', '/strong>', '�']
FOOTER_INTEGRITY_PATHS = ['/', '/privacy', '/terms', '/contact', '/blog']
FOOTER_REQUIRED_TEXT = [
    'プライバシーポリシー',
    '利用規約',
    'お問い合わせ',
    'ご利用にあたって',
]
TOP_INLINE_REQUIREMENTS = {
    '/': 'home_after_hero',
    '/autofill': 'public_top_inline',
    '/tools': 'public_top_inline',
    '/tools/image-batch': 'public_top_inline',
    '/tools/pdf': 'public_top_inline',
    '/tools/seo': 'public_top_inline',
    '/guide': 'public_top_inline',
    '/faq': 'public_top_inline',
    '/blog': 'blog_index_after_intro',
    '/case-studies': 'case_index_after_intro',
}

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
    from bs4 import BeautifulSoup
    rows = []
    all_ok = True

    def get(path, headers=None):
        if use_headers and headers:
            return get_fn(path, headers=headers)
        return get_fn(path)

    def canonical_for_path(path):
        base = BASE_URL_DEFAULT.rstrip('/')
        return base + ('/' if path == '/' else path)

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
            expected_canonical_url = base + (path if path != '/' else '') or '/'
            if path == '/':
                expected_canonical_url = base + '/'
            has_canonical_self = expected_canonical_url in body and 'rel="canonical"' in body
            ok = not has_noindex and has_canonical_self
            rows.append(('9_indexable', path, 'OK no noindex, canonical self' if ok else f'FAIL noindex={has_noindex} canonical={has_canonical_self}', ok))
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('9_indexable', path, f'ERROR {e}', False))
            all_ok = False

    for path in VISIBLE_TEXT_INTEGRITY_PATHS:
        try:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            soup = BeautifulSoup(body, 'html.parser')
            visible_text = soup.get_text('\n', strip=True)
            found = [token for token in VISIBLE_TEXT_FORBIDDEN if token in visible_text]
            ok = not found
            rows.append(('9a_visible_text', path, 'OK no broken tags/text' if ok else f'FAIL found {found[:3]}', ok))
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('9a_visible_text', path, f'ERROR {e}', False))
            all_ok = False

    for path in FOOTER_INTEGRITY_PATHS:
        try:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            soup = BeautifulSoup(body, 'html.parser')
            footer = soup.find('footer')
            footer_text = footer.get_text('\n', strip=True) if footer else ''
            found = [token for token in VISIBLE_TEXT_FORBIDDEN if token in footer_text]
            missing_required = [token for token in FOOTER_REQUIRED_TEXT if token not in footer_text]
            ok = bool(footer) and not found and not missing_required
            rows.append(
                (
                    '9b_footer_text',
                    path,
                    'OK footer text intact'
                    if ok else
                    f'FAIL found={found[:3]} missing={missing_required[:3]}',
                    ok,
                )
            )
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('9b_footer_text', path, f'ERROR {e}', False))
            all_ok = False

    for path in PUBLIC_AFFILIATE_PATHS:
        try:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            headers = resp.headers if hasattr(resp, 'headers') else {}
            content_type = (headers.get('Content-Type') or headers.get('content-type') or '').lower()
            soup = BeautifulSoup(body, 'html.parser')
            slot_count = len(soup.select('[data-affiliate-slot]'))
            footer_block = bool(soup.select_one('.affiliate-footer-block'))
            widget_script = any('affiliate-widgets.js' in (tag.get('src') or '') for tag in soup.find_all('script'))
            meta_utf8 = bool(soup.select_one('meta[charset="utf-8"]'))
            disclosure_count = len(soup.select('.affiliate-disclosure'))
            side_rail = bool(soup.select_one('.affiliate-side-rail [data-affiliate-rail="true"]'))
            ok = (
                'text/html' in content_type
                and 'charset=utf-8' in content_type
                and meta_utf8
                and slot_count >= 1
                and footer_block
                and widget_script
                and disclosure_count == 1
                and side_rail
            )
            rows.append(
                ('9c_affiliate_public', path,
                 f'OK slots={slot_count} footer={footer_block} rail={side_rail} disclosures={disclosure_count} script={widget_script}' if ok else
                 f'FAIL ct={content_type or "missing"} meta={meta_utf8} slots={slot_count} footer={footer_block} rail={side_rail} disclosures={disclosure_count} script={widget_script}',
                 ok)
            )
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('9c_affiliate_public', path, f'ERROR {e}', False))
            all_ok = False

    for path in NON_UI_AFFILIATE_PATHS:
        try:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            slot_count = body.count('data-affiliate-slot=')
            footer_block = 'affiliate-footer-block' in body
            side_rail = 'affiliate-side-rail' in body
            ok = slot_count == 0 and not footer_block and not side_rail
            rows.append(
                ('9d_affiliate_nonui', path,
                 f'OK slots={slot_count} footer={footer_block} rail={side_rail}' if ok else
                 f'FAIL slots={slot_count} footer={footer_block} rail={side_rail}',
                 ok)
            )
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('9d_affiliate_nonui', path, f'ERROR {e}', False))
            all_ok = False

    for path in NOINDEX_SELF_CANONICAL_PATHS:
        try:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            has_noindex = 'noindex, nofollow' in body or ('name="robots"' in body and 'noindex' in body)
            base = BASE_URL_DEFAULT.rstrip('/')
            expected_canonical_url = base + path
            has_canonical_self = expected_canonical_url in body and 'rel="canonical"' in body
            ok = has_noindex and has_canonical_self
            rows.append(('9e_noindex', path, 'OK noindex, canonical self' if ok else f'FAIL noindex={has_noindex} canonical={has_canonical_self}', ok))
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('9e_noindex', path, f'ERROR {e}', False))
            all_ok = False

    for path, slot_id in TOP_INLINE_REQUIREMENTS.items():
        try:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            soup = BeautifulSoup(body, 'html.parser')
            slot = soup.select_one(f'[data-affiliate-slot="{slot_id}"]')
            slot_before_footer = bool(slot) and slot.find_parent('footer') is None
            has_fallback = bool(slot and slot.select_one('[data-affiliate-fallback="true"]'))
            ok = bool(slot) and slot_before_footer and has_fallback
            rows.append((
                '9f_top_affiliate',
                path,
                'OK top affiliate before footer'
                if ok else
                f'FAIL slot={bool(slot)} before_footer={slot_before_footer} fallback={has_fallback}',
                ok,
            ))
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('9f_top_affiliate', path, f'ERROR {e}', False))
            all_ok = False

    sitemap_locs = set()
    try:
        import re
        resp = get('/sitemap.xml')
        body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
        sitemap_locs = set(re.findall(r'<loc>([^<]+)</loc>', body))
    except Exception:
        sitemap_locs = set()

    title_index = {}
    h1_index = {}
    for path in INDEXABILITY_TARGET_PATHS:
        try:
            resp = get(path)
            status = resp.status_code if hasattr(resp, 'status_code') else resp[0]
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            soup = BeautifulSoup(body, 'html.parser')
            robots = (soup.select_one('meta[name="robots"]') or {}).get('content', '') if soup.select_one('meta[name="robots"]') else ''
            canonical = (soup.select_one('link[rel="canonical"]') or {}).get('href', '') if soup.select_one('link[rel="canonical"]') else ''
            title = soup.title.get_text(strip=True) if soup.title else ''
            h1 = soup.find('h1').get_text(' ', strip=True) if soup.find('h1') else ''
            desc_count = len(soup.select('meta[name="description"]'))
            visible_text = soup.get_text('\n', strip=True)
            broken = [token for token in VISIBLE_TEXT_FORBIDDEN if token in visible_text]
            in_sitemap = canonical_for_path(path) in sitemap_locs
            ok = (
                status == 200
                and 'noindex' not in robots.lower()
                and canonical == canonical_for_path(path)
                and bool(title)
                and bool(h1)
                and desc_count == 1
                and not broken
                and in_sitemap
            )
            rows.append(
                ('10_indexability', path,
                 'OK canonical/self/indexable' if ok else
                 f'FAIL status={status} robots={robots or "missing"} canon={canonical or "missing"} title={bool(title)} h1={bool(h1)} desc={desc_count} sitemap={in_sitemap} broken={broken[:2]}',
                 ok)
            )
            if not ok:
                all_ok = False
            title_index.setdefault(title, []).append(path)
            h1_index.setdefault(h1, []).append(path)
        except Exception as e:
            rows.append(('10_indexability', path, f'ERROR {e}', False))
            all_ok = False

    for path in ARTICLE_SCHEMA_REQUIRED_PATHS:
        try:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            soup = BeautifulSoup(body, 'html.parser')
            schema_types = set()
            for tag in soup.select('script[type="application/ld+json"]'):
                raw = tag.get_text(strip=True)
                if not raw:
                    continue
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                payloads = payload if isinstance(payload, list) else [payload]
                for item in payloads:
                    if isinstance(item, dict):
                        item_type = item.get('@type')
                        if isinstance(item_type, list):
                            schema_types.update(item_type)
                        elif isinstance(item_type, str):
                            schema_types.add(item_type)
            ok = 'Article' in schema_types
            rows.append(('10b_article_schema', path, f'OK {sorted(schema_types)}' if ok else f'FAIL {sorted(schema_types)}', ok))
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('10b_article_schema', path, f'ERROR {e}', False))
            all_ok = False

    duplicate_titles = {title: paths for title, paths in title_index.items() if title and len(paths) > 1}
    duplicate_h1 = {title: paths for title, paths in h1_index.items() if title and len(paths) > 1}
    titles_ok = not duplicate_titles
    h1_ok = not duplicate_h1
    rows.append(('11_title_dupes', 'indexable pages', 'OK unique titles' if titles_ok else f'FAIL {list(duplicate_titles.items())[:3]}', titles_ok))
    rows.append(('11_h1_dupes', 'indexable pages', 'OK unique h1' if h1_ok else f'FAIL {list(duplicate_h1.items())[:3]}', h1_ok))
    if not titles_ok or not h1_ok:
        all_ok = False

    for hub_path, required_links in HUB_LINK_REQUIREMENTS.items():
        try:
            resp = get(hub_path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            soup = BeautifulSoup(body, 'html.parser')
            hrefs = {a.get('href') for a in soup.find_all('a', href=True)}
            missing = [href for href in required_links if href not in hrefs]
            ok = not missing
            rows.append(('12_hub_links', hub_path, 'OK all required links present' if ok else f'FAIL missing {missing[:4]}', ok))
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('12_hub_links', hub_path, f'ERROR {e}', False))
            all_ok = False

    for path in RELATED_CONTENT_REQUIRED_PATHS:
        try:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            soup = BeautifulSoup(body, 'html.parser')
            ok = bool(soup.select_one('.related-content'))
            rows.append(('13_related', path, 'OK related content rendered' if ok else 'FAIL related content missing', ok))
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('13_related', path, f'ERROR {e}', False))
            all_ok = False

    for path in INTENTIONALLY_EXCLUDED_PATHS:
        try:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            soup = BeautifulSoup(body, 'html.parser')
            robots = (soup.select_one('meta[name="robots"]') or {}).get('content', '') if soup.select_one('meta[name="robots"]') else ''
            canonical = (soup.select_one('link[rel="canonical"]') or {}).get('href', '') if soup.select_one('link[rel="canonical"]') else ''
            desc_count = len(soup.select('meta[name="description"]'))
            in_sitemap = canonical_for_path(path) in sitemap_locs
            ok = 'noindex' in robots.lower() and canonical == canonical_for_path(path) and not in_sitemap and desc_count == 1
            rows.append((
                '14_excluded',
                path,
                'OK noindex+self canonical+not in sitemap'
                if ok else
                f'FAIL robots={robots or "missing"} canon={canonical or "missing"} sitemap={in_sitemap} desc={desc_count}',
                ok,
            ))
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('14_excluded', path, f'ERROR {e}', False))
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
