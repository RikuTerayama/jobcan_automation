/* The browser only retries status reads; attendance submissions are never replayed. */
(() => {
    'use strict';
    const $ = id => document.getElementById(id);
    const storageKey = 'jobcan.active-job.v1';
    let jobId = null, active = false, timer = null, failures = 0;
    const terminal = new Set(['completed', 'failed', 'error', 'cancelled', 'expired', 'timeout']);
    function remember(value) {
        try { value ? sessionStorage.setItem(storageKey, value) : sessionStorage.removeItem(storageKey); } catch (_) {}
    }
    function status(title, message, logs) {
        $('statusPanel').classList.add('is-visible');
        $('statusTitle').textContent = title;
        $('statusMessage').textContent = message || '';
        if (Array.isArray(logs)) $('progressLog').textContent = logs.join('\n');
    }
    function finish() {
        active = false;
        clearTimeout(timer);
        remember(null);
        $('submitBtn').disabled = false;
        $('cancelQueuedBtn').hidden = true;
    }
    function showRows(rows) {
        $('rowResults').replaceChildren();
        for (const row of rows || []) {
            const item = document.createElement('li');
            const label = value => ({registered:'登録確認済み', existing:'登録済み', pending:'未確認'}[value] || '未確認');
            item.textContent = row.date + ' — 開始: ' + label(row.start) + ' / 終了: ' + label(row.end);
            item.dataset.state = row.status;
            $('rowResults').appendChild(item);
        }
    }
    function schedule(delay = 5000) {
        clearTimeout(timer);
        if (active && jobId) timer = setTimeout(poll, delay);
    }
    async function poll() {
        if (!active || !jobId) return;
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 20000);
        try {
            const response = await fetch('/status/' + encodeURIComponent(jobId) + '?last_n=80', {signal: controller.signal, cache:'no-store'});
            if (response.status === 404) {
                finish();
                status('処理状況を確認できません', 'サーバー再起動などで処理情報が失われた可能性があります。Jobcanの登録内容を確認し、未入力の日付だけを再実行してください。');
                return;
            }
            const data = await response.json();
            if (!data.status || (!response.ok && !terminal.has(data.status))) throw new Error('status unavailable');
            failures = 0;
            showRows(data.row_results);
            const logs = data.logs || data.progress_log || [];
            const message = data.user_message || data.login_message || data.message || '';
            const count = Number(data.confirmed_rows || 0);
            const total = Number(data.total_data || 0);
            $('progressCount').textContent = total ? count + ' / ' + total + ' 日の登録を確認済み' : 'Jobcanへの接続を確認しています';
            $('jobProgress').max = total || 1;
            $('jobProgress').value = count;
            $('cancelQueuedBtn').hidden = data.status !== 'queued';
            if (terminal.has(data.status)) {
                finish();
                status(data.status === 'completed' ? '入力が完了しました' : '登録内容を確認してください',
                    message || 'Jobcan側の登録内容を確認してください。', logs);
                $('retryBtn').hidden = data.status === 'completed';
                return;
            }
            if (data.status === 'queued') {
                status('順番待ちです', 'あなたの順番: ' + (data.queue_position || '確認中') + '。このタブを開いたままお待ちください。', logs);
            } else {
                status('入力を進めています', data.step_name || message, logs);
            }
            schedule();
        } catch (_) {
            failures += 1;
            status('接続を確認しています', '通信が一時的に途切れました。サーバー上の処理は継続している可能性があります。入力を再送信せず、状態の確認を続けます。');
            schedule(Math.min(30000, 5000 * failures));
        } finally { clearTimeout(timeout); }
    }
    $('uploadForm').addEventListener('submit', async event => {
        event.preventDefault();
        if (active) return;
        active = true; // Lock before the first await.
        $('submitBtn').disabled = true;
        $('retryBtn').hidden = true;
        $('cancelQueuedBtn').hidden = true;
        $('progressCount').textContent = '';
        $('jobProgress').value = 0;
        showRows([]);
        status('送信しています', 'Excelファイルと入力内容を確認しています。', []);
        const body = new FormData(event.currentTarget);
        try {
            const response = await fetch('/upload', {method:'POST', body});
            const data = await response.json();
            if (!response.ok || data.error) {
                if (response.status >= 500 && data.error_code !== 'QUEUE_FULL' && data.status_code !== 503) throw new Error('unknown submission result');
                finish();
                status('受付できませんでした', data.error || '入力内容を確認してください。');
                return;
            }
            if (!data.job_id) throw new Error('missing job id');
            jobId = data.job_id;
            remember(jobId);
            $('password').value = '';
            status('受付しました', '処理状況を確認しています。');
            schedule(0);
        } catch (_) {
            // A lost upload response does not establish that the server rejected it.
            status('受付結果を確認できません', '送信後に通信が中断されました。重複入力を避けるため、Jobcanの登録内容を確認してからページを再読み込みしてください。');
        }
    });
    $('cancelQueuedBtn').addEventListener('click', async () => {
        if (!jobId) return;
        $('cancelQueuedBtn').disabled = true;
        try {
            const response = await fetch('/cancel/' + encodeURIComponent(jobId), {method:'POST'});
            const data = await response.json();
            if (response.ok && data.status === 'cancelled') {
                finish();
                status('順番待ちをキャンセルしました', '入力内容を確認して再実行できます。');
            } else {
                status('処理状況を再確認します', data.error || '処理が開始された可能性があります。');
                schedule(0);
            }
        } catch (_) { status('キャンセル結果を確認中', '処理状況を再確認しています。'); schedule(0); }
        finally { $('cancelQueuedBtn').disabled = false; }
    });
    $('retryBtn').addEventListener('click', () => {
        $('file').value = '';
        $('retryBtn').hidden = true;
        status('未入力の日付だけを準備してください', 'Jobcanの登録内容を確認し、未入力の日付だけを残したExcelを選択してください。');
        $('file').focus();
    });
    try { jobId = sessionStorage.getItem(storageKey); } catch (_) {}
    if (jobId) {
        active = true;
        $('submitBtn').disabled = true;
        status('処理状況を復元しています', '前回受け付けた処理を確認しています。');
        schedule(0);
    }
})();

