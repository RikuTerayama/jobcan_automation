#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Route and page-type keyword mapping for Amazon recommendations.
Keep this file small and explicit so keyword tuning is easy in future PRs.
"""

from typing import Dict, List, Tuple

# Approved theme pool for Amazon recommendation cards.
# - Only entries with enabled=True are eligible for production rendering.
# - Keep display copy (title/category_label) separate from search query.
# - Future flow: AI proposes candidates -> human approves by toggling enabled.
AMAZON_THEME_POOL: List[Dict[str, object]] = [
    {
        "id": "remote-work-comfort",
        "enabled": True,
        "category_label": "快適ワーク環境",
        "title": "在宅勤務を快適にするおすすめ",
        "query": "在宅勤務 快適 グッズ",
        "query_variants": ["在宅勤務 快適化 アイテム", "リモートワーク 快適 グッズ"],
        "cta": "Amazonで見る",
        "priority_page_types": ["landing", "tool", "tool_index", "trust_sensitive", "info"],
        "priority_path_prefixes": ["/", "/autofill", "/tools", "/faq"],
    },
    {
        "id": "desk-organization-productivity",
        "enabled": True,
        "category_label": "仕事効率化",
        "title": "デスク整理・仕事効率化のおすすめ",
        "query": "デスク整理 仕事効率化 グッズ",
        "query_variants": ["デスク周り 整理 便利グッズ", "作業効率アップ デスクアイテム"],
        "cta": "Amazonで見る",
        "priority_page_types": ["landing", "tool", "tool_index", "info", "generic"],
        "priority_path_prefixes": ["/", "/tools", "/faq"],
    },
    {
        "id": "business-books-ai",
        "enabled": True,
        "category_label": "学び・インプット",
        "title": "仕事に効くビジネス書・AI活用本",
        "query": "ビジネス書 おすすめ",
        "query_variants": ["生成AI 本", "仕事術 本"],
        "cta": "Amazonで見る",
        "priority_page_types": ["landing", "info", "generic"],
        "priority_path_prefixes": ["/", "/faq"],
    },
    {
        "id": "long-hours-deskwork",
        "enabled": True,
        "category_label": "長時間作業対策",
        "title": "長時間デスクワークをラクにするおすすめ",
        "query": "長時間 デスクワーク 疲労軽減 グッズ",
        "query_variants": ["デスクワーク 疲れ対策 アイテム", "仕事中 疲労軽減 グッズ"],
        "cta": "Amazonで見る",
        "priority_page_types": ["landing", "tool", "trust_sensitive"],
        "priority_path_prefixes": ["/", "/autofill", "/tools"],
    },
    {
        "id": "posture-shoulder-back",
        "enabled": True,
        "category_label": "姿勢ケア",
        "title": "姿勢改善・肩腰対策のおすすめ",
        "query": "姿勢改善 肩こり 腰痛 対策 グッズ",
        "query_variants": ["肩こり 腰痛 デスクワーク 対策", "姿勢サポート アイテム"],
        "cta": "Amazonで見る",
        "priority_page_types": ["landing", "tool", "info", "trust_sensitive"],
        "priority_path_prefixes": ["/", "/faq", "/autofill", "/tools"],
    },
    {
        "id": "space-saving-desk",
        "enabled": True,
        "category_label": "省スペース整備",
        "title": "省スペースで整うデスク環境のおすすめ",
        "query": "省スペース デスク環境 整理 グッズ",
        "query_variants": ["狭いデスク 整理 便利グッズ", "デスク収納 省スペース おすすめ"],
        "cta": "Amazonで見る",
        "priority_page_types": ["tool", "tool_index", "landing", "generic"],
        "priority_path_prefixes": ["/tools", "/", "/contact"],
    },
    # Reserved candidates (disabled by default until human review/approval).
    {
        "id": "focus-sound-environment",
        "enabled": False,
        "category_label": "集中環境",
        "title": "集中しやすい作業環境をつくるおすすめ",
        "query": "集中力 作業環境 グッズ",
        "query_variants": [],
        "cta": "Amazonで見る",
        "priority_page_types": ["landing", "info"],
        "priority_path_prefixes": ["/", "/faq"],
    },
]

# Backward-compat alias for older imports.
AMAZON_PURPOSE_GENRES = AMAZON_THEME_POOL

PATH_KEYWORD_RULES: List[Tuple[str, List[str]]] = [
    ("/tools/csv", ["デスク収納", "仕事効率化 グッズ", "ビジネス書 おすすめ"]),
    ("/tools", ["デスク収納", "在宅勤務 グッズ", "仕事効率化 グッズ"]),
    ("/autofill", ["在宅勤務 グッズ", "デスクワーク 快適 グッズ", "仕事術 本"]),
    ("/faq", ["仕事効率化 グッズ", "ビジネス書 おすすめ", "デスクワーク 快適 グッズ"]),
    ("/", ["在宅勤務 グッズ", "デスク収納", "ビジネス書 おすすめ"]),
]

PAGE_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "landing": ["在宅勤務 グッズ", "デスク収納", "ビジネス書 おすすめ"],
    "tool": ["デスク収納", "仕事効率化 グッズ", "デスクワーク 快適 グッズ"],
    "tool_index": ["デスク収納", "在宅勤務 グッズ", "仕事効率化 グッズ"],
    "trust_sensitive": ["在宅勤務 グッズ", "デスクワーク 快適 グッズ", "仕事術 本"],
    "info": ["仕事効率化 グッズ", "ビジネス書 おすすめ", "デスクワーク 快適 グッズ"],
    "legal": ["ビジネス書 おすすめ", "仕事効率化 グッズ"],
    "contact": ["在宅勤務 グッズ", "デスク収納"],
    "generic": ["在宅勤務 グッズ", "デスク収納", "ビジネス書 おすすめ"],
}


# Lightweight Amazon Associates sections for the simplified site.
# These are static, approved editorial themes. They intentionally avoid price,
# inventory, rating, or review claims so they stay stable without API refreshes.
LIGHTWEIGHT_AMAZON_SECTIONS: Dict[str, Dict[str, object]] = {
    "home": {
        "anchor_id": "amazon-work-items",
        "title": "作業をもっと楽にするアイテム",
        "lead": "ツール利用の前後で使いやすい、業務効率化向けの周辺アイテムをまとめています。",
        "more_label": "業務効率化アイテムをまとめて見る",
        "more_path": "/recommend",
        "items": [
            {
                "category_label": "勤怠入力",
                "title": "勤怠入力を楽にする",
                "description": "テンキーや入力しやすい周辺機器をまとめて探せます。",
                "query": "テンキー ワイヤレス",
                "query_variants": ["テンキー", "ワイヤレスマウス", "キーボード", "タイマー"],
                "cta": "Amazonで探す",
            },
            {
                "category_label": "CSV/Excel",
                "title": "Excel/CSV作業を楽にする",
                "description": "確認作業や表計算の効率化に役立つアイテムを見比べられます。",
                "query": "Excel 効率化 本",
                "query_variants": ["Excel効率化本", "テンキー", "モバイルモニター", "USB-Cハブ"],
                "cta": "Amazonで探す",
            },
            {
                "category_label": "デスク作業",
                "title": "デスク作業を楽にする",
                "description": "長時間の入力や確認作業をしやすくするデスク周りを整えます。",
                "query": "デスクワーク 便利グッズ",
                "query_variants": ["デスク収納", "ノートPCスタンド", "モニターアーム", "フットレスト"],
                "cta": "Amazonで探す",
            },
        ],
    },
    "autofill": {
        "anchor_id": "amazon-autofill-items",
        "title": "勤怠入力を楽にする周辺アイテム",
        "lead": "入力や確認を少し楽にしたい方向けの、控えめな補助導線です。",
        "more_label": "作業環境のおすすめをまとめて見る",
        "more_path": "/recommend",
        "items": [
            {
                "category_label": "入力補助",
                "title": "テンキーで数字入力をしやすくする",
                "description": "勤務時間や日付の確認入力を、手元で扱いやすくできます。",
                "query": "テンキー",
                "query_variants": ["ワイヤレス テンキー", "テンキー USB"],
                "cta": "Amazonで探す",
            },
            {
                "category_label": "操作環境",
                "title": "マウス・キーボードを見直す",
                "description": "毎月の入力作業を進めやすい操作環境を整えられます。",
                "query": "ワイヤレスマウス キーボード",
                "query_variants": ["ワイヤレスマウス", "キーボード"],
                "cta": "Amazonで探す",
            },
            {
                "category_label": "時間管理",
                "title": "作業時間を区切って集中する",
                "description": "タイマーを使って、入力や確認の作業時間を管理しやすくします。",
                "query": "タイマー デスク",
                "query_variants": ["タイマー 勉強", "デスク タイマー"],
                "cta": "Amazonで探す",
            },
        ],
    },
    "tools": {
        "anchor_id": "amazon-tools-items",
        "title": "業務効率化アイテムを見る",
        "lead": "ツールとあわせて使いやすい、入力・確認・デスク環境の補助アイテムです。",
        "more_label": "カテゴリ別にまとめて見る",
        "more_path": "/recommend",
        "items": [
            {
                "category_label": "入力",
                "title": "数字入力を楽にする周辺機器",
                "description": "勤怠やCSV確認で使いやすいテンキー類を探せます。",
                "query": "テンキー",
                "query_variants": ["ワイヤレス テンキー", "テンキー Bluetooth"],
                "cta": "Amazonで探す",
            },
            {
                "category_label": "表示",
                "title": "確認画面を見やすくする",
                "description": "表や資料を見比べやすいモニター周辺を確認できます。",
                "query": "モバイルモニター",
                "query_variants": ["ノートPCスタンド", "モニターアーム"],
                "cta": "Amazonで探す",
            },
            {
                "category_label": "整理",
                "title": "デスク周りを整える",
                "description": "ケーブルや小物を整理して、作業前後の手間を減らします。",
                "query": "デスク収納",
                "query_variants": ["ケーブル整理", "USB-Cハブ"],
                "cta": "Amazonで探す",
            },
        ],
    },
    "csv": {
        "anchor_id": "amazon-csv-items",
        "title": "Excel/CSV作業を楽にするアイテム",
        "lead": "変換や確認作業の前後で使いやすい、表計算まわりの補助アイテムです。",
        "more_label": "Excel作業向けのおすすめをまとめて見る",
        "more_path": "/recommend",
        "items": [
            {
                "category_label": "入力補助",
                "title": "テンキーで表入力を進めやすくする",
                "description": "数値入力や確認が多い作業に向いた周辺機器を探せます。",
                "query": "テンキー",
                "query_variants": ["ワイヤレス テンキー", "テンキー USB"],
                "cta": "Amazonで探す",
            },
            {
                "category_label": "学習",
                "title": "Excel効率化の本を見比べる",
                "description": "関数や表整理を学び直したいときの参考書を探せます。",
                "query": "Excel 効率化 本",
                "query_variants": ["Excel 本 おすすめ", "Excel 関数 本"],
                "cta": "Amazonで探す",
            },
            {
                "category_label": "作業環境",
                "title": "画面と接続まわりを整える",
                "description": "モバイルモニターやUSB-Cハブで確認環境を整えられます。",
                "query": "モバイルモニター USB-Cハブ",
                "query_variants": ["モバイルモニター", "USB-Cハブ"],
                "cta": "Amazonで探す",
            },
        ],
    },
    "faq": {
        "anchor_id": "amazon-faq-items",
        "title": "作業環境を整えたい方へ",
        "lead": "よくある質問を確認したあとに、作業しやすい環境づくりも見直せます。",
        "more_label": "カテゴリ別のおすすめを見る",
        "more_path": "/recommend",
        "items": [
            {
                "category_label": "入力環境",
                "title": "入力しやすい周辺機器を探す",
                "description": "テンキー、マウス、キーボードなどをまとめて確認できます。",
                "query": "入力 作業 効率化 グッズ",
                "query_variants": ["テンキー", "ワイヤレスマウス", "キーボード"],
                "cta": "Amazonで探す",
            },
            {
                "category_label": "デスク環境",
                "title": "長時間作業をしやすくする",
                "description": "姿勢や机まわりを整えるアイテムを探せます。",
                "query": "デスクワーク 快適 グッズ",
                "query_variants": ["フットレスト", "クッション デスクワーク", "ノートPCスタンド"],
                "cta": "Amazonで探す",
            },
            {
                "category_label": "仕事術",
                "title": "業務効率化のヒントを読む",
                "description": "仕事術やExcel効率化の本を見比べられます。",
                "query": "仕事術 本",
                "query_variants": ["ビジネス書 おすすめ", "Excel効率化本"],
                "cta": "Amazonで探す",
            },
        ],
    },
    "recommend": {
        "anchor_id": "recommend-categories",
        "title": "業務効率化アイテムおすすめ",
        "lead": "Jobcan入力、Excel/CSV作業、デスク作業を少し楽にする周辺アイテムをカテゴリ別にまとめています。",
        "max_items": 4,
        "items": [
            {
                "category_label": "勤怠入力",
                "title": "勤怠入力を楽にする",
                "description": "入力作業を少し楽にしたい方向けに、テンキーや操作しやすい周辺機器を探せます。",
                "query": "テンキー ワイヤレス",
                "query_variants": ["テンキー", "ワイヤレスマウス", "キーボード"],
                "cta": "Amazonで探す",
            },
            {
                "category_label": "Excel/CSV",
                "title": "Excel/CSV作業を楽にする",
                "description": "Excel作業が多い方向けに、入力補助や学習用の本、確認環境を見比べられます。",
                "query": "Excel 効率化 本",
                "query_variants": ["Excel効率化本", "Excel 関数 本", "モバイルモニター"],
                "cta": "Amazonで探す",
            },
            {
                "category_label": "デスク作業",
                "title": "デスク作業を楽にする",
                "description": "デスク周りを整えたい方向けに、収納や姿勢サポート系のアイテムを探せます。",
                "query": "デスクワーク 快適 グッズ",
                "query_variants": ["デスク収納", "ノートPCスタンド", "フットレスト"],
                "cta": "Amazonで探す",
            },
            {
                "category_label": "時間管理",
                "title": "時間管理・集中を助ける",
                "description": "作業時間を区切って集中したい方向けに、タイマーや仕事術の本を確認できます。",
                "query": "タイマー デスク",
                "query_variants": ["タイマー 勉強", "仕事術 本", "ビジネス書 おすすめ"],
                "cta": "Amazonで探す",
            },
        ],
    },
}
