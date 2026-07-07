# RT Tools - 讌ｭ蜍吝柑邇・喧繝・・繝ｫ髮・

## Amazon Creators API Affiliate Stack

Affiliate layout order across public pages is:
1. Amazon (upper)
2. Rakuten (mid)
3. A8.net (lower)

### Render environment variables

- `AMAZON_CREATORS_CLIENT_ID`
- `AMAZON_CREATORS_CLIENT_SECRET`
- `AMAZON_ASSOCIATE_TAG` (example: `jobcanauto-22`)
- `AMAZON_AFFILIATE_ENABLED` (`true` / `false`)
- `AMAZON_CACHE_TTL_SECONDS` (default: `3300`)
- `AMAZON_MAX_ITEMS` (default: `6`)
- `AMAZON_THEME_ROTATION_CADENCE` (`daily` / `weekly` / `biweekly`, default: `daily`)
- `AMAZON_THEME_ROTATION_TZ` (default: `Asia/Tokyo`)
- `AFFILIATE_STACK_ONLY` (default: `true`)

### Lightweight Render free-plan settings

This simplified site can run on Render Free for low traffic, but keep the
runtime conservative because Jobcan AutoFill still uses Chrome/Playwright.

Required/important production environment variables:

- `AMAZON_ASSOCIATE_TAG`: required for Amazon Associates revenue attribution.
  If this is unset, Amazon search links still render but are not monetized.
- `MAX_ACTIVE_SESSIONS=1`: recommended for Render Free memory limits.
- `MAX_QUEUE_SIZE=3`: recommended upper bound for the in-memory waiting queue.
- `WEB_CONCURRENCY=1` and `WEB_THREADS=1`: recommended to avoid Chrome memory
  pressure on the free plan.
- `MAX_FILE_SIZE_MB=10`: keeps Jobcan Excel uploads small enough for the free instance.
- `PDF_LOCK_MAX_FILE_SIZE_MB=20`: rejects oversized server-side PDF password-lock requests before processing.
- `ADSENSE_ENABLED=true`: only if AdSense is intentionally enabled in
  production.

Operational notes for Render Free:

- The service may spin down after roughly 15 minutes without traffic, so the
  first request can be slow.
- The filesystem is ephemeral. Uploaded files and generated templates must be
  treated as temporary, not durable storage.
- The AutoFill waiting queue is in-memory. A restart, deploy, crash, or free
  plan spin-down clears queued/running state.
- AutoFill is intentionally limited to one active session by default. Additional
  users should retry later or wait in the short queue.
- When the short queue is full, `/upload` returns `503` with
  `error_code=QUEUE_FULL`, `retry_after_sec`, and queue limit metadata instead
  of starting another Chrome/Playwright run.
- The AutoFill UI keeps the submit button disabled while a job is running or
  queued, polls `/status/<job_id>` at a conservative interval, and sends a
  best-effort detach signal when the tab closes.
- After changing `AMAZON_ASSOCIATE_TAG` or other Render env vars, trigger a
  restart/redeploy so worker processes read the new values.

### Operational notes

- Amazon credentials are used server-side only. Secrets are never exposed to client-side JavaScript.
- Recommendation inputs use page path, page type, product tags/categories, and recent on-site browsing history from a first-party cookie.
- Amazon destination URLs are generated from approved `query` / `query_variants` only (page titles/headings are never used as search query text).
- Amazon `tag` is always injected from runtime `AMAZON_ASSOCIATE_TAG` (existing stale `tag=` in upstream URLs is overwritten).
- Upper/Mid Amazon cards are selected from an approved theme pool (`lib/amazon_affiliate_map.py` -> `AMAZON_THEME_POOL`) using deterministic rotation.
- Only `enabled: true` themes are eligible for production. Keep new AI-proposed themes as `enabled: false` until manual approval.
- Rotation is stable per cadence bucket (`daily` / `weekly` / `biweekly`) and does not flicker per request.
- Theme display copy (`title`, `category_label`) and destination query (`query`, `query_variants`) are managed separately.
- If Amazon API auth is incomplete, API returns an error, or no items are returned, the page still renders and theme-based Amazon links remain available.
- Affiliate placement is intentionally distributed: Amazon (upper area), Rakuten (mid section), A8.net (bottom area). Do not collapse all three into one footer-only block.
- The A8.net bottom text link (`A8.net 縺ｮ縺翫☆縺吶ａ繧定ｦ九ｋ`) is intentionally removed; only the A8 rotation banner remains.
- After deploy, verify `/`, `/autofill`, `/tools`, `/tools/pdf`, `/recommend`, `/faq`, `/privacy`, `/terms`, and `/contact`.

### Theme refresh workflow (recommended)

1. ChatGPT proposes 6 candidate themes (purpose/pain/workstyle based).
2. Human reviewer enables 3-6 approved themes in `AMAZON_THEME_POOL`.
3. Production rotates only approved entries by cadence.

### Render deploy-branch checklist (important)

- Confirm the Render Web Service deploy branch matches the branch that contains affiliate changes.
- If production is still old while this repository branch is updated, check Render Dashboard:
  1. `Settings -> Build & Deploy -> Branch`
  2. `Auto-Deploy` status
  3. Manual deploy of latest commit if needed
- If Render is tracking `main` while changes are only on `feature/add-csv-excel-utility`, production will not reflect those changes until merge/cherry-pick to `main` (or changing Render deploy branch).
- After changing Render environment variables (including `AMAZON_ASSOCIATE_TAG`), trigger a service restart/redeploy so worker processes load the new value.

### Production verification checklist

After merging or manually deploying the latest branch, verify:

- `/` shows the simplified Jobcan/PDF choice as the primary entry point.
- `/autofill` starts with template download and file upload guidance before credentials and execution.
- `/tools/pdf` starts with the PDF operation chooser and does not expose unlock/decrypt UI.
- `/tools/csv` redirects to `/tools`.
- `/api/pdf/lock` remains enabled and `/api/pdf/unlock` remains `404`.
- `/sitemap.xml` includes `/tools/pdf` and does not include `/tools/csv`.
- `/recommend` and the footer keep the Amazon Associates disclosure.
- `/healthz` returns quickly during and after deploy.

If production still shows the old UI, check that the PR was merged into the Render deploy branch, Auto Deploy is enabled or a manual deploy was triggered, the deployed commit SHA matches the GitHub branch, and the service was restarted after environment variable changes.

Jobcan閾ｪ蜍募・蜉帙→蜷・ｨｮ讌ｭ蜍吝柑邇・喧繝・・繝ｫ繧呈署萓帙☆繧妓eb繧｢繝励Μ繧ｱ繝ｼ繧ｷ繝ｧ繝ｳ縺ｧ縺吶・

## 噫 讖溯・讎りｦ・

### Jobcan AutoFill
- **Excel繝・Φ繝励Ξ繝ｼ繝医ム繧ｦ繝ｳ繝ｭ繝ｼ繝・*: 蜍､諤繝・・繧ｿ蜈･蜉帷畑縺ｮ繝・Φ繝励Ξ繝ｼ繝医ヵ繧｡繧､繝ｫ繧偵ム繧ｦ繝ｳ繝ｭ繝ｼ繝・
- **閾ｪ蜍輔ョ繝ｼ繧ｿ蜈･蜉・*: Excel繝輔ぃ繧､繝ｫ縺ｮ繝・・繧ｿ縺ｫ蝓ｺ縺･縺・※Jobcan縺ｫ蜍､諤繝・・繧ｿ繧定・蜍募・蜉・
- **繝ｪ繧｢繝ｫ繧ｿ繧､繝騾ｲ謐苓｡ｨ遉ｺ**: 蜃ｦ逅・・騾ｲ謐礼憾豕√ｒ繝ｪ繧｢繝ｫ繧ｿ繧､繝縺ｧ陦ｨ遉ｺ

### 逕ｻ蜒丈ｸ諡ｬ螟画鋤 (v2)
- 隍・焚繧ｵ繧､繧ｺ蜷梧凾蜃ｺ蜉帙√・繝ｪ繧ｻ繝・ヨ縲∝刀雉ｪ隱ｿ謨ｴ縲√Μ繝阪・繝

### PDF繝ｦ繝ｼ繝・ぅ繝ｪ繝・ぅ (v2)
- 邨仙粋繝ｻ蛻・牡繝ｻ謚ｽ蜃ｺ縲￣DF竊堤判蜒丞､画鋤縲∝悸邵ｮ縲∫判蜒鞘・PDF螟画鋤

### 逕ｻ蜒上Θ繝ｼ繝・ぅ繝ｪ繝・ぅ (v2)
- 騾城℃竊堤區閭梧勹螟画鋤縲∽ｽ咏區繝医Μ繝縲∫ｸｦ讓ｪ豈皮ｵｱ荳縲∬レ譎ｯ髯､蜴ｻ

### 隴ｰ莠矩鹸謨ｴ蠖｢ (v2)
- 豎ｺ螳壻ｺ矩・ToDo謚ｽ蜃ｺ縲∵悄髯先ｭ｣隕丞喧縲，SV/JSON蜃ｺ蜉・

### Web/SEO繝ｦ繝ｼ繝・ぅ繝ｪ繝・ぅ (v2)
- OGP逕ｻ蜒冗函謌舌￣ageSpeed繝√ぉ繝・け繝ｪ繧ｹ繝医√Γ繧ｿ繧ｿ繧ｰ讀懈渊縲《itemap.xml/robots.txt逕滓・

## 白 繝・・繧ｿ菫晄戟譁ｹ驥・

**蜃ｦ逅・婿蠑上・讖溯・縺ｫ繧医ｊ逡ｰ縺ｪ繧翫∪縺吶・*
- **逕ｻ蜒・PDF/CSV/SEO 遲峨・繝・・繝ｫ**: 繝悶Λ繧ｦ繧ｶ蜀・〒蜃ｦ逅・ゅヵ繧｡繧､繝ｫ縺ｯ繧ｵ繝ｼ繝舌・縺ｫ騾∽ｿ｡縺輔ｌ縺ｾ縺帙ｓ
- **Jobcan AutoFill**: 繧ｵ繝ｼ繝舌・蛛ｴ縺ｧ荳譎ょ女鬆倥＠縺ｦ蜃ｦ逅・＠縲∝・逅・ｾ後↓蜑企勁縺励∪縺吶らｶ咏ｶ壻ｿ晏ｭ倥・縺励∪縺帙ｓ

## 投 UI逶｣譟ｻ繝ｬ繝昴・繝育函謌・

Gemini縺ｫUI謾ｹ蝟・ｒ萓晞ｼ縺吶ｋ縺溘ａ縺ｮ迴ｾ迥ｶ逅・ｧ｣繝ｬ繝昴・繝医ｒ閾ｪ蜍慕函謌舌〒縺阪∪縺吶・

### 螳溯｡梧婿豕・

```bash
npm install  # 蛻晏屓縺ｮ縺ｿ・・ypeScript, ts-node縺ｮ繧､繝ｳ繧ｹ繝医・繝ｫ・・
npm run audit:ui
```

### 蜃ｺ蜉・

`docs/ui-audit/current-ui-report.md` 縺ｫ繝ｬ繝昴・繝医′逕滓・縺輔ｌ縺ｾ縺吶・

縺薙・繝ｬ繝昴・繝医↓縺ｯ莉･荳九′蜷ｫ縺ｾ繧後∪縺呻ｼ・
- 蜈ｨ繝壹・繧ｸ縺ｮUI讒矩蛻・梵
- 蜈ｱ騾壹さ繝ｳ繝昴・繝阪Φ繝医→繧ｹ繧ｿ繧､繝ｫ繝代ち繝ｼ繝ｳ
- 謾ｹ蝟・ｽ吝慍縺ｨ螟画峩繝ｪ繧ｹ繧ｯ
- Gemini蜷代￠縺ｮ繝励Ο繝ｳ繝励ヨ譯・

繝ｬ繝昴・繝医ｒGemini縺ｫ雋ｼ繧贋ｻ倥￠繧九％縺ｨ縺ｧ縲∝・菴鍋噪縺ｪUI謾ｹ蝟・署譯医ｒ蠕励ｋ縺薙→縺後〒縺阪∪縺吶・

## 塘 繧ｳ繝ｳ繝・Φ繝・Ξ繝昴・繝育函謌撰ｼ郁ｨ倅ｺ狗畑邏譚撰ｼ・

AdSense 繧呈э隴倥＠縺溯ｨ倅ｺ倶ｽ懈・逕ｨ縺ｮ縲檎ｴ譚舌Ξ繝昴・繝医阪ｒ閾ｪ蜍慕函謌舌〒縺阪∪縺吶ょ推繧ｵ繝ｼ繝薙せ縺ｮ讎りｦ√・菴ｿ縺・婿繝ｻFAQ繝ｻSEO 邏譚舌↑縺ｩ縺ｮ遶遶九※繧呈純縺医◆ Markdown 縺・`docs/content-reports/` 縺ｫ蜃ｺ蜉帙＆繧後∪縺吶ょｾ檎ｶ壹〒 ChatGPT 繧・Cursor 縺ｧ險倅ｺ句喧縺吶ｋ蜑肴署縺ｮ繝・Φ繝励Ξ縺ｧ縺吶・

### 螳溯｡梧婿豕・

```bash
npm run report:content
```

### 蜃ｺ蜉・

- `docs/content-reports/00_master_overview.md` 窶ｦ 繧ｵ繝ｼ繝薙せ荳隕ｧ繝ｻ諠・ｱ險ｭ險医・繝・Φ繝励Ξ讒区・
- `docs/content-reports/01_<繧ｵ繝ｼ繝薙せID>.md` 窶ｦ 蜷・し繝ｼ繝薙せ縺斐→縺ｮ繝ｬ繝昴・繝茨ｼ・utofill, image-batch, pdf, image-cleanup, minutes, seo・・
- `docs/content-reports/99_adsense_readiness_checklist.md` 窶ｦ 蠢・医・繝ｼ繧ｸ繝ｻ繧ｳ繝ｳ繝・Φ繝・刀雉ｪ繝ｻ1險倅ｺ九≠縺溘ｊ縺ｮ逶ｮ螳・

逕滓・蠕後∝推 md 繧帝幕縺・※ TODO 繧貞沂繧√◆繧翫∬ｨ倅ｺ狗畑繝励Ο繝ｳ繝励ヨ縺ｫ豬√＠霎ｼ繧薙〒蛻ｩ逕ｨ縺励※縺上□縺輔＞縲・

## 盗 IA繝ｬ繝昴・繝育函謌撰ｼ・uide / Resources 迴ｾ迥ｶ逶｣譟ｻ・・

Guide 縺ｨ Resource 蜻ｨ繧翫・諠・ｱ險ｭ險医ｒ險ｼ諡莉倥″縺ｧ譽壼査縺励＠縲∵紛蛯呵ｨ育判繧堤ｫ九※繧九◆繧√・縲檎樟迥ｶ逅・ｧ｣繝ｬ繝昴・繝医阪ｒ閾ｪ蜍慕函謌舌〒縺阪∪縺吶ゅΝ繝ｼ繝亥ｮ夂ｾｩ・・pp.py・峨→繝・Φ繝励Ξ繝ｼ繝磯・鄂ｮ繝ｻ蜀・Κ繝ｪ繝ｳ繧ｯ繧定ｵｰ譟ｻ縺励・譛ｬ縺ｮ Markdown 縺ｫ縺ｾ縺ｨ繧√∪縺吶・

### 螳溯｡梧婿豕・

```bash
npm run report:ia
```

### 蜃ｺ蜉・

- `docs/ia-reports/guide-resources-audit.md` 窶ｦ Guide/Resources 縺ｮ迴ｾ迥ｶ譽壼査縺励∝ｮ夐㍼・医・繝ｼ繧ｸ謨ｰ繝ｻ髫主ｱ､繝ｻURL竊斐ヵ繧｡繧､繝ｫ・峨・㍾隍・蛻・妙/谺關ｽ縲∬ｨｭ險域｡・譯茨ｼ・/B/C・峨∵紛蛯儺oDo縲√お繝薙ョ繝ｳ繧ｹ

謾ｹ菫ｮ縺ｯ陦後＞縺ｾ縺帙ｓ縲ゅΞ繝昴・繝医・縺ｿ逕滓・縺励∪縺吶・

## 搭 讖溯・繧ｮ繝｣繝・・繝ｻ蜆ｪ蜈磯・ｽ阪Ξ繝昴・繝育函謌・

霑ｽ蜉讖溯・蛟呵｣懊Μ繧ｹ繝医↓蟇ｾ縺吶ｋ迴ｾ迥ｶ縺ｮ螳溯｣・き繝舌Ξ繝・ず繧定ｨｼ諡莉倥″縺ｧ譽壼査縺励＠縲∵ｬ｡縺ｫ霑ｽ蜉縺吶∋縺肴ｩ溯・縺ｮ蜆ｪ蜈磯・ｽ阪ｒ謠先｡医☆繧九Ξ繝昴・繝医ｒ逕滓・縺ｧ縺阪∪縺吶・

### 螳溯｡梧婿豕・

```bash
npm run report:feature-gap
```

### 蜃ｺ蜉・

- `docs/feature-reports/feature-gap-prioritization.md` 窶ｦ 迴ｾ迥ｶ繝・・繝ｫ荳隕ｧ縲∝呵｣・0讖溯・縺ｨ縺ｮ蟇ｾ蠢懆｡ｨ・域里縺ｫ縺ゅｋ/荳驛ｨ縺ゅｋ/縺ｪ縺・ｼ峨√ぐ繝｣繝・・隧ｳ邏ｰ縲√せ繧ｳ繧｢陦ｨ縺ｨ荳贋ｽ肴署譯医∝ｮ溯｣・婿蠑上・謗ｨ螂ｨ縲√ぎ繧､繝芽ｨ倅ｺ九・蠅励∴譁ｹ

繝ｪ繝昴ず繝医Μ縺ｮ `app.py`繝ｻ`lib/products_catalog.py`繝ｻ`templates/tools/*.html`繝ｻ`static/js/*.js` 繧定ｵｰ譟ｻ縺励※繝ｬ繝昴・繝医ｒ逕滓・縺励∪縺吶よｩ溯・縺ｮ螳溯｣・・陦後＞縺ｾ縺帙ｓ縲・

## 投 繧ｹ繝・・繧ｿ繧ｹ繝ｬ繝昴・繝茨ｼ医・繝ｭ繝繧ｯ繝医・UI繝ｻ讖溯・逶｣譟ｻ・・

迴ｾ譎らせ縺ｮ繝励Ο繝繧ｯ繝育憾諷九ｒ縲，hatGPT 繧・隼蝟・Ο繝ｼ繝峨・繝・・逕ｨ縺ｫ1譛ｬ縺ｮ繝ｬ繝昴・繝医↓縺ｾ縺ｨ繧√◆逶｣譟ｻ縺ｧ縺吶ゅけ繧ｪ繝ｪ繝・ぅ隧穂ｾ｡繝ｻUI謾ｹ蝟・婿驥昴・霑ｽ蜉謗ｨ螂ｨ繧ｵ繝ｼ繝薙せ縺ｮ萓晞ｼ縺ｫ菴ｿ縺医∪縺吶・

### 螳溯｡梧婿豕・

```bash
npm run report:status
```

### 蜃ｺ蜉・

- 讓呎ｺ門・蜉帙↓繝ｫ繝ｼ繝井ｸ隕ｧ繝ｻ陬ｽ蜩！D縺ｮ邁｡譏笛SON繧定｡ｨ遉ｺ縺励√ヵ繝ｫ繝ｬ繝昴・繝医・繝代せ繧呈｡亥・縺励∪縺吶・
- 繝輔Ν逶｣譟ｻ縺ｯ謇句虚繝｡繝ｳ繝・・ `docs/status-reports/2026-02-06_product_ui_and_feature_audit.md` 繧貞盾辣ｧ縺励※縺上□縺輔＞・医・繝ｼ繧ｸ譽壼査縺励ゞI/UX謗｡轤ｹ縲ヾEO/AdSense縲∝ｮ溯｣・婿蠑上∬ｿｽ蜉謗ｨ螂ｨ繧ｵ繝ｼ繝薙せ縲，hatGPT逕ｨ隕∫ｴ・ヶ繝ｭ繝・け繧貞性繧・峨・

## 刀 繝励Ο繧ｸ繧ｧ繧ｯ繝域ｧ矩

```
jobcan_automation-main/
笏懌楳笏 app.py              # 繝｡繧､繝ｳ縺ｮFlask繧｢繝励Μ繧ｱ繝ｼ繧ｷ繝ｧ繝ｳ
笏懌楳笏 utils.py            # 繝ｦ繝ｼ繝・ぅ繝ｪ繝・ぅ髢｢謨ｰ・・xcel蜃ｦ逅・√Ο繧ｰ讖溯・・・
笏懌楳笏 automation.py       # 閾ｪ蜍募喧蜃ｦ逅・Ο繧ｸ繝・け
笏懌楳笏 requirements.txt    # Python萓晏ｭ倬未菫・
笏懌楳笏 Dockerfile         # Docker險ｭ螳・
笏懌楳笏 render.yaml        # Render險ｭ螳・
笏懌楳笏 templates/
笏・  笏披楳笏 index.html     # Web繧､繝ｳ繧ｿ繝ｼ繝輔ぉ繝ｼ繧ｹ
笏披楳笏 uploads/           # 繧｢繝・・繝ｭ繝ｼ繝峨ヵ繧｡繧､繝ｫ菫晏ｭ倥ョ繧｣繝ｬ繧ｯ繝医Μ
```

## 屏・・謚陦薙せ繧ｿ繝・け

- **Backend**: Flask (Python)
- **Browser Automation**: Playwright
- **Excel Processing**: pandas / openpyxl
- **Deployment**: Render (Docker)
- **WSGI Server**: Gunicorn

## 肌 繧ｻ繝・ヨ繧｢繝・・

### 繝ｭ繝ｼ繧ｫ繝ｫ髢狗匱

1. **繝ｪ繝昴ず繝医Μ繧偵け繝ｭ繝ｼ繝ｳ**
   ```bash
   git clone https://github.com/your-username/jobcan_automation.git
   cd jobcan_automation
   ```

2. **萓晏ｭ倬未菫ゅｒ繧､繝ｳ繧ｹ繝医・繝ｫ**
   ```bash
   pip install -r requirements.txt
   ```

3. **Playwright繝悶Λ繧ｦ繧ｶ繧偵う繝ｳ繧ｹ繝医・繝ｫ**
   ```bash
   playwright install chromium
   ```

4. **繧｢繝励Μ繧ｱ繝ｼ繧ｷ繝ｧ繝ｳ繧定ｵｷ蜍・*
   ```bash
   python app.py
   ```

### Render 繝・・繝ｭ繧､

1. **GitHub繝ｪ繝昴ず繝医Μ繧坦ender縺ｫ謗･邯・*
   - Render縺ｧ譁ｰ縺励＞Web Service繧剃ｽ懈・
   - GitHub繝ｪ繝昴ず繝医Μ繧帝∈謚・
   - 迺ｰ蠅・､画焚繧定ｨｭ螳夲ｼ亥ｿ・ｦ√↓蠢懊§縺ｦ・・

2. **Start Command縺ｮ險ｭ螳・*
   - Render縺ｮWeb Service險ｭ螳壹〒縲郡tart Command縲阪ｒ莉･荳九↓險ｭ螳夲ｼ・
   ```bash
   gunicorn app:app
   ```

3. **閾ｪ蜍輔ョ繝励Ο繧､**
   - 繝励ャ繧ｷ繝･譎ゅ↓閾ｪ蜍慕噪縺ｫ繝・・繝ｭ繧､縺輔ｌ縺ｾ縺・
   - 讒区枚繝√ぉ繝・け縺隈itHub Actions縺ｧ螳溯｡後＆繧後∪縺・

### 驥崎ｦ√↑萓晏ｭ倬未菫・

- **gunicorn**: WSGI HTTP繧ｵ繝ｼ繝舌・・域悽逡ｪ迺ｰ蠅・畑・・
- **Flask**: Web繝輔Ξ繝ｼ繝繝ｯ繝ｼ繧ｯ
- **Playwright**: 繝悶Λ繧ｦ繧ｶ閾ｪ蜍募喧
- **openpyxl**: Excel繝輔ぃ繧､繝ｫ蜃ｦ逅・
- **psutil**: 繧ｷ繧ｹ繝・Β繝ｪ繧ｽ繝ｼ繧ｹ逶｣隕・

## 搭 菴ｿ逕ｨ譁ｹ豕・

1. **繝・Φ繝励Ξ繝ｼ繝医ヵ繧｡繧､繝ｫ繧偵ム繧ｦ繝ｳ繝ｭ繝ｼ繝・*
   - 縲後ユ繝ｳ繝励Ξ繝ｼ繝医ヵ繧｡繧､繝ｫ繧偵ム繧ｦ繝ｳ繝ｭ繝ｼ繝峨阪・繧ｿ繝ｳ繧偵け繝ｪ繝・け
   - Excel繝輔ぃ繧､繝ｫ縺後ム繧ｦ繝ｳ繝ｭ繝ｼ繝峨＆繧後∪縺・

2. **蜍､諤繝・・繧ｿ繧貞・蜉・*
   - 繝繧ｦ繝ｳ繝ｭ繝ｼ繝峨＠縺檸xcel繝輔ぃ繧､繝ｫ縺ｫ蜍､諤繝・・繧ｿ繧貞・蜉・
   - 譌･莉倥・幕蟋区凾蛻ｻ縲∫ｵゆｺ・凾蛻ｻ繧定ｨ伜・

3. **繝輔ぃ繧､繝ｫ繧偵い繝・・繝ｭ繝ｼ繝・*
   - 繝｡繝ｼ繝ｫ繧｢繝峨Ξ繧ｹ縺ｨ繝代せ繝ｯ繝ｼ繝峨ｒ蜈･蜉・
   - Excel繝輔ぃ繧､繝ｫ繧偵い繝・・繝ｭ繝ｼ繝・
   - 縲悟共諤繝・・繧ｿ繧定・蜍募・蜉帙阪・繧ｿ繝ｳ繧偵け繝ｪ繝・け

4. **騾ｲ謐励ｒ遒ｺ隱・*
   - 繝ｪ繧｢繝ｫ繧ｿ繧､繝縺ｧ蜃ｦ逅・・騾ｲ謐励ｒ遒ｺ隱・
   - 隧ｳ邏ｰ縺ｪ繝ｭ繧ｰ縺ｧ蜷・せ繝・ャ繝励・迥ｶ豕√ｒ謚頑升

## 剥 繝医Λ繝悶Ν繧ｷ繝･繝ｼ繝・ぅ繝ｳ繧ｰ

### 繧医￥縺ゅｋ蝠城｡・

1. **讒区枚繧ｨ繝ｩ繝ｼ**
   - GitHub Actions縺ｧ閾ｪ蜍慕噪縺ｫ讒区枚繝√ぉ繝・け縺悟ｮ溯｡後＆繧後∪縺・
   - 繝ｭ繝ｼ繧ｫ繝ｫ縺ｧ `python -m py_compile app.py` 繧貞ｮ溯｡後＠縺ｦ遒ｺ隱・

2. **Playwright繧ｨ繝ｩ繝ｼ**
   - Render迺ｰ蠅・〒縺ｯ蛻ｶ髯舌′縺ゅｋ蝣ｴ蜷医′縺ゅｊ縺ｾ縺・
   - 繝ｭ繝ｼ繧ｫ繝ｫ迺ｰ蠅・〒縺ｮ螳溯｡後ｒ謗ｨ螂ｨ

3. **Excel繝輔ぃ繧､繝ｫ繧ｨ繝ｩ繝ｼ**
   - 繝輔ぃ繧､繝ｫ蠖｢蠑上′.xlsx縺ｾ縺溘・.xls縺ｧ縺ゅｋ縺薙→繧堤｢ｺ隱・
   - 繝倥ャ繝繝ｼ陦後′豁｣縺励￥險ｭ螳壹＆繧後※縺・ｋ縺薙→繧堤｢ｺ隱・

### 繝ｭ繧ｰ縺ｮ遒ｺ隱・

- 繧｢繝励Μ繧ｱ繝ｼ繧ｷ繝ｧ繝ｳ縺ｮ繝ｭ繧ｰ縺ｧ隧ｳ邏ｰ縺ｪ繧ｨ繝ｩ繝ｼ諠・ｱ繧堤｢ｺ隱・
- 蜷・せ繝・ャ繝励・騾ｲ謐礼憾豕√ｒ繝ｪ繧｢繝ｫ繧ｿ繧､繝縺ｧ陦ｨ遉ｺ

## 噫 繝・・繝ｭ繧､

### 繝・・繝ｭ繧､蜑阪メ繧ｧ繝・け・亥ｿ・茨ｼ・

sitemap 縺ｮ lastmod 繝槭ル繝輔ぉ繧ｹ繝医・縲・*繝・Φ繝励Ξ繝ｼ繝亥､画峩譎ゅ↓謇句・縺ｧ蜀咲函謌舌＠縺ｦ繧ｳ繝溘ャ繝医☆繧・*蠢・ｦ√′縺ゅｊ縺ｾ縺吶ら函謌仙ｿ倥ｌ縺後≠繧九→ CI 縺悟､ｱ謨励＠縺ｾ縺吶・

1. **繝槭ル繝輔ぉ繧ｹ繝医ｒ逕滓・**・医ユ繝ｳ繝励Ξ繝ｼ繝亥､画峩蠕鯉ｼ・
   ```bash
   python scripts/generate_sitemap_lastmod_manifest.py --write
   ```
2. **繝・・繝ｭ繧､蜑阪Ρ繝ｳ繧ｳ繝槭Φ繝・*・・anifest 魄ｮ蠎ｦ + preflight・・
   ```bash
   python scripts/predeploy.py
   ```
3. **萓句､・*: Docker 繝薙Ν繝臥腸蠅・↓ `.git` 縺ｯ辟｡縺・◆繧√∵悽逡ｪ繝薙Ν繝我ｸｭ縺ｮ閾ｪ蜍慕函謌舌・陦後＞縺ｾ縺帙ｓ縲ょｿ・★謇句・縺ｧ `--write` 繧貞ｮ溯｡後＠縲～data/sitemap_lastmod.json` 繧偵さ繝溘ャ繝医＠縺ｦ縺九ｉ繝・・繝ｭ繧､縺励※縺上□縺輔＞縲・

### Render 縺ｧ縺ｮ繝・・繝ｭ繧､

1. **render.yaml** 繝輔ぃ繧､繝ｫ縺瑚ｨｭ螳壽ｸ医∩
2. **Dockerfile** 縺ｧ繧ｳ繝ｳ繝・リ蛹・
3. **requirements.txt** 縺ｧ萓晏ｭ倬未菫らｮ｡逅・

### Render縺ｮ繧ｹ繝ｪ繝ｼ繝怜ｯｾ遲厄ｼ磯㍾隕・ｼ・

**Render縺ｮ辟｡譁吶・繝ｩ繝ｳ縺ｯ15蛻・俣繧｢繧ｯ繧ｻ繧ｹ縺後↑縺・→繧ｹ繝ｪ繝ｼ繝励＠縺ｾ縺吶・* Google AdSense蟇ｩ譟ｻ縺ｧ縲後し繧､繝医′蛻ｩ逕ｨ荳榊庄縲阪→蛻､螳壹＆繧後↑縺・ｈ縺・∽ｻ･荳九・蟇ｾ遲悶ｒ螳滓命縺励※縺上□縺輔＞縲・

#### **謗ｨ螂ｨ・啅ptimeRobot縺ｧ逶｣隕厄ｼ育┌譁呻ｼ・*

1. **UptimeRobot 縺ｫ逋ｻ骭ｲ**: https://uptimerobot.com/
2. **繝｢繝九ち繝ｼ繧定ｿｽ蜉**:
   - Monitor Type: `HTTP(s)`
   - URL: `https://<your-domain>/ping`
   - Monitoring Interval: `5 minutes`
3. **蜉ｹ譫・*: 5蛻・＃縺ｨ縺ｫ繧｢繧ｯ繧ｻ繧ｹ縺励※繧ｵ繝ｼ繝舌・繧定ｵｷ蜍慕憾諷九↓菫昴■縺ｾ縺・

縺薙ｌ縺ｫ繧医ｊ縲；oogle繧ｯ繝ｭ繝ｼ繝ｩ繝ｼ縺後い繧ｯ繧ｻ繧ｹ縺励◆髫帙ｂ蜊ｳ蠎ｧ縺ｫ蠢懃ｭ斐〒縺阪∪縺吶・

### 迺ｰ蠅・､画焚

蠢・ｦ√↓蠢懊§縺ｦ莉･荳九・迺ｰ蠅・､画焚繧定ｨｭ螳夲ｼ・

- `PORT`: 繧｢繝励Μ繧ｱ繝ｼ繧ｷ繝ｧ繝ｳ縺ｮ繝昴・繝育分蜿ｷ
- `SECRET_KEY`: Flask縺ｮ繧ｷ繝ｼ繧ｯ繝ｬ繝・ヨ繧ｭ繝ｼ
- `ADSENSE_ENABLED`: Google AdSense譛牙柑蛹悶ヵ繝ｩ繧ｰ・域悽逡ｪ迺ｰ蠅・・縺ｿ `true` 縺ｫ險ｭ螳夲ｼ・
  - 繝・ヵ繧ｩ繝ｫ繝・ `false`・磯幕逋ｺ迺ｰ蠅・ｼ・
  - 譛ｬ逡ｪ迺ｰ蠅・ `true` 縺ｫ險ｭ螳壹☆繧九％縺ｨ縺ｧAdSense繧ｹ繧ｯ繝ｪ繝励ヨ縺瑚ｪｭ縺ｿ霎ｼ縺ｾ繧後∪縺・
- `MAX_ACTIVE_SESSIONS`: Jobcan AutoFill 縺ｮ蜷梧凾螳溯｡梧焚・・ender 512MB 縺ｧ縺ｯ 1 謗ｨ螂ｨ・・
- `QUEUED_MAX_WAIT_SEC`: 蠕・ｩ溘く繝･繝ｼ蜀・ず繝ｧ繝悶・譛螟ｧ蠕・ｩ溽ｧ呈焚・域里螳・1800・・0蛻・ｼ峨りｶ・℃縺ｧ timeout 謇ｱ縺・
- `MAX_QUEUE_SIZE`: 蠕・ｩ溘く繝･繝ｼ縺ｮ譛螟ｧ髟ｷ・域里螳・5・峨りｶ・℃譎ゅ・ 503 QUEUE_FULL

## 投 繝｢繝九ち繝ｪ繝ｳ繧ｰ

- **繝倥Ν繧ｹ繝√ぉ繝・け**: `/health` 繧ｨ繝ｳ繝峨・繧､繝ｳ繝・
- **貅門ｙ迥ｶ諷・*: `/ready` 繧ｨ繝ｳ繝峨・繧､繝ｳ繝・
- **萓晏ｭ倬未菫・*: pandas, openpyxl, playwright縺ｮ蛻ｩ逕ｨ蜿ｯ閭ｽ諤ｧ繧堤｢ｺ隱・

## 塘 繧ｳ繝ｳ繝・Φ繝・・繝ｼ繧ｸ

譛ｬ繧ｵ繝ｼ繝薙せ縺ｫ縺ｯ縲∝・螳溘＠縺溘さ繝ｳ繝・Φ繝・・繝ｼ繧ｸ縺檎畑諢上＆繧後※縺・∪縺呻ｼ・

### 豕慕噪諠・ｱ
- **繝励Λ繧､繝舌す繝ｼ繝昴Μ繧ｷ繝ｼ** (`/privacy`): 蛟倶ｺｺ諠・ｱ縺ｮ蜿悶ｊ謇ｱ縺・↓髢｢縺吶ｋ譁ｹ驥・
- **蛻ｩ逕ｨ隕冗ｴ・* (`/terms`): 繧ｵ繝ｼ繝薙せ蛻ｩ逕ｨ縺ｫ髢｢縺吶ｋ隕冗ｴ・
- **縺雁撫縺・粋繧上○** (`/contact`): 繧ｵ繝昴・繝育ｪ灘哨

### 繧ｬ繧､繝・
- **縺ｯ縺倥ａ縺ｦ縺ｮ菴ｿ縺・婿** (`/guide/getting-started`): 蛻昴ａ縺ｦ縺ｮ譁ｹ蜷代￠縺ｮ隧ｳ邏ｰ繧ｬ繧､繝・
- **Excel繝輔ぃ繧､繝ｫ縺ｮ菴懈・譁ｹ豕・* (`/guide/excel-format`): 繝輔ぃ繧､繝ｫ蠖｢蠑上・隧ｳ邏ｰ隱ｬ譏・
- **繝医Λ繝悶Ν繧ｷ繝･繝ｼ繝・ぅ繝ｳ繧ｰ** (`/guide/troubleshooting`): 繧医￥縺ゅｋ繧ｨ繝ｩ繝ｼ縺ｨ隗｣豎ｺ譁ｹ豕・

### 繝ｪ繧ｽ繝ｼ繧ｹ
- **繧医￥縺ゅｋ雉ｪ蝠擾ｼ・AQ・・* (`/faq`): 25莉･荳翫・Q&A
- **逕ｨ隱樣寔** (`/glossary`): 蜍､諤邂｡逅・・Jobcan逕ｨ隱槭・隗｣隱ｬ
- **繧ｵ繧､繝医↓縺､縺・※** (`/about`): 繧ｵ繝ｼ繝薙せ讎りｦ√→謚陦薙せ繧ｿ繝・け

**蜷郁ｨ・0繝壹・繧ｸ** - Google AdSense蟇ｩ譟ｻ縺ｫ蜊∝・縺ｪ繧ｳ繝ｳ繝・Φ繝・㍼縺ｧ縺吶・

## 討 Google AdSense 險ｭ螳・

### 讎りｦ・

縺薙・繧｢繝励Μ繧ｱ繝ｼ繧ｷ繝ｧ繝ｳ縺ｯ縲∵悽逡ｪ迺ｰ蠅・〒Google AdSense繧偵し繝昴・繝医＠縺ｦ縺・∪縺吶・

### 譛牙柑蛹匁婿豕・

1. **迺ｰ蠅・､画焚繧定ｨｭ螳・*
   ```bash
   # 譛ｬ逡ｪ迺ｰ蠅・〒莉･荳九ｒ險ｭ螳・
   ADSENSE_ENABLED=true
   ```

2. **繝・・繝ｭ繧､**
   - Render縺ｪ縺ｩ縺ｮ繝・・繝ｭ繧､迺ｰ蠅・〒迺ｰ蠅・､画焚 `ADSENSE_ENABLED=true` 繧定ｨｭ螳・
   - 髢狗匱迺ｰ蠅・〒縺ｯ譛ｪ險ｭ螳夲ｼ医∪縺溘・ `false`・峨・縺ｾ縺ｾ縺ｫ縺吶ｋ縺薙→繧呈耳螂ｨ

### AdSense Publisher ID

- **Publisher ID**: `ca-pub-4232725615106709`
- AdSense繧ｹ繧ｯ繝ｪ繝励ヨ縺ｯ `<head>` 蜀・↓1蝗槭・縺ｿ隱ｭ縺ｿ霎ｼ縺ｾ繧後∪縺・

### 髯､螟悶・繝ｼ繧ｸ

莉･荳九・繝壹・繧ｸ縺ｧ縺ｯ縲、dSense繧ｹ繧ｯ繝ｪ繝励ヨ縺ｯ隱ｭ縺ｿ霎ｼ縺ｾ繧後∪縺帙ｓ・・
- `/privacy` - 繝励Λ繧､繝舌す繝ｼ繝昴Μ繧ｷ繝ｼ繝壹・繧ｸ
- `/contact` - 縺雁撫縺・粋繧上○繝壹・繧ｸ
- `/thanks` - 繧ｵ繝ｳ繧ｯ繧ｹ繝壹・繧ｸ
- `/login` - 繝ｭ繧ｰ繧､繝ｳ繝壹・繧ｸ
- `/app/*` - 繧｢繝励Μ繧ｱ繝ｼ繧ｷ繝ｧ繝ｳ邂｡逅・・繝ｼ繧ｸ

**髯､螟悶・繝ｼ繧ｸ繧定ｿｽ蜉縺吶ｋ譁ｹ豕・**

`templates/index.html` (縺ｾ縺溘・莉悶・繝・Φ繝励Ξ繝ｼ繝・ 縺ｮ譚｡莉ｶ蠑上ｒ邱ｨ髮・ｼ・

```jinja2
{% if ADSENSE_ENABLED and not (request.path.startswith('/login') or request.path.startswith('/app/') or request.path in ['/privacy', '/contact', '/thanks', '/譁ｰ縺励＞繝代せ']) %}
```

### ads.txt 繝輔ぃ繧､繝ｫ

Google AdSense縺ｮ隱崎ｨｼ縺ｮ縺溘ａ縲～ads.txt` 繝輔ぃ繧､繝ｫ繧帝・菫｡縺励※縺・∪縺吶・

- **URL**: `https://<your-domain>/ads.txt`
- **蜀・ｮｹ**:
  ```
  google.com, pub-4232725615106709, DIRECT, f08c47fec0942fa0
  ```

**驟咲ｽｮ蝣ｴ謇**: `app.py` 縺ｮ `/ads.txt` 繝ｫ繝ｼ繝医〒閾ｪ蜍暮・菫｡

### 繝・・繝ｭ繧､蠕後・遒ｺ隱肴焔鬆・

1. **繝悶Λ繧ｦ繧ｶ縺ｧ繧ｵ繧､繝医↓繧｢繧ｯ繧ｻ繧ｹ**
   ```
   https://<your-domain>/
   ```

2. **繝壹・繧ｸ縺ｮ繧ｽ繝ｼ繧ｹ繧定｡ｨ遉ｺ**
   - 蜿ｳ繧ｯ繝ｪ繝・け 竊・縲後・繝ｼ繧ｸ縺ｮ繧ｽ繝ｼ繧ｹ繧定｡ｨ遉ｺ縲・
   - 縺ｾ縺溘・ `Ctrl+U` (Windows) / `Cmd+Option+U` (Mac)

3. **AdSense繧ｹ繧ｯ繝ｪ繝励ヨ縺ｮ遒ｺ隱・*
   - `<head>` 蜀・↓莉･荳九・繧ｹ繧ｯ繝ｪ繝励ヨ縺・*1蝗槭・縺ｿ**蟄伜惠縺吶ｋ縺薙→繧堤｢ｺ隱搾ｼ・
     ```html
     <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4232725615106709" crossorigin="anonymous"></script>
     ```

4. **ads.txt 縺ｮ遒ｺ隱・*
   ```
   https://<your-domain>/ads.txt
   ```
   荳願ｨ篭RL縺ｫ繧｢繧ｯ繧ｻ繧ｹ縺励∽ｻ･荳九・蜀・ｮｹ縺瑚｡ｨ遉ｺ縺輔ｌ繧九％縺ｨ繧堤｢ｺ隱搾ｼ・
   ```
   google.com, pub-4232725615106709, DIRECT, f08c47fec0942fa0
   ```

5. **髯､螟悶・繝ｼ繧ｸ縺ｮ遒ｺ隱・*
   - 髯､螟悶・繝ｼ繧ｸ・井ｾ・ `/privacy`, `/login` 縺ｪ縺ｩ・峨〒繧ｽ繝ｼ繧ｹ繧定｡ｨ遉ｺ
   - AdSense繧ｹ繧ｯ繝ｪ繝励ヨ縺悟性縺ｾ繧後※縺・↑縺・％縺ｨ繧堤｢ｺ隱・

### 繝医Λ繝悶Ν繧ｷ繝･繝ｼ繝・ぅ繝ｳ繧ｰ

- **繧ｹ繧ｯ繝ｪ繝励ヨ縺瑚｡ｨ遉ｺ縺輔ｌ縺ｪ縺・*: `ADSENSE_ENABLED=true` 縺瑚ｨｭ螳壹＆繧後※縺・ｋ縺狗｢ｺ隱・
- **繧ｹ繧ｯ繝ｪ繝励ヨ縺碁㍾隍・＠縺ｦ縺・ｋ**: 繝・Φ繝励Ξ繝ｼ繝医・邯呎価讒矩繧堤｢ｺ隱阪＠縲・㍾隍・ｒ蜑企勁
- **ads.txt 縺後い繧ｯ繧ｻ繧ｹ縺ｧ縺阪↑縺・*: `/ads.txt` 繝ｫ繝ｼ繝医′豁｣縺励￥險ｭ螳壹＆繧後※縺・ｋ縺狗｢ｺ隱・

## 白 繧ｻ繧ｭ繝･繝ｪ繝・ぅ

- 繧｢繝・・繝ｭ繝ｼ繝峨＆繧後◆繝輔ぃ繧､繝ｫ縺ｯ蜃ｦ逅・ｾ後↓閾ｪ蜍募炎髯､
- 荳譎ゅヵ繧｡繧､繝ｫ縺ｮ驕ｩ蛻・↑邂｡逅・
- 繧ｨ繝ｩ繝ｼ繝上Φ繝峨Μ繝ｳ繧ｰ縺ｮ螳溯｣・

## 圷 SRE繝ｻ驕狗畑逶｣隕・

### 讎りｦ・

譛ｬ逡ｪ迺ｰ蠅・・螳牙ｮ夂ｨｼ蜒阪・縺溘ａ縲∝桁諡ｬ逧・↑逶｣隕悶→繝ｭ繧ｰ讖溯・繧貞ｮ溯｣・＠縺ｦ縺・∪縺吶・

### 繝倥Ν繧ｹ繝√ぉ繝・け繧ｨ繝ｳ繝峨・繧､繝ｳ繝・

| 繧ｨ繝ｳ繝峨・繧､繝ｳ繝・| 逕ｨ騾・| 繝ｬ繧ｹ繝昴Φ繧ｹ繧ｿ繧､繝 | 謗ｨ螂ｨ逕ｨ騾・|
|--------------|------|-----------------|---------|
| `/healthz` | Render Health Check | <10ms | **譛ｬ逡ｪ逶｣隕・* |
| `/livez` | 繝励Ο繧ｻ繧ｹ逕溷ｭ倡｢ｺ隱・| <5ms | Kubernetes liveness |
| `/readyz` | 貅門ｙ螳御ｺ・｢ｺ隱・| <20ms | Kubernetes readiness |
| `/ping` | UptimeRobot逶｣隕・| 10-30ms | 螟夜Κ逶｣隕・|
| `/health` | 隧ｳ邏ｰ險ｺ譁ｭ | 100-300ms | 繝・ヰ繝・げ縺ｮ縺ｿ |

### 逶｣隕冶ｨｭ螳・

#### **Render Health Check**
```
Path: /healthz
Interval: 10遘・
Timeout: 3遘・
Retries: 3蝗・
```

#### **UptimeRobot**
```
URL: https://<your-domain>/healthz
Interval: 5蛻・
Alert: Uptime < 99%
```

### 繝ｭ繧ｰ縺ｨ繝医Ξ繝ｼ繧ｷ繝ｳ繧ｰ

縺吶∋縺ｦ縺ｮ繝ｪ繧ｯ繧ｨ繧ｹ繝医↓莉･荳九′險倬鹸縺輔ｌ縺ｾ縺呻ｼ・

```
2025-10-11 23:45:30 [INFO] req_start rid=a1b2c3d4 method=POST path=/upload
2025-10-11 23:45:32 [INFO] bg_job_start job_id=xxx session_id=yyy file_size=12345
2025-10-11 23:47:10 [INFO] bg_job_success job_id=xxx duration_sec=100.2
2025-10-11 23:47:10 [INFO] req_end rid=a1b2c3d4 status=200 ms=234.5
```

- `rid`: 繝ｪ繧ｯ繧ｨ繧ｹ繝・D・・-Request-ID繝倥ャ繝・・
- `duration_ms`: 繝ｬ繧ｹ繝昴Φ繧ｹ繧ｿ繧､繝
- `SLOW_REQUEST`: 5遘剃ｻ･荳翫・繝ｪ繧ｯ繧ｨ繧ｹ繝医ｒ隴ｦ蜻・

### 蜷梧凾蜃ｦ逅・・蜉・

**迴ｾ蝨ｨ縺ｮ險ｭ螳夲ｼ・ender free plan・・**

| 蜃ｦ逅・・遞ｮ鬘・| 蜷梧凾蜃ｦ逅・庄閭ｽ謨ｰ | 蛻ｶ髯千炊逕ｱ |
|-----------|---------------|---------|
| **蜍､諤繝・・繧ｿ繧｢繝・・繝ｭ繝ｼ繝・*・・laywright菴ｿ逕ｨ・・| **1-2莠ｺ** | 繝｡繝｢繝ｪ蛻ｶ髯撰ｼ・12MB・・|
| **繝壹・繧ｸ髢ｲ隕ｧ繝ｻ繝繧ｦ繝ｳ繝ｭ繝ｼ繝・*・郁ｻｽ縺・・逅・ｼ・| **4繝ｪ繧ｯ繧ｨ繧ｹ繝・* | workers ﾃ・threads |

**繝励Λ繝ｳ蛻･縺ｮ謗ｨ螂ｨ:**

| Render繝励Λ繝ｳ | RAM | 蜷梧凾繝ｦ繝ｼ繧ｶ繝ｼ謨ｰ | 譛磯｡・| 謗ｨ螂ｨ逕ｨ騾・|
|-------------|-----|--------------|------|---------|
| Free | 512MB | 1-2莠ｺ | $0 | 蛟倶ｺｺ蛻ｩ逕ｨ |
| Starter | 1GB+ | 3-4莠ｺ | $7 | 蟆剰ｦ乗ｨ｡繝√・繝 |
| Standard | 2GB+ | 6-8莠ｺ | $25 | 荳ｭ隕乗ｨ｡繝√・繝 |

**蛻ｶ髯舌・莉慕ｵ・∩:**
- **512MB・・ender free・峨〒縺ｯ `MAX_ACTIVE_SESSIONS=1` 繧呈耳螂ｨ**・・ender.yaml 縺ｧ險ｭ螳壽ｸ医∩縲３ENDER 迺ｰ蠅・〒縺ｯ譛ｪ險ｭ螳壽凾繧・default 1・・
- **隍・焚莠ｺ縺悟酔譎ゅ↓繧｢繝・・繝ｭ繝ｼ繝牙庄閭ｽ縲ょｮ溯｡後・逶ｴ蛻暦ｼ・莉ｶ縺壹▽・・*縲・莉ｶ逶ｮ莉･髯阪・ 503 縺ｧ蠑ｾ縺九★縲・*蠕・ｩ溘く繝･繝ｼ・医う繝ｳ繝｡繝｢繝ｪ FIFO・峨↓遨阪∩縲～job_id` 繧定ｿ斐☆**・・TTP 202 Accepted・峨る・分縺梧擂縺溘ｉ閾ｪ蜍輔〒髢句ｧ九・
- UI 縺ｯ縲悟ｾ・ｩ滉ｸｭ 竊・螳溯｡御ｸｭ 竊・螳御ｺ・螟ｱ謨励阪ｒ繝昴・繝ｪ繝ｳ繧ｰ縺ｧ陦ｨ遉ｺ縲・
- **/upload 縺ｧ 503 繧定ｿ斐☆縺ｮ縺ｯ谺｡縺ｮ縺ｿ**: (1) 繧ｭ繝･繝ｼ貅譚ｯ・・error_code: "QUEUE_FULL"`・峨・2) 繝｡繝｢繝ｪ繧ｬ繝ｼ繝芽ｶ・℃縲・*縲悟酔譎ょ・逅・焚荳企剞縲阪〒 503 縺ｯ霑斐＆縺壹∝ｿ・★ queued 縺ｧ job_id 繧定ｿ斐☆縲・*
- 蠕・ｩ溘く繝･繝ｼ縺ｯ繧､繝ｳ繝｡繝｢繝ｪ縺ｮ縺溘ａ **繧ｵ繝ｼ繝舌・蜀崎ｵｷ蜍輔〒繧ｭ繝･繝ｼ縺ｯ豸医∴繧・*縲ＡQUEUED_MAX_WAIT_SEC`・域里螳・1800・・0蛻・ｼ芽ｶ・℃縺ｧ蠕・ｩ溘ず繝ｧ繝悶・ timeout 謇ｱ縺・ＡMAX_QUEUE_SIZE`・域里螳・5・峨〒繧ｭ繝･繝ｼ髟ｷ荳企剞縲・

**AutoFill 繧ｭ繝･繝ｼ蛻ｩ逕ｨ荳翫・豕ｨ諢擾ｼ・I 縺ｨ蜷後ヨ繝ｼ繝ｳ・・**
- **繧ｿ繝悶ｒ髢峨§縺ｦ繧ゅく繝｣繝ｳ繧ｻ繝ｫ縺ｫ縺ｯ縺ｪ繧翫∪縺帙ｓ**縲るｲ謐苓｡ｨ遉ｺ縺ｯ豁｢縺ｾ繧翫∪縺吶′縲√し繝ｼ繝蝉ｸ翫・蜃ｦ逅・・邯壹￥蝣ｴ蜷医′縺ゅｊ縺ｾ縺吶よｭ｢繧√◆縺・ｴ蜷医・蠕・ｩ滉ｸｭ縺ｫ縲後く繝｣繝ｳ繧ｻ繝ｫ縲阪ｒ謚ｼ縺励※縺上□縺輔＞縲・
- **蠕・ｩ滉ｸｭ・・ueued・峨・繧ｭ繝｣繝ｳ繧ｻ繝ｫ蜿ｯ閭ｽ**縺ｧ縺呻ｼ・POST /cancel/<job_id>`・峨ょｮ溯｡御ｸｭ・・unning・峨・迴ｾ迥ｶ繧ｭ繝｣繝ｳ繧ｻ繝ｫ荳榊庄縺ｧ縺吶・
- 繧ｭ繝･繝ｼ縺ｯ繧､繝ｳ繝｡繝｢繝ｪ縺ｮ縺溘ａ **繧｢繝励Μ蜀崎ｵｷ蜍輔〒繧ｭ繝･繝ｼ縺ｯ豸医∴縺ｾ縺・*縲ょｾ・ｩ滉ｸｭ繧ｸ繝ｧ繝悶・蜀崎ｵｷ蜍募ｾ後・蠕ｩ蜈・＆繧後∪縺帙ｓ縲・

### Gunicorn 險ｭ螳・

譛驕ｩ蛹悶＆繧後◆Gunicorn險ｭ螳夲ｼ育腸蠅・､画焚縺ｧ繧ｫ繧ｹ繧ｿ繝槭う繧ｺ蜿ｯ閭ｽ・会ｼ・

```bash
workers: ${WEB_CONCURRENCY:-2}        # 繝・ヵ繧ｩ繝ｫ繝・
threads: ${WEB_THREADS:-2}            # 繝・ヵ繧ｩ繝ｫ繝・
timeout: ${WEB_TIMEOUT:-180}          # 繝・ヵ繧ｩ繝ｫ繝・80遘・
max-requests: 500                     # 繝｡繝｢繝ｪ繝ｪ繝ｼ繧ｯ蟇ｾ遲・
MAX_ACTIVE_SESSIONS: 1                # 512MB縺ｧ縺ｯ1謗ｨ螂ｨ縲・莉ｶ逶ｮ莉･髯阪・蠕・ｩ溘く繝･繝ｼ縺ｧ蜿嶺ｻ・
```

### 繝｡繝｢繝ｪ邂｡逅・

- **MEMORY_LIMIT_MB**: 450MB・・12MB縺ｮ88%・峨〒隴ｦ蜻・
- **max-requests**: 500繝ｪ繧ｯ繧ｨ繧ｹ繝医＃縺ｨ縺ｫ繝ｯ繝ｼ繧ｫ繝ｼ蜀崎ｵｷ蜍包ｼ医Γ繝｢繝ｪ繝ｪ繝ｼ繧ｯ蟇ｾ遲厄ｼ・
- **謗ｨ螂ｨ繝励Λ繝ｳ**: Render Starter・・GB RAM・峨〒OOM髦ｲ豁｢

### 503繧ｨ繝ｩ繝ｼ蟇ｾ遲・

**螳滓命貂医∩蟇ｾ遲・**
1. 繝倥Ν繧ｹ繝√ぉ繝・け繧定ｶ・ｻｽ驥丞喧・・10ms・・
2. workers=2縺ｧ蜷梧凾蜃ｦ逅・・蜉帛髄荳・
3. timeout=180s縺ｧ髟ｷ譎る俣蜃ｦ逅・↓蟇ｾ蠢・
4. 讒矩蛹悶Ο繧ｰ縺ｧ蝠城｡檎ｮ・園繧貞叉蠎ｧ縺ｫ迚ｹ螳・
5. 繝｡繝｢繝ｪ逶｣隕悶→隴ｦ蜻・

**隧ｳ邏ｰ:** `SRE_RUNBOOK.md` 繧貞盾辣ｧ

### 繝医Λ繝悶Ν繧ｷ繝･繝ｼ繝・ぅ繝ｳ繧ｰ

503繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺溷ｴ蜷茨ｼ・

1. **Render繝ｭ繧ｰ繧堤｢ｺ隱・*: `killed`, `OOM`, `timeout` 繧呈､懃ｴ｢
2. **繝｡繝｢繝ｪ菴ｿ逕ｨ邇・ｒ遒ｺ隱・*: 90%雜・∴縺ｪ繧峨・繝ｩ繝ｳ螟画峩
3. **SRE_RUNBOOK.md 繧貞盾辣ｧ**: 繧､繝ｳ繧ｷ繝・Φ繝亥ｯｾ蠢懈焔鬆・

## 統 繝ｩ繧､繧ｻ繝ｳ繧ｹ

縺薙・繝励Ο繧ｸ繧ｧ繧ｯ繝医・MIT繝ｩ繧､繧ｻ繝ｳ繧ｹ縺ｮ荳九〒蜈ｬ髢九＆繧後※縺・∪縺吶・

## ､・雋｢迪ｮ

1. 繝輔か繝ｼ繧ｯ繧剃ｽ懈・
2. 讖溯・繝悶Λ繝ｳ繝√ｒ菴懈・ (`git checkout -b feature/amazing-feature`)
3. 螟画峩繧偵さ繝溘ャ繝・(`git commit -m 'Add amazing feature'`)
4. 繝悶Λ繝ｳ繝√↓繝励ャ繧ｷ繝･ (`git push origin feature/amazing-feature`)
5. 繝励Ν繝ｪ繧ｯ繧ｨ繧ｹ繝医ｒ菴懈・

## 到 繧ｵ繝昴・繝・

蝠城｡後′逋ｺ逕溘＠縺溷ｴ蜷医・縲；itHub縺ｮIssues縺ｧ蝣ｱ蜻翫＠縺ｦ縺上□縺輔＞縲・
