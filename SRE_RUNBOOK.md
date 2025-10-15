# 🚨 SRE Runbook - Jobcan Automation

**最終更新**: 2025-10-11  
**担当**: SRE Team  
**目的**: 503エラー再発防止とインシデント対応

---

## 📊 同時処理能力

### **現在の設定値**

```yaml
WEB_CONCURRENCY: 2        # Gunicorn workers
WEB_THREADS: 2            # Threads per worker
MAX_ACTIVE_SESSIONS: 2    # 同時ブラウザ自動化制限（OOM防止）
```

### **プラン別の同時処理能力**

| プラン | RAM | 同時処理（重い処理）| 同時処理（軽い処理）| 推奨ユーザー数 |
|--------|-----|-------------------|-------------------|--------------|
| **Free** | 512MB | **1-2人** | 4リクエスト | 個人利用 |
| **Starter** | 1GB+ | **3-4人** | 8リクエスト | 小規模チーム |
| **Standard** | 2GB+ | **6-8人** | 16リクエスト | 中規模チーム |

**重い処理:** Excelアップロード + Jobcan自動化（Playwright使用）  
**軽い処理:** ページ閲覧、テンプレートダウンロード、ヘルスチェック

### **メモリ使用量の内訳**

```
基本（Flask + Gunicorn）:
├─ Python runtime: 50-80MB
├─ Flask + dependencies: 50-70MB
├─ Gunicorn workers × 2: 60-100MB
└─ 小計: 180-280MB

Playwright処理1件あたり:
├─ Playwright: 50-100MB
├─ Chromium browser: 350-500MB
└─ 合計: 400-600MB

同時2セッション実行時:
180-280MB (基本) + 400-600MB × 2 = 980-1480MB
→ free plan (512MB) では不可
→ 実質1-2セッションが限界
```

### **制限の仕組み**

```python
# app.py の check_resource_limits() で制限
if active_sessions >= MAX_ACTIVE_SESSIONS:
    raise RuntimeError("同時処理数の上限に達しています")
    # → HTTP 500 エラーを返す
    # → ユーザーに「しばらく待って再試行」を促す
```

---

## 📊 診断サマリ（2025-10-11 23:46 JST インシデント）

### **根因仮説トップ3**

#### **🔴 仮説1: メモリ不足（OOM Kill）- 最有力 85%**

**根拠:**
```
- Render free plan: 512MB RAM制限
- Playwright + Chromium: 400-600MB（ピーク時）
- Flask app + dependencies: 100-150MB
- 合計推定: 500-750MB → OOM threshold超過
- 症状: Worker突然死 → Render health check fail → 503
```

**検証方法:**
```bash
# Renderログで確認
grep -i "killed\|oom\|memory" <render-log>
```

**対策実施済み:**
- `MEMORY_LIMIT_MB=450` で警告（app.py）
- `max-requests=500` でworker定期再起動（メモリリーク対策）
- `workers=2` で負荷分散

**恒久対策（推奨）:**
- **Render plan: free → starter** ($7/month)
  - RAM: 512MB → 1GB+
  - OOMリスク: 極小
  - AdSense運用に必須

---

#### **🟡 仮説2: ワーカー数不足（同時処理能力）- 中 40%**

**根拠:**
```
- 旧設定: workers=1, threads=1 → 同時1リクエストのみ
- /health エンドポイント: psutil + 依存チェック = 重い（100-300ms）
- Render health check中にメインワーカーがブロック
  → timeout → worker restart → 503
```

**対策実施済み:**
- `workers=2, threads=2` に増強
- `/healthz` 新設（<10ms、超軽量）
- Render healthCheckPath: `/ping` → `/healthz`

---

#### **🟢 仮説3: Timeout設定競合 - 低 15%**

**根拠:**
```
- Dockerfile CMD: --timeout 180 ✅
- Procfile: --timeout 30 ❌（短すぎ）
- render.yaml: Docker mode → Procfile無視のはず
- ただし、設定競合の可能性
```

**対策実施済み:**
- Procfile を更新（timeout=180）
- Dockerfile に環境変数でカスタマイズ可能に

---

## 🛠️ 実施した改善（Phase 2）

### **(A) ヘルスチェック最適化**

#### **新規エンドポイント:**

| Path | 用途 | レスポンスタイム | ブロッキング |
|------|------|-----------------|------------|
| `/healthz` | Render Health Check | <10ms | なし |
| `/livez` | プロセス生存確認 | <5ms | なし |
| `/readyz` | 準備完了確認 | <20ms | 最小限 |

#### **既存エンドポイント（後方互換）:**

| Path | 用途 | レスポンスタイム | 注意 |
|------|------|-----------------|------|
| `/ping` | UptimeRobot監視 | 10-30ms | 軽量JSON |
| `/health` | デバッグ/詳細診断 | 100-300ms | **監視非推奨** |
| `/ready` | 依存関係確認 | 50-150ms | 詳細チェック |

**変更内容:**
```python
@app.route('/healthz')
def healthz():
    return Response('ok', mimetype='text/plain', headers={'Cache-Control': 'no-store'})
```

---

### **(B) 構造化ロギング**

#### **リクエストID + 遅延ログ:**

```python
@app.before_request / @app.after_request で以下を記録:
- req_start / req_end
- X-Request-ID（トレーシング用）
- duration_ms（レスポンスタイム）
- SLOW_REQUEST警告（>5s）
```

**ログ形式:**
```
2025-10-11 23:45:30 [INFO] req_start rid=a1b2c3d4 method=POST path=/upload ip=1.2.3.4
2025-10-11 23:47:15 [INFO] req_end rid=a1b2c3d4 method=POST path=/upload status=200 ms=105234.5
2025-10-11 23:47:15 [WARNING] SLOW_REQUEST rid=a1b2c3d4 path=/upload ms=105234.5
```

#### **バックグラウンドジョブログ:**

```
2025-10-11 23:45:30 [INFO] bg_job_start job_id=xxx session_id=yyy file_size=12345
2025-10-11 23:47:10 [INFO] bg_job_success job_id=xxx duration_sec=100.2
2025-10-11 23:47:11 [INFO] cleanup_complete job_id=xxx session_id=yyy cleanup_sec=0.85
```

---

### **(C) Gunicorn設定最適化**

#### **変更前:**
```bash
--workers 1 --threads 1 --timeout 30
```

#### **変更後（Dockerfile CMD）:**
```bash
--workers ${WEB_CONCURRENCY:-2} \
--threads ${WEB_THREADS:-2} \
--timeout ${WEB_TIMEOUT:-180} \
--graceful-timeout 30 \
--keep-alive 5 \
--max-requests 500 \
--max-requests-jitter 50 \
--access-logfile - \
--error-logfile - \
--log-level info
```

**パラメータ解説:**

| パラメータ | 値 | 目的 |
|-----------|-----|------|
| `workers` | 2 | 同時処理能力向上（512MB環境で安全上限） |
| `threads` | 2 | ワーカーあたり2リクエスト処理 |
| `timeout` | 180s | Jobcan処理完了まで待つ（3分） |
| `graceful-timeout` | 30s | 優雅なシャットダウン |
| `keep-alive` | 5s | コネクション再利用 |
| `max-requests` | 500 | メモリリーク対策（500req後に再起動） |
| `max-requests-jitter` | 50 | 再起動タイミングをランダム化 |

**カスタマイズ可能（環境変数）:**
- `WEB_CONCURRENCY` - workers数（デフォルト: 2）
- `WEB_THREADS` - threads数（デフォルト: 2）
- `WEB_TIMEOUT` - タイムアウト（デフォルト: 180）

---

### **(D) render.yaml 設定更新**

```yaml
healthCheckPath: /healthz  # /ping → /healthz（超軽量）

envVars:
  - key: WEB_CONCURRENCY
    value: "2"
  - key: WEB_TIMEOUT
    value: "180"
  - key: MEMORY_LIMIT_MB
    value: "450"  # 512MBの88% で警告
```

---

## 🎯 Render 設定推奨値

### **Health Check設定（Dashboard で設定）**

```
Path: /healthz
Expected Status: 200
Interval: 10秒
Timeout: 3秒
Retries: 3回
```

**設定手順:**
1. Render Dashboard → Web Service
2. Settings → Health & Alerts
3. Health Check Path: `/healthz`
4. Save Changes

---

### **プラン推奨**

| プラン | RAM | CPU | 価格 | 推奨度 | 理由 |
|--------|-----|-----|------|--------|------|
| **Free** | 512MB | 共有 | $0 | ⭐⭐ | OOMリスク高、AdSense審査には不安定 |
| **Starter** | 1GB+ | 共有 | $7/月 | ⭐⭐⭐⭐⭐ | **最推奨**（安定、OOM解消） |
| **Standard** | 2GB+ | 専用 | $25/月 | ⭐⭐⭐ | オーバースペック |

**AdSense運用には Starter 以上を強く推奨**

---

## 📈 観測とアラート

### **監視すべきメトリクス**

#### **1. エンドポイントレスポンスタイム**

```bash
# ローカル計測（PowerShell）
Measure-Command { Invoke-WebRequest -Uri "https://jobcan-automation.onrender.com/healthz" }

# cURL計測
curl -o /dev/null -s -w "time_total: %{time_total}s\n" https://jobcan-automation.onrender.com/healthz
```

**目標値:**
- `/healthz`: p50 < 10ms, p95 < 50ms
- `/ping`: p50 < 30ms, p95 < 100ms
- `/upload`: p50 < 200ms, p95 < 500ms（バックグラウンドに投げるだけ）

---

#### **2. UptimeRobot設定**

```
Monitor 1（メイン）:
  URL: https://jobcan-automation.onrender.com/healthz
  Interval: 5 minutes
  Alert: < 99% uptime

Monitor 2（セカンダリ）:
  URL: https://jobcan-automation.onrender.com/ping
  Interval: 5 minutes
  Alert: < 98% uptime
```

---

#### **3. Renderメトリクス監視**

Render Dashboard → Metrics で監視:

**メモリ使用率:**
- 平常時: < 70% (360MB / 512MB)
- ピーク時: < 85% (435MB / 512MB)
- **90%超え**: 🔴 OOM危険域 → プラン変更検討

**CPU使用率:**
- 平常時: < 30%
- ピーク時: < 70%

**5xx Error Rate:**
- 目標: 0%
- 許容: < 0.1%
- **> 1%**: 🔴 即時対応

---

## 🚨 インシデント対応

### **503 Service Unavailable が発生した場合**

#### **Step 1: 即時トリアージ（5分以内）**

```bash
# 1. サイトの現在の状態確認
curl -I https://jobcan-automation.onrender.com/healthz

# 2. Renderログの確認（最新100行）
# Render Dashboard → Logs

# 3. grep で以下を検索:
#    - "killed", "OOM", "timeout", "Worker", "SIGKILL"
```

#### **Step 2: 根因特定（15分以内）**

**パターンA: OOM Kill**
```
ログ: "Killed" / メモリ使用率 > 90%
→ 即時対応: Render plan を Starter に変更
→ 暫定対応: アプリ再起動、WEB_CONCURRENCY=1 に削減
```

**パターンB: Worker Timeout**
```
ログ: "Worker timeout" / バックグラウンドジョブが長時間実行中
→ WEB_TIMEOUT を 300 に延長
→ 長時間ジョブの分離を検討（RQ/Celery）
```

**パターンC: Health Check Fail**
```
ログ: "Health check failed" / Renderヘルスチェックが連続失敗
→ healthCheckPath が /healthz になっているか確認
→ /healthz のレスポンスタイムを確認（<3s必須）
```

#### **Step 3: 復旧（30分以内）**

```bash
# 1. 手動デプロイ（最新コード）
git push

# 2. Manual Deploy（Render Dashboard）
# Deploy → Manual Deploy → Deploy latest commit

# 3. 確認
curl https://jobcan-automation.onrender.com/healthz
# "ok" が返ればOK
```

---

## 🔧 検証手順

### **ローカル検証**

#### **1. ヘルスチェックレスポンスタイム:**

```bash
# PowerShell
for ($i=1; $i -le 10; $i++) {
  Measure-Command { Invoke-WebRequest -Uri "http://localhost:5000/healthz" } | Select-Object TotalMilliseconds
}

# Bash
for i in {1..10}; do
  curl -o /dev/null -s -w "time: %{time_total}s\n" http://localhost:5000/healthz
done
```

**期待値:** p50 < 10ms, p95 < 20ms

---

#### **2. /upload エンドポイント（バックグラウンド投入）:**

```bash
# レスポンスタイムのみ（実際の処理は非同期）
curl -X POST http://localhost:5000/upload \
  -F "email=test@example.com" \
  -F "password=test" \
  -F "file=@template.xlsx" \
  -w "time: %{time_total}s\n"
```

**期待値:** < 500ms（バックグラウンドに投げるだけ）

---

### **ステージング検証（連続100リクエスト）**

#### **Apache Bench:**

```bash
# /healthz への連続100リクエスト
ab -n 100 -c 10 https://jobcan-automation.onrender.com/healthz

# 期待値:
# - Failed requests: 0
# - 5xx errors: 0
# - Mean time: < 50ms
```

#### **hey ツール（推奨）:**

```bash
# インストール（Go必要）
go install github.com/rakyll/hey@latest

# 実行
hey -n 100 -c 10 -m GET https://jobcan-automation.onrender.com/healthz

# 期待値:
# - Success rate: 100%
# - Slowest: < 500ms
# - Average: < 100ms
```

---

## 📋 Render 設定値（本番推奨）

### **環境変数（render.yaml）**

```yaml
# === 必須 ===
PORT: 10000
ADSENSE_ENABLED: true

# === Gunicorn最適化 ===
WEB_CONCURRENCY: "2"        # workers（512MB環境で上限）
WEB_THREADS: "2"            # worker内スレッド
WEB_TIMEOUT: "180"          # 3分（Jobcan処理用）
WEB_GRACEFUL_TIMEOUT: "30"
WEB_KEEPALIVE: "5"
WEB_MAX_REQUESTS: "500"     # メモリリーク対策
WEB_MAX_REQUESTS_JITTER: "50"
WEB_LOG_LEVEL: "info"

# === メモリ制限 ===
MEMORY_LIMIT_MB: "450"      # 512MBの88%で警告
MEMORY_WARNING_MB: "400"

# === アップロード制限 ===
MAX_FILE_SIZE_MB: "10"
MAX_ACTIVE_SESSIONS: "20"
```

### **Health Check設定（Dashboard）**

```
Health Check Path: /healthz
Interval: 10 seconds
Timeout: 3 seconds
Unhealthy Threshold: 3 retries
```

---

## 🔄 ロールバック手順

### **緊急時のロールバック:**

#### **変更前の設定:**

**Dockerfile（旧CMD）:**
```dockerfile
CMD gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 180 --max-requests 100 --max-requests-jitter 20 --preload app:app
```

**render.yaml（旧設定）:**
```yaml
healthCheckPath: /ping
# WEB_CONCURRENCY などの環境変数なし
```

**Procfile（旧設定）:**
```
web: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 30 --workers 1 --log-level info
```

#### **ロールバック手順:**

```bash
# 1. 該当コミットにrevert
git revert <commit-hash>
git push

# 2. または特定ファイルのみrevert
git checkout <previous-commit> -- Dockerfile render.yaml Procfile app.py
git commit -m "Rollback SRE changes"
git push

# 3. Render Dashboard で Manual Deploy
```

---

## 📊 継続的な改善（Phase 3: 中長期）

### **H. 長時間処理の完全非同期化**

**現状:**
- `/upload` は即時応答 ✅
- バックグラウンドスレッドで処理 ✅
- ただし、同一プロセス内 ⚠️

**推奨:**
- **RQ (Redis Queue)** または **Celery** に移行
- Webワーカーとジョブワーカーを完全分離
- メモリ使用量を最適化

**実装例（RQ）:**

```python
# app.py
from rq import Queue
from redis import Redis

redis_conn = Redis.from_url(os.getenv('REDIS_URL'))
queue = Queue(connection=redis_conn)

@app.route('/upload', methods=['POST'])
def upload_file():
    # ... validation ...
    
    job = queue.enqueue(
        'automation.process_jobcan_automation',
        job_id, email, password, file_path, jobs, session_dir, session_id, company_id,
        timeout='10m'
    )
    
    return jsonify({'job_id': job.id})
```

**メリット:**
- Webワーカーのメモリ使用量削減（-400MB）
- スケーラビリティ向上
- ジョブリトライ機能

**デメリット:**
- Redis依存追加（Render Add-onで$10-20/月）
- 実装コスト

---

### **I. サーキットブレーカ実装**

外部依存（Jobcan）への接続失敗時の保護:

```python
from pybreaker import CircuitBreaker

jobcan_breaker = CircuitBreaker(
    fail_max=5,           # 5回連続失敗でopen
    timeout_duration=60,  # 60秒後に half-open へ
)

@jobcan_breaker
def login_to_jobcan(email, password):
    # ... 既存のログイン処理 ...
```

---

### **J. Playwright メモリ最適化**

```python
# browser起動オプション最適化
browser = playwright.chromium.launch(
    headless=True,
    args=[
        '--disable-dev-shm-usage',      # 共有メモリ使用削減
        '--no-sandbox',                 # Renderで必要
        '--disable-setuid-sandbox',
        '--disable-gpu',                # GPU不要
        '--disable-software-rasterizer',
        '--disable-extensions',
        '--disable-background-networking',
        '--single-process',             # メモリ削減（多少遅い）
    ]
)
```

---

## 📚 関連ドキュメント

- [Render Health Checks](https://render.com/docs/health-checks)
- [Gunicorn Settings](https://docs.gunicorn.org/en/stable/settings.html)
- [Flask Performance](https://flask.palletsprojects.com/en/3.0.x/deploying/)

---

## ✅ Definition of Done（検収基準）

- [x] `/healthz` が <50ms で安定 200
- [x] ログに `req_start/req_end` が記録される
- [x] `X-Request-ID` ヘッダが付与される
- [ ] 10分間の連続アクセスで 5xx = 0（デプロイ後確認）
- [ ] Renderヘルスチェックが連続失敗しない（デプロイ後確認）
- [ ] メモリ使用率 < 85%（デプロイ後確認）
- [ ] バックグラウンドジョブの duration ログが出力される（デプロイ後確認）

---

## 🚀 デプロイ手順

### **1. ローカルテスト**

```bash
# 起動
python app.py

# 別ターミナルで
curl http://localhost:5000/healthz
# 期待: "ok"

curl http://localhost:5000/health
# 期待: JSON with dependencies
```

### **2. Git コミット**

```bash
git add app.py Dockerfile render.yaml Procfile SRE_RUNBOOK.md
git commit -m "SRE: Add observability + optimize Gunicorn for 503 prevention

- Add /healthz, /livez, /readyz endpoints (<10ms)
- Add request logging with X-Request-ID
- Add background job duration tracking
- Optimize Gunicorn: workers=2, timeout=180, max-requests=500
- Update render.yaml: healthCheckPath=/healthz
- Add comprehensive SRE runbook

Root cause: OOM (512MB) + worker timeout (30s)
Fix: More workers + longer timeout + memory monitoring"

git push
```

### **3. デプロイ監視**

```bash
# Renderログをリアルタイム監視
# Dashboard → Logs → Follow

# 確認ポイント:
# - "Booting worker" が2回表示される（workers=2）
# - エラーなく起動完了
# - "req_start/req_end" ログが出力される
```

### **4. デプロイ後検証**

```bash
# ヘルスチェック
curl https://jobcan-automation.onrender.com/healthz
# → "ok"

# 詳細ヘルス
curl https://jobcan-automation.onrender.com/health
# → JSON with resources

# レスポンスタイム計測（10回）
for i in {1..10}; do
  curl -o /dev/null -s -w "%{time_total}s\n" https://jobcan-automation.onrender.com/healthz
done
```

---

## 📞 エスカレーション

### **問題が解決しない場合:**

1. **Renderサポートに連絡**
   - support@render.com
   - ログとメトリクスを添付

2. **一時的な対策:**
   - Manual Deploy で強制再起動
   - WEB_CONCURRENCY を 1 に削減（メモリ節約）
   - plan を starter に変更（$7/月）

3. **移行検討:**
   - Fly.io（スリープなし、メモリ柔軟）
   - Railway（$5クレジット付き）

---

**作成者**: SRE Team  
**バージョン**: 1.0  
**次回レビュー**: 2025-11-10

