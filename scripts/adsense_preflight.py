#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AdSense/site-quality preflight for the lightweight Jobcan + PDF site."""

import sys
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app

PUBLIC_200_PATHS = ['/', '/autofill', '/tools', '/tools/pdf', '/faq', '/about', '/recommend', '/privacy', '/terms', '/contact']
INDEXABLE_PATHS = ['/', '/autofill', '/tools', '/tools/pdf', '/faq', '/about']
NOINDEX_PATHS = ['/recommend', '/privacy', '/terms', '/contact']
REDIRECTS = {
    '/tools/csv': '/tools',
    '/tools/csv/': '/tools',
    '/guide/csv': '/tools',
    '/guide/excel-format': '/tools',
    '/guide/autofill': '/autofill',
    '/guide/getting-started': '/',
    '/blog/example': '/',
    '/case-studies': '/',
    '/case-study/example': '/',
    '/glossary': '/faq',
    '/best-practices': '/faq',
    '/sitemap.html': '/sitemap.xml',
    '/tools/image-batch': '/tools',
    '/tools/image-cleanup': '/tools',
    '/tools/seo': '/tools',
}
DISABLED_API_PATHS = ['/api/seo/crawl-urls', '/api/minutes/format', '/api/pdf/unlock']
SITEMAP_REQUIRED = ['/', '/autofill', '/tools', '/tools/pdf', '/faq', '/about']
SITEMAP_FORBIDDEN = ['/recommend', '/tools/csv', '/blog', '/guide', '/case-study', '/glossary', '/best-practices', '/tools/seo']
AMAZON_DISCLOSURE = 'Amazonのアソシエイトとして、当サイトは適格販売により収入を得ています。'
MOJIBAKE_FRAGMENTS = ['繝', '縺', '譁', '荳', '蜍', '諤', '邱', '縲', '陦', '隕', '螳']
FORBIDDEN_PUBLIC_LINKS = ['/tools/csv', '/guide/csv', '/guide/excel-format', '/blog', '/case-study', '/glossary', '/best-practices']
COMMERCE_FORBIDDEN_TERMS = ['最安', '必ず買うべき', 'Amazon公式おすすめ', '公式認定', '今だけ', 'ランキング1位', 'レビュー数', '星評価']
EXTERNAL_AFFILIATE_ALLOWED_PATHS = {'/recommend'}
ADSENSE_BLOCKED_PATHS = {'/recommend', '/privacy', '/terms', '/contact'}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.in_h1 = False
        self.in_ignored = False
        self.title = ''
        self.h1 = ''
        self.text_parts = []
        self.links = []
        self.canonical = ''
        self.robots = ''
        self.description = ''
        self.anchors = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = {k.lower(): (v or '') for k, v in attrs}
        tag = tag.lower()
        if tag == 'title':
            self.in_title = True
        elif tag == 'h1':
            self.in_h1 = True
        elif tag in ('script', 'style', 'noscript'):
            self.in_ignored = True
        elif tag == 'a' and attrs_dict.get('href'):
            self.links.append(attrs_dict['href'])
            self.anchors.append(attrs_dict)
        elif tag == 'link' and attrs_dict.get('rel', '').lower() == 'canonical':
            self.canonical = attrs_dict.get('href', '')
        elif tag == 'meta':
            name = attrs_dict.get('name', '').lower()
            if name == 'robots':
                self.robots = attrs_dict.get('content', '')
            elif name == 'description':
                self.description = attrs_dict.get('content', '')

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == 'title':
            self.in_title = False
        elif tag == 'h1':
            self.in_h1 = False
        elif tag in ('script', 'style', 'noscript'):
            self.in_ignored = False

    def handle_data(self, data):
        if self.in_ignored:
            return
        text = ' '.join((data or '').split())
        if not text:
            return
        self.text_parts.append(text)
        if self.in_title:
            self.title += text
        if self.in_h1:
            self.h1 += text

    @property
    def visible_text(self):
        return ' '.join(self.text_parts)


def parse_page(html):
    parser = PageParser()
    parser.feed(html)
    return parser


def expect(condition, message, failures):
    if not condition:
        failures.append(message)


def run():
    app.config['TESTING'] = True
    client = app.test_client()
    failures = []
    pages = {}

    for path in PUBLIC_200_PATHS:
        resp = client.get(path)
        html = resp.data.decode('utf-8', errors='replace')
        parser = parse_page(html)
        pages[path] = (resp, html, parser)
        expect(resp.status_code == 200, f'{path} expected 200 got {resp.status_code}', failures)
        expect(bool(parser.title.strip()), f'{path} missing title', failures)
        expect(bool(parser.h1.strip()), f'{path} missing h1', failures)
        expect(bool(parser.description.strip()), f'{path} missing meta description', failures)
        expect(path in (urlparse(parser.canonical).path or parser.canonical), f'{path} canonical is not self: {parser.canonical}', failures)
        for fragment in MOJIBAKE_FRAGMENTS:
            expect(fragment not in html, f'{path} contains mojibake fragment {fragment!r}', failures)
        for term in COMMERCE_FORBIDDEN_TERMS:
            expect(term not in parser.visible_text, f'{path} contains forbidden commerce term {term}', failures)
        if path in ADSENSE_BLOCKED_PATHS:
            expect('googlesyndication.com/pagead' not in html, f'{path} should not load AdSense', failures)

    for path in INDEXABLE_PATHS:
        expect('noindex' not in pages[path][2].robots.lower(), f'{path} should be indexable but robots={pages[path][2].robots}', failures)
    for path in NOINDEX_PATHS:
        expect('noindex' in pages[path][2].robots.lower(), f'{path} should be noindex but robots={pages[path][2].robots}', failures)

    for path, target in REDIRECTS.items():
        resp = client.get(path, follow_redirects=False)
        loc = resp.headers.get('Location', '')
        expect(resp.status_code == 301, f'{path} expected 301 got {resp.status_code}', failures)
        expect(loc.endswith(target) or target in loc, f'{path} expected redirect to {target}, got {loc}', failures)

    for path in DISABLED_API_PATHS:
        resp = client.post(path)
        expect(resp.status_code == 404, f'{path} expected 404 got {resp.status_code}', failures)
    expect(client.post('/api/pdf/lock').status_code != 404, '/api/pdf/lock should exist', failures)

    sitemap_resp = client.get('/sitemap.xml')
    sitemap = sitemap_resp.data.decode('utf-8', errors='replace')
    expect(sitemap_resp.status_code == 200, '/sitemap.xml expected 200', failures)
    for path in SITEMAP_REQUIRED:
        expect(path in sitemap, f'sitemap missing {path}', failures)
    for path in SITEMAP_FORBIDDEN:
        expect(path not in sitemap, f'sitemap still contains {path}', failures)

    ads_resp = client.get('/ads.txt')
    ads_text = ads_resp.data.decode('utf-8', errors='replace').strip()
    expect(ads_resp.status_code == 200, '/ads.txt expected 200', failures)
    expect(ads_text == 'google.com, pub-4232725615106709, DIRECT, f08c47fec0942fa0', f'ads.txt unexpected content: {ads_text}', failures)

    for path, (_, html, parser) in pages.items():
        for href in parser.links:
            for forbidden in FORBIDDEN_PUBLIC_LINKS:
                expect(not href.startswith(forbidden), f'{path} links to retired path {href}', failures)
            if 'amazon.' in href or 'a8.net' in href:
                expect(path in EXTERNAL_AFFILIATE_ALLOWED_PATHS, f'{path} has external affiliate link outside /recommend: {href}', failures)
        for attrs in parser.anchors:
            href = attrs.get('href', '')
            if 'amazon.' in href or 'a8.net' in href:
                rel = attrs.get('rel', '')
                expect('nofollow' in rel and 'sponsored' in rel, f'{path} affiliate link missing rel sponsored/nofollow: {href}', failures)
                if 'amazon.' in href:
                    query = parse_qs(urlparse(href).query).get('k', [''])[0]
                    expect(query and len(query) <= 48, f'{path} Amazon link has invalid query: {href}', failures)
                    expect('Jobcan AutoFill |' not in query, f'{path} Amazon query leaked page title: {href}', failures)

    recommend_html = pages['/recommend'][1]
    expect(AMAZON_DISCLOSURE in recommend_html, '/recommend missing Amazon disclosure', failures)
    for path in ['/privacy', '/terms', '/contact']:
        html = pages[path][1]
        expect('amazon.' not in html and 'a8.net' not in html, f'{path} should not include external affiliate links', failures)

    if failures:
        for failure in failures:
            print(f'FAIL: {failure}')
        print(f'Total failures: {len(failures)}')
        return 1
    print('OK: AdSense/site-quality preflight passed')
    return 0


if __name__ == '__main__':
    sys.exit(run())
