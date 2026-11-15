import time
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from openpyxl import Workbook
import automation
from lib import jobcan_attendance
from app import app, jobs, jobs_lock


def workbook():
    wb = Workbook()
    wb.active.append(['日付', '開始時刻', '終了時刻'])
    wb.active.append(['2026-11-02', '09:00', '18:00'])
    wb.active.append(['2026-11-03', '22:00', '02:00'])
    return wb


def test_row_failure_preserves_confirmed_start_and_stops_next_date(monkeypatch):
    page = Mock()
    page.goto.return_value = SimpleNamespace(status=200)
    submit = Mock(side_effect=['registered', jobcan_attendance.AttendanceInputError('未確認')])
    monkeypatch.setattr(jobcan_attendance, 'punch_once', submit)
    job = {'status':'running', 'start_time':time.time()}
    with pytest.raises(jobcan_attendance.AttendanceInputError, match='確認済み 0/2件'):
        automation.perform_actual_data_input(page, workbook(), 2, False, 'test', {'test':job})
    assert page.goto.call_count == 1
    assert submit.call_count == 2
    assert job['confirmed_rows'] == 0
    assert job['row_results'][0] == {
        'date':'2026-11-02', 'start':'registered', 'end':'pending', 'status':'needs_review',
    }


def test_confirmed_rows_include_existing_times_and_overnight(monkeypatch):
    page = Mock()
    page.goto.return_value = SimpleNamespace(status=200)
    submit = Mock(side_effect=['existing', 'registered', 'registered', 'registered'])
    monkeypatch.setattr(jobcan_attendance, 'punch_once', submit)
    job = {'status':'running', 'start_time':time.time()}
    assert automation.perform_actual_data_input(page, workbook(), 2, False, 'test', {'test':job}) == 2
    assert [c.args[1] for c in submit.call_args_list] == ['0900', '1800', '2200', '2600']
    assert all(row['status'] == 'confirmed' for row in job['row_results'])
    assert all(c.kwargs['wait_until'] == 'domcontentloaded' for c in page.goto.call_args_list)


def test_timeout_stops_before_any_mutation(monkeypatch):
    page = Mock()
    submit = Mock()
    monkeypatch.setattr(jobcan_attendance, 'punch_once', submit)
    job = {'status':'running', 'start_time':time.time()-100}
    with pytest.raises(jobcan_attendance.AttendanceInputError):
        automation.perform_actual_data_input(page, workbook(), 2, False, 'test', {'test':job}, 60)
    assert job['status'] == 'timeout'
    page.goto.assert_not_called()
    submit.assert_not_called()


def test_status_returns_actual_partial_results():
    job_id = 'offline-partial-regression'
    with jobs_lock:
        jobs[job_id] = {'status':'error', 'start_time':time.time(), 'end_time':time.time(),
                       'confirmed_rows':1, 'total_data':2, 'logs':[],
                       'login_message':'2日目の結果を確認してください',
                       'row_results':[{'date':'2026-11-02','status':'confirmed'}]}
    try:
        response = app.test_client().get('/status/'+job_id)
        assert response.status_code == 500
        data = response.get_json()
        assert data['status'] == 'error' and data['confirmed_rows'] == 1
        assert data['row_results'][0]['status'] == 'confirmed'
        assert '2日目' in data['user_message']
    finally:
        with jobs_lock:
            jobs.pop(job_id, None)
