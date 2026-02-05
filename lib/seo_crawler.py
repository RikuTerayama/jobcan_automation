# -*- coding: utf-8 -*-
"""
SEO sitemap 用 URL クローラ（同一ホスト・BFS・制限付き）
"""

import time
from collections import deque
from urllib.parse import urljoin, urlparse, urlunparse

# 収集対象から除外する拡張子（小文字）
EXCLUDED_EXTENSIONS = (
    '.pdf', '.zip', '.jpg', '.jpeg', '.png', '.gif', '.webp',
    '.css', '.js', '.ico', '.svg', '.woff', '.woff2', '.mp4', '.mp3',
    '.xml', '.json', '.txt', '.rss', '.atom',
)

# User-Agent（robots.txt 取得・ページ取得で使用）
USER_AGENT = 'SeoSitemapCrawler/1.0'


def _get_requests():
    try:
        import requests
        return requests
    except ImportError:
        return None


def _get_bs4():
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup
    except ImportError:
        return None


def normalize_url(url, strip_query=True):
    """URLを正規化（フラグメント除去、クエリ除去、パス末尾スラッシュ統一）"""
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        return None
    path = parsed.path or '/'
    path = path.rstrip('/') or '/'
    if strip_query:
        query = ''
        fragment = ''
    else:
        query = parsed.query
        fragment = parsed.fragment
    normalized = urlunparse((parsed.scheme, parsed.netloc.lower(), path, parsed.params, query, fragment))
    return normalized


def _should_exclude_by_extension(url):
    path = urlparse(url).path or '/'
    path_lower = path.lower()
    return any(path_lower.endswith(ext) or path_lower.rstrip('/').endswith(ext) for ext in EXCLUDED_EXTENSIONS)


def _fetch_robots_disallow_prefixes(origin, request_timeout, requests_mod):
    """robots.txt を取得し、Disallow のパスプレフィックスを返す（簡易）"""
    prefixes = []
    try:
        robots_url = f"https://{origin}/robots.txt" if not origin.startswith('http') else urljoin(origin, '/robots.txt')
        if not robots_url.startswith('http'):
            robots_url = f"https://{origin}/robots.txt"
        r = requests_mod.get(robots_url, timeout=request_timeout, headers={'User-Agent': USER_AGENT})
        if r.status_code != 200:
            return []
        for line in r.text.splitlines():
            line = line.strip()
            if line.lower().startswith('disallow:'):
                path = line[9:].strip()
                if path and path != '/':
                    prefixes.append(path if path.startswith('/') else '/' + path)
    except Exception:
        pass
    return prefixes


def _is_disallowed(path, disallow_prefixes):
    """パスが Disallow のいずれかにマッチするか（プレフィックス一致）"""
    path = path or '/'
    for prefix in disallow_prefixes:
        p = prefix.rstrip('*')
        if path == p or path.startswith(p.rstrip('/') + '/') or path.startswith(p):
            return True
    return False


def crawl(start_url, max_urls=300, max_depth=3, request_timeout=5, total_timeout=60):
    """
    同一ホスト内で BFS クロールし、URL 一覧を返す。

    Args:
        start_url: 開始URL
        max_urls: 最大収集URL数
        max_depth: 最大深さ（0が開始URLのみ）
        request_timeout: 1リクエストあたりのタイムアウト（秒）
        total_timeout: 全体のタイムアウト（秒）

    Returns:
        (urls: list[str], warnings: list[str])
    """
    requests_mod = _get_requests()
    BeautifulSoup = _get_bs4()
    if not requests_mod or not BeautifulSoup:
        return [], ['requests または beautifulsoup4 がインストールされていません']

    try:
        parsed_start = urlparse(start_url)
        if parsed_start.scheme not in ('http', 'https') or not parsed_start.netloc:
            return [], ['開始URLが無効です（http/https の完全なURLを指定してください）']
        origin = parsed_start.netloc.lower()
        start_normalized = normalize_url(start_url)
        if not start_normalized:
            return [], ['開始URLの正規化に失敗しました']
    except Exception as e:
        return [], [f'開始URLの解析エラー: {e}']

    disallow_prefixes = _fetch_robots_disallow_prefixes(
        f"{parsed_start.scheme}://{parsed_start.netloc}",
        request_timeout,
        requests_mod
    )

    visited = set()
    urls = []
    warnings = []
    queue = deque([(start_url, 0)])
    deadline = time.time() + total_timeout

    while queue and time.time() < deadline and len(urls) < max_urls:
        current, depth = queue.popleft()

        if depth > max_depth:
            continue

        try:
            norm = normalize_url(current)
        except Exception:
            continue
        if not norm or norm in visited:
            continue
        if urlparse(norm).netloc.lower() != origin:
            continue

        path = urlparse(norm).path or '/'
        if _is_disallowed(path, disallow_prefixes):
            warnings.append(f'robots.txt により除外: {norm}')
            continue
        if _should_exclude_by_extension(norm):
            continue

        visited.add(norm)
        urls.append(norm)

        if len(urls) >= max_urls:
            warnings.append(f'最大URL数（{max_urls}）に達したため打ち切りました')
            break

        try:
            r = requests_mod.get(
                current,
                timeout=request_timeout,
                headers={'User-Agent': USER_AGENT},
                allow_redirects=True
            )
            r.raise_for_status()
            ct = r.headers.get('Content-Type', '')
            if 'text/html' not in ct and 'application/xhtml' not in ct:
                continue
        except requests_mod.exceptions.Timeout:
            warnings.append(f'タイムアウト: {current}')
            continue
        except requests_mod.exceptions.RequestException as e:
            warnings.append(f'取得失敗 {current}: {getattr(e, "message", str(e))}')
            continue
        except Exception as e:
            warnings.append(f'エラー {current}: {e}')
            continue

        try:
            soup = BeautifulSoup(r.text, 'html.parser')
        except Exception:
            continue

        for a in soup.find_all('a', href=True):
            href = (a.get('href') or '').strip()
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue
            try:
                abs_url = urljoin(current, href)
            except Exception:
                continue
            abs_parsed = urlparse(abs_url)
            if abs_parsed.scheme not in ('http', 'https') or not abs_parsed.netloc:
                continue
            if abs_parsed.netloc.lower() != origin:
                continue
            try:
                child_norm = normalize_url(abs_url)
            except Exception:
                continue
            if not child_norm or child_norm in visited:
                continue
            if _is_disallowed(abs_parsed.path or '/', disallow_prefixes):
                continue
            if _should_exclude_by_extension(child_norm):
                continue
            queue.append((abs_url, depth + 1))

    if time.time() >= deadline:
        warnings.append('全体のタイムアウト（60秒）に達しました')

    return urls, warnings
