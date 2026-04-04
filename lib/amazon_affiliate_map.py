#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Route and page-type keyword mapping for Amazon recommendations.
Keep this file small and explicit so keyword tuning is easy in future PRs.
"""

from typing import Dict, List, Tuple

# Prefix based mapping: first match wins.
AMAZON_PURPOSE_GENRES: List[Dict[str, object]] = [
    {
        "id": "remote-work-comfort",
        "category_label": "快適ワーク環境",
        "title": "在宅勤務を快適にするおすすめ",
        "query": "在宅勤務 快適 グッズ",
        "keywords": ["在宅勤務 快適 グッズ", "フットレスト", "ノートPCスタンド", "クッション"],
        "cta": "Amazonで見る",
    },
    {
        "id": "desk-organization-productivity",
        "category_label": "仕事効率化",
        "title": "デスク整理・仕事効率化のおすすめ",
        "query": "デスク整理 仕事効率化 グッズ",
        "keywords": ["デスク整理 仕事効率化 グッズ", "デスク収納", "ケーブル整理", "タイマー"],
        "cta": "Amazonで見る",
    },
    {
        "id": "business-books-ai",
        "category_label": "学び・インプット",
        "title": "仕事に効くビジネス書・AI活用本",
        "query": "ビジネス書 AI活用本 おすすめ",
        "keywords": ["ビジネス書 AI活用本 おすすめ", "ビジネス書", "生成AI 活用", "業務効率化 本"],
        "cta": "Amazonで見る",
    },
]

PATH_KEYWORD_RULES: List[Tuple[str, List[str]]] = [
    ("/guide", ["在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ", "ビジネス書 AI活用本 おすすめ"]),
    ("/tools/image", ["デスク整理 仕事効率化 グッズ", "ケーブル整理", "在宅勤務 快適 グッズ"]),
    ("/tools/pdf", ["デスク整理 仕事効率化 グッズ", "在宅勤務 快適 グッズ", "業務効率化 本"]),
    ("/tools/seo", ["ビジネス書 AI活用本 おすすめ", "デスク整理 仕事効率化 グッズ", "生成AI 活用"]),
    ("/tools/csv", ["デスク整理 仕事効率化 グッズ", "在宅勤務 快適 グッズ", "ビジネス書 AI活用本 おすすめ"]),
    ("/tools", ["デスク整理 仕事効率化 グッズ", "在宅勤務 快適 グッズ", "ビジネス書 AI活用本 おすすめ"]),
    ("/autofill", ["在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ", "ビジネス書 AI活用本 おすすめ"]),
    ("/blog", ["ビジネス書 AI活用本 おすすめ", "業務効率化 本", "デスク整理 仕事効率化 グッズ"]),
    ("/case", ["在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ", "ビジネス書 AI活用本 おすすめ"]),
    ("/faq", ["デスク整理 仕事効率化 グッズ", "在宅勤務 快適 グッズ", "ビジネス書 AI活用本 おすすめ"]),
    ("/glossary", ["ビジネス書 AI活用本 おすすめ", "在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ"]),
]

PAGE_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "landing": ["在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ", "ビジネス書 AI活用本 おすすめ"],
    "guide": ["在宅勤務 快適 グッズ", "ビジネス書 AI活用本 おすすめ", "デスク整理 仕事効率化 グッズ"],
    "tool": ["デスク整理 仕事効率化 グッズ", "在宅勤務 快適 グッズ", "ビジネス書 AI活用本 おすすめ"],
    "tool_index": ["デスク整理 仕事効率化 グッズ", "在宅勤務 快適 グッズ", "ビジネス書 AI活用本 おすすめ"],
    "article": ["ビジネス書 AI活用本 おすすめ", "デスク整理 仕事効率化 グッズ", "在宅勤務 快適 グッズ"],
    "blog_index": ["ビジネス書 AI活用本 おすすめ", "業務効率化 本", "デスク整理 仕事効率化 グッズ"],
    "case_index": ["在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ", "ビジネス書 AI活用本 おすすめ"],
    "info": ["デスク整理 仕事効率化 グッズ", "在宅勤務 快適 グッズ", "ビジネス書 AI活用本 おすすめ"],
    "trust_sensitive": ["在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ", "ビジネス書 AI活用本 おすすめ"],
    "legal": ["ビジネス書 AI活用本 おすすめ", "デスク整理 仕事効率化 グッズ"],
    "contact": ["在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ"],
    "generic": ["在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ", "ビジネス書 AI活用本 おすすめ"],
}
