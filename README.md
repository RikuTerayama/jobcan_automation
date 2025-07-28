# Jobcan勤怠申請Webアプリケーション

Flask + Playwright + Pandasを使用した、Jobcan勤怠申請の自動化Webアプリケーションです。

## 🚀 機能

- **Webインターフェース**: ブラウザから簡単にアクセス可能
- **Excelファイルアップロード**: 勤怠データをExcelファイルでアップロード
- **自動勤怠入力**: PlaywrightでJobcanに自動入力
- **リアルタイム進捗表示**: 処理状況をリアルタイムで確認
- **セキュアな処理**: ログイン済みURLを使用してセキュリティを確保

## 📋 要件

- Python 3.8以上
- Windows 10/11
- インターネット接続

## 🛠️ ローカル開発

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. Playwrightブラウザのインストール

```bash
playwright install chromium
```

### 3. サンプルデータの作成

```bash
python create_sample.py
```

### 4. アプリケーションの起動

```bash
python app.py
```

### 5. ブラウザでアクセス

```
http://localhost:5000
```

## 🚀 Railwayデプロイ

### 1. Railwayアカウント作成
- [Railway](https://railway.app/) にアクセス
- GitHubアカウントでログイン

### 2. プロジェクト作成
- 「New Project」をクリック
- 「Deploy from GitHub repo」を選択
- このリポジトリを選択

### 3. 環境変数設定（オプション）
Railwayダッシュボードで以下を設定：
- `PORT`: 5000（自動設定）

### 4. デプロイ
- 自動的にデプロイが開始されます
- 完了後、提供されるURLでアクセス可能

## 🚀 Renderデプロイ（代替案）

### 1. Renderアカウント作成
- [Render](https://render.com/) にアクセス
- GitHubアカウントでログイン

### 2. 新しいWeb Service作成
- 「New +」→「Web Service」
- GitHubリポジトリを接続

### 3. 設定
- **Name**: jobcan-web-app
- **Environment**: Python 3
- **Build Command**: `pip install -r requirements.txt && playwright install chromium`
- **Start Command**: `python app.py`

### 4. デプロイ
- 「Create Web Service」をクリック
- 自動デプロイが開始されます

## 📊 使用方法

### 1. **Jobcanにログイン**
- ブラウザでJobcanにログイン
- 出勤簿ページに移動: `https://ssl.jobcan.jp/employee/attendance`

### 2. **URLをコピー**
- ブラウザのアドレスバーからURLをコピー

### 3. **Excelファイルを準備**
- A列: 日付（yyyy/mm/dd）
- B列: 始業時刻（HH:MM）
- C列: 終業時刻（HH:MM）

### 4. **Webアプリで送信**
- URLを入力欄に貼り付け
- Excelファイルをアップロード
- 「勤怠データを自動入力」ボタンをクリック

## 📊 Excelファイル形式

| A列（日付） | B列（始業時刻） | C列（終業時刻） |
|------------|----------------|----------------|
| 2025/07/01 | 09:30          | 18:30          |
| 2025/07/02 | 09:00          | 18:00          |
| 2025/07/03 | 09:45          | 18:45          |

## 🔧 技術仕様

### バックエンド
- **Flask**: Webフレームワーク
- **Playwright**: ブラウザ自動化
- **Pandas**: Excelファイル処理
- **Threading**: 非同期処理
- **Gunicorn**: 本番環境用WSGIサーバー

### フロントエンド
- **HTML5**: レスポンシブデザイン
- **CSS3**: モダンなUI
- **JavaScript**: リアルタイム更新

## 📁 ファイル構成

```
jobcan_web_app/
├── app.py                 # メインアプリケーション
├── requirements.txt       # 依存関係
├── create_sample.py      # サンプルデータ作成
├── railway.json          # Railway設定
├── Procfile             # プロセスタイプ指定
├── build.sh             # ビルドスクリプト
├── README.md            # このファイル
├── templates/           # HTMLテンプレート
│   └── index.html      # メインページ
└── uploads/            # アップロードファイル（自動生成）
```

## 🔒 セキュリティ

- **ログイン情報不要**: ユーザーが事前にログインしたURLを使用
- **一時ファイル**: アップロードされたファイルは処理後に自動削除
- **ヘッドレスブラウザ**: バックグラウンドで安全に実行

## ⚠️ 注意事項

- Jobcanの利用規約を確認してからご利用ください
- 大量のデータを処理する場合は、適切な間隔を設けてください
- 本ツールは個人利用を想定しています

## 🐛 トラブルシューティング

### よくある問題

1. **Playwrightがインストールされない**
   ```bash
   pip install playwright
   playwright install chromium
   ```

2. **Excelファイルが読み込めない**
   - ファイル形式が正しいか確認
   - ヘッダー行があるか確認

3. **URLにアクセスできない**
   - Jobcanにログインしているか確認
   - URLが正しいか確認

4. **デプロイエラー**
   - Railway/Renderのログを確認
   - 依存関係が正しくインストールされているか確認

## 📝 ライセンス

このプロジェクトは個人利用を目的としています。

## 🤝 サポート

問題が発生した場合は、以下の情報を含めてご連絡ください：
- エラーメッセージ
- 使用しているExcelファイルの形式
- Jobcanのバージョン（確認可能な場合）
- デプロイプラットフォーム（Railway/Render等） 
