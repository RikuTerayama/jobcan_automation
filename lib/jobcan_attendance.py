"""Confirmed, single-submission attendance entry for the Jobcan correction page.

Never retry a mutation when its outcome is unknown. Registration is confirmed
from the correction table's time column, including pending approval entries.
"""
import re
from urllib.parse import urlparse

READ_TIMES = r"""() => {
    const visible = el => !!(el.getClientRects().length);
    const times = [];
    let found = false;
    for (const table of document.querySelectorAll('table')) {
        if (!visible(table)) continue;
        const rows = Array.from(table.rows);
        const header = rows.find(row => Array.from(row.cells).some(
            cell => /^(打刻)?時刻$/.test(cell.innerText.trim().replace(/\s/g, ''))));
        if (!header) continue;
        const column = Array.from(header.cells).findIndex(
            cell => /^(打刻)?時刻$/.test(cell.innerText.trim().replace(/\s/g, '')));
        found = true;
        for (const row of rows.slice(rows.indexOf(header) + 1)) {
            if (!visible(row)) continue;
            const cell = row.cells[column];
            if (!cell) continue;
            const match = cell.innerText.trim().match(/^(\d{1,2}):(\d{2})(?::\d{2})?(?:\s|$)/);
            if (match) times.push(match[1].padStart(2, '0') + match[2]);
        }
    }
    return {found, times};
}"""

class AttendanceInputError(RuntimeError):
    """Safe-to-display failure without credentials, raw DOM or request bodies."""


def require_correction_page(page):
    url = urlparse(page.url)
    if url.hostname != 'ssl.jobcan.jp' or url.path.rstrip('/') != '/employee/adit/modify':
        raise AttendanceInputError('打刻修正画面を確認できません。ログイン状態と操作権限を確認してください。')


def recorded_times(page):
    require_correction_page(page)
    state = page.evaluate(READ_TIMES)
    if not state['found']:
        raise AttendanceInputError('打刻一覧の時刻列を確認できません。画面仕様または操作権限を確認してください。')
    return state['times']


def punch_once(page, value, check_active, confirmation_timeout=15000):
    """Return existing/registered, or stop on an ambiguous submission."""
    check_active()
    if value in recorded_times(page):
        return 'existing'

    button = page.get_by_role('button', name='打刻', exact=True)
    if button.count() != 1 or not button.is_visible() or not button.is_enabled():
        raise AttendanceInputError('操作可能な打刻ボタンを一意に特定できません。')

    # Prefer the labelled field. Legacy pages can omit labels; only accept an
    # unambiguous editable field in the punch form, never an arbitrary first input.
    field = page.get_by_label(re.compile(r'^(?:打刻)?時刻[：:]?$'))
    if field.count() != 1 or not field.is_visible():
        forms = button.locator('xpath=ancestor::form[1]')
        scope = forms if forms.count() == 1 else page
        field = scope.locator('input[type="text"]:visible:not([readonly]):not([disabled]), input[type="time"]:visible:not([readonly]):not([disabled])')
    if field.count() != 1:
        raise AttendanceInputError('時刻入力欄を一意に特定できません。打刻は送信していません。')
    entry = value if field.get_attribute('type') != 'time' else f'{value[:2]}:{value[2:]}'
    field.fill(entry, timeout=10000)
    if field.input_value(timeout=3000).replace(':', '') != value:
        raise AttendanceInputError('時刻入力の確認に失敗しました。打刻は送信していません。')
    check_active()
    try:
        # Exactly one click. In particular, a post-click timeout is not permission
        # to try a second selector and submit the same time again.
        button.click(timeout=10000, no_wait_after=True)
        page.wait_for_function(
            f"target => {{ const result = ({READ_TIMES})(); return result.found && result.times.includes(target); }}",
            arg=value, timeout=confirmation_timeout,
        )
        if value not in recorded_times(page):
            raise AttendanceInputError('送信後の時刻を確認できません。')
    except Exception as exc:
        raise AttendanceInputError(
            f'{value[:2]}:{value[2:]} の登録結果を確認できないため停止しました。'
            '再送信の前にJobcanの打刻一覧を確認してください。'
        ) from exc
    return 'registered'

