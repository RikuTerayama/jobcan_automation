# -*- coding: utf-8 -*-
"""SEO defaults and helpers for the Jobcan + PDF lightweight site."""

from copy import deepcopy

SIMPLIFIED_SEO_PATHS = frozenset((
    '/', '/autofill', '/tools', '/tools/pdf', '/faq', '/recommend',
    '/about', '/privacy', '/terms', '/contact',
))

SEO_DEFAULTS = {
    '/': {
        'title': 'Jobcan AutoFill | Jobcan入力とPDF作業を軽くする無料ツール',
        'description': 'Jobcan入力とPDF作業を、必要なときだけ軽く使える無料ツールです。',
        'og_type': 'website',
    },
    '/autofill': {
        'title': 'Jobcan AutoFill | 勤怠入力をExcelからまとめて進める無料ツール',
        'description': 'Excelテンプレートに入力した勤怠情報をもとに、Jobcanへの入力作業を補助する無料ツールです。',
        'og_type': 'website',
        'breadcrumb_title': 'Jobcan AutoFill',
    },
    '/tools': {
        'title': 'ツール一覧 | Jobcan AutoFill',
        'description': 'Jobcan AutoFill と PDFツールをまとめた、軽量な無料ツール一覧です。',
        'og_type': 'website',
        'breadcrumb_title': 'ツール一覧',
    },
    '/tools/pdf': {
        'title': 'PDFツール | パスワード付与・分割・結合・抽出・圧縮',
        'description': 'PDFのパスワード付与、分割、結合、ページ抽出、圧縮、画像変換を扱う無料ツールです。ロック解除や復号は提供していません。',
        'og_type': 'website',
        'breadcrumb_title': 'PDFツール',
    },
    '/faq': {
        'title': 'FAQ | Jobcan AutoFill',
        'description': 'Jobcan AutoFill と PDFツールの使い方、データの扱い、Render無料版での待機や制限についてまとめています。',
        'og_type': 'website',
        'breadcrumb_title': 'FAQ',
    },
    '/about': {
        'title': 'このサイトについて | Jobcan AutoFill',
        'description': 'Jobcan AutoFill の運営方針、提供している機能、広告・アフィリエイトの扱い、データ保護の考え方を説明します。',
        'og_type': 'website',
        'breadcrumb_title': 'このサイトについて',
    },
    '/recommend': {
        'title': 'コンサルワーク向けおすすめアイテム | Jobcan AutoFill',
        'description': 'Jobcan入力、PDF・書類作業、資料作成、集中環境を整えたい方向けのAmazon Associates導線です。価格やレビュー順位は掲載しません。',
        'og_type': 'website',
        'robots': 'noindex,follow',
        'breadcrumb_title': 'おすすめアイテム',
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
        'description': 'Jobcan AutoFill と PDFツールに関するお問い合わせ、不具合報告、改善要望の連絡先です。',
        'og_type': 'website',
        'robots': 'noindex,follow',
        'breadcrumb_title': 'お問い合わせ',
    },
}

NOINDEX_PATHS = frozenset(
    path for path, defaults in SEO_DEFAULTS.items()
    if 'noindex' in (defaults.get('robots') or '').lower()
)

TOOL_APPLICATIONS = {
    '/autofill': {
        'name': 'Jobcan AutoFill',
        'category': 'BusinessApplication',
        'feature_list': [
            'Excelテンプレートから勤怠情報を読み込み',
            'Jobcanへの入力作業を補助',
            '順番待ちと処理状況を表示',
        ],
    },
    '/tools/pdf': {
        'name': 'PDFツール',
        'category': 'UtilitiesApplication',
        'feature_list': [
            'PDFのパスワード付与',
            'PDFの分割・結合・ページ抽出',
            'PDFの圧縮と画像変換',
        ],
    },
}

BLOG_ARTICLES = []
ARTICLE_SCHEMA_PAGES = {}

RELATED_CONTENT = {
    '/': {
        'title': '次に確認するページ',
        'intro': 'Jobcan入力とPDF作業に絞って確認できます。',
        'links': [
            {'path': '/autofill', 'label': 'Jobcan AutoFill', 'description': '勤怠入力をまとめて進めたいときに使います。'},
            {'path': '/tools/pdf', 'label': 'PDFツール', 'description': 'PDFの整理やパスワード付与に使います。'},
            {'path': '/about', 'label': 'このサイトについて', 'description': '運営方針とデータの扱いを確認できます。'},
        ],
    },
    '/tools': {
        'title': '使えるツール',
        'intro': '現在公開している軽量ツールです。',
        'links': [
            {'path': '/autofill', 'label': 'Jobcan AutoFill', 'description': 'Jobcan勤怠入力の補助に使います。'},
            {'path': '/tools/pdf', 'label': 'PDFツール', 'description': '提案書や請求書PDFの整理に使います。'},
        ],
    },
    '/autofill': {
        'title': '入力前後に見るページ',
        'intro': '勤怠入力の前後に必要なページだけをまとめています。',
        'links': [
            {'path': '/tools/pdf', 'label': 'PDFツール', 'description': '関連資料のPDF整理に使います。'},
            {'path': '/faq', 'label': 'FAQ', 'description': '利用前の注意点を確認できます。'},
            {'path': '/about', 'label': 'このサイトについて', 'description': 'データの扱いと運営方針を確認できます。'},
        ],
    },
    '/tools/pdf': {
        'title': 'PDF作業とあわせて見るページ',
        'intro': 'PDF作業の前後に確認しやすいページです。',
        'links': [
            {'path': '/autofill', 'label': 'Jobcan AutoFill', 'description': '勤怠入力の補助に使います。'},
            {'path': '/faq', 'label': 'FAQ', 'description': 'PDFツールの制限を確認できます。'},
            {'path': '/about', 'label': 'このサイトについて', 'description': '提供範囲と安全方針を確認できます。'},
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
    if path in ('/recommend', '/about'):
        return 'resource'
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
    copied['links'] = [
        link for link in copied.get('links', [])
        if isinstance(link, dict) and link.get('path') in SIMPLIFIED_SEO_PATHS
    ]
    return copied if copied['links'] else None
