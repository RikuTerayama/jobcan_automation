# Jobcan input recovery and editorial redesign — 2026-11-15

## Evidence and scope

User symptom: login succeeds, but attendance entry stops partway through.
Baseline: origin/main 45de711 (PR #110). The public /healthz response reported
x-deploy-commit 45de711b9b05 during investigation. An initial public fetch returned
503 and a subsequent health request returned 200; this does not identify its cause.
No authenticated Jobcan session or Render event/memory logs were available.
The changes address demonstrated code defects; the exact production incident
cause remains unconfirmed.

## Defects addressed

- Attendance submission mixed button clicks with networkidle waiting inside a
  selector retry loop. A successful click followed by a wait timeout could trigger
  a second click. Failures could then be skipped and the whole task marked complete.
- Completion now requires a visible correction-table time after a single submit.
  Existing matching times are skipped. Unknown outcomes stop the batch without
  another click; the partial start/end result and confirmed-day count are retained.
- pandas and openpyxl use the same submission loop. Existing time normalization
  and overnight conversion are retained. Default job timeout is 30 minutes, checked
  before each day and punch. Login failure is an error, not completion.
- Browser resources close before leaving Playwright's live transport context.
- One failed status fetch previously stopped the browser's monitoring. Status reads
  now retry with backoff, keep submission locked, restore the job ID on reload,
  display server explanations, and handle cancellation racing with job start.
  Only the opaque job ID is stored in sessionStorage; credentials are not stored.
- Gunicorn request-count recycling could kill daemon threads performing attendance.
  Docker now forces one gthread worker and disables max-requests recycling.
  In-memory job state must not be split across multiple workers.
- Browser QA found duplicate top-level PDF error constants causing script load
  SyntaxErrors. The compress and image-extract constants now have distinct names.

## Design

Warm ivory, ink and muted green; serif headlines, thin borders and generous space.
The home and AutoFill pages have been rebuilt, with shared navigation and theme
across the retained pages. The visual paper composition uses CSS, not remote images.
Existing routes, advertising configuration and affiliate configuration are preserved.
Home/FAQ sitemap mapping now points to the templates actually displayed.

## Validation

- python -m pytest tests -q -p no:cacheprovider: 22 passed.
- scripts/verify_recovery_browser.py: intercepted, offline Chrome tests; no real
  Jobcan credentials or submissions. Covers pending network requests, existing
  times, 26:00, unknown outcomes with exactly one click, ambiguous fields,
  unsupported tables, full-page POST navigation, status 503 recovery, reload/404,
  cancellation/start race and password clearing.
- Desktop 1440px and mobile 390px screenshots for ten retained public pages;
  horizontal overflow and one-H1 checks, JavaScript page-error capture.
- scripts/smoke_test.py --deploy: passed.
- scripts/smoke_test.py --jobcan-guardrails and scripts/predeploy.py: passed.
- Queue guardrail smoke fixture updated to an actual workbook: the former fake
  file was rejected by the existing Excel signature check before reaching the queue.
- Historical scripts/verify_phase1.py: two existing copy assertions still fail
  (the About operator section and Contact fallback text). Those templates and the
  script are identical to origin/main. Contact also still contains the pre-existing
  example form URL; this work does not invent a replacement contact destination.
- Local browser environment: Windows Python 3.14, Playwright 1.65.2, installed
  Chrome 157. Production remains Python 3.11 / pinned Playwright 1.40; no production
  dependency changes. The browser harness also supports JOBCAN_TEST_CHANNEL.

## Deployment and remaining verification

- Publish through the existing main/Render Docker path. A dashboard start-command
  override must not restore multiple workers or max-requests recycling.
- Keep MAX_ACTIVE_SESSIONS=1 on the existing small instance. A pre-existing explicit
  JOB_TIMEOUT_SEC environment value overrides the new 1800-second default.
- Do not deploy while a real input is running: deployments still replace the process.
- This remains an in-memory queue. Platform restarts, deployments and OOM can still
  interrupt work and lose job status. Disabling periodic recycling does not create
  durable execution, and the paid plan has not been changed.
- The correction reader expects /employee/adit/modify, a visible table headed 時刻
  or 打刻時刻, one 打刻 button, and an unambiguous input. Official documentation
  supports this visible layout, but its authenticated DOM has not been verified.
  Unsupported layouts stop before sending. A confirmed time is a recorded entry,
  not proof of manager approval or a verified punch direction.
- After deployment, verify one authorized day with the user's own account, compare
  the two times in Jobcan, then process the remaining days. If it stops, retain the
  date/result message and sanitized final log lines; inspect Render restart/OOM
  events at the same time. Do not replay a whole workbook without checking entries.
- No claim of restored authenticated end-to-end production operation is made until
  that verification succeeds.

## Primary references

- Playwright page readiness and discouraged networkidle:
  https://playwright.dev/python/docs/api/class-page
- Gunicorn max_requests / max_requests_jitter (0 disables request-count restarts):
  https://gunicorn.org/reference/settings/
- Render free-service restart, spin-down and ephemeral-storage limitations:
  https://render.com/docs/free
- Jobcan official attendance manuals:
  https://id.jobcan.jp/manuals?key=manual_am

