#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Server-side Amazon Associates helpers.

Secrets stay server-side. The lightweight site mainly renders approved search-link
cards, while the Creators API path remains graceful-fallback only.
"""

import hashlib
import logging
import os
import threading
import time
from datetime import datetime
from typing import Dict, Iterable, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

try:
    import requests
except Exception:  # pragma: no cover - fallback for minimal local envs
    requests = None  # type: ignore

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

from lib.amazon_affiliate_map import (
    AMAZON_THEME_POOL,
    LIGHTWEIGHT_AMAZON_SECTIONS,
    PAGE_TYPE_KEYWORDS,
    PATH_KEYWORD_RULES,
)

logger = logging.getLogger(__name__)

_CACHE_LOCK = threading.Lock()
_TOKEN_CACHE: Dict[str, object] = {"token": None, "expires_at": 0.0}
_SEARCH_CACHE: Dict[str, Dict[str, object]] = {}
_FORBIDDEN_QUERY_FRAGMENTS = ("jobcan autofill |", "jobcan autofill")
_MAX_SEARCH_QUERY_LEN = 48
DEFAULT_FALLBACK_KEYWORDS: List[str] = ["ロジカルシンキング 本", "PDF 編集", "ビジネス書 おすすめ", "タイマー 勉強"]


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
    if normalized in {"com", "ca", "mx", "br"}:
        return "2.1"
    if normalized in {"co.uk", "de", "fr", "it", "es", "nl", "se", "pl", "be", "ie"}:
        return "2.2"
    return "2.3"


def get_settings() -> Dict[str, object]:
    locale = (os.getenv("AMAZON_CREATORS_LOCALE", "co.jp") or "co.jp").strip().lower()
    version = (os.getenv("AMAZON_CREATORS_API_VERSION", "") or "").strip() or _version_from_locale(locale)
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


def _current_associate_tag(settings: Optional[Dict[str, object]] = None) -> str:
    env_tag = (os.getenv("AMAZON_ASSOCIATE_TAG") or "").strip()
    if env_tag:
        if settings is not None:
            settings["associate_tag"] = env_tag
        return env_tag
    if settings is None:
        return ""
    return str(settings.get("associate_tag") or "").strip()


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


def _normalize_search_keyword(value: str) -> str:
    cleaned = " ".join(str(value or "").split()).strip()
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    if any(fragment in lowered for fragment in _FORBIDDEN_QUERY_FRAGMENTS):
        return ""
    if "|" in cleaned or cleaned.startswith(("http://", "https://")):
        return ""
    if len(cleaned) > _MAX_SEARCH_QUERY_LEN:
        return ""
    return cleaned


def _dedupe_search_keywords(values: Iterable[str]) -> List[str]:
    return _dedupe_keep_order([cleaned for value in values if (cleaned := _normalize_search_keyword(value))])


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
    return _dedupe_search_keywords(keyword_pool)


def _fallback_keywords_for_page(path: str, page_type: str) -> List[str]:
    fallback_pool: List[str] = []
    fallback_pool.extend(PAGE_TYPE_KEYWORDS.get(page_type or "", []))
    normalized_path = path or "/"
    for prefix, words in PATH_KEYWORD_RULES:
        if normalized_path.startswith(prefix):
            fallback_pool.extend(words)
            break
    fallback_pool.extend(DEFAULT_FALLBACK_KEYWORDS)
    return _dedupe_search_keywords(fallback_pool) or list(DEFAULT_FALLBACK_KEYWORDS)


def _theme_query_candidates(theme: Dict[str, object]) -> List[str]:
    return _dedupe_search_keywords(
        [str(theme.get("query") or "")] + [str(v) for v in (theme.get("query_variants") or [])]
    )


def _stable_hash_int(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:12], 16)


def _rotation_bucket_key() -> str:
    cadence = (os.getenv("AMAZON_THEME_ROTATION_CADENCE") or "daily").strip().lower()
    tz_name = (os.getenv("AMAZON_THEME_ROTATION_TZ") or "Asia/Tokyo").strip() or "Asia/Tokyo"
    try:
        now = datetime.now(ZoneInfo(tz_name)) if ZoneInfo else datetime.utcnow()
    except Exception:
        now = datetime.utcnow()
    if cadence == "weekly":
        iso = now.isocalendar()
        return f"weekly:{iso.year}-W{iso.week:02d}"
    if cadence == "biweekly":
        iso = now.isocalendar()
        return f"biweekly:{iso.year}-BW{((iso.week - 1) // 2) + 1:02d}"
    if cadence == "hourly":
        return now.strftime("hourly:%Y-%m-%d-%H")
    return now.strftime("daily:%Y-%m-%d")


def _enabled_theme_pool() -> List[Dict[str, object]]:
    return [theme for theme in AMAZON_THEME_POOL if bool(theme.get("enabled", False))]


def _theme_score(theme: Dict[str, object], path: str, page_type: str, context_keywords: List[str]) -> int:
    score = 0
    normalized_path = path or "/"
    if page_type and page_type in [str(v) for v in (theme.get("priority_page_types") or [])]:
        score += 3
    for prefix in [str(v) for v in (theme.get("priority_path_prefixes") or [])]:
        if prefix and normalized_path.startswith(prefix):
            score += 4
            break
    context_text = " ".join(context_keywords).lower()
    for keyword in _theme_query_candidates(theme):
        if keyword.lower() in context_text:
            score += 1
            break
    return score


def _rotate_group(items: List[Dict[str, object]], seed: str) -> List[Dict[str, object]]:
    if len(items) <= 1:
        return list(items)
    ordered = sorted(items, key=lambda x: str(x.get("id") or ""))
    offset = _stable_hash_int(seed) % len(ordered)
    return ordered[offset:] + ordered[:offset]


def _append_associate_tag(url: str, associate_tag: str) -> str:
    if not url:
        return url
    parsed = urlparse(url)
    if "amazon." not in parsed.netloc:
        return url
    query_pairs = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k.lower() != "tag"]
    if associate_tag:
        query_pairs.append(("tag", associate_tag))
    return urlunparse(parsed._replace(query=urlencode(query_pairs)))


def _build_search_url(settings: Dict[str, object], keyword: str) -> str:
    host = str(settings.get("marketplace_host") or "www.amazon.co.jp").strip()
    base_url = f"https://{host}/s?{urlencode({'k': keyword})}"
    return _append_associate_tag(base_url, _current_associate_tag(settings))


def build_rotating_theme_cards(
    path: str,
    page_type: str,
    title: str = "",
    tags: Optional[Iterable[str]] = None,
    recent_history: Optional[Iterable[dict]] = None,
    slot_id: str = "upper-amazon",
    count: int = 3,
    exclude_theme_ids: Optional[Iterable[str]] = None,
) -> List[dict]:
    settings = get_settings()
    max_count = max(1, int(count))
    exclude_ids = {str(v) for v in (exclude_theme_ids or []) if v}
    approved_pool = _enabled_theme_pool()
    if not approved_pool:
        return []
    keyword_pool = build_keywords(path, page_type, title, tags, recent_history) or _fallback_keywords_for_page(path, page_type)
    rotation_key = _rotation_bucket_key()

    grouped_by_score: Dict[int, List[Dict[str, object]]] = {}
    for theme in approved_pool:
        score = _theme_score(theme, path, page_type, keyword_pool)
        grouped_by_score.setdefault(score, []).append(theme)

    ordered_candidates: List[Dict[str, object]] = []
    for score in sorted(grouped_by_score.keys(), reverse=True):
        ordered_candidates.extend(_rotate_group(grouped_by_score[score], f"{rotation_key}:{path}:{page_type}:{slot_id}:{score}"))

    selected: List[Dict[str, object]] = []
    for theme in ordered_candidates:
        theme_id = str(theme.get("id") or "")
        if theme_id in exclude_ids:
            continue
        selected.append(theme)
        if len(selected) >= max_count:
            break

    cards: List[dict] = []
    for theme in selected:
        theme_id = str(theme.get("id") or "")
        query_candidates = _theme_query_candidates(theme) or _fallback_keywords_for_page(path, page_type)
        query = query_candidates[_stable_hash_int(f"{rotation_key}:{path}:{page_type}:{slot_id}:{theme_id}:query") % len(query_candidates)]
        cards.append(
            {
                "title": str(theme.get("title") or query),
                "category_label": str(theme.get("category_label") or "おすすめ"),
                "image_url": "",
                "url": _build_search_url(settings, query),
                "cta": str(theme.get("cta") or "Amazonで探す"),
                "keyword": query,
                "theme_id": theme_id,
                "rotation_bucket": rotation_key,
            }
        )
    return cards


def build_purpose_genre_cards(
    path: str,
    page_type: str,
    title: str = "",
    tags: Optional[Iterable[str]] = None,
    recent_history: Optional[Iterable[dict]] = None,
) -> List[dict]:
    return build_rotating_theme_cards(path, page_type, title, tags, recent_history, slot_id="upper-amazon", count=3)


def _lightweight_section_key(path: str) -> str:
    normalized = (path or "/").rstrip("/") or "/"
    if normalized == "/":
        return "home"
    if normalized == "/autofill":
        return "autofill"
    if normalized == "/tools":
        return "tools"
    if normalized == "/tools/pdf":
        return "pdf"
    if normalized == "/faq":
        return "faq"
    if normalized == "/recommend":
        return "recommend"
    return ""


def build_lightweight_amazon_sections(path: str, page_type: str = "") -> Dict[str, dict]:
    section_key = _lightweight_section_key(path)
    if not section_key:
        return {}
    section = LIGHTWEIGHT_AMAZON_SECTIONS.get(section_key)
    if not isinstance(section, dict):
        return {}

    settings = get_settings()
    rotation_key = _rotation_bucket_key()
    cards: List[dict] = []
    for index, raw_item in enumerate(section.get("items") or []):
        if not isinstance(raw_item, dict):
            continue
        query_candidates = _dedupe_search_keywords(
            [str(raw_item.get("query") or "")] + [str(v) for v in (raw_item.get("query_variants") or [])]
        ) or _fallback_keywords_for_page(path, page_type)
        query = query_candidates[_stable_hash_int(f"{rotation_key}:{section_key}:{index}:lightweight") % len(query_candidates)]
        cards.append(
            {
                "category_label": str(raw_item.get("category_label") or "おすすめ"),
                "title": str(raw_item.get("title") or query),
                "description": str(raw_item.get("description") or ""),
                "url": _build_search_url(settings, query),
                "cta": str(raw_item.get("cta") or "Amazonで探す"),
                "keyword": query,
            }
        )

    if not cards:
        return {}
    return {
        section_key: {
            "anchor_id": str(section.get("anchor_id") or f"amazon-{section_key}-items"),
            "title": str(section.get("title") or "関連アイテム"),
            "lead": str(section.get("lead") or ""),
            "items": cards[: max(1, int(section.get("max_items") or 3))],
            "rotation_bucket": rotation_key,
            "more_label": str(section.get("more_label") or ""),
            "more_path": str(section.get("more_path") or ""),
            "source": "lightweight_static",
        }
    }


def _make_cache_key(settings: Dict[str, object], keywords: List[str]) -> str:
    raw = "|".join([str(settings.get("marketplace_locale", "")), _current_associate_tag(settings), str(settings.get("max_items", "")), "::".join(keywords[:10])])
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
        _SEARCH_CACHE[cache_key] = {"items": items, "expires_at": time.time() + max(30, int(ttl))}


def _build_fallback_items(settings: Dict[str, object], keywords: List[str]) -> List[dict]:
    max_items = max(1, int(settings.get("max_items") or 6))
    items: List[dict] = []
    seen_urls = set()
    for keyword in _dedupe_search_keywords(keywords) or DEFAULT_FALLBACK_KEYWORDS:
        url = _build_search_url(settings, keyword)
        if url in seen_urls:
            continue
        seen_urls.add(url)
        items.append({"title": f"{keyword} を探す", "image_url": "", "url": url, "cta": "Amazonで探す", "keyword": keyword, "fallback": True})
        if len(items) >= max_items:
            break
    return items


def _apply_fallback(result: Dict[str, object], reason: str, settings: Dict[str, object], keywords: List[str]) -> Dict[str, object]:
    result["items"] = _build_fallback_items(settings, keywords or DEFAULT_FALLBACK_KEYWORDS)[: int(settings["max_items"])]
    result["source"] = "fallback" if result["items"] else "none"
    result["error"] = reason
    return result


def _get_access_token(settings: Dict[str, object]) -> Optional[str]:
    if requests is None:
        return None
    now = time.time()
    with _CACHE_LOCK:
        token = _TOKEN_CACHE.get("token")
        expires_at = float(_TOKEN_CACHE.get("expires_at", 0))
        if token and now < (expires_at - 30):
            return str(token)
    payload = {
        "grant_type": "client_credentials",
        "client_id": str(settings["client_id"]),
        "client_secret": str(settings["client_secret"]),
        "scope": "creatorsapi/default",
    }
    try:
        resp = requests.post(str(settings["token_endpoint"]), data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=float(settings["timeout_sec"]))
    except Exception as exc:
        logger.warning("amazon_creators_token_request_error type=%s detail=%s", type(exc).__name__, str(exc))
        return None
    if resp.status_code != 200:
        logger.warning("amazon_creators_token_http_error status=%s body=%s", resp.status_code, resp.text[:300])
        return None
    try:
        body = resp.json()
    except ValueError:
        return None
    access_token = (body.get("access_token") or "").strip()
    if not access_token:
        return None
    with _CACHE_LOCK:
        _TOKEN_CACHE["token"] = access_token
        _TOKEN_CACHE["expires_at"] = time.time() + max(120, int(body.get("expires_in") or 3600))
    return access_token


def _extract_items(payload: dict, associate_tag: str, max_items: int) -> List[dict]:
    if not isinstance(payload, dict):
        return []
    candidates = []
    for path in (("searchResult", "items"), ("SearchResult", "Items"), ("itemsResult", "items"), ("ItemsResult", "Items"), ("items",), ("Items",)):
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
        info = raw_item.get("itemInfo") or raw_item.get("ItemInfo") or {}
        title_node = info.get("title") or info.get("Title") or {}
        title = str(title_node.get("displayValue") or title_node.get("DisplayValue") or raw_item.get("title") or raw_item.get("Title") or "").strip()
        images = raw_item.get("images") or raw_item.get("Images") or {}
        primary = images.get("primary") or images.get("Primary") or {}
        large = primary.get("large") or primary.get("Large") or {}
        image_url = str(large.get("url") or large.get("URL") or raw_item.get("imageUrl") or raw_item.get("ImageURL") or "").strip()
        detail_url = _append_associate_tag(str(raw_item.get("detailPageURL") or raw_item.get("DetailPageURL") or raw_item.get("url") or raw_item.get("Url") or "").strip(), associate_tag)
        if not title or not detail_url or detail_url in seen_urls:
            continue
        seen_urls.add(detail_url)
        items.append({"title": title, "image_url": image_url, "url": detail_url, "cta": "Amazonで見る"})
        if len(items) >= max_items:
            break
    return items


def _search_items(settings: Dict[str, object], token: str, keyword: str) -> List[dict]:
    if requests is None:
        return []
    associate_tag = _current_associate_tag(settings)
    endpoint = "https://{host}{base}/{operation}".format(host=settings["api_host"], base=str(settings["api_base_path"]).rstrip("/"), operation=str(settings["api_operation"]).lstrip("/"))
    payload = {
        "partnerTag": associate_tag,
        "partnerType": "Associates",
        "keywords": keyword,
        "itemCount": min(10, int(settings["max_items"])),
        "searchIndex": "All",
        "availability": "Available",
        "resources": ["images.primary.large", "itemInfo.title", "detailPageURL"],
    }
    headers = {"Content-Type": "application/json; charset=utf-8", "Authorization": f"Bearer {token}, Version {settings['version']}", "x-marketplace": settings["marketplace_host"]}
    try:
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=float(settings["timeout_sec"]))
    except Exception as exc:
        logger.warning("amazon_creators_search_request_error keyword=%s type=%s detail=%s", keyword, type(exc).__name__, str(exc))
        return []
    if resp.status_code != 200:
        logger.warning("amazon_creators_search_http_error keyword=%s status=%s body=%s", keyword, resp.status_code, resp.text[:300])
        return []
    try:
        body = resp.json()
    except ValueError:
        return []
    if isinstance(body, dict) and body.get("errors"):
        logger.warning("amazon_creators_search_semantic_error keyword=%s errors=%s", keyword, str(body.get("errors"))[:300])
        return []
    return _extract_items(body, associate_tag, int(settings["max_items"]))


def get_recommendations(
    path: str,
    page_type: str,
    title: str = "",
    tags: Optional[Iterable[str]] = None,
    recent_history: Optional[Iterable[dict]] = None,
) -> Dict[str, object]:
    settings = get_settings()
    enabled = bool(settings["enabled"])
    result: Dict[str, object] = {"enabled": enabled, "items": [], "keywords": [], "error": None, "source": "none"}
    if not enabled:
        return result

    keywords = build_keywords(path, page_type, title, tags, recent_history) or _fallback_keywords_for_page(path, page_type)
    result["keywords"] = keywords
    if not _current_associate_tag(settings):
        logger.warning("amazon_creators_missing_associate_tag path=%s page_type=%s", path, page_type)
        return _apply_fallback(result, "missing_associate_tag", settings, keywords)

    cache_key = _make_cache_key(settings, keywords)
    cached = _cached_get(cache_key)
    if cached is not None:
        result["items"] = cached[: int(settings["max_items"])]
        result["source"] = "cache"
        return result

    if not settings["client_id"] or not settings["client_secret"]:
        return _apply_fallback(result, "missing_credentials", settings, keywords)
    token = _get_access_token(settings)
    if not token:
        return _apply_fallback(result, "token_unavailable", settings, keywords)

    combined: List[dict] = []
    seen = set()
    for keyword in keywords[:6]:
        for item in _search_items(settings, token, keyword):
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
        return _apply_fallback(result, "empty_response", settings, keywords)
    _cached_set(cache_key, int(settings["cache_ttl_seconds"]), combined)
    result["items"] = combined
    result["source"] = "api"
    return result
