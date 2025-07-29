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

## 📊 モニタリング

- **ヘルスチェック**: `/health` エンドポイント
- **準備状態**: `/ready` エンドポイント
- **依存関係**: pandas, openpyxl, playwrightの利用可能性を確認

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
