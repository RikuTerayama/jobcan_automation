# -*- coding: utf-8 -*-
"""Shared navigation and footer link definitions."""

try:
    from lib.products_catalog import PRODUCTS
except Exception:
    PRODUCTS = []

SIMPLIFIED_PRODUCT_PATHS = frozenset(('/autofill', '/tools/pdf'))


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
    products = _visible_products()
    tool_links = [{'name': 'すべてのツール', 'path': '/tools', 'icon': ''}]
    for product in products:
        tool_links.append({
            'name': product.get('name', ''),
            'path': product.get('path', '#'),
            'icon': product.get('icon', ''),
        })

    resource_links = [
        {'name': 'FAQ', 'path': '/faq', 'icon': ''},
        {'name': 'このサイトについて', 'path': '/about', 'icon': ''},
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
    return [
        {'id': 'home', 'label': 'ホーム', 'path': '/', 'children': None},
        {'id': 'tools', 'label': 'ツール', 'path': '/tools', 'children': [{'name': 'すべてのツール', 'path': '/tools', 'icon': ''}]},
        {'id': 'resource', 'label': 'リソース', 'path': '/faq', 'children': [
            {'name': 'FAQ', 'path': '/faq', 'icon': ''},
            {'name': 'このサイトについて', 'path': '/about', 'icon': ''},
            {'name': 'プライバシーポリシー', 'path': '/privacy', 'icon': ''},
            {'name': '利用規約', 'path': '/terms', 'icon': ''},
            {'name': 'お問い合わせ', 'path': '/contact', 'icon': ''},
        ]},
    ]


def get_footer_columns():
    products = _visible_products()
    tool_links = [{'name': 'すべてのツール', 'path': '/tools'}]
    for product in products:
        tool_links.append({'name': product.get('name', ''), 'path': product.get('path', '#'), 'icon': product.get('icon', '')})

    return [
        {'title': 'ツール', 'links': tool_links},
        {'title': 'リソース', 'links': [
            {'name': 'FAQ', 'path': '/faq'},
            {'name': 'このサイトについて', 'path': '/about'},
            {'name': '関連アイテム', 'path': '/recommend'},
        ]},
        {'title': '法務・連絡先', 'links': [
            {'name': 'プライバシーポリシー', 'path': '/privacy'},
            {'name': '利用規約', 'path': '/terms'},
            {'name': 'お問い合わせ', 'path': '/contact'},
        ]},
    ]
