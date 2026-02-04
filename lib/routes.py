# -*- coding: utf-8 -*-
"""
ルート定義と製品情報を管理するモジュール
"""

# ベースURL
BASE_URL = 'https://jobcan-automation.onrender.com'

# 製品情報の定義
PRODUCTS = [
    {
        'id': 'autofill',
        'name': 'Jobcan AutoFill',
        'description': 'Jobcanへの勤怠データをExcelから一括入力。月次締め作業を大幅に短縮します。',
        'path': '/autofill',
        'status': 'available',
        'icon': '🕒',
        'category': 'attendance'
    },
    {
        'id': 'image-batch',
        'name': '画像一括変換',
        'description': 'png/jpg/webpの一括変換、リサイズ、品質圧縮、複数サイズ同時出力。ローカル処理でアップロード不要。',
        'path': '/tools/image-batch',
        'status': 'available',
        'icon': '🖼️',
        'category': 'image',
        'tags': ['File', 'Image'],
        'features': ['複数サイズ同時出力', 'プリセット', '品質調整']
    },
    {
        'id': 'pdf',
        'name': 'PDFユーティリティ',
        'description': 'PDFの結合・分割・ページ抽出、PDF→画像zip変換、圧縮、画像→PDF変換。ローカル処理でアップロード不要。',
        'path': '/tools/pdf',
        'status': 'available',
        'icon': '📄',
        'category': 'document',
        'tags': ['File', 'PDF'],
        'features': ['結合・分割', '圧縮', '画像変換']
    },
    {
        'id': 'image-cleanup',
        'name': '画像ユーティリティ',
        'description': '透過→白背景JPEG変換、余白トリム、縦横比統一、背景除去。ローカル処理でアップロード不要。',
        'path': '/tools/image-cleanup',
        'status': 'available',
        'icon': '✨',
        'category': 'image',
        'tags': ['File', 'Image'],
        'features': ['背景除去', '余白トリム', '縦横比統一']
    },
    {
        'id': 'minutes',
        'name': '議事録整形',
        'description': 'テキストから決定事項/ToDo/担当/期限を抽出し、報告書テンプレートを生成。CSV/JSON出力対応。ローカル処理でアップロード不要。',
        'path': '/tools/minutes',
        'status': 'available',
        'icon': '📝',
        'category': 'text',
        'tags': ['Writing', 'Text'],
        'features': ['決定事項抽出', 'ToDo抽出', 'CSV/JSON出力']
    },
    {
        'id': 'seo',
        'name': 'Web/SEOユーティリティ',
        'description': 'OGP画像ジェネレーター、PageSpeedチェックリスト、メタタグ検査、sitemap.xml/robots.txt生成。ローカル処理でアップロード不要。',
        'path': '/tools/seo',
        'status': 'available',
        'icon': '🔍',
        'category': 'web',
        'tags': ['Web', 'SEO'],
        'features': ['OGP生成', 'メタタグ検査', 'sitemap生成']
    }
]

# ナビゲーション項目
NAV_ITEMS = [
    {'name': 'Home', 'path': '/', 'icon': '🏠'},
    {'name': 'AutoFill', 'path': '/autofill', 'icon': '🕒'},
    {'name': 'Tools', 'path': '/tools', 'icon': '🛠️'},
    {'name': 'Guide', 'path': '/guide/getting-started', 'icon': '📚'},
]

def get_product_by_id(product_id):
    """製品IDから製品情報を取得"""
    for product in PRODUCTS:
        if product['id'] == product_id:
            return product
    return None

def get_product_by_path(path):
    """パスから製品情報を取得"""
    for product in PRODUCTS:
        if product['path'] == path:
            return product
    return None

def get_available_products():
    """利用可能な製品一覧を取得"""
    return [p for p in PRODUCTS if p['status'] == 'available']

def get_coming_soon_products():
    """準備中の製品一覧を取得"""
    return [p for p in PRODUCTS if p['status'] == 'coming-soon']
