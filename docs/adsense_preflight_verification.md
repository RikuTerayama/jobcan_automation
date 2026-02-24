# AdSense 再申請前ゲート 検証手順

## 変更ファイル一覧

| ファイル | 内容 |
|----------|------|
| `templates/tools/index.html` | no-results 文言をサーバ返却HTMLに含めない（`String.fromCharCode` で生成、既対応済み） |
| `scripts/adsense_preflight.py` | 3a: /tools の no-results 文言なしを明示チェック。5/6: ads.txt・robots.txt を 200 必須で FAIL に統一 |

## なぜ /tools HTML に文言が残っていたか（発生源）

- **発生源**: `templates/tools/index.html` の `<script>` 内に、次のような**日本語の直書き**があったため。
  - `const NO_RESULTS_MSG = '検索条件に一致するツールが見つかりませんでした。';`
- サーバはこのテンプレートをそのまま返すため、**JS 実行前の HTML 本文（script 含む）** に上記文字列が含まれていた。
- **対応**: 上記を `String.fromCharCode(0x691c,0x7d22,...)` に変更し、**サーバ返却HTMLには日本語の生文字列が含まれない**ようにした。文言は JS 実行時にのみ生成される。

## preflight --live 実行結果（期待）

```
python scripts/adsense_preflight.py --live https://jobcan-automation.onrender.com
```

- `3a_tools_no_results` … /tools のサーバ返却HTMLに no-results 文言が含まれない → **OK**
- `5_ads_txt` … /ads.txt が 200 かつ pub- 行あり → **OK**
- `6_robots_txt` … /robots.txt が 200 かつ主要ページをブロックしていない → **OK**
- **7_sitemap** … sitemap.xml に /, /autofill, /tools, /privacy, /blog, /glossary, /guide/excel-format, /best-practices が含まれる → **OK**
- **8_robots_format** … robots.txt が複数行で Sitemap 行あり → **OK**
- **9_indexable** … /, /privacy, /blog, /glossary, /guide/excel-format に noindex が無く canonical 自己参照 → **OK**
- 上記を含め全チェック PASS で exit 0。

## 本番反映確認用コマンド

### PowerShell

```powershell
# /tools のHTMLに no-results 文言が含まれないこと
$r = Invoke-WebRequest -Uri "https://jobcan-automation.onrender.com/tools" -UseBasicParsing
if ($r.Content -match [regex]::Escape("検索条件に一致するツールが見つかりませんでした。")) { "FAIL: found" } else { "OK: not in HTML" }

# /ads.txt が 200 であること
(Invoke-WebRequest -Uri "https://jobcan-automation.onrender.com/ads.txt" -UseBasicParsing).StatusCode

# /robots.txt が 200 であること
(Invoke-WebRequest -Uri "https://jobcan-automation.onrender.com/robots.txt" -UseBasicParsing).StatusCode
```

### curl（WSL/Git Bash 等）

```bash
# /tools に文言が含まれないこと（ヒットしなければ OK）
curl -s "https://jobcan-automation.onrender.com/tools" | grep -q "検索条件に一致するツールが見つかりませんでした" && echo "FAIL" || echo "OK"

# /ads.txt 200
curl -s -o /dev/null -w "%{http_code}" "https://jobcan-automation.onrender.com/ads.txt"

# /robots.txt 200
curl -s -o /dev/null -w "%{http_code}" "https://jobcan-automation.onrender.com/robots.txt"
```

## デプロイ対象（main）の整合確認

本番が main をデプロイしている前提:

1. **main に修正コミットが含まれるか**
   ```bash
   git fetch origin main
   git log origin/main -1 --oneline
   git log origin/main --oneline -- templates/tools/index.html
   ```
   - `templates/tools/index.html` の最新変更に `String.fromCharCode` が含まれることを確認。

2. **Render のデプロイログ**
   - Render Dashboard → 該当サービス → Deploys で、最新デプロイの **Commit SHA** を確認。
   - 上記 `git log origin/main -1` の SHA と一致していれば、本番は最新 main を反映済み。

3. **修正が main に無い場合**
   - 修正ブランチを main にマージして push し、Render の自動デプロイ完了後に上記コマンドおよび `scripts/adsense_preflight.py --live` で再確認。
