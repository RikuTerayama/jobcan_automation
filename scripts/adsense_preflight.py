#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEO/AdSense preflight for the intentionally small public site."""

import os
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
from urllib.robotparser import RobotFileParser

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app import app

BASE_URL = 'https://jobcan-automation.onrender.com'
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
    '/guide/complete': '/',
    '/guide/troubleshooting': '/',
    '/blog': '/',
    '/blog/example': '/',
    '/blog/automation-roadmap': '/',
    '/blog/playwright-jobcan-challenges-and-solutions': '/',
    '/blog/excel-attendance-limits': '/',
    '/blog/convince-it-and-hr-for-automation': '/',
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
AMAZON_DISCLOSURE = 'Amazonのアソシエイトとして、当サイトは適格販売により収入を得ています。'
MOJIBAKE_FRAGMENTS = ['繝', '縺', '譁', '荳', '蜍', '諤', '邱', '縲', '陦', '隕', '螳']
FORBIDDEN_PUBLIC_LINKS = ['/tools/csv', '/guide/csv', '/guide/excel-format', '/blog', '/case-study', '/glossary', '/best-practices']
COMMERCE_FORBIDDEN_TERMS = ['最安', '必ず買うべき', 'Amazon公式おすすめ', '公式認定', '今だけ', 'ランキング1位', 'レビュー数', '星評価']
EXTERNAL_AFFILIATE_ALLOWED_PATHS = {'/recommend'}
ADSENSE_PUBLISHER = 'ca-pub-4232725615106709'
ADSENSE_SCRIPT_SRC = f'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_PUBLISHER}'
ADS_TXT_RECORD = 'google.com, pub-4232725615106709, DIRECT, f08c47fec0942fa0'
ROBOTS_AGENTS = ('Googlebot', 'AdsBot-Google', 'Mediapartners-Google', 'Google-Display-Ads-Bot')
PRIVATE_ROBOTS_PATHS = ('/status/example', '/api/example', '/sessions', '/download-template', '/download-previous-template', '/cleanup-sessions')


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.in_h1 = False
        self.ignored_depth = 0
        self.title = ''
        self.title_count = 0
        self.h1 = ''
        self.h1_count = 0
        self.text_parts = []
        self.links = []
        self.canonicals = []
        self.robots_values = []
        self.descriptions = []
        self.anchors = []
        self.scripts = []
        self.open_graph = {}
        self.adsense_slot_count = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = {k.lower(): (v or '') for k, v in attrs}
        tag = tag.lower()
        if tag == 'title':
            self.in_title = True
            self.title_count += 1
        elif tag == 'h1':
            self.in_h1 = True
            self.h1_count += 1
        elif tag in ('script', 'style', 'noscript'):
            if tag == 'script':
                self.scripts.append(attrs_dict)
            self.ignored_depth += 1
        elif tag == 'a' and attrs_dict.get('href'):
            self.links.append(attrs_dict['href'])
            self.anchors.append(attrs_dict)
        elif tag == 'link' and 'canonical' in attrs_dict.get('rel', '').lower().split():
            self.canonicals.append(attrs_dict.get('href', ''))
        elif tag == 'meta':
            name = attrs_dict.get('name', '').lower()
            if name == 'robots':
                self.robots_values.append(attrs_dict.get('content', ''))
            elif name == 'description':
                self.descriptions.append(attrs_dict.get('content', ''))
            property_name = attrs_dict.get('property', '').lower()
            if property_name.startswith('og:'):
                self.open_graph[property_name] = attrs_dict.get('content', '')
        elif tag == 'ins' and 'adsbygoogle' in attrs_dict.get('class', '').lower().split():
            self.adsense_slot_count += 1

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == 'title':
            self.in_title = False
        elif tag == 'h1':
            self.in_h1 = False
        elif tag in ('script', 'style', 'noscript') and self.ignored_depth:
            self.ignored_depth -= 1

    def handle_data(self, data):
        if self.ignored_depth:
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
    def canonical(self):
        return self.canonicals[0] if self.canonicals else ''

    @property
    def robots(self):
        return self.robots_values[0] if self.robots_values else ''

    @property
    def description(self):
        return self.descriptions[0] if self.descriptions else ''

    @property
    def visible_text(self):
        return ' '.join(self.text_parts)


def parse_page(html):
    parser = PageParser()
    parser.feed(html)
    return parser


def expected_url(path):
    return f'{BASE_URL}{path}'


def directives(value):
    return {part for part in re.split(r'[\s,]+', (value or '').strip().lower()) if part}


def robots_parser(robots_text):
    parser = RobotFileParser()
    parser.set_url(f'{BASE_URL}/robots.txt')
    parser.parse(robots_text.splitlines())
    return parser


def expect(condition, message, failures):
    if not condition:
        failures.append(message)


def run():
    app.config['TESTING'] = True
    client = app.test_client()
    failures = []
    pages = {}

    # Use the production feature flag so this cannot pass just because AdSense is
    # disabled in the local shell.
    with patch.dict(os.environ, {'ADSENSE_ENABLED': 'true', 'BASE_URL': BASE_URL}):
        for path in PUBLIC_200_PATHS:
            resp = client.get(path, follow_redirects=False)
            html = resp.data.decode('utf-8', errors='replace')
            parser = parse_page(html)
            pages[path] = (resp, html, parser)
            expect(resp.status_code == 200, f'{path} expected 200 got {resp.status_code}', failures)
            expect(parser.title_count == 1 and bool(parser.title.strip()), f'{path} expected exactly one non-empty title', failures)
            expect(parser.h1_count >= 1 and bool(parser.h1.strip()), f'{path} missing h1', failures)
            expect(len(parser.descriptions) == 1 and bool(parser.description.strip()), f'{path} expected exactly one meta description', failures)
            expect(parser.canonicals == [expected_url(path)], f'{path} expected one self canonical, got {parser.canonicals}', failures)
            expect(len(parser.robots_values) == 1, f'{path} expected exactly one robots meta tag', failures)
            expect(all(parser.open_graph.get(name) for name in ('og:title', 'og:description', 'og:url', 'og:image')), f'{path} missing required Open Graph metadata', failures)
            expect(parser.open_graph.get('og:url') == expected_url(path), f'{path} og:url is not self: {parser.open_graph.get("og:url")}', failures)
            expect(any(href.startswith('/') and not href.startswith('//') for href in parser.links), f'{path} missing crawlable internal anchors', failures)
            expect(len(parser.visible_text) >= 100, f'{path} public content is unexpectedly sparse', failures)
            for fragment in MOJIBAKE_FRAGMENTS:
                expect(fragment not in html, f'{path} contains mojibake fragment {fragment!r}', failures)
            for term in COMMERCE_FORBIDDEN_TERMS:
                expect(term not in parser.visible_text, f'{path} contains forbidden commerce term {term}', failures)

    expected_legal_links = {'/about', '/privacy', '/terms', '/contact'}
    for path in INDEXABLE_PATHS:
        resp, html, parser = pages[path]
        meta_directives = directives(parser.robots)
        header_directives = directives(resp.headers.get('X-Robots-Tag', ''))
        expect({'index', 'follow'} <= meta_directives, f'{path} robots meta should be index,follow: {parser.robots}', failures)
        expect(not ({'noindex', 'nofollow'} & meta_directives), f'{path} has conflicting robots meta: {parser.robots}', failures)
        expect('noindex' not in header_directives, f'{path} has conflicting X-Robots-Tag: {resp.headers.get("X-Robots-Tag")}', failures)
        internal_paths = {urlparse(href).path for href in parser.links if href.startswith('/') and not href.startswith('//')}
        expect(expected_legal_links <= internal_paths, f'{path} cannot reach all legal/about pages with normal anchors', failures)
        loaders = [script for script in parser.scripts if script.get('src') == ADSENSE_SCRIPT_SRC]
        expect(len(loaders) == 1, f'{path} expected one AdSense loader, got {len(loaders)}', failures)
        if loaders:
            expect('async' in loaders[0], f'{path} AdSense loader is not async', failures)
            expect(loaders[0].get('crossorigin') == 'anonymous', f'{path} AdSense loader crossorigin is not anonymous', failures)
        publisher_ids = set(re.findall(r'ca-pub-\d+', html))
        expect(publisher_ids == {ADSENSE_PUBLISHER}, f'{path} unexpected AdSense publisher IDs: {sorted(publisher_ids)}', failures)
        expect(parser.adsense_slot_count == 0, f'{path} unexpectedly contains a visible AdSense slot', failures)

    tools_paths = {urlparse(href).path for href in pages['/tools'][2].links if href.startswith('/')}
    expect({'/autofill', '/tools/pdf'} <= tools_paths, '/tools cards must use normal anchors to both retained tools', failures)

    for path in NOINDEX_PATHS:
        resp, _, parser = pages[path]
        meta_directives = directives(parser.robots)
        header_directives = directives(resp.headers.get('X-Robots-Tag', ''))
        expect({'noindex', 'follow'} <= meta_directives, f'{path} robots meta should be noindex,follow: {parser.robots}', failures)
        expect('index' not in meta_directives and 'nofollow' not in meta_directives, f'{path} has conflicting robots meta: {parser.robots}', failures)
        expect({'noindex', 'follow'} <= header_directives, f'{path} X-Robots-Tag should be noindex,follow: {resp.headers.get("X-Robots-Tag")}', failures)
        expect('index' not in header_directives and 'nofollow' not in header_directives, f'{path} has conflicting X-Robots-Tag: {resp.headers.get("X-Robots-Tag")}', failures)
        expect(not any(script.get('src') == ADSENSE_SCRIPT_SRC for script in parser.scripts), f'{path} should not load AdSense', failures)
        expect(parser.adsense_slot_count == 0, f'{path} unexpectedly contains a visible AdSense slot', failures)

    for path, target in REDIRECTS.items():
        resp = client.get(path, follow_redirects=False)
        location = (resp.headers.get('Location') or '').strip()
        location_path = urlparse(location).path or location
        expect(resp.status_code == 301, f'{path} expected 301 got {resp.status_code}', failures)
        expect(location_path == target, f'{path} expected redirect to {target}, got {location}', failures)
        final_resp = client.get(location_path, follow_redirects=False) if location_path else resp
        expect(final_resp.status_code == 200, f'{path} final target expected 200 got {final_resp.status_code}', failures)
        expect(not final_resp.headers.get('Location'), f'{path} has a redirect chain via {location_path}', failures)

    expect(client.get('/not-a-real-retired-url', follow_redirects=False).status_code == 404, 'unrelated missing URLs must not redirect to the home page', failures)

    for path in DISABLED_API_PATHS:
        resp = client.post(path)
        expect(resp.status_code == 404, f'{path} expected 404 got {resp.status_code}', failures)
        api_directives = directives(resp.headers.get('X-Robots-Tag', ''))
        expect({'noindex', 'nofollow'} <= api_directives, f'{path} missing dynamic/API X-Robots-Tag', failures)
    expect(client.post('/api/pdf/lock').status_code != 404, '/api/pdf/lock should exist', failures)

    robots_resp = client.get('/robots.txt', follow_redirects=False)
    robots_text = robots_resp.data.decode('utf-8', errors='replace')
    expect(robots_resp.status_code == 200, '/robots.txt expected 200', failures)
    expect(robots_resp.mimetype == 'text/plain', f'/robots.txt expected text/plain got {robots_resp.mimetype}', failures)
    expect(robots_text.count(f'Sitemap: {BASE_URL}/sitemap.xml') == 1, '/robots.txt expected exactly one production sitemap line', failures)
    expect(not (REPO_ROOT / 'static' / 'robots.txt').exists(), 'static/robots.txt duplicates the dynamic robots route', failures)
    for agent in ROBOTS_AGENTS:
        rules = robots_parser(robots_text)
        for path in INDEXABLE_PATHS + NOINDEX_PATHS + ['/ads.txt']:
            expect(rules.can_fetch(agent, expected_url(path)), f'robots.txt blocks {agent} from {path}', failures)
    for path in PRIVATE_ROBOTS_PATHS:
        expected_rule = f'Disallow: {path.removesuffix("example")}'
        expect(robots_text.count(expected_rule) == 3, f'/robots.txt missing private route rule: {expected_rule}', failures)

    sitemap_resp = client.get('/sitemap.xml', follow_redirects=False)
    sitemap = sitemap_resp.data.decode('utf-8', errors='replace')
    expect(sitemap_resp.status_code == 200, '/sitemap.xml expected 200', failures)
    expect(sitemap_resp.mimetype == 'application/xml', f'/sitemap.xml expected application/xml got {sitemap_resp.mimetype}', failures)
    try:
        sitemap_root = ET.fromstring(sitemap)
        namespace = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        sitemap_urls = [(node.text or '').strip() for node in sitemap_root.findall('sm:url/sm:loc', namespace)]
    except ET.ParseError as exc:
        sitemap_urls = []
        failures.append(f'/sitemap.xml is invalid XML: {exc}')
    expected_sitemap_urls = [expected_url(path) for path in INDEXABLE_PATHS]
    expect(sitemap_urls == expected_sitemap_urls, f'sitemap URLs differ: {sitemap_urls}', failures)
    expect(len(sitemap_urls) == len(set(sitemap_urls)), 'sitemap contains duplicate URLs', failures)
    for sitemap_url in sitemap_urls:
        parsed_url = urlparse(sitemap_url)
        expect(parsed_url.scheme == 'https' and parsed_url.netloc == urlparse(BASE_URL).netloc, f'sitemap URL is not production HTTPS: {sitemap_url}', failures)
        path = parsed_url.path or '/'
        if path in pages:
            resp, _, parser = pages[path]
            expect(resp.status_code == 200 and not resp.headers.get('Location'), f'sitemap URL is not direct 200: {sitemap_url}', failures)
            expect(parser.canonicals == [sitemap_url], f'sitemap URL canonical mismatch: {sitemap_url}', failures)
            expect('noindex' not in directives(parser.robots), f'sitemap URL is noindex: {sitemap_url}', failures)
            expect('noindex' not in directives(resp.headers.get('X-Robots-Tag', '')), f'sitemap URL has X-Robots noindex: {sitemap_url}', failures)

    ads_resp = client.get('/ads.txt', follow_redirects=False)
    ads_text = ads_resp.data.decode('utf-8', errors='replace').strip()
    expect(ads_resp.status_code == 200, '/ads.txt expected 200', failures)
    expect(not ads_resp.headers.get('Location'), '/ads.txt must not redirect', failures)
    expect(ads_resp.mimetype == 'text/plain', f'/ads.txt expected text/plain got {ads_resp.mimetype}', failures)
    expect(ads_text == ADS_TXT_RECORD, f'ads.txt unexpected content: {ads_text}', failures)

    template_ids = set()
    template_loader_count = 0
    template_slot_count = 0
    for template_path in (REPO_ROOT / 'templates').rglob('*.html'):
        source = template_path.read_text(encoding='utf-8', errors='replace')
        template_ids.update(re.findall(r'ca-pub-\d+', source))
        template_loader_count += source.count(ADSENSE_SCRIPT_SRC)
        template_slot_count += len(re.findall(r'<ins\b[^>]*\badsbygoogle\b', source, flags=re.IGNORECASE))
    expect(template_ids == {ADSENSE_PUBLISHER}, f'templates contain unexpected AdSense publisher IDs: {sorted(template_ids)}', failures)
    expect(template_loader_count == 1, f'templates expected one AdSense loader source, got {template_loader_count}', failures)
    expect(template_slot_count == 0, f'templates unexpectedly contain {template_slot_count} visible AdSense slots', failures)

    for path, (_, _, parser) in pages.items():
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
    print('OK: minimal SEO/AdSense preflight passed (6 direct indexable URLs; 1 canonical + 1 loader each; 0 visible ad slots)')
    return 0


if __name__ == '__main__':
    sys.exit(run())
