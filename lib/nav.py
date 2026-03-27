# -*- coding: utf-8 -*-
"""
Shared navigation and footer link definitions.
Keep labels in UTF-8 so common layout text stays stable across pages.
"""
try:
    from lib.products_catalog import PRODUCTS
except Exception:
    PRODUCTS = []


def get_nav_sections():
    """
    Build header navigation sections.
    Each child entry is either a flat link list or grouped items for dropdowns.
    """
    products = [p for p in PRODUCTS if isinstance(p, dict) and p.get('status') == 'available']

    tool_links = [{'name': 'すべてのツール', 'path': '/tools', 'icon': ''}]
    for p in products:
        tool_links.append({
            'name': p.get('name', ''),
            'path': p.get('path', '#'),
            'icon': p.get('icon', ''),
        })

    tool_guide_items = []
    for p in products:
        guide_path = p.get('guide_path') or ''
        if guide_path:
            tool_guide_items.append({
                'name': p.get('name', ''),
                'path': guide_path,
                'icon': p.get('icon', ''),
            })

    guide_links = []
    if tool_guide_items:
        guide_links.append({'group_label': 'ツール別ガイド', 'items': tool_guide_items})
    guide_links.append({
        'group_label': 'Jobcan AutoFill ガイド',
        'items': [
            {'name': 'ガイド一覧', 'path': '/guide', 'icon': ''},
            {'name': 'Jobcan AutoFill', 'path': '/guide/autofill', 'icon': ''},
            {'name': '完全ガイド', 'path': '/guide/complete', 'icon': ''},
            {'name': 'はじめての使い方', 'path': '/guide/getting-started', 'icon': ''},
            {'name': 'Excelファイルの作成方法', 'path': '/guide/excel-format', 'icon': ''},
            {'name': 'トラブルシューティング', 'path': '/guide/troubleshooting', 'icon': ''},
            {'name': '総合ガイド', 'path': '/guide/comprehensive-guide', 'icon': ''},
        ],
    })

    resource_links = [
        {'name': 'よくある質問', 'path': '/faq', 'icon': ''},
        {'name': '用語集', 'path': '/glossary', 'icon': ''},
        {'name': 'ベストプラクティス', 'path': '/best-practices', 'icon': ''},
        {'name': '導入事例', 'path': '/case-studies', 'icon': ''},
        {'name': 'ブログ', 'path': '/blog', 'icon': ''},
        {'name': 'サイトについて', 'path': '/about', 'icon': ''},
        {'name': 'サイトマップ', 'path': '/sitemap.html', 'icon': ''},
        {'name': 'プライバシーポリシー', 'path': '/privacy', 'icon': ''},
        {'name': '利用規約', 'path': '/terms', 'icon': ''},
        {'name': 'お問い合わせ', 'path': '/contact', 'icon': ''},
    ]

    return [
        {'id': 'home', 'label': 'Home', 'path': '/', 'children': None},
        {'id': 'tools', 'label': 'Tools', 'path': '/tools', 'children': tool_links},
        {'id': 'guide', 'label': 'Guide', 'path': '/guide', 'children': guide_links},
        {'id': 'resource', 'label': 'Resource', 'path': '/faq', 'children': resource_links},
    ]


def get_nav_sections_fallback():
    """Fallback navigation used when PRODUCTS cannot be read."""
    return [
        {'id': 'home', 'label': 'Home', 'path': '/', 'children': None},
        {'id': 'tools', 'label': 'Tools', 'path': '/tools', 'children': [{'name': 'すべてのツール', 'path': '/tools', 'icon': ''}]},
        {'id': 'guide', 'label': 'Guide', 'path': '/guide', 'children': [
            {
                'group_label': 'Jobcan AutoFill ガイド',
                'items': [
                    {'name': 'ガイド一覧', 'path': '/guide', 'icon': ''},
                    {'name': 'Jobcan AutoFill', 'path': '/guide/autofill', 'icon': ''},
                    {'name': '完全ガイド', 'path': '/guide/complete', 'icon': ''},
                    {'name': 'はじめての使い方', 'path': '/guide/getting-started', 'icon': ''},
                    {'name': 'Excelファイルの作成方法', 'path': '/guide/excel-format', 'icon': ''},
                    {'name': 'トラブルシューティング', 'path': '/guide/troubleshooting', 'icon': ''},
                    {'name': '総合ガイド', 'path': '/guide/comprehensive-guide', 'icon': ''},
                ],
            }
        ]},
        {'id': 'resource', 'label': 'Resource', 'path': '/faq', 'children': [
            {'name': 'よくある質問', 'path': '/faq', 'icon': ''},
            {'name': '用語集', 'path': '/glossary', 'icon': ''},
            {'name': 'ベストプラクティス', 'path': '/best-practices', 'icon': ''},
            {'name': '導入事例', 'path': '/case-studies', 'icon': ''},
            {'name': 'ブログ', 'path': '/blog', 'icon': ''},
            {'name': 'サイトについて', 'path': '/about', 'icon': ''},
            {'name': 'サイトマップ', 'path': '/sitemap.html', 'icon': ''},
            {'name': 'プライバシーポリシー', 'path': '/privacy', 'icon': ''},
            {'name': '利用規約', 'path': '/terms', 'icon': ''},
            {'name': 'お問い合わせ', 'path': '/contact', 'icon': ''},
        ]},
    ]


def get_footer_columns():
    """Footer columns for tools, guides, resources, and legal pages."""
    products = [p for p in PRODUCTS if isinstance(p, dict) and p.get('status') == 'available']

    tool_links = [{'name': 'すべてのツール', 'path': '/tools'}]
    for p in products:
        tool_links.append({'name': p.get('name', ''), 'path': p.get('path', '#'), 'icon': p.get('icon', '')})

    guide_links = [
        {'name': 'ガイド一覧', 'path': '/guide'},
        {'name': 'Jobcan AutoFill', 'path': '/guide/autofill'},
        {'name': '完全ガイド', 'path': '/guide/complete'},
        {'name': 'はじめての使い方', 'path': '/guide/getting-started'},
        {'name': 'Excelファイルの作成方法', 'path': '/guide/excel-format'},
        {'name': 'トラブルシューティング', 'path': '/guide/troubleshooting'},
        {'name': '総合ガイド', 'path': '/guide/comprehensive-guide'},
    ]
    for p in products:
        guide_path = p.get('guide_path') or ''
        if guide_path and p.get('id') != 'autofill':
            guide_links.append({'name': p.get('name', ''), 'path': guide_path, 'icon': p.get('icon', '')})

    return [
        {'title': 'ツール一覧', 'links': tool_links},
        {'title': 'ガイド', 'links': guide_links},
        {'title': 'リソース', 'links': [
            {'name': 'よくある質問', 'path': '/faq'},
            {'name': '用語集', 'path': '/glossary'},
            {'name': 'ベストプラクティス', 'path': '/best-practices'},
            {'name': '導入事例', 'path': '/case-studies'},
            {'name': 'ブログ', 'path': '/blog'},
            {'name': 'サイトについて', 'path': '/about'},
            {'name': 'サイトマップ', 'path': '/sitemap.html'},
        ]},
        {'title': '法務情報', 'links': [
            {'name': 'プライバシーポリシー', 'path': '/privacy'},
            {'name': '利用規約', 'path': '/terms'},
            {'name': 'お問い合わせ', 'path': '/contact'},
        ]},
    ]
