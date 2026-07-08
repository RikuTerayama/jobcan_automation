#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Approved A8.net affiliate link definitions for lightweight blocks.

No advertiser is rendered unless the operator explicitly enables A8 and provides
approved link data. This prevents placeholder or unapproved programs from
leaking into production.
"""

import json
import os
from typing import Dict, List


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _load_approved_links() -> List[Dict[str, str]]:
    """Load approved A8 links from JSON in A8_AFFILIATE_LINKS_JSON.

    Expected item shape:
    {
      "enabled": true,
      "approved": true,
      "category_label": "...",
      "title": "...",
      "description": "...",
      "url": "https://...",
      "cta": "..."
    }
    """
    raw = (os.getenv("A8_AFFILIATE_LINKS_JSON") or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []

    links: List[Dict[str, str]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        if not item.get("enabled") or not item.get("approved"):
            continue
        url = str(item.get("url") or "").strip()
        title = str(item.get("title") or "").strip()
        if not (url.startswith("https://") and title):
            continue
        links.append(
            {
                "category_label": str(item.get("category_label") or "サービス").strip(),
                "title": title,
                "description": str(item.get("description") or "").strip(),
                "url": url,
                "cta": str(item.get("cta") or "詳しく見る").strip(),
            }
        )
    return links


def build_a8_lightweight_sections(path: str = "/") -> Dict[str, Dict[str, object]]:
    if not _env_flag("ENABLE_A8_AFFILIATE", False):
        return {}

    items = _load_approved_links()
    if not items:
        return {}

    # Keep the home page restrained. Other placements can be added with the same
    # approved data structure when needed.
    if (path or "/") != "/":
        return {}

    return {
        "home": {
            "anchor_id": "a8-work-services",
            "tracking_placement": "top",
            "title": "仕事環境を整えるサービス",
            "lead": "承認済みのA8.net提携サービスがある場合だけ表示します。",
            "items": items[:3],
        }
    }
