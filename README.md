# RT Tools - 業務効率化ツール集

Jobcan自動入力と各種業務効率化ツールを提供するWebアプリケーションです。

## 🚀 機能概要

### Jobcan AutoFill
- **Excelテンプレートダウンロード**: 勤怠データ入力用のテンプレートファイルをダウンロード
- **自動データ入力**: Excelファイルのデータに基づいてJobcanに勤怠データを自動入力
- **リアルタイム進捗表示**: 処理の進捗状況をリアルタイムで表示

### 画像一括変換 (v2)
- 複数サイズ同時出力、プリセット、品質調整、リネーム

### PDFユーティリティ (v2)
- 結合・分割・抽出、PDF→画像変換、圧縮、画像→PDF変換

### 画像ユーティリティ (v2)
- 透過→白背景変換、余白トリム、縦横比統一、背景除去

### 議事録整形 (v2)
- 決定事項/ToDo抽出、期限正規化、CSV/JSON出力

### Web/SEOユーティリティ (v2)
- OGP画像生成、PageSpeedチェックリスト、メタタグ検査、sitemap.xml/robots.txt生成

## 🔒 ローカル処理方針

**すべてのツールはブラウザ内で完結します。**
- ファイルやテキストはアップロードしません
- サーバーには保存されません
- 処理はクライアント側（ブラウザ）で実行されます
- 処理完了後、メモリから自動的に削除されます

## 📊 UI監査レポート生成

GeminiにUI改善を依頼するための現状理解レポートを自動生成できます。

### 実行方法

```bash
npm install  # 初回のみ（TypeScript, ts-nodeのインストール）
npm run audit:ui
```

### 出力

`docs/ui-audit/current-ui-report.md` にレポートが生成されます。

このレポートには以下が含まれます：
- 全ページのUI構造分析
- 共通コンポーネントとスタイルパターン
- 改善余地と変更リスク
- Gemini向けのプロンプト案

レポートをGeminiに貼り付けることで、具体的なUI改善提案を得ることができます。

## 📄 コンテンツレポート生成（記事用素材）

AdSense を意識した記事作成用の「素材レポート」を自動生成できます。各サービスの概要・使い方・FAQ・SEO 素材などの章立てを揃えた Markdown が `docs/content-reports/` に出力されます。後続で ChatGPT や Cursor で記事化する前提のテンプレです。

### 実行方法

```bash
npm run report:content
```

### 出力

- `docs/content-reports/00_master_overview.md` … サービス一覧・情報設計・テンプレ構成
- `docs/content-reports/01_<サービスID>.md` … 各サービスごとのレポート（autofill, image-batch, pdf, image-cleanup, minutes, seo）
- `docs/content-reports/99_adsense_readiness_checklist.md` … 必須ページ・コンテンツ品質・1記事あたりの目安

生成後、各 md を開いて TODO を埋めたり、記事用プロンプトに流し込んで利用してください。

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

### Renderのスリープ対策（重要）

**Renderの無料プランは15分間アクセスがないとスリープします。** Google AdSense審査で「サイトが利用不可」と判定されないよう、以下の対策を実施してください。

#### **推奨：UptimeRobotで監視（無料）**

1. **UptimeRobot に登録**: https://uptimerobot.com/
2. **モニターを追加**:
   - Monitor Type: `HTTP(s)`
   - URL: `https://<your-domain>/ping`
   - Monitoring Interval: `5 minutes`
3. **効果**: 5分ごとにアクセスしてサーバーを起動状態に保ちます

これにより、Googleクローラーがアクセスした際も即座に応答できます。

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

## 📄 コンテンツページ

本サービスには、充実したコンテンツページが用意されています：

### 法的情報
- **プライバシーポリシー** (`/privacy`): 個人情報の取り扱いに関する方針
- **利用規約** (`/terms`): サービス利用に関する規約
- **お問い合わせ** (`/contact`): サポート窓口

### ガイド
- **はじめての使い方** (`/guide/getting-started`): 初めての方向けの詳細ガイド
- **Excelファイルの作成方法** (`/guide/excel-format`): ファイル形式の詳細説明
- **トラブルシューティング** (`/guide/troubleshooting`): よくあるエラーと解決方法

### リソース
- **よくある質問（FAQ）** (`/faq`): 25以上のQ&A
- **用語集** (`/glossary`): 勤怠管理・Jobcan用語の解説
- **サイトについて** (`/about`): サービス概要と技術スタック

**合計10ページ** - Google AdSense審査に十分なコンテンツ量です。

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

## 🚨 SRE・運用監視

### 概要

本番環境の安定稼働のため、包括的な監視とログ機能を実装しています。

### ヘルスチェックエンドポイント

| エンドポイント | 用途 | レスポンスタイム | 推奨用途 |
|--------------|------|-----------------|---------|
| `/healthz` | Render Health Check | <10ms | **本番監視** |
| `/livez` | プロセス生存確認 | <5ms | Kubernetes liveness |
| `/readyz` | 準備完了確認 | <20ms | Kubernetes readiness |
| `/ping` | UptimeRobot監視 | 10-30ms | 外部監視 |
| `/health` | 詳細診断 | 100-300ms | デバッグのみ |

### 監視設定

#### **Render Health Check**
```
Path: /healthz
Interval: 10秒
Timeout: 3秒
Retries: 3回
```

#### **UptimeRobot**
```
URL: https://<your-domain>/healthz
Interval: 5分
Alert: Uptime < 99%
```

### ログとトレーシング

すべてのリクエストに以下が記録されます：

```
2025-10-11 23:45:30 [INFO] req_start rid=a1b2c3d4 method=POST path=/upload
2025-10-11 23:45:32 [INFO] bg_job_start job_id=xxx session_id=yyy file_size=12345
2025-10-11 23:47:10 [INFO] bg_job_success job_id=xxx duration_sec=100.2
2025-10-11 23:47:10 [INFO] req_end rid=a1b2c3d4 status=200 ms=234.5
```

- `rid`: リクエストID（X-Request-IDヘッダ）
- `duration_ms`: レスポンスタイム
- `SLOW_REQUEST`: 5秒以上のリクエストを警告

### 同時処理能力

**現在の設定（Render free plan）:**

| 処理の種類 | 同時処理可能数 | 制限理由 |
|-----------|---------------|---------|
| **勤怠データアップロード**（Playwright使用） | **1-2人** | メモリ制限（512MB） |
| **ページ閲覧・ダウンロード**（軽い処理） | **4リクエスト** | workers × threads |

**プラン別の推奨:**

| Renderプラン | RAM | 同時ユーザー数 | 月額 | 推奨用途 |
|-------------|-----|--------------|------|---------|
| Free | 512MB | 1-2人 | $0 | 個人利用 |
| Starter | 1GB+ | 3-4人 | $7 | 小規模チーム |
| Standard | 2GB+ | 6-8人 | $25 | 中規模チーム |

**制限の仕組み:**
- `MAX_ACTIVE_SESSIONS=2`（free plan）
- 同時処理数が上限に達すると、エラーメッセージを表示
- ユーザーに「しばらく待って再試行」を促す

### Gunicorn 設定

最適化されたGunicorn設定（環境変数でカスタマイズ可能）：

```bash
workers: ${WEB_CONCURRENCY:-2}        # デフォルト2
threads: ${WEB_THREADS:-2}            # デフォルト2  
timeout: ${WEB_TIMEOUT:-180}          # デフォルト180秒
max-requests: 500                     # メモリリーク対策
MAX_ACTIVE_SESSIONS: 2                # 同時実行制限（OOM防止）
```

### メモリ管理

- **MEMORY_LIMIT_MB**: 450MB（512MBの88%）で警告
- **max-requests**: 500リクエストごとにワーカー再起動（メモリリーク対策）
- **推奨プラン**: Render Starter（1GB RAM）でOOM防止

### 503エラー対策

**実施済み対策:**
1. ヘルスチェックを超軽量化（<10ms）
2. workers=2で同時処理能力向上
3. timeout=180sで長時間処理に対応
4. 構造化ログで問題箇所を即座に特定
5. メモリ監視と警告

**詳細:** `SRE_RUNBOOK.md` を参照

### トラブルシューティング

503エラーが発生した場合：

1. **Renderログを確認**: `killed`, `OOM`, `timeout` を検索
2. **メモリ使用率を確認**: 90%超えならプラン変更
3. **SRE_RUNBOOK.md を参照**: インシデント対応手順

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
