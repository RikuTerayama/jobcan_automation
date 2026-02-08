# -*- coding: utf-8 -*-
"""
ヘッダー・フッター共通のナビゲーション構造。
1ソースで両方に渡し、重複を避ける。
"""
try:
    from lib.products_catalog import PRODUCTS
except Exception:
    PRODUCTS = []


def get_nav_sections():
    """
    4大項目: Home, Tools, Guide, Resource の構造を返す。
    各項目は label, path, children を持つ。children は None（単一リンク）または
    [ { 'name', 'path', 'icon'? } ] のリスト。
    """
    products = [p for p in PRODUCTS if isinstance(p, dict) and p.get('status') == 'available']

    tool_links = [{'name': 'すべてのツール', 'path': '/tools', 'icon': ''}]
    for p in products:
        tool_links.append({
            'name': p.get('name', ''),
            'path': p.get('path', '#'),
            'icon': p.get('icon', '')
        })

    jobcan_sub_guides = [
        {'name': 'はじめての使い方', 'path': '/guide/getting-started', 'icon': ''},
        {'name': 'Excelファイルの作成方法', 'path': '/guide/excel-format', 'icon': ''},
        {'name': 'トラブルシューティング', 'path': '/guide/troubleshooting', 'icon': ''},
        {'name': '完全ガイド', 'path': '/guide/complete', 'icon': ''},
        {'name': '総合ガイド（勤怠管理の効率化）', 'path': '/guide/comprehensive-guide', 'icon': ''},
    ]
    tool_guide_items = []
    for p in products:
        gp = p.get('guide_path') or ''
        if gp:
            tool_guide_items.append({'name': p.get('name', ''), 'path': gp, 'icon': p.get('icon', '')})

    # 1ツール=1ガイドの粒度: トップは「ガイド一覧」+「ツール別ガイド」（autofill含む全ツール）+「Jobcan AutoFill 詳細」（5本はサブ）
    guide_links = [
        {'name': 'ガイド一覧', 'path': '/guide', 'icon': ''},
        {'group_label': 'ツール別ガイド', 'items': tool_guide_items},
        {'group_label': 'Jobcan AutoFill 詳細', 'items': jobcan_sub_guides},
    ]

    resource_links = [
        {'name': 'よくある質問（FAQ）', 'path': '/faq', 'icon': ''},
        {'name': '用語集', 'path': '/glossary', 'icon': ''},
        {'name': 'ブログ', 'path': '/blog', 'icon': ''},
        {'name': 'サイトについて', 'path': '/about', 'icon': ''},
        {'name': 'お問い合わせ', 'path': '/contact', 'icon': ''},
        {'name': 'プライバシーポリシー', 'path': '/privacy', 'icon': ''},
        {'name': '利用規約', 'path': '/terms', 'icon': ''},
    ]

    return [
        {'id': 'home', 'label': 'Home', 'path': '/', 'children': None},
        {'id': 'tools', 'label': 'Tools', 'path': '/tools', 'children': tool_links},
        {'id': 'guide', 'label': 'Guide', 'path': '/guide', 'children': guide_links},
        {'id': 'resource', 'label': 'Resource', 'path': '/faq', 'children': resource_links},
    ]


def get_nav_sections_fallback():
    """PRODUCTS が空でも使える最小ナビ（context_processor 失敗時用）"""
    return [
        {'id': 'home', 'label': 'Home', 'path': '/', 'children': None},
        {'id': 'tools', 'label': 'Tools', 'path': '/tools', 'children': [{'name': 'すべてのツール', 'path': '/tools', 'icon': ''}]},
        {'id': 'guide', 'label': 'Guide', 'path': '/guide', 'children': [
            {'name': 'ガイド一覧', 'path': '/guide', 'icon': ''},
            {'group_label': 'ツール別ガイド', 'items': [
                {'name': 'Jobcan AutoFill', 'path': '/guide/autofill', 'icon': '🕒'},
                {'name': '画像一括変換', 'path': '/guide/image-batch', 'icon': '🖼️'},
                {'name': 'PDFユーティリティ', 'path': '/guide/pdf', 'icon': '📄'},
                {'name': '画像ユーティリティ', 'path': '/guide/image-cleanup', 'icon': '✨'},
                {'name': '議事録整形', 'path': '/guide/minutes', 'icon': '📝'},
                {'name': 'Web/SEO', 'path': '/guide/seo', 'icon': '🔍'},
            ]},
            {'group_label': 'Jobcan AutoFill 詳細', 'items': [
                {'name': 'はじめての使い方', 'path': '/guide/getting-started', 'icon': ''},
                {'name': 'Excelファイルの作成方法', 'path': '/guide/excel-format', 'icon': ''},
                {'name': 'トラブルシューティング', 'path': '/guide/troubleshooting', 'icon': ''},
                {'name': '完全ガイド', 'path': '/guide/complete', 'icon': ''},
                {'name': '総合ガイド（勤怠管理の効率化）', 'path': '/guide/comprehensive-guide', 'icon': ''},
            ]},
        ]},
        {'id': 'resource', 'label': 'Resource', 'path': '/faq', 'children': [
            {'name': 'よくある質問（FAQ）', 'path': '/faq', 'icon': ''},
            {'name': '用語集', 'path': '/glossary', 'icon': ''},
            {'name': 'ブログ', 'path': '/blog', 'icon': ''},
            {'name': 'サイトについて', 'path': '/about', 'icon': ''},
            {'name': 'お問い合わせ', 'path': '/contact', 'icon': ''},
            {'name': 'プライバシーポリシー', 'path': '/privacy', 'icon': ''},
            {'name': '利用規約', 'path': '/terms', 'icon': ''},
        ]},
    ]


def get_footer_columns():
    """
    フッター用の4カラム（ツール一覧・ガイド・リソース・法的情報）を返す。
    ヘッダーの nav_sections と整合させる。各カラムは title と links。
    """
    products = [p for p in PRODUCTS if isinstance(p, dict) and p.get('status') == 'available']

    tool_links = [{'name': 'すべてのツール', 'path': '/tools'}]
    for p in products:
        tool_links.append({'name': p.get('name', ''), 'path': p.get('path', '#'), 'icon': p.get('icon', '')})

    guide_links = [
        {'name': 'ガイド一覧', 'path': '/guide'},
        {'name': 'Jobcan AutoFill', 'path': '/guide/autofill'},
        {'name': 'はじめての使い方', 'path': '/guide/getting-started'},
        {'name': 'Excelファイルの作成方法', 'path': '/guide/excel-format'},
        {'name': 'トラブルシューティング', 'path': '/guide/troubleshooting'},
        {'name': '完全ガイド', 'path': '/guide/complete'},
        {'name': '総合ガイド（勤怠管理の効率化）', 'path': '/guide/comprehensive-guide'},
    ]
    for p in products:
        gp = p.get('guide_path') or ''
        if gp and p.get('id') != 'autofill':
            guide_links.append({'name': p.get('name', ''), 'path': gp})

    return [
        {'title': 'ツール一覧', 'links': tool_links},
        {'title': 'ガイド', 'links': guide_links},
        {'title': 'リソース', 'links': [
            {'name': 'よくある質問（FAQ）', 'path': '/faq'},
            {'name': '用語集', 'path': '/glossary'},
            {'name': 'ブログ', 'path': '/blog'},
            {'name': 'サイトについて', 'path': '/about'},
        ]},
        {'title': '法的情報', 'links': [
            {'name': 'プライバシーポリシー', 'path': '/privacy'},
            {'name': '利用規約', 'path': '/terms'},
            {'name': 'お問い合わせ', 'path': '/contact'},
        ]},
    ]
