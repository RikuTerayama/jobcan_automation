#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Route and page-type keyword mapping for Amazon recommendations.
Keep this file small and explicit so keyword tuning is easy in future PRs.
"""

from typing import Dict, List, Tuple

# Prefix based mapping: first match wins.
PATH_KEYWORD_RULES: List[Tuple[str, List[str]]] = [
    ("/guide", ["フットレスト", "クッション", "ノートPCスタンド", "モニターアーム"]),
    ("/tools/image", ["デスク収納", "ケーブル整理", "タイマー", "USBハブ"]),
    ("/tools/pdf", ["ドキュメントファイル", "デスク収納", "タイマー"]),
    ("/tools/seo", ["モニターライト", "キーボード", "ケーブル整理"]),
    ("/tools/csv", ["デスク収納", "ノートPCスタンド", "タイマー"]),
    ("/tools", ["デスク収納", "タイマー", "ケーブル整理", "ノートPCスタンド"]),
    ("/autofill", ["ノートPCスタンド", "クッション", "モニターアーム", "ケーブル整理"]),
    ("/blog", ["バックオフィス", "業務効率化", "デスク収納", "タイマー"]),
    ("/case", ["ノートPCスタンド", "デスク収納", "バックパック"]),
    ("/faq", ["デスク収納", "ケーブル整理", "タイマー"]),
    ("/glossary", ["ノートPCスタンド", "モニターアーム", "フットレスト"]),
]

PAGE_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "landing": ["ノートPCスタンド", "デスク収納", "タイマー", "バックパック"],
    "guide": ["フットレスト", "クッション", "ノートPCスタンド", "モニターアーム"],
    "tool": ["デスク収納", "ケーブル整理", "タイマー", "USBハブ"],
    "tool_index": ["デスク収納", "タイマー", "ノートPCスタンド"],
    "article": ["業務効率化", "バックオフィス", "デスク収納"],
    "blog_index": ["業務効率化", "バックオフィス", "タイマー"],
    "case_index": ["ノートPCスタンド", "バックパック", "デスク収納"],
    "info": ["デスク収納", "ケーブル整理", "ノートPCスタンド"],
    "trust_sensitive": ["ノートPCスタンド", "モニターアーム", "ケーブル整理"],
    "legal": ["デスク収納", "タイマー"],
    "contact": ["デスク収納", "タイマー"],
    "generic": ["デスク収納", "ノートPCスタンド", "タイマー"],
}

