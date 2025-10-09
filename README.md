# Jobcan Automation Web Application

Jobcanの勤怠データを自動入力するWebアプリケーションです。

## 🚀 機能

- **Excelテンプレートダウンロード**: 勤怠データ入力用のテンプレートファイルをダウンロード
- **自動データ入力**: Excelファイルのデータに基づいてJobcanに勤怠データを自動入力
- **リアルタイム進捗表示**: 処理の進捗状況をリアルタイムで表示
- **詳細ログ**: 各ステップの詳細なログを提供

## 📁 プロジェクト構造

```
jobcan_automation-main/
├── app.py              # メインのFlaskアプリケーション
├── utils.py            # ユーティリティ関数（Excel処理、ログ機能）
├── automation.py       # 自動化処理ロジック
├── requirements.txt    # Python依存関係
├── Dockerfile         # Docker設定
├── render.yaml        # Render設定
├── templates/
│   └── index.html     # Webインターフェース
└── uploads/           # アップロードファイル保存ディレクトリ
```

## 🛠️ 技術スタック

- **Backend**: Flask (Python)
- **Browser Automation**: Playwright
- **Excel Processing**: pandas / openpyxl
- **Deployment**: Render (Docker)
- **WSGI Server**: Gunicorn

## 🔧 セットアップ

### ローカル開発

1. **リポジトリをクローン**
   ```bash
   git clone https://github.com/your-username/jobcan_automation.git
   cd jobcan_automation
   ```

2. **依存関係をインストール**
   ```bash
   pip install -r requirements.txt
   ```

3. **Playwrightブラウザをインストール**
   ```bash
   playwright install chromium
   ```

4. **アプリケーションを起動**
   ```bash
   python app.py
   ```

### Render デプロイ

1. **GitHubリポジトリをRenderに接続**
   - Renderで新しいWeb Serviceを作成
   - GitHubリポジトリを選択
   - 環境変数を設定（必要に応じて）

2. **Start Commandの設定**
   - RenderのWeb Service設定で「Start Command」を以下に設定：
   ```bash
   gunicorn app:app
   ```

3. **自動デプロイ**
   - プッシュ時に自動的にデプロイされます
   - 構文チェックがGitHub Actionsで実行されます

### 重要な依存関係

- **gunicorn**: WSGI HTTPサーバー（本番環境用）
- **Flask**: Webフレームワーク
- **Playwright**: ブラウザ自動化
- **openpyxl**: Excelファイル処理
- **psutil**: システムリソース監視

## 📋 使用方法

1. **テンプレートファイルをダウンロード**
   - 「テンプレートファイルをダウンロード」ボタンをクリック
   - Excelファイルがダウンロードされます

2. **勤怠データを入力**
   - ダウンロードしたExcelファイルに勤怠データを入力
   - 日付、開始時刻、終了時刻を記入

3. **ファイルをアップロード**
   - メールアドレスとパスワードを入力
   - Excelファイルをアップロード
   - 「勤怠データを自動入力」ボタンをクリック

4. **進捗を確認**
   - リアルタイムで処理の進捗を確認
   - 詳細なログで各ステップの状況を把握

## 🔍 トラブルシューティング

### よくある問題

1. **構文エラー**
   - GitHub Actionsで自動的に構文チェックが実行されます
   - ローカルで `python -m py_compile app.py` を実行して確認

2. **Playwrightエラー**
   - Render環境では制限がある場合があります
   - ローカル環境での実行を推奨

3. **Excelファイルエラー**
   - ファイル形式が.xlsxまたは.xlsであることを確認
   - ヘッダー行が正しく設定されていることを確認

### ログの確認

- アプリケーションのログで詳細なエラー情報を確認
- 各ステップの進捗状況をリアルタイムで表示

## 🚀 デプロイ

### Render でのデプロイ

1. **render.yaml** ファイルが設定済み
2. **Dockerfile** でコンテナ化
3. **requirements.txt** で依存関係管理

### 環境変数

必要に応じて以下の環境変数を設定：

- `PORT`: アプリケーションのポート番号
- `SECRET_KEY`: Flaskのシークレットキー
- `ADSENSE_ENABLED`: Google AdSense有効化フラグ（本番環境のみ `true` に設定）
  - デフォルト: `false`（開発環境）
  - 本番環境: `true` に設定することでAdSenseスクリプトが読み込まれます

## 📊 モニタリング

- **ヘルスチェック**: `/health` エンドポイント
- **準備状態**: `/ready` エンドポイント
- **依存関係**: pandas, openpyxl, playwrightの利用可能性を確認

## 📢 Google AdSense 設定

### 概要

このアプリケーションは、本番環境でGoogle AdSenseをサポートしています。

### 有効化方法

1. **環境変数を設定**
   ```bash
   # 本番環境で以下を設定
   ADSENSE_ENABLED=true
   ```

2. **デプロイ**
   - Renderなどのデプロイ環境で環境変数 `ADSENSE_ENABLED=true` を設定
   - 開発環境では未設定（または `false`）のままにすることを推奨

### AdSense Publisher ID

- **Publisher ID**: `ca-pub-4232725615106709`
- AdSenseスクリプトは `<head>` 内に1回のみ読み込まれます

### 除外ページ

以下のページでは、AdSenseスクリプトは読み込まれません：
- `/privacy` - プライバシーポリシーページ
- `/contact` - お問い合わせページ
- `/thanks` - サンクスページ
- `/login` - ログインページ
- `/app/*` - アプリケーション管理ページ

**除外ページを追加する方法:**

`templates/index.html` (または他のテンプレート) の条件式を編集：

```jinja2
{% if ADSENSE_ENABLED and not (request.path.startswith('/login') or request.path.startswith('/app/') or request.path in ['/privacy', '/contact', '/thanks', '/新しいパス']) %}
```

### ads.txt ファイル

Google AdSenseの認証のため、`ads.txt` ファイルを配信しています。

- **URL**: `https://<your-domain>/ads.txt`
- **内容**:
  ```
  google.com, pub-4232725615106709, DIRECT, f08c47fec0942fa0
  ```

**配置場所**: `app.py` の `/ads.txt` ルートで自動配信

### デプロイ後の確認手順

1. **ブラウザでサイトにアクセス**
   ```
   https://<your-domain>/
   ```

2. **ページのソースを表示**
   - 右クリック → 「ページのソースを表示」
   - または `Ctrl+U` (Windows) / `Cmd+Option+U` (Mac)

3. **AdSenseスクリプトの確認**
   - `<head>` 内に以下のスクリプトが**1回のみ**存在することを確認：
     ```html
     <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4232725615106709" crossorigin="anonymous"></script>
     ```

4. **ads.txt の確認**
   ```
   https://<your-domain>/ads.txt
   ```
   上記URLにアクセスし、以下の内容が表示されることを確認：
   ```
   google.com, pub-4232725615106709, DIRECT, f08c47fec0942fa0
   ```

5. **除外ページの確認**
   - 除外ページ（例: `/privacy`, `/login` など）でソースを表示
   - AdSenseスクリプトが含まれていないことを確認

### トラブルシューティング

- **スクリプトが表示されない**: `ADSENSE_ENABLED=true` が設定されているか確認
- **スクリプトが重複している**: テンプレートの継承構造を確認し、重複を削除
- **ads.txt がアクセスできない**: `/ads.txt` ルートが正しく設定されているか確認

## 🔒 セキュリティ

- アップロードされたファイルは処理後に自動削除
- 一時ファイルの適切な管理
- エラーハンドリングの実装

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🤝 貢献

1. フォークを作成
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📞 サポート

問題が発生した場合は、GitHubのIssuesで報告してください。 
