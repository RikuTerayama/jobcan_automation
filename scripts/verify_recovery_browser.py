"""Offline browser regression: fake Jobcan pages and intercepted local HTML only.

Run: python scripts/verify_recovery_browser.py
Requires Playwright and installed Chrome (JOBCAN_TEST_CHANNEL overrides channel).
No real Jobcan login or attendance submission is performed.
"""
import json
import os
import sys
import logging
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from playwright.sync_api import sync_playwright
from lib.jobcan_attendance import AttendanceInputError, punch_once
from app import app
logging.disable(logging.CRITICAL)

FIXTURE = """<!doctype html><html lang="ja"><head><meta charset="utf-8"></head><body>
<table><tr><th>打刻区分</th><th>時刻</th><th>打刻方法</th></tr><tbody id="records"></tbody></table>
<form onsubmit="event.preventDefault(); window.clicks++; if (!window.fail) setTimeout(() => {
 const row=document.createElement('tr'); const v=document.getElementById('time').value.replace(':','');
 row.innerHTML='<td>出退勤</td><td>'+v.slice(0,-2)+':'+v.slice(-2)+'</td><td>修正申請</td>';
 document.getElementById('records').append(row); document.getElementById('time').value='';
}, 80);">
<label for="time">時刻</label><input id="time" type="text"><button type="submit">打刻</button>
</form><script>window.clicks=0;window.fail=false;fetch('/long-poll');</script></body></html>"""
JOB_URL = 'https://ssl.jobcan.jp/employee/adit/modify?year=2026&month=11&day=2'

def main():
    checks = []
    output = ROOT / '.diagnostics'
    output.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=os.getenv('JOBCAN_TEST_CHANNEL', 'chrome'), headless=True)
        context = browser.new_context()
        page = context.new_page()
        # All Jobcan requests are intercepted; keep an outstanding request to
        # reproduce why networkidle is the wrong readiness condition.
        page.route('**/*', lambda route: route.fulfill(body=FIXTURE, content_type='text/html') if '/adit/modify' in route.request.url else None)
        page.goto(JOB_URL, wait_until='domcontentloaded')
        assert punch_once(page, '0900', lambda: None) == 'registered'
        assert punch_once(page, '0900', lambda: None) == 'existing'
        assert page.evaluate('window.clicks') == 1
        assert punch_once(page, '2600', lambda: None) == 'registered'
        assert page.evaluate('window.clicks') == 2
        checks.append('pending network request does not stall; existing time is not resubmitted; 26:00 confirmed')
        page.evaluate('window.fail=true')
        try:
            punch_once(page, '1800', lambda: None, confirmation_timeout=300)
            raise AssertionError('unconfirmed click must stop')
        except AttendanceInputError:
            assert page.evaluate('window.clicks') == 3
        checks.append('unconfirmed submission stops after exactly one click')
        page.evaluate("document.querySelector('label').remove(); document.querySelector('form').insertAdjacentHTML('afterbegin','<input type=text>')")
        try:
            punch_once(page, '1900', lambda: None, confirmation_timeout=300)
            raise AssertionError('ambiguous fields must stop')
        except AttendanceInputError:
            assert page.evaluate('window.clicks') == 3
        checks.append('ambiguous fields stop without mutation')
        page.evaluate("document.querySelector('table').remove()")
        try:
            punch_once(page, '2000', lambda: None, confirmation_timeout=300)
            raise AssertionError('missing table must stop')
        except AttendanceInputError:
            assert page.evaluate('window.clicks') == 3
        checks.append('unsupported correction layout stops without mutation')
        # Legacy correction forms can navigate after submitting, rather than use AJAX.
        page.unroute('**/*')
        navigation_submits = []
        def correction_navigation(route):
            if route.request.method == 'POST':
                navigation_submits.append(route.request.post_data)
                body = '<table><tr><th>時刻</th></tr><tr><td>09:00</td></tr></table>'
            else:
                body = '<table><tr><th>時刻</th></tr></table><form method="post"><label for="t">時刻</label><input type="text" id="t" name="time"><button>打刻</button></form>'
            route.fulfill(body=body, content_type='text/html; charset=utf-8')
        page.route('**/*', correction_navigation)
        page.goto(JOB_URL, wait_until='domcontentloaded')
        assert punch_once(page, '0900', lambda: None) == 'registered'
        assert navigation_submits == ['time=0900']
        checks.append('full-page POST navigation confirms the result after one submission')
        context.close()

        app.config['TESTING'] = True
        client = app.test_client()
        context = browser.new_context(viewport={'width':1440, 'height':1000}, device_scale_factor=1)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        status_reads = [0]
        uploads = [0]
        state = {'mode':'recover'}
        def serve(route):
            path = urlparse(route.request.url).path
            if not route.request.url.startswith('http://jobcan.test'):
                route.abort()
                return
            if path == '/upload':
                uploads[0] += 1
                route.fulfill(json={'job_id':'offline-test', 'status':'running'})
            elif path.startswith('/status/'):
                status_reads[0] += 1
                if state['mode'] == 'recover' and status_reads[0] == 1:
                    route.fulfill(status=503, content_type='text/html', body='unavailable')
                elif state['mode'] == 'missing':
                    route.fulfill(status=404, json={'error':'missing'})
                elif state['mode'] == 'queued':
                    route.fulfill(json={'status':'queued', 'queue_position':1})
                elif state['mode'] == 'running':
                    route.fulfill(json={'status':'running', 'step_name':'登録を確認中', 'total_data':2, 'confirmed_rows':1})
                else:
                    route.fulfill(json={'status':'completed','user_message':'確認済み 1件','logs':[], 'total_data':1, 'confirmed_rows':1,
                        'row_results':[{'date':'2026-11-02','start':'registered','end':'registered','status':'confirmed'}]})
            elif path.startswith('/cancel/'):
                state['mode'] = 'running'
                route.fulfill(status=409, json={'status':'running','error':'入力を開始しました'})
            else:
                resp = client.get(path)
                route.fulfill(status=resp.status_code, content_type=resp.content_type, body=resp.data)
        page.route('**/*', serve)
        for width, tag in [(1440,'desktop'), (390,'mobile')]:
            page.set_viewport_size({'width':width, 'height':1000 if width==1440 else 844})
            for path, name in [('/','home'),('/autofill','autofill'),('/tools/pdf','pdf'),('/faq','faq'),('/about','about'),('/tools','tools'),('/recommend','recommend'),('/privacy','privacy'),('/terms','terms'),('/contact','contact')]:
                page.goto('http://jobcan.test'+path, wait_until='load')
                page.screenshot(path=str(output / f'{name}-{tag}.png'), full_page=True)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), (path, tag, 'horizontal overflow')
                assert page.locator('h1').count() == 1, path
        checks.append('ten public pages: desktop/mobile layout, no horizontal overflow, one H1')
        page.set_viewport_size({'width':1200,'height':1000})
        page.goto('http://jobcan.test/autofill')
        page.locator('#file').set_input_files({'name':'test.xlsx','mimeType':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','buffer':b'fixture'})
        page.locator('#email').fill('offline@example.com')
        page.locator('#password').fill('not-a-real-password')
        page.locator('#submitBtn').click()
        page.get_by_text('接続を確認しています', exact=True).wait_for()
        assert page.locator('#submitBtn').is_disabled()
        page.get_by_text('入力が完了しました', exact=True).wait_for(timeout=12000)
        assert uploads[0] == 1 and status_reads[0] == 2
        assert page.locator('#password').input_value() == ''
        assert page.locator('#jobProgress').get_attribute('value') == '1'
        checks.append('503 status recovers automatically without another upload; password cleared')
        state['mode'] = 'missing'
        page.evaluate("sessionStorage.setItem('jobcan.active-job.v1','offline-test')")
        page.reload()
        page.get_by_text('処理状況を確認できません', exact=True).wait_for()
        assert '未入力の日付だけ' in page.locator('#statusMessage').inner_text()
        assert uploads[0] == 1
        checks.append('reload resumes monitoring; missing job instructs verification, not blind replay')
        state['mode'] = 'queued'
        page.evaluate("sessionStorage.setItem('jobcan.active-job.v1','offline-test')")
        page.reload()
        page.get_by_text('順番待ちです', exact=True).wait_for()
        page.locator('#cancelQueuedBtn').click()
        page.get_by_text('入力を進めています', exact=True).wait_for()
        assert page.locator('#submitBtn').is_disabled()
        checks.append('cancel/start race (409) keeps monitoring and submission lock')
        assert not errors, errors
        context.close()
        browser.close()
    print(json.dumps({'passed':checks, 'screenshots':str(output)}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
