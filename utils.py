import os
import time
import uuid
from datetime import datetime

# pandasとopenpyxlの利用可能性をチェック
try:
    import pandas as pd
    pandas_available = True
except ImportError:
    pandas_available = False

try:
    import openpyxl
    from openpyxl import Workbook
    openpyxl_available = True
except ImportError:
    openpyxl_available = False

# Playwrightの利用可能性をチェック
try:
    from playwright.sync_api import sync_playwright
    playwright_available = True
except ImportError:
    playwright_available = False

def allowed_file(filename):
    """許可されたファイル形式かチェック"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls'}

def add_job_log(job_id: str, message: str, jobs: dict):
    """ジョブログを追加"""
    if job_id not in jobs:
        jobs[job_id] = {'logs': [], 'status': 'running', 'progress': 0, 'start_time': time.time()}
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    jobs[job_id]['logs'].append(log_entry)
    
    # ログが多すぎる場合は古いものを削除
    if len(jobs[job_id]['logs']) > 100:
        jobs[job_id]['logs'] = jobs[job_id]['logs'][-50:]

def update_progress(job_id: str, step: int, step_name: str, jobs: dict, current_data: int = 0, total_data: int = 0):
    """進捗を更新"""
    if job_id in jobs:
        jobs[job_id]['progress'] = step
        jobs[job_id]['step_name'] = step_name
        jobs[job_id]['current_data'] = current_data
        jobs[job_id]['total_data'] = total_data

def create_template_excel():
    """テンプレートExcelファイルを作成"""
    if pandas_available:
        # pandasを使用
        df = pd.DataFrame({
            '日付': ['2025/01/01', '2025/01/02', '2025/01/03'],
            '開始時刻': ['09:00', '09:00', '09:00'],
            '終了時刻': ['18:00', '18:00', '18:00']
        })
        
        # 一時ファイルに保存
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        df.to_excel(temp_file.name, index=False)
        return temp_file.name
    elif openpyxl_available:
        # openpyxlを使用
        wb = Workbook()
        ws = wb.active
        ws.title = "勤怠データ"
        
        # ヘッダーを追加
        ws['A1'] = '日付'
        ws['B1'] = '開始時刻'
        ws['C1'] = '終了時刻'
        
        # サンプルデータを追加
        sample_data = [
            ['2025/01/01', '09:00', '18:00'],
            ['2025/01/02', '09:00', '18:00'],
            ['2025/01/03', '09:00', '18:00']
        ]
        
        for row, data in enumerate(sample_data, start=2):
            ws[f'A{row}'] = data[0]
            ws[f'B{row}'] = data[1]
            ws[f'C{row}'] = data[2]
        
        # 一時ファイルに保存
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        wb.save(temp_file.name)
        return temp_file.name
    else:
        raise Exception("pandasとopenpyxlの両方が利用できません")

def load_excel_data(file_path):
    """Excelファイルを読み込み、データを返す"""
    if pandas_available:
        df = pd.read_excel(file_path)
        return df, len(df)
    elif openpyxl_available:
        wb = openpyxl.load_workbook(file_path)
        ws = wb.active
        total_data = ws.max_row - 1  # ヘッダー行を除く
        return wb, total_data
    else:
        raise Exception("Excelファイルを読み込むためのライブラリが利用できません")

def extract_date_info(date):
    """日付から年月日を抽出"""
    if hasattr(date, 'strftime'):
        date_str = date.strftime('%Y/%m/%d')
    else:
        date_str = str(date)
    
    if hasattr(date, 'year') and hasattr(date, 'month') and hasattr(date, 'day'):
        year = date.year
        month = date.month
        day = date.day
    else:
        # 文字列から年月日を抽出
        date_parts = str(date_str).split('/')
        if len(date_parts) >= 3:
            year = date_parts[0]
            month = date_parts[1]
            day = date_parts[2]
        else:
            year = month = day = "01"
    
    return date_str, year, month, day

def simulate_data_processing(job_id, data_source, total_data, pandas_available, jobs):
    """データ処理のシミュレーション"""
    try:
        if pandas_available:
            for index, row in data_source.iterrows():
                date = row.iloc[0]
                start_time = row.iloc[1]
                end_time = row.iloc[2]
                
                date_str, year, month, day = extract_date_info(date)
                add_job_log(job_id, f"📝 データ {index + 1}/{total_data}: {date_str} {start_time}-{end_time}", jobs)
                add_job_log(job_id, f"🔧 打刻修正URL: https://ssl.jobcan.jp/employee/adit/modify?year={year}&month={month}&day={day}", jobs)
                add_job_log(job_id, "⚠️ 実際のデータ入力はスキップされました（シミュレーションモード）", jobs)
                
                time.sleep(1)
                update_progress(job_id, 6, f"勤怠データ入力中 ({index + 1}/{total_data})", jobs, index + 1, total_data)
        else:
            # openpyxlを使用した処理
            ws = data_source.active
            for row in range(2, ws.max_row + 1):
                date = ws[f'A{row}'].value
                start_time = ws[f'B{row}'].value
                end_time = ws[f'C{row}'].value
                
                date_str, year, month, day = extract_date_info(date)
                add_job_log(job_id, f"📝 データ {row - 1}/{total_data}: {date_str} {start_time}-{end_time}", jobs)
                add_job_log(job_id, f"🔧 打刻修正URL: https://ssl.jobcan.jp/employee/adit/modify?year={year}&month={month}&day={day}", jobs)
                add_job_log(job_id, "⚠️ 実際のデータ入力はスキップされました（シミュレーションモード）", jobs)
                
                time.sleep(1)
                update_progress(job_id, 6, f"勤怠データ入力中 ({row - 1}/{total_data})", jobs, row - 1, total_data)
    except Exception as e:
        add_job_log(job_id, f"❌ データ処理エラー: {e}", jobs) 
