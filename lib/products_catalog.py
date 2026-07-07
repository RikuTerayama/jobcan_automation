# -*- coding: utf-8 -*-
"""Product catalog for the Jobcan + PDF lightweight site.

Keep this module dependency-free so page rendering never imports Playwright,
pandas, pypdf, or other heavier runtime modules.
"""

PRODUCTS = [
    {
        'id': 'autofill',
        'name': 'Jobcan AutoFill',
        'description': 'Jobcanへの勤怠データをExcelから一括入力。月次締め作業を短縮します。',
        'path': '/autofill',
        'guide_path': '',
        'status': 'available',
        'icon': '🕒',
        'category': 'attendance',
        'tags': ['Jobcan', '勤怠', 'Excel'],
        'features': ['Excel一括入力', '月次締め補助', 'ブラウザ自動化'],
        'capabilities': [
            'Excelテンプレートから勤怠データを読み込み',
            'Jobcanの入力作業をまとめて処理',
            '処理状況とログを画面上で確認',
        ],
        'recommended_for': [
            '毎月の勤怠入力をまとめて処理したい方',
            'Excelで勤怠データを管理している方',
        ],
        'usage_steps': [
            'テンプレートに勤怠データを入力',
            'ファイルをアップロード',
            'ブラウザを開いたまま処理完了を待つ',
        ],
        'constraints': [
            'Jobcanへのログイン情報が必要です',
            '処理中はブラウザ操作が発生します',
            'Render無料版では同時実行を1件に絞り、混雑時は順番待ちになります',
        ],
        'faq': [
            {'q': 'Jobcanのログイン情報は保存されますか？', 'a': '保存しません。処理に必要な範囲で利用します。'},
            {'q': '複数日のデータをまとめて処理できますか？', 'a': 'テンプレート形式に沿ったデータをまとめて処理できます。'},
        ],
    },
    {
        'id': 'pdf',
        'name': 'PDFユーティリティ',
        'description': 'PDFの結合・分割・ページ抽出・圧縮・画像変換・パスワード付与を扱う無料ツールです。ロック解除は提供しません。',
        'path': '/tools/pdf',
        'guide_path': '',
        'status': 'available',
        'icon': '📄',
        'category': 'document',
        'tags': ['File', 'PDF'],
        'features': ['結合・分割', 'ページ抽出', '圧縮', 'パスワード付与'],
        'capabilities': [
            '複数のPDFファイルを1つに結合',
            'PDFを指定ページで分割',
            '特定ページを抽出',
            'PDFを圧縮してファイルサイズを削減',
            'PDFにユーザーパスワードを付与',
        ],
        'recommended_for': [
            '提案書や資料PDFを整理したい方',
            'クライアント提出前のPDFをまとめたい方',
            'PDFに閲覧用パスワードを付けたい方',
        ],
        'usage_steps': [
            'PDFファイルを選択',
            '操作モードを選択',
            'ページ範囲やパスワードなど必要な設定を入力',
            '処理を実行',
            '結果をダウンロード',
        ],
        'constraints': [
            '保護済みPDFを開くための機能は提供しません',
            'ブラウザ内処理が中心ですが、パスワード付与のみサーバーで一時処理します',
            'パスワード付与APIは標準で20MBまでに制限しています',
        ],
        'faq': [
            {'q': 'PDFを分割できますか？', 'a': 'はい。ページ範囲を指定して複数PDFに分割できます。'},
            {'q': 'PDFにパスワードを付けられますか？', 'a': 'はい。保護されていないPDFにユーザーパスワードを付与できます。'},
            {'q': '保護済みPDFを開く機能はありますか？', 'a': 'いいえ。閲覧制限を外すための機能は提供していません。'},
        ],
    },
]
