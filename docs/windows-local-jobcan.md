# Windowsローカル版 Jobcan Tool

`JobcanTool.exe` は、既存のJobcan AutoFillを利用者のWindows PC内で実行するデスクトップ向け構成です。Flaskはランダムな `127.0.0.1` ポートだけで待ち受け、既定ブラウザに操作画面を開きます。Render上のJobcan処理とは独立して起動します。

## インストールと起動

1. GitHub Releasesの `JobcanTool-windows-x64.zip` をダウンロードします。
2. ZIPを任意のフォルダーへ展開します。ZIP内のファイル構成は変更しないでください。
3. `JobcanTool.exe` をダブルクリックします。数秒後に既定ブラウザで画面が開きます。
4. テンプレートをダウンロードし、勤怠を記入したExcelを選択して実行します。
5. 終了時は画面右上の「アプリを終了」を押します。

署名証明書をまだ使用していないため、Windows SmartScreenが警告する場合があります。配布元とファイルを確認したうえで利用してください。自動更新は行わず、新版はGitHub Releasesから取得します。

## データとプライバシー

- Jobcanのメールアドレス、会社ID、パスワードはメモリ上で処理し、保存機能は提供しません。
- Excelはブラウザから `localhost` へ送られ、このPCの一時フォルダーでだけ処理されます。一時ファイルは処理後またはアプリ終了時に削除します。
- Jobcanへのログイン通信は、利用者PC上で起動したMicrosoft EdgeまたはPlaywright ChromiumからJobcanへ直接行われます。「外部通信ゼロ」を意味するものではありません。
- ローカル画面ではGA4、AdSense、Amazon Associates、A8.netを読み込みません。通常リンク「しごと道具箱を見る」にアフィリエイトパラメーターは付けません。
- パスワードをログ、ファイル名、localStorageへ記録しません。ただし、利用者PCやJobcan側の安全性まで保証する表現ではありません。

## ローカルセキュリティ

- bind先は `127.0.0.1` のみで、起動ごとに空きポートを選びます。
- Host/Origin検証とセッション単位のCSRFトークンで書き込みAPIを保護します。
- Excelは拡張子、コンテナシグネチャ、サイズ上限を検査します。
- 同時実行は1件、待機キューは0件です。実行中の二重送信はUIとサーバーの両方で拒否します。
- Windows named mutexで二重起動を防ぎます。

## ブラウザ方式

ローカル版はWindows標準のMicrosoft Edgeを `channel="msedge"` で優先します。Edgeを利用できない場合だけPlaywright Chromiumへフォールバックします。Edge再利用は配布サイズを抑えられる一方、Chromium fallbackを使うには開発環境または配布工程で `playwright install chromium` が必要です。通常の配布物ではEdgeを前提とし、Chromium本体はZIPへ同梱しません。

## 開発・ビルド

```powershell
py -3 -m venv .venv-local
.\.venv-local\Scripts\python.exe -m pip install -r requirements-local.txt
.\.venv-local\Scripts\python.exe local_app.py

# テスト、PyInstaller onedir、ZIP生成
.\scripts\build_windows_local.ps1
```

`onedir` は、テンプレート・静的資産・Playwright Pythonモジュールを確実に参照でき、`onefile` の毎回展開コストとウイルス対策ソフトによる起動遅延を避けやすいため採用しています。出力は `dist/JobcanTool/JobcanTool.exe` と `dist/JobcanTool-windows-x64.zip` です。タグ `jobcan-tool-v*` のpush時だけGitHub ActionsがReleaseを作成します。

依存区分:

- shared: Flask、openpyxl、jpholiday、psutil
- local-only: playwright（Edge制御とChromium fallback）
- web-only: gunicorn、requests、beautifulsoup4、pypdf
- build-only: PyInstaller、pytest

## トラブルシューティング

- 画面が開かない: Edgeを更新し、アプリを一度終了して再起動してください。
- 「すでに起動しています」: 既存のブラウザ画面を確認し、見つからない場合はタスクマネージャーで `JobcanTool.exe` を終了してください。
- Excelを受け付けない: `.xlsx` / `.xls` の実ファイルで、10MB以下か確認してください。
- Jobcanログイン失敗: メールアドレス、会社ID、パスワードとJobcan側のログイン可否を確認してください。技術的なstack traceではなく画面の日本語メッセージを確認します。
- EdgeもChromiumも起動できない: Edgeをインストール・更新するか、開発環境では `playwright install chromium` を実行してください。

## 実アカウント確認（USER VERIFICATION REQUIRED）

リリース前に、認証情報をテストコードへ保存せず、利用者自身が管理する実アカウントで次を確認してください。

1. 会社IDなし/ありの対象フローでログインできる。
2. 管理対象外の日付を含まない小さなテストExcelで勤怠入力が完了する。
3. Jobcan画面上の登録結果を目視確認する。
4. 完了・失敗・タイムアウト後にEdge/Chromeプロセスが残らない。
5. 最終Excel以外の一時ファイルが残らない。

この実機確認と正式Release artifactの検証が完了するまでは、RenderのJobcan Web Serviceを停止・削除しないでください。公開Web版はLegacy/Server modeとして既存デプロイ手順を維持します。
