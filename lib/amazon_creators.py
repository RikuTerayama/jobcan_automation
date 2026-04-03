#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import logging
import os
import threading
import time
from typing import Dict, Iterable, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

from lib.amazon_affiliate_map import PAGE_TYPE_KEYWORDS, PATH_KEYWORD_RULES

logger = logging.getLogger(__name__)

_CACHE_LOCK = threading.Lock()
_TOKEN_CACHE: Dict[str, object] = {"token": None, "expires_at": 0.0}
_SEARCH_CACHE: Dict[str, Dict[str, object]] = {}


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


def _version_from_locale(locale: str) -> str:
    normalized = (locale or "co.jp").strip().lower()
    na = {"com", "ca", "mx", "br"}
    eu = {"co.uk", "de", "fr", "it", "es", "nl", "se", "pl", "be", "ie"}
    if normalized in na:
        return "2.1"
    if normalized in eu:
        return "2.2"
    return "2.3"


def get_settings() -> Dict[str, object]:
    locale = (os.getenv("AMAZON_CREATORS_LOCALE", "co.jp") or "co.jp").strip().lower()
    version = (os.getenv("AMAZON_CREATORS_API_VERSION", "") or "").strip()
    if not version:
        version = _version_from_locale(locale)

    token_endpoints = {
        "2.1": "https://creatorsapi.auth.us-east-1.amazoncognito.com/oauth2/token",
        "2.2": "https://creatorsapi.auth.eu-south-2.amazoncognito.com/oauth2/token",
        "2.3": "https://creatorsapi.auth.us-west-2.amazoncognito.com/oauth2/token",
    }

    return {
        "enabled": _env_flag("AMAZON_AFFILIATE_ENABLED", False),
        "client_id": (os.getenv("AMAZON_CREATORS_CLIENT_ID") or "").strip(),
        "client_secret": (os.getenv("AMAZON_CREATORS_CLIENT_SECRET") or "").strip(),
        "associate_tag": (os.getenv("AMAZON_ASSOCIATE_TAG") or "").strip(),
        "cache_ttl_seconds": _env_int("AMAZON_CACHE_TTL_SECONDS", 3300),
        "max_items": _env_int("AMAZON_MAX_ITEMS", 6),
        "marketplace_locale": locale,
        "marketplace_host": f"www.amazon.{locale}",
        "api_host": (os.getenv("AMAZON_CREATORS_API_HOST") or "creatorsapi.amazon").strip(),
        "api_base_path": (os.getenv("AMAZON_CREATORS_API_BASE_PATH") or "/catalog/v1").strip(),
        "api_operation": (os.getenv("AMAZON_CREATORS_OPERATION") or "searchItems").strip(),
        "version": version,
        "token_endpoint": token_endpoints.get(version, token_endpoints["2.3"]),
        "timeout_sec": float(os.getenv("AMAZON_CREATORS_TIMEOUT_SEC", "5.0")),
    }


def _dedupe_keep_order(values: Iterable[str]) -> List[str]:
    seen = set()
    output: List[str] = []
    for value in values:
        cleaned = (value or "").strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(cleaned)
    return output


def build_keywords(
    path: str,
    page_type: str,
    title: str = "",
    tags: Optional[Iterable[str]] = None,
    recent_history: Optional[Iterable[dict]] = None,
) -> List[str]:
    normalized_path = path or "/"
    keyword_pool: List[str] = []

    keyword_pool.extend(PAGE_TYPE_KEYWORDS.get(page_type or "", []))

    for prefix, words in PATH_KEYWORD_RULES:
        if normalized_path.startswith(prefix):
            keyword_pool.extend(words)
            break

    if tags:
        keyword_pool.extend([str(tag) for tag in tags if tag])

    if title:
        # Keep the title itself as a weak hint to diversify the first query.
        keyword_pool.append(str(title).strip())

    if recent_history:
        for entry in recent_history:
            if not isinstance(entry, dict):
                continue
            hist_keywords = entry.get("keywords") or entry.get("k") or []
            if isinstance(hist_keywords, list):
                keyword_pool.extend([str(v) for v in hist_keywords if v])
            hist_page_type = entry.get("page_type") or entry.get("t")
            if hist_page_type:
                keyword_pool.extend(PAGE_TYPE_KEYWORDS.get(str(hist_page_type), []))

    return _dedupe_keep_order(keyword_pool)


def _make_cache_key(settings: Dict[str, object], keywords: List[str]) -> str:
    raw = "|".join(
        [
            str(settings.get("marketplace_locale", "")),
            str(settings.get("associate_tag", "")),
            str(settings.get("max_items", "")),
            "::".join(keywords[:10]),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cached_get(cache_key: str) -> Optional[List[dict]]:
    with _CACHE_LOCK:
        entry = _SEARCH_CACHE.get(cache_key)
        if not entry:
            return None
        if time.time() > float(entry.get("expires_at", 0)):
            _SEARCH_CACHE.pop(cache_key, None)
            return None
        return entry.get("items")  # type: ignore[return-value]


def _cached_set(cache_key: str, ttl: int, items: List[dict]) -> None:
    with _CACHE_LOCK:
        _SEARCH_CACHE[cache_key] = {
            "items": items,
            "expires_at": time.time() + max(30, int(ttl)),
        }


def _get_access_token(settings: Dict[str, object]) -> Optional[str]:
    now = time.time()
    with _CACHE_LOCK:
        token = _TOKEN_CACHE.get("token")
        expires_at = float(_TOKEN_CACHE.get("expires_at", 0))
        if token and now < (expires_at - 30):
            return str(token)

    token_endpoint = str(settings["token_endpoint"])
    payload = {
        "grant_type": "client_credentials",
        "client_id": str(settings["client_id"]),
        "client_secret": str(settings["client_secret"]),
        "scope": "creatorsapi/default",
    }

    try:
        resp = requests.post(
            token_endpoint,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=float(settings["timeout_sec"]),
        )
    except requests.RequestException as exc:
        logger.warning("amazon_creators_token_request_error type=%s detail=%s", type(exc).__name__, str(exc))
        return None

    if resp.status_code != 200:
        logger.warning("amazon_creators_token_http_error status=%s body=%s", resp.status_code, resp.text[:300])
        return None

    try:
        body = resp.json()
    except ValueError:
        logger.warning("amazon_creators_token_invalid_json")
        return None

    access_token = (body.get("access_token") or "").strip()
    expires_in = int(body.get("expires_in") or 3600)
    if not access_token:
        logger.warning("amazon_creators_token_missing_access_token")
        return None

    with _CACHE_LOCK:
        _TOKEN_CACHE["token"] = access_token
        _TOKEN_CACHE["expires_at"] = time.time() + max(120, expires_in)
    return access_token


def _append_associate_tag(url: str, associate_tag: str) -> str:
    if not url or not associate_tag:
        return url
    parsed = urlparse(url)
    if "amazon." not in parsed.netloc:
        return url
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if "tag" in query:
        return url
    query["tag"] = associate_tag
    return urlunparse(parsed._replace(query=urlencode(query)))


def _extract_items(payload: dict, associate_tag: str, max_items: int) -> List[dict]:
    if not isinstance(payload, dict):
        return []

    candidates = []
    # Creators API and PA-API style variants.
    for path in (
        ("searchResult", "items"),
        ("SearchResult", "Items"),
        ("itemsResult", "items"),
        ("ItemsResult", "Items"),
        ("result", "items"),
        ("items",),
        ("Items",),
    ):
        node = payload
        for key in path:
            if not isinstance(node, dict):
                node = None
                break
            node = node.get(key)
        if isinstance(node, list):
            candidates = node
            break

    items: List[dict] = []
    seen_urls = set()
    for raw_item in candidates:
        if not isinstance(raw_item, dict):
            continue

        item_info = raw_item.get("itemInfo") or raw_item.get("ItemInfo") or {}
        title_node = item_info.get("title") or item_info.get("Title") or {}
        title = (
            title_node.get("displayValue")
            or title_node.get("DisplayValue")
            or title_node.get("value")
            or title_node.get("Value")
            or raw_item.get("title")
            or raw_item.get("Title")
            or ""
        )
        title = str(title).strip()

        images = raw_item.get("images") or raw_item.get("Images") or {}
        primary = images.get("primary") or images.get("Primary") or {}
        large = primary.get("large") or primary.get("Large") or {}
        image_url = (
            large.get("url")
            or large.get("URL")
            or raw_item.get("imageUrl")
            or raw_item.get("ImageURL")
            or ""
        )
        image_url = str(image_url).strip()

        detail_url = (
            raw_item.get("detailPageURL")
            or raw_item.get("DetailPageURL")
            or raw_item.get("url")
            or raw_item.get("Url")
            or ""
        )
        detail_url = _append_associate_tag(str(detail_url).strip(), associate_tag)

        if not title or not detail_url:
            continue
        if detail_url in seen_urls:
            continue
        seen_urls.add(detail_url)

        items.append(
            {
                "title": title,
                "image_url": image_url,
                "url": detail_url,
                "cta": "Amazonで見る",
            }
        )
        if len(items) >= max_items:
            break
    return items


def _search_items(settings: Dict[str, object], token: str, keyword: str) -> List[dict]:
    endpoint = "https://{host}{base}/{operation}".format(
        host=settings["api_host"],
        base=str(settings["api_base_path"]).rstrip("/"),
        operation=str(settings["api_operation"]).lstrip("/"),
    )
    payload = {
        "partnerTag": settings["associate_tag"],
        "partnerType": "Associates",
        "keywords": keyword,
        "itemCount": min(10, int(settings["max_items"])),
        "searchIndex": "All",
        "availability": "Available",
        "resources": [
            "images.primary.large",
            "itemInfo.title",
            "detailPageURL",
        ],
    }
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {token}, Version {settings['version']}",
        "x-marketplace": settings["marketplace_host"],
    }

    try:
        resp = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=float(settings["timeout_sec"]),
        )
    except requests.RequestException as exc:
        logger.warning(
            "amazon_creators_search_request_error keyword=%s type=%s detail=%s",
            keyword,
            type(exc).__name__,
            str(exc),
        )
        return []

    if resp.status_code != 200:
        logger.warning(
            "amazon_creators_search_http_error keyword=%s status=%s body=%s",
            keyword,
            resp.status_code,
            resp.text[:300],
        )
        return []

    try:
        body = resp.json()
    except ValueError:
        logger.warning("amazon_creators_search_invalid_json keyword=%s", keyword)
        return []

    if isinstance(body, dict) and body.get("errors"):
        logger.warning("amazon_creators_search_semantic_error keyword=%s errors=%s", keyword, str(body.get("errors"))[:300])
        return []

    return _extract_items(body, str(settings["associate_tag"]), int(settings["max_items"]))


def get_recommendations(
    path: str,
    page_type: str,
    title: str = "",
    tags: Optional[Iterable[str]] = None,
    recent_history: Optional[Iterable[dict]] = None,
) -> Dict[str, object]:
    settings = get_settings()
    enabled = bool(settings["enabled"])

    result: Dict[str, object] = {
        "enabled": enabled,
        "items": [],
        "keywords": [],
        "error": None,
        "source": "none",
    }
    if not enabled:
        return result

    if not settings["associate_tag"]:
        result["error"] = "missing_associate_tag"
        return result

    keywords = build_keywords(
        path=path,
        page_type=page_type,
        title=title,
        tags=tags,
        recent_history=recent_history,
    )
    if not keywords:
        result["error"] = "no_keywords"
        return result

    result["keywords"] = keywords
    cache_key = _make_cache_key(settings, keywords)
    cached = _cached_get(cache_key)
    if cached is not None:
        result["items"] = cached[: int(settings["max_items"])]
        result["source"] = "cache"
        return result

    if not settings["client_id"] or not settings["client_secret"]:
        result["error"] = "missing_credentials"
        return result

    token = _get_access_token(settings)
    if not token:
        result["error"] = "token_unavailable"
        return result

    combined: List[dict] = []
    seen = set()
    for keyword in keywords[:6]:
        batch = _search_items(settings, token, keyword)
        for item in batch:
            url = item.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            enriched = dict(item)
            enriched["keyword"] = keyword
            combined.append(enriched)
            if len(combined) >= int(settings["max_items"]):
                break
        if len(combined) >= int(settings["max_items"]):
            break

    if not combined:
        result["error"] = "empty_response"
        return result

    _cached_set(cache_key, int(settings["cache_ttl_seconds"]), combined)
    result["items"] = combined
    result["source"] = "api"
    return result

