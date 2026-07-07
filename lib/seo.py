# -*- coding: utf-8 -*-
"""SEO defaults and helpers for the Jobcan + PDF lightweight site."""

from copy import deepcopy

SIMPLIFIED_SEO_PATHS = frozenset((
    '/', '/autofill', '/tools', '/tools/pdf', '/faq', '/recommend',
    '/privacy', '/terms', '/contact',
))

SEO_DEFAULTS = {
    '/': {
        'title': 'Jobcan AutoFill | 勤怠入力とPDF作業を軽くする無料ツール',
        'description': 'Jobcan勤怠入力の自動化とPDFの結合・分割・パスワード付与を扱う軽量な無料ツールサイトです。',
        'og_type': 'website',
    },
    '/autofill': {
        'title': 'Jobcan勤怠自動入力ツール | Jobcan AutoFill',
        'description': 'Excelにまとめた勤怠データをもとに、Jobcanへの入力作業を補助する無料ツールです。',
        'og_type': 'website',
    },
    '/tools': {
        'title': 'ツール一覧 | Jobcan AutoFill',
        'description': 'Jobcan AutoFill と PDFユーティリティをまとめた軽量な無料ツール一覧です。',
        'og_type': 'website',
    },
    '/tools/pdf': {
        'title': 'PDFユーティリティ | Jobcan AutoFill',
        'description': 'PDFの結合、分割、ページ抽出、圧縮、画像変換、保護されていないPDFへのパスワード付与を扱う無料ツールです。',
        'og_type': 'website',
        'breadcrumb_title': 'PDFユーティリティ',
    },
    '/faq': {
        'title': 'FAQ | Jobcan AutoFill',
        'description': 'Jobcan AutoFill と PDFツールの使い方、データの扱い、Render無料版での制約をまとめています。',
        'og_type': 'website',
        'breadcrumb_title': 'FAQ',
    },
    '/recommend': {
        'title': 'コンサルワーク向けアイテムおすすめ | Jobcan AutoFill',
        'description': 'Jobcan入力、PDF・書類作業、資料作成、集中環境を整えたい方向けのAmazon Associates導線です。',
        'og_type': 'website',
        'breadcrumb_title': '関連アイテム',
    },
    '/privacy': {
        'title': 'プライバシーポリシー | Jobcan AutoFill',
        'description': 'Jobcan AutoFill と PDFツールにおけるデータの取り扱い、Cookie、広告・アフィリエイトについて説明します。',
        'og_type': 'website',
        'robots': 'noindex,follow',
        'breadcrumb_title': 'プライバシーポリシー',
    },
    '/terms': {
        'title': '利用規約 | Jobcan AutoFill',
        'description': 'Jobcan AutoFill と PDFツールの利用条件、禁止事項、免責事項をまとめています。',
        'og_type': 'website',
        'robots': 'noindex,follow',
        'breadcrumb_title': '利用規約',
    },
    '/contact': {
        'title': 'お問い合わせ | Jobcan AutoFill',
        'description': 'Jobcan AutoFill と PDFツールに関するお問い合わせ、不具合報告、改善要望はこちらからご連絡ください。',
        'og_type': 'website',
        'robots': 'noindex,follow',
        'breadcrumb_title': 'お問い合わせ',
    },
}

NOINDEX_PATHS = frozenset(path for path, defaults in SEO_DEFAULTS.items() if 'noindex' in (defaults.get('robots') or '').lower())

TOOL_APPLICATIONS = {
    '/autofill': {
        'name': 'Jobcan AutoFill',
        'category': 'BusinessApplication',
        'feature_list': ['Excelテンプレートから勤怠データを読み込み', 'Jobcanへの入力作業を補助', '順番待ちと進捗表示'],
    },
    '/tools/pdf': {
        'name': 'PDFユーティリティ',
        'category': 'UtilitiesApplication',
        'feature_list': ['PDFの結合・分割・ページ抽出', 'PDFの圧縮と画像変換', '保護されていないPDFへのパスワード付与'],
    },
}

BLOG_ARTICLES = []
ARTICLE_SCHEMA_PAGES = {}

RELATED_CONTENT = {
    '/': {
        'title': '次に確認するページ',
        'intro': 'Jobcan入力とPDF作業に絞って確認できます。',
        'links': [
            {'path': '/autofill', 'label': 'Jobcan AutoFill', 'description': '勤怠データの入力補助に使えます。'},
            {'path': '/tools/pdf', 'label': 'PDFユーティリティ', 'description': 'PDFの分割・結合・パスワード付与に使えます。'},
            {'path': '/recommend', 'label': '関連アイテム', 'description': 'コンサルワーク向けの周辺アイテムを探せます。'},
        ],
    },
    '/tools': {
        'title': '使えるツール',
        'intro': '現在公開している軽量ツールです。',
        'links': [
            {'path': '/autofill', 'label': 'Jobcan AutoFill', 'description': 'Jobcan勤怠入力の補助に使えます。'},
            {'path': '/tools/pdf', 'label': 'PDFユーティリティ', 'description': '提案書や帳票PDFの整理に使えます。'},
        ],
    },
    '/autofill': {
        'title': '入力前後に見るページ',
        'intro': '勤怠入力の前後に確認できます。',
        'links': [
            {'path': '/tools/pdf', 'label': 'PDFユーティリティ', 'description': '関連資料のPDF整理に使えます。'},
            {'path': '/faq', 'label': 'FAQ', 'description': '利用前の注意点を確認できます。'},
            {'path': '/recommend', 'label': '関連アイテム', 'description': '作業環境づくりのヒントを確認できます。'},
        ],
    },
    '/tools/pdf': {
        'title': 'PDF作業とあわせて見るページ',
        'intro': 'PDF整理のあとに確認できます。',
        'links': [
            {'path': '/autofill', 'label': 'Jobcan AutoFill', 'description': '勤怠入力の一括処理に使えます。'},
            {'path': '/faq', 'label': 'FAQ', 'description': 'PDFツールの制約を確認できます。'},
            {'path': '/recommend', 'label': '関連アイテム', 'description': 'PDF・資料作成まわりの導線です。'},
        ],
    },
}

RELATED_CONTENT_PREFIXES = ()


def get_seo_defaults(path):
    normalized = path if path in SIMPLIFIED_SEO_PATHS else '/'
    return deepcopy(SEO_DEFAULTS.get(normalized, SEO_DEFAULTS['/']))


def is_noindex_path(path):
    defaults = SEO_DEFAULTS.get(path) or {}
    return 'noindex' in (defaults.get('robots') or '').lower() or path in NOINDEX_PATHS


def get_og_type(path):
    return (SEO_DEFAULTS.get(path) or SEO_DEFAULTS['/']).get('og_type', 'website')


def get_page_kind(path):
    if path in ('/', '/tools'):
        return 'hub'
    if path in ('/autofill', '/tools/pdf'):
        return 'tool'
    if path in ('/privacy', '/terms', '/contact'):
        return 'support'
    return 'resource'


def build_breadcrumb_items(path, base_url='https://jobcan-automation.onrender.com', page_title='', breadcrumb_title=''):
    if path == '/':
        return []
    label = (breadcrumb_title or page_title or path.split('/')[-1] or 'ホーム').strip()
    label = label.split('|')[0].strip()
    return [
        {'name': 'ホーム', 'url': f'{base_url}/'},
        {'name': label, 'url': f'{base_url}{path}'},
    ]


def get_web_application_schema(path, title='', description='', base_url=''):
    config = TOOL_APPLICATIONS.get(path)
    if not config:
        return None
    url_base = (base_url or '').rstrip('/')
    return {
        '@context': 'https://schema.org',
        '@type': 'SoftwareApplication',
        'name': config['name'],
        'description': description or '',
        'applicationCategory': config['category'],
        'operatingSystem': 'Web Browser',
        'url': f'{url_base}{path}',
        'offers': {'@type': 'Offer', 'price': '0', 'priceCurrency': 'JPY'},
        'featureList': config.get('feature_list', []),
    }


def get_blog_articles():
    return []


def get_article_schema(path, base_url, default_title='', default_description=''):
    return None


def get_related_content(path):
    section = RELATED_CONTENT.get(path)
    if not section:
        return None
    copied = deepcopy(section)
    copied['links'] = [link for link in copied.get('links', []) if isinstance(link, dict) and link.get('path') in SIMPLIFIED_SEO_PATHS]
    return copied if copied['links'] else None
