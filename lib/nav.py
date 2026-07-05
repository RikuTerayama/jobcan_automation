# -*- coding: utf-8 -*-
"""
Shared navigation and footer link definitions.
Keep labels in UTF-8 so common layout text stays stable across pages.
"""
try:
    from lib.products_catalog import PRODUCTS
except Exception:
    PRODUCTS = []


SIMPLIFIED_PRODUCT_PATHS = frozenset(('/autofill', '/tools/csv'))


def _visible_products():
    products = []
    for product in PRODUCTS:
        if not isinstance(product, dict):
            continue
        if product.get('status') != 'available':
            continue
        if product.get('path') not in SIMPLIFIED_PRODUCT_PATHS:
            continue
        item = dict(product)
        item['guide_path'] = ''
        products.append(item)
    return products


def get_nav_sections():
    """
    Build header navigation sections.
    Each child entry is either a flat link list or grouped items for dropdowns.
    """
    products = _visible_products()

    tool_links = [{'name': 'すべてのツール', 'path': '/tools', 'icon': ''}]
    for p in products:
        tool_links.append({
            'name': p.get('name', ''),
            'path': p.get('path', '#'),
            'icon': p.get('icon', ''),
        })

    resource_links = [
        {'name': 'よくある質問', 'path': '/faq', 'icon': ''},
        {'name': 'プライバシーポリシー', 'path': '/privacy', 'icon': ''},
        {'name': '利用規約', 'path': '/terms', 'icon': ''},
        {'name': 'お問い合わせ', 'path': '/contact', 'icon': ''},
    ]

    return [
        {'id': 'home', 'label': 'ホーム', 'path': '/', 'children': None},
        {'id': 'tools', 'label': 'ツール', 'path': '/tools', 'children': tool_links},
        {'id': 'resource', 'label': 'リソース', 'path': '/faq', 'children': resource_links},
    ]


def get_nav_sections_fallback():
    """Fallback navigation used when PRODUCTS cannot be read."""
    return [
        {'id': 'home', 'label': 'ホーム', 'path': '/', 'children': None},
        {'id': 'tools', 'label': 'ツール', 'path': '/tools', 'children': [{'name': 'すべてのツール', 'path': '/tools', 'icon': ''}]},
        {'id': 'resource', 'label': 'リソース', 'path': '/faq', 'children': [
            {'name': 'よくある質問', 'path': '/faq', 'icon': ''},
            {'name': 'プライバシーポリシー', 'path': '/privacy', 'icon': ''},
            {'name': '利用規約', 'path': '/terms', 'icon': ''},
            {'name': 'お問い合わせ', 'path': '/contact', 'icon': ''},
        ]},
    ]


def get_footer_columns():
    """Footer columns for tools, guides, resources, and legal pages."""
    products = _visible_products()

    tool_links = [{'name': 'すべてのツール', 'path': '/tools'}]
    for p in products:
        tool_links.append({'name': p.get('name', ''), 'path': p.get('path', '#'), 'icon': p.get('icon', '')})

    return [
        {'title': 'ツール一覧', 'links': tool_links},
        {'title': 'リソース', 'links': [
            {'name': 'よくある質問', 'path': '/faq'},
        ]},
        {'title': '法務情報', 'links': [
            {'name': 'プライバシーポリシー', 'path': '/privacy'},
            {'name': '利用規約', 'path': '/terms'},
            {'name': 'お問い合わせ', 'path': '/contact'},
        ]},
    ]
