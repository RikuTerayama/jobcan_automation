# Jobcan勤怠申請Webアプリケーション

Flask + Playwrightで構築された勤怠自動入力Webサービスです。

## 🚀 機能

- **Webブラウザからアクセス** - 直感的なWebインターフェース
- **Excelファイルアップロード** - 勤怠データを簡単にアップロード
- **URL直接指定** - Jobcanログイン後のURLを貼り付けるだけ
- **リアルタイム進捗表示** - 処理状況をリアルタイムで確認
- **詳細結果表示** - 成功/失敗の詳細な結果を表示

## 📋 使用方法

### 1. 準備
1. **Jobcanにログイン** - ブラウザでJobcanにログイン
2. **出勤簿ページに移動** - 出勤簿ページのURLをコピー
3. **Excelファイルを準備** - A列:日付、B列:始業時刻、C列:終業時刻

### 2. Webアプリの起動
```bash
# 依存関係をインストール
pip install -r requirements_web.txt

# Playwrightブラウザをインストール
playwright install chromium

# Webアプリを起動
python web_app.py
```

### 3. ブラウザでアクセス
- http://localhost:5000 にアクセス
- JobcanのURLとExcelファイルを入力
- 「勤怠データを自動入力」ボタンをクリック

## 📁 ファイル構成

```
jobcan_automation/
├── web_app.py              # Flask Webアプリケーション
├── templates/
│   └── index.html          # メインHTMLテンプレート
├── uploads/                # アップロードファイル保存先
├── requirements_web.txt    # Webアプリ用依存関係
├── sample_attendance.xlsx  # サンプルExcelファイル
└── README_WEB.md          # このファイル
```

## 🔧 技術仕様

### バックエンド
- **Flask 3.0.0** - Webフレームワーク
- **Playwright 1.40.0** - ブラウザ自動化
- **Pandas 2.2.0+** - Excelファイル処理
- **OpenPyXL 3.1.2** - Excelファイル読み込み

### フロントエンド
- **HTML5** - マークアップ
- **CSS3** - スタイリング（グラデーション、アニメーション）
- **JavaScript** - 非同期処理、リアルタイム更新

### セキュリティ
- **ファイルアップロード制限** - Excelファイルのみ許可
- **ファイルサイズ制限** - 16MB以下
- **セッション管理** - 処理状況の追跡
- **一時ファイル削除** - 処理完了後の自動削除

## 📊 Excelファイル形式

| A列（日付） | B列（始業時刻） | C列（終業時刻） |
|------------|----------------|----------------|
| 2025/01/15 | 09:30          | 18:30          |
| 2025/01/16 | 09:00          | 18:00          |
| 2025/01/17 | 09:45          | 18:45          |

## 🔄 処理フロー

1. **ファイルアップロード** - Excelファイルをサーバーにアップロード
2. **データ読み込み** - PandasでExcelデータを解析
3. **バックグラウンド処理** - Playwrightでブラウザ自動操作
4. **リアルタイム更新** - 処理状況を2秒ごとに確認
5. **結果表示** - 成功/失敗の詳細結果を表示

## ⚙️ 設定

### 環境変数
```bash
# セッションキー（本番環境では変更してください）
export FLASK_SECRET_KEY="your-secret-key"

# アップロードフォルダ
export UPLOAD_FOLDER="uploads"

# 最大ファイルサイズ（バイト）
export MAX_CONTENT_LENGTH=16777216
```

### サーバー設定
```python
# 開発環境
app.run(debug=True, host='0.0.0.0', port=5000)

# 本番環境
app.run(host='0.0.0.0', port=5000)
```

## 🚀 デプロイ

### ローカル実行
```bash
python web_app.py
```

### Docker実行
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements_web.txt .
RUN pip install -r requirements_web.txt

RUN playwright install chromium

COPY . .
EXPOSE 5000

CMD ["python", "web_app.py"]
```

### クラウドデプロイ
- **Heroku** - `Procfile`でWebプロセスを定義
- **AWS** - EC2またはECSでデプロイ
- **Google Cloud** - App EngineまたはCompute Engine
- **Azure** - App ServiceまたはContainer Instances

## 🔍 トラブルシューティング

### よくある問題

1. **Playwrightブラウザが起動しない**
   ```bash
   playwright install chromium
   ```

2. **Excelファイルが読み込めない**
   - ファイル形式を確認（.xlsx, .xls）
   - ファイルサイズを確認（16MB以下）

3. **JobcanのURLにアクセスできない**
   - ログイン状態を確認
   - URLの形式を確認

4. **処理が途中で止まる**
   - ネットワーク接続を確認
   - Jobcanのセッション切れを確認

### ログ確認
```bash
# Flaskのログを確認
python web_app.py

# ブラウザのログを確認（ヘッドレスモードを無効化）
# web_app.pyのheadless=TrueをFalseに変更
```

## 📈 パフォーマンス

### 最適化ポイント
- **バックグラウンド処理** - 非同期でブラウザ操作
- **ファイル削除** - 処理完了後の自動削除
- **セッション管理** - 効率的な状態管理
- **エラーハンドリング** - 適切なエラー処理

### 推奨環境
- **CPU**: 2コア以上
- **メモリ**: 4GB以上
- **ストレージ**: 1GB以上の空き容量
- **ネットワーク**: 安定したインターネット接続

## 🔒 セキュリティ注意事項

1. **本番環境での使用**
   - セッションキーを変更
   - HTTPS通信を有効化
   - ファイアウォール設定

2. **ファイル管理**
   - アップロードファイルの自動削除
   - ファイル形式の厳密なチェック
   - ファイルサイズの制限

3. **アクセス制御**
   - 必要に応じて認証機能を追加
   - IPアドレス制限の検討
   - レート制限の実装

## 📞 サポート

問題が発生した場合は、以下の情報を含めてご連絡ください：
- エラーメッセージ
- 使用しているExcelファイルの形式
- JobcanのURL（機密情報は除く）
- 実行環境（OS、Pythonバージョン）

## 📄 ライセンス

このプロジェクトは個人利用を目的としています。 
