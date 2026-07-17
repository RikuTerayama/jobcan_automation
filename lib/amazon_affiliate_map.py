#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Amazon Associates theme definitions for the lightweight site.

Display titles and search queries are kept separate. Only approved themes with
``enabled=True`` can be rendered.
"""

from typing import Dict, List, Tuple

AMAZON_THEME_POOL: List[Dict[str, object]] = [
    {
        "id": "proposal-thinking",
        "enabled": True,
        "category_label": "思考整理",
        "title": "提案書前の思考整理",
        "description": "提案前に論点や仮説を整理したい方向け。",
        "query": "仮説思考",
        "query_variants": ["ロジカルシンキング 本", "問題解決 本", "戦略思考 本"],
        "cta": "思考法の本を探す",
        "priority_page_types": ["landing", "info", "generic"],
        "priority_path_prefixes": ["/", "/recommend", "/faq"],
    },
    {
        "id": "slide-production",
        "enabled": True,
        "category_label": "資料作成",
        "title": "スライド作成を速くする",
        "description": "資料作成やプレゼン準備を効率化したい方向け。",
        "query": "PowerPoint 資料作成 本",
        "query_variants": ["プレゼン 本", "図解 本", "ビジネスライティング 本"],
        "cta": "資料作成に役立つ本を見る",
        "priority_page_types": ["landing", "tool_index", "info"],
        "priority_path_prefixes": ["/", "/tools", "/recommend"],
    },
    {
        "id": "pdf-contract-work",
        "enabled": True,
        "category_label": "PDF・書類作業",
        "title": "PDF・契約書作業を整える",
        "description": "契約書・提案書・PDF資料を扱うことが多い方向け。",
        "query": "ドキュメントスキャナー",
        "query_variants": ["PDF 編集", "書類整理 グッズ", "USB-C ハブ"],
        "cta": "PDF・書類作業アイテムを見る",
        "priority_page_types": ["tool", "tool_index", "landing"],
        "priority_path_prefixes": ["/tools/pdf", "/tools", "/recommend"],
    },
    {
        "id": "remote-work-travel",
        "enabled": True,
        "category_label": "出張・リモート",
        "title": "出張・リモートワーク環境",
        "description": "出張先や自宅でも作業環境を整えたい方向け。",
        "query": "リモートワーク 便利グッズ",
        "query_variants": ["出張 便利グッズ", "モバイルモニター", "USB-C ハブ"],
        "cta": "出張・リモートワーク用品を見る",
        "priority_page_types": ["landing", "tool", "info"],
        "priority_path_prefixes": ["/", "/autofill", "/recommend"],
    },
    {
        "id": "focus-desk-environment",
        "enabled": True,
        "category_label": "集中環境",
        "title": "集中力を保つデスク環境",
        "description": "長時間の集中作業を支える環境づくりに。",
        "query": "ノイズキャンセリング",
        "query_variants": ["デスク タイマー", "モニター 仕事", "キーボード マウス セット"],
        "cta": "集中環境を整える",
        "priority_page_types": ["landing", "tool", "info"],
        "priority_path_prefixes": ["/", "/autofill", "/recommend"],
    },
    {
        "id": "consulting-business-books",
        "enabled": True,
        "category_label": "ビジネス書",
        "title": "コンサルワークに役立つビジネス書",
        "description": "コンサルワークの基礎体力を高める本を探す。",
        "query": "ビジネス書 おすすめ",
        "query_variants": ["仕事術 本", "生成AI 本", "コンサル 本"],
        "cta": "ビジネス書を探す",
        "priority_page_types": ["landing", "info", "generic"],
        "priority_path_prefixes": ["/", "/faq", "/recommend"],
    },
]

AMAZON_PURPOSE_GENRES = AMAZON_THEME_POOL

PATH_KEYWORD_RULES: List[Tuple[str, List[str]]] = [
    ("/tools/pdf", ["ドキュメントスキャナー", "PDF 編集", "書類整理 グッズ"]),
    ("/tools", ["PowerPoint 資料作成 本", "ドキュメントスキャナー", "仮説思考"]),
    ("/autofill", ["ノイズキャンセリング", "デスク タイマー", "仮説思考"]),
    ("/faq", ["ビジネス書 おすすめ", "リモートワーク 便利グッズ", "PDF 編集"]),
    ("/recommend", ["仮説思考", "PowerPoint 資料作成 本", "ドキュメントスキャナー"]),
    ("/", ["仮説思考", "PowerPoint 資料作成 本", "ノイズキャンセリング"]),
]

PAGE_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "landing": ["仮説思考", "PowerPoint 資料作成 本", "ノイズキャンセリング"],
    "tool": ["PDF 編集", "ドキュメントスキャナー", "PowerPoint 資料作成 本"],
    "tool_index": ["ドキュメントスキャナー", "仮説思考", "PowerPoint 資料作成 本"],
    "trust_sensitive": ["デスク タイマー", "ノイズキャンセリング", "ビジネス書 おすすめ"],
    "info": ["ビジネス書 おすすめ", "仕事術 本", "PDF 編集"],
    "generic": ["仮説思考", "ビジネス書 おすすめ", "PDF 編集"],
}


def _section(title: str, lead: str, item_ids: List[str], anchor_id: str, more_label: str = "おすすめをまとめて見る") -> Dict[str, object]:
    items = [theme for theme in AMAZON_THEME_POOL if theme["id"] in item_ids]
    return {
        "anchor_id": anchor_id,
        "title": title,
        "lead": lead,
        "more_label": more_label,
        "more_path": "/recommend",
        "items": items,
    }

LIGHTWEIGHT_AMAZON_SECTIONS: Dict[str, Dict[str, object]] = {
    "home": _section(
        "コンサルワークを支える本・作業環境",
        "Jobcan入力やPDF作業の前後に、思考整理・書類作業・集中環境を短く見比べられます。",
        ["proposal-thinking", "pdf-contract-work", "focus-desk-environment"],
        "amazon-consulting-items",
    ),
    "autofill": _section(
        "作業後の集中環境を整える",
        "勤怠入力を終えたあと、資料作成や確認作業に戻りやすい環境づくりの入口です。",
        ["focus-desk-environment", "remote-work-travel", "proposal-thinking"],
        "amazon-autofill-items",
    ),
    "tools": _section(
        "PDF・資料作業の周辺アイテム",
        "PDF整理や資料作成を進めやすくする本・道具をカテゴリ別に確認できます。",
        ["pdf-contract-work", "slide-production", "proposal-thinking"],
        "amazon-tools-items",
    ),
    "pdf": _section(
        "PDF・契約書作業を整えるアイテム",
        "提案書、契約書、請求書などPDF資料を扱うことが多い方向けの補助導線です。",
        ["pdf-contract-work", "slide-production", "remote-work-travel"],
        "amazon-pdf-items",
    ),
    "faq": _section(
        "作業環境を整えたい方へ",
        "FAQを確認したあとに、資料作成・PDF作業・集中環境のカテゴリも見比べられます。",
        ["proposal-thinking", "pdf-contract-work", "consulting-business-books"],
        "amazon-faq-items",
    ),
    "recommend": {
        "anchor_id": "recommend-categories",
        "title": "コンサルワークに役立つカテゴリ",
        "lead": "資料作成、PDF・契約書作業、思考整理、集中環境を整えたい方向けに、作業別で探せる入口をまとめています。",
        "max_items": 6,
        "items": AMAZON_THEME_POOL,
    },
}
