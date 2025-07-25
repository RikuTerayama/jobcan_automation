# Jobcan勤怠打刻自動申請ツール

Excelファイルに記載された日付・始業時刻・終業時刻をJobcanに自動入力するPythonスクリプトです。

## 🚀 ダウンロード

### 最新リリース
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/YOUR_USERNAME/jobcan_automation)](https://github.com/YOUR_USERNAME/jobcan_automation/releases/latest)

**Windows版（推奨）:**
- [jobcan_bot.exe (CLI版)](https://github.com/YOUR_USERNAME/jobcan_automation/releases/latest/download/jobcan_bot.exe)
- [jobcan_gui.exe (GUI版)](https://github.com/YOUR_USERNAME/jobcan_automation/releases/latest/download/jobcan_gui.exe)

> **注意**: `YOUR_USERNAME` を実際のGitHubユーザー名に置き換えてください

### 必要なファイル
- `jobcan_bot.exe` または `jobcan_gui.exe` - メイン実行ファイル
- `sample_data.py` - サンプルデータ作成スクリプト
- `sample_attendance.xlsx` - サンプルExcelファイル
- `README.md` - このファイル

## 機能

- Excelファイルから勤怠データを読み込み
- Jobcanへの自動ログイン
- 勤怠打刻の自動入力
- ログイン情報の暗号化保存
- 処理結果の詳細表示
- GUI版とCLI版の両方を提供

## 必要な環境

- Windows 10/11
- Python 3.8以上（ソースコードから実行する場合のみ）

## インストール

### 方法1: 実行ファイル版（推奨）
1. [リリースページ](https://github.com/YOUR_USERNAME/jobcan_automation/releases/latest)からファイルをダウンロード
2. 任意のフォルダに解凍
3. `jobcan_bot.exe` または `jobcan_gui.exe` を実行

### 方法2: ソースコード版
1. 依存関係をインストール:
```bash
pip install -r requirements.txt
```

2. Playwrightのブラウザをインストール:
```bash
playwright install chromium
```

## 使用方法

### CLI版
```bash
# 基本的な使用方法
jobcan_bot.exe sample_attendance.xlsx

# 初回ログイン（認証情報を保存）
jobcan_bot.exe sample_attendance.xlsx --email your-email@example.com --password your-password --save-credentials

# ヘッドレスモードで実行
jobcan_bot.exe sample_attendance.xlsx --headless
```

### GUI版
1. `jobcan_gui.exe` をダブルクリック
2. Excelファイルを選択
3. ログイン情報を入力（初回のみ）
4. 「勤怠データを自動入力」ボタンをクリック

## Excelファイル形式

Excelファイルは以下の形式で作成してください：

| A列（日付） | B列（始業時刻） | C列（終業時刻） |
|------------|----------------|----------------|
| 2025/01/15 | 09:30          | 18:30          |
| 2025/01/16 | 09:00          | 18:00          |
| 2025/01/17 | 09:45          | 18:45          |

### サンプルファイルの作成
```bash
python sample_data.py
```

## セキュリティ

- ログイン情報は`cryptography`ライブラリを使用して暗号化されます
- 暗号化キーは`key.key`ファイルに保存されます
- 暗号化された認証情報は`credentials.enc`ファイルに保存されます
- **重要**: これらのファイルはGitHubにアップロードされません

## ファイル構成

```
jobcan_automation/
├── jobcan_bot.py          # メインスクリプト（CLI版）
├── jobcan_gui.py          # GUI版スクリプト
├── config.py              # 設定ファイル
├── sample_data.py         # サンプルデータ作成スクリプト
├── build_exe.py           # 実行ファイル作成スクリプト
├── requirements.txt       # 依存関係
├── requirements_gui.txt   # GUI版依存関係
├── setup.bat             # セットアップスクリプト
├── README.md             # このファイル
├── .gitignore            # Git除外設定
├── .github/workflows/    # GitHub Actions
│   └── build.yml
├── credentials.enc       # 暗号化された認証情報（自動生成）
└── key.key               # 暗号化キー（自動生成）
```

## 処理フロー

1. **ログイン**: Jobcanにログイン（保存された認証情報または新規入力）
2. **出勤簿アクセス**: 出勤簿ページに移動
3. **日付選択**: Excelの各行の日付を選択
4. **打刻修正**: 打刻修正ボタンをクリック
5. **時刻入力**: 始業時刻と終業時刻を順次入力
6. **結果表示**: 処理結果をターミナルに表示

## エラーハンドリング

- ログイン失敗時の再試行
- ページ要素が見つからない場合の代替セレクター使用
- 処理失敗時の詳細エラー表示
- キーボード割り込み（Ctrl+C）での安全な終了

## 注意事項

- 初回実行時はブラウザが表示されるため、手動での操作は避けてください
- 大量のデータを処理する場合は、適切な間隔を設けてください
- 本ツールは個人利用を想定しています
- 勤怠システムの利用規約を確認してからご利用ください

## トラブルシューティング

### ログインに失敗する場合
- メールアドレスとパスワードが正しいか確認
- 2段階認証が有効な場合は無効にするか、アプリパスワードを使用

### ページ要素が見つからない場合
- JobcanのUIが変更された可能性があります
- `config.py`のセレクター設定を更新してください

### ブラウザが起動しない場合
- Playwrightが正しくインストールされているか確認
- `playwright install chromium`を実行してください

### 実行ファイルが動作しない場合
- Windows Defenderやアンチウイルスソフトがブロックしている可能性があります
- ソースコード版を試してください

## 開発者向け

### ローカルビルド
```bash
# 実行ファイルを作成
python build_exe.py

# または手動でPyInstallerを使用
pip install pyinstaller
pyinstaller --onefile jobcan_bot.py
```

### GitHub Actions
- タグをプッシュすると自動的にリリースが作成されます
- `v1.0.0` のような形式でタグを作成してください

## ライセンス

このプロジェクトは個人利用を目的としています。

## サポート

問題が発生した場合は、以下の情報を含めて[Issues](https://github.com/YOUR_USERNAME/jobcan_automation/issues)に投稿してください：
- エラーメッセージ
- 使用しているExcelファイルの形式
- Jobcanのバージョン（確認可能な場合）
- 実行環境（Windows 10/11、Python版/実行ファイル版）

## 更新履歴

### v1.0.0
- 初回リリース
- CLI版とGUI版の両方を提供
- 自動ログイン機能
- 暗号化された認証情報保存
- サンプルデータ作成機能 
