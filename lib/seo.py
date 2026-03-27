# -*- coding: utf-8 -*-
"""Shared SEO defaults and helpers for metadata, breadcrumbs, and schema."""

from copy import deepcopy


SEO_DEFAULTS = {
    '/': {
        'description': 'Jobcan の勤怠入力を Excel から一括化できる無料の自動化ツールです。月次締めや手入力の負担を減らし、導入前に確認したいガイド、FAQ、導入事例もまとめています。',
        'og_type': 'website',
    },
    '/autofill': {
        'description': 'Jobcan への勤怠入力を Excel からまとめて処理できる自動入力ツールです。手入力の時短と月次対応の効率化を支援します。',
        'og_type': 'website',
    },
    '/tools': {
        'description': 'Jobcan AutoFill、CSV/Excel、PDF、画像処理、Web/SEO などの業務効率化ツール一覧です。実務に近い用途別に比較できます。',
        'og_type': 'website',
    },
    '/guide': {
        'description': 'Jobcan AutoFill と関連ツールのガイド一覧です。はじめての使い方、Excel 形式、トラブルシューティング、導入前の確認事項をまとめています。',
        'og_type': 'website',
        'breadcrumb_title': 'ガイド一覧',
    },
    '/guide/autofill': {
        'description': 'Jobcan AutoFill の使い方ガイドです。Excel から Jobcan へ勤怠データを自動入力する手順、制約、FAQ をまとめています。',
        'og_type': 'article',
    },
    '/guide/getting-started': {
        'description': 'Jobcan AutoFill のはじめての使い方ガイドです。テンプレート準備から実行前チェックまで順番に確認できます。',
        'og_type': 'article',
    },
    '/guide/excel-format': {
        'description': 'Jobcan AutoFill 用 Excel ファイルの形式ガイドです。日付、時刻、列構成、よくある形式エラーを確認できます。',
        'og_type': 'article',
    },
    '/guide/troubleshooting': {
        'description': 'Jobcan AutoFill のトラブルシューティングです。ログインエラー、形式エラー、タイムアウトなどの対処方法をまとめています。',
        'og_type': 'article',
    },
    '/guide/complete': {
        'description': 'Jobcan AutoFill の完全ガイドです。使い方、注意点、セキュリティ、導入判断の観点を 1 ページで確認できます。',
        'og_type': 'article',
    },
    '/guide/comprehensive-guide': {
        'description': 'Jobcan 勤怠入力の効率化を検討する方向けの総合ガイドです。導入背景、比較観点、運用設計まで整理しています。',
        'og_type': 'article',
    },
    '/guide/image-batch': {
        'description': '画像一括処理ツールの使い方ガイドです。複数画像のまとめ処理、対応形式、注意点、よくある質問を確認できます。',
        'og_type': 'article',
    },
    '/guide/pdf': {
        'description': 'PDF ツールの使い方ガイドです。結合、分割、圧縮、ページ整理の手順と注意点をまとめています。',
        'og_type': 'article',
    },
    '/guide/image-cleanup': {
        'description': '画像クリーンアップツールの使い方ガイドです。トリミングや不要部分の整理、利用時の注意点を確認できます。',
        'og_type': 'article',
    },
    '/guide/minutes': {
        'description': '議事録作成ツールの使い方ガイドです。入力の流れ、出力の整え方、業務で使う際の注意点をまとめています。',
        'og_type': 'article',
    },
    '/guide/seo': {
        'description': 'Web/SEO ツールの使い方ガイドです。メタ情報、OGP、sitemap、robots.txt を確認するときの進め方を整理しています。',
        'og_type': 'article',
    },
    '/guide/csv': {
        'description': 'CSV/Excel ツールの使い方ガイドです。変換、整形、列の確認、業務データを扱う際の注意点をまとめています。',
        'og_type': 'article',
    },
    '/faq': {
        'description': 'Jobcan AutoFill に関する FAQ です。使い方、セキュリティ、Excel 形式、ブラウザ要件、エラー対処をまとめています。',
        'og_type': 'website',
        'breadcrumb_title': 'FAQ',
    },
    '/glossary': {
        'description': '勤怠管理、Jobcan、自動入力に関連する用語集です。打刻、勤務時間、Playwright などの用語をわかりやすく整理しています。',
        'og_type': 'website',
    },
    '/best-practices': {
        'description': 'Jobcan AutoFill を安全かつ効率的に使うためのベストプラクティスです。Excel 設計、運用、セキュリティの勘所をまとめています。',
        'og_type': 'article',
    },
    '/about': {
        'description': 'Jobcan AutoFill とは何か、このサイトの目的、対象ユーザー、運用方針をまとめたページです。',
        'og_type': 'website',
    },
    '/case-studies': {
        'description': 'Jobcan AutoFill の導入事例一覧です。勤怠入力の時短、月次締めの効率化、バックオフィス DX に関する実例を確認できます。',
        'og_type': 'website',
        'breadcrumb_title': '導入事例',
    },
    '/case-study/contact-center': {
        'description': 'コンタクトセンター部門での Jobcan AutoFill 導入事例です。月次処理の時短と運用改善の進め方をまとめています。',
        'og_type': 'article',
        'breadcrumb_title': 'コンタクトセンターの導入事例',
    },
    '/case-study/consulting-firm': {
        'description': 'コンサルティングファームでの Jobcan AutoFill 導入事例です。月次締めの短縮と社内展開の進め方を整理しています。',
        'og_type': 'article',
        'breadcrumb_title': 'コンサルティングファームの導入事例',
    },
    '/case-study/remote-startup': {
        'description': 'リモート中心のスタートアップでの Jobcan AutoFill 導入事例です。分散チームの勤怠入力を効率化した実例をまとめています。',
        'og_type': 'article',
        'breadcrumb_title': 'リモートスタートアップの導入事例',
    },
    '/blog': {
        'description': 'Jobcan 自動入力、勤怠効率化、バックオフィス DX に関するブログ一覧です。導入判断や運用改善に役立つ記事を掲載しています。',
        'og_type': 'website',
        'breadcrumb_title': 'ブログ',
    },
    '/blog/implementation-checklist': {
        'description': 'Jobcan AutoFill 導入前に確認したい 10 のチェックポイントを整理した記事です。セキュリティ、社内運用、導入判断の論点をまとめています。',
        'og_type': 'article',
    },
    '/blog/automation-roadmap': {
        'description': '勤怠自動化を進めるためのロードマップ記事です。小さく始めて運用へつなげる進め方を整理しています。',
        'og_type': 'article',
    },
    '/blog/workstyle-reform-automation': {
        'description': '働き方改革とバックオフィス効率化を両立する自動化の考え方をまとめた記事です。勤怠 DX のヒントを確認できます。',
        'og_type': 'article',
    },
    '/blog/excel-attendance-limits': {
        'description': 'Excel だけで勤怠管理を続ける限界と、自動入力ツール導入で解消できる課題を整理した記事です。',
        'og_type': 'article',
    },
    '/blog/playwright-security': {
        'description': 'Playwright を使った自動入力のセキュリティ論点を整理した記事です。ブラウザ自動化を業務で扱う際の注意点を確認できます。',
        'og_type': 'article',
    },
    '/blog/month-end-closing-hell-and-automation': {
        'description': '月末処理が重くなる原因と自動化で改善できるポイントを整理した記事です。勤怠入力の時短策を具体的に確認できます。',
        'og_type': 'article',
    },
    '/blog/excel-format-mistakes-and-design': {
        'description': '勤怠 Excel で起きやすい形式ミスと、AutoFill で扱いやすい設計の考え方をまとめた記事です。',
        'og_type': 'article',
    },
    '/blog/convince-it-and-hr-for-automation': {
        'description': 'IT 部門や人事に自動化導入を説明するときの論点を整理した記事です。社内調整や稟議づくりに役立ちます。',
        'og_type': 'article',
    },
    '/blog/playwright-jobcan-challenges-and-solutions': {
        'description': 'Jobcan 自動入力で直面しやすい技術課題と対策をまとめた記事です。Playwright 運用の現実的なポイントを確認できます。',
        'og_type': 'article',
    },
    '/blog/jobcan-auto-input-tools-overview': {
        'description': 'Jobcan の勤怠入力を自動化する方法を比較した記事です。Excel マクロ、RPA、ブラウザ自動化の違いを整理しています。',
        'og_type': 'article',
    },
    '/blog/reduce-manual-work-checklist': {
        'description': '手作業を減らすための業務効率化チェックリストです。勤怠入力の自動化と運用改善の観点を整理しています。',
        'og_type': 'article',
    },
    '/blog/jobcan-month-end-tips': {
        'description': 'Jobcan の月末処理を楽にするためのチェックポイントをまとめた記事です。締め日前後の作業を効率化するヒントを紹介しています。',
        'og_type': 'article',
    },
    '/blog/jobcan-auto-input-dos-and-donts': {
        'description': 'Jobcan 自動入力でやってよいこと、避けたいことを整理した記事です。安全な運用と効率化のバランスを確認できます。',
        'og_type': 'article',
    },
    '/blog/month-end-closing-checklist': {
        'description': '月末の勤怠入力締めを楽にするための実務チェックリストです。混乱を減らし、入力作業を時短する観点をまとめています。',
        'og_type': 'article',
    },
    '/privacy': {
        'description': 'Jobcan AutoFill のプライバシーポリシーです。個人情報、Cookie、アフィリエイト広告の取り扱いを説明しています。',
        'og_type': 'website',
        'robots': 'noindex,follow',
    },
    '/terms': {
        'description': 'Jobcan AutoFill の利用規約です。サービスの利用条件、免責事項、外部リンクに関する方針をまとめています。',
        'og_type': 'website',
        'robots': 'noindex,follow',
    },
    '/contact': {
        'description': 'Jobcan AutoFill のお問い合わせページです。ご質問や掲載内容に関する連絡先を案内しています。',
        'og_type': 'website',
        'robots': 'noindex,follow',
    },
    '/sitemap.html': {
        'description': 'Jobcan AutoFill の HTML サイトマップです。主要ページ、ガイド、記事、事例への導線を一覧で確認できます。',
        'og_type': 'website',
        'robots': 'noindex,follow',
    },
}


NOINDEX_PATHS = frozenset(
    path for path, config in SEO_DEFAULTS.items() if config.get('robots', '').startswith('noindex')
)


TOOL_APPLICATIONS = {
    '/autofill': {
        'name': 'Jobcan AutoFill',
        'category': 'BusinessApplication',
        'feature_list': [
            'Excel テンプレートから Jobcan へ勤怠データを一括入力',
            '月次締め時の手入力作業を時短',
            'ブラウザ上で完結するワークフロー',
        ],
    },
    '/tools/csv': {
        'name': 'CSV/Excel ツール',
        'category': 'BusinessApplication',
        'feature_list': [
            'CSV と XLSX の変換・整形',
            '列の確認や簡易加工をブラウザで実行',
        ],
    },
    '/tools/pdf': {
        'name': 'PDF ツール',
        'category': 'UtilitiesApplication',
        'feature_list': [
            '結合、分割、圧縮、ページ整理などの PDF 処理',
        ],
    },
    '/tools/image-batch': {
        'name': '画像一括処理ツール',
        'category': 'UtilitiesApplication',
        'feature_list': [
            '複数画像の一括リサイズや形式変換',
        ],
    },
    '/tools/image-cleanup': {
        'name': '画像クリーンアップツール',
        'category': 'UtilitiesApplication',
        'feature_list': [
            '画像整理、トリミング、不要部分のクリーニング',
        ],
    },
    '/tools/seo': {
        'name': 'Web/SEO ツール',
        'category': 'BusinessApplication',
        'feature_list': [
            'OGP、メタ情報、sitemap、robots.txt の確認と改善',
        ],
    },
    '/tools/minutes': {
        'name': '議事録作成ツール',
        'category': 'BusinessApplication',
        'feature_list': [
            '会議メモから議事録のたたき台を整理',
            '要点、決定事項、ToDo をまとめて出力',
        ],
    },
}


def get_seo_defaults(path):
    config = deepcopy(SEO_DEFAULTS.get(path, {}))
    if 'og_type' not in config:
        config['og_type'] = get_og_type(path)
    if 'robots' not in config:
        config['robots'] = 'index,follow'
    return config


def is_noindex_path(path):
    return path in NOINDEX_PATHS


def get_og_type(path):
    if path.startswith('/blog/') or path.startswith('/case-study/') or (path.startswith('/guide/') and path != '/guide'):
        return 'article'
    return 'website'


def get_page_kind(path):
    if path == '/':
        return 'homepage'
    if path in ('/blog', '/case-studies', '/guide'):
        return 'collection'
    if path.startswith('/blog/') or path.startswith('/case-study/') or (path.startswith('/guide/') and path != '/guide'):
        return 'article'
    if path in ('/faq', '/glossary', '/best-practices', '/about'):
        return 'resource'
    if path == '/autofill' or path.startswith('/tools/'):
        return 'tool'
    return 'page'


def build_breadcrumb_items(path, page_title='', breadcrumb_title=''):
    label = (breadcrumb_title or page_title or path.split('/')[-1] or 'ホーム').strip()
    items = [{'name': 'ホーム', 'url': '/'}]

    if path == '/':
        return items
    if path == '/tools':
        items.append({'name': 'ツール一覧', 'url': '/tools'})
        return items
    if path.startswith('/tools/'):
        items.append({'name': 'ツール一覧', 'url': '/tools'})
        items.append({'name': label, 'url': path})
        return items
    if path == '/guide':
        items.append({'name': 'ガイド一覧', 'url': '/guide'})
        return items
    if path.startswith('/guide/'):
        items.append({'name': 'ガイド一覧', 'url': '/guide'})
        items.append({'name': label, 'url': path})
        return items
    if path == '/blog':
        items.append({'name': 'ブログ', 'url': '/blog'})
        return items
    if path.startswith('/blog/'):
        items.append({'name': 'ブログ', 'url': '/blog'})
        items.append({'name': label, 'url': path})
        return items
    if path == '/case-studies':
        items.append({'name': '導入事例', 'url': '/case-studies'})
        return items
    if path.startswith('/case-study/'):
        items.append({'name': '導入事例', 'url': '/case-studies'})
        items.append({'name': label, 'url': path})
        return items

    items.append({'name': label, 'url': path})
    return items


def get_web_application_schema(path, title, description, base_url):
    config = TOOL_APPLICATIONS.get(path)
    if not config:
        return None
    return {
        '@context': 'https://schema.org',
        '@type': 'WebApplication',
        'name': config['name'],
        'url': f'{base_url}{path}',
        'applicationCategory': config['category'],
        'operatingSystem': 'Web Browser',
        'isAccessibleForFree': True,
        'description': description,
        'offers': {
            '@type': 'Offer',
            'price': '0',
            'priceCurrency': 'JPY',
        },
        'featureList': config['feature_list'],
    }
