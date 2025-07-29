import time
import tempfile
from datetime import datetime, date
import calendar
import re
import os # 追加: ファイルシステム操作のため

# ライブラリの利用可能性をチェック
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

try:
    import jpholiday
    jpholiday_available = True
except ImportError:
    jpholiday_available = False

try:
    from playwright.sync_api import sync_playwright
    playwright_available = True
except ImportError:
    playwright_available = False

def get_weekdays_in_current_month():
    """本日の月の平日（土日・祝日を除く）を取得"""
    today = date.today()
    year = today.year
    month = today.month
    
    # その月の1日から末日までを取得
    _, last_day = calendar.monthrange(year, month)
    weekdays = []
    
    for day in range(1, last_day + 1):
        current_date = date(year, month, day)
        
        # 土日チェック（0=月曜日, 6=日曜日）
        if current_date.weekday() >= 5:  # 土曜日(5)または日曜日(6)
            continue
        
        # 祝日チェック
        if jpholiday_available:
            if jpholiday.is_holiday(current_date):
                continue
        
        # 平日の場合、YYYY-MM-DD形式で追加
        weekdays.append(current_date.strftime('%Y-%m-%d'))
    
    return weekdays

def validate_excel_data(data_source, pandas_available, job_id, jobs):
    """Excelデータの内容を検証"""
    errors = []
    warnings = []
    
    try:
        if pandas_available:
            # pandasを使用した検証
            if len(data_source) == 0:
                errors.append("Excelファイルにデータが含まれていません")
                return errors, warnings
            
            # ヘッダー行の確認
            expected_columns = ['日付', '開始時刻', '終了時刻']
            actual_columns = list(data_source.columns)
            
            if not all(col in actual_columns for col in expected_columns):
                errors.append(f"必要な列が見つかりません。期待: {expected_columns}, 実際: {actual_columns}")
                return errors, warnings
            
            # 各行のデータを検証
            for index, row in data_source.iterrows():
                row_num = index + 2  # ヘッダー行を考慮
                
                # 日付の検証
                date_value = row.iloc[0]
                if pd.isna(date_value):
                    errors.append(f"行{row_num}: 日付が空です")
                    continue
                
                # 日付形式の検証
                try:
                    if isinstance(date_value, str):
                        # 文字列の場合、複数の形式を試行
                        date_formats = ['%Y-%m-%d', '%Y/%m/%d', '%Y年%m月%d日']
                        parsed_date = None
                        for fmt in date_formats:
                            try:
                                parsed_date = datetime.strptime(date_value, fmt).date()
                                break
                            except ValueError:
                                continue
                        
                        if parsed_date is None:
                            errors.append(f"行{row_num}: 日付形式が無効です: {date_value}")
                            continue
                    else:
                        parsed_date = pd.to_datetime(date_value).date()
                    
                    # 未来日チェック
                    if parsed_date > date.today():
                        warnings.append(f"行{row_num}: 未来の日付です: {parsed_date}")
                    
                    # 過去すぎる日付チェック（1年前まで）
                    one_year_ago = date.today().replace(year=date.today().year - 1)
                    if parsed_date < one_year_ago:
                        warnings.append(f"行{row_num}: 過去すぎる日付です: {parsed_date}")
                    
                except Exception as e:
                    errors.append(f"行{row_num}: 日付の解析に失敗しました: {date_value}")
                    continue
                
                # 時刻の検証
                start_time = row.iloc[1]
                end_time = row.iloc[2]
                
                if pd.isna(start_time) or pd.isna(end_time):
                    errors.append(f"行{row_num}: 開始時刻または終了時刻が空です")
                    continue
                
                # 時刻形式の検証
                for time_value, time_name in [(start_time, "開始時刻"), (end_time, "終了時刻")]:
                    try:
                        if isinstance(time_value, str):
                            # 時刻形式の正規化
                            time_str = str(time_value).strip()
                            if not re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', time_str):
                                errors.append(f"行{row_num}: {time_name}の形式が無効です: {time_value}")
                                continue
                        elif hasattr(time_value, 'time'):
                            # datetimeオブジェクトの場合
                            pass
                        else:
                            errors.append(f"行{row_num}: {time_name}の形式が無効です: {time_value}")
                            continue
                    except Exception as e:
                        errors.append(f"行{row_num}: {time_name}の解析に失敗しました: {time_value}")
                        continue
                
                # 勤務時間の妥当性チェック
                try:
                    start_str = str(start_time)
                    end_str = str(end_time)
                    
                    # 時刻を分に変換
                    start_parts = start_str.split(':')
                    end_parts = end_str.split(':')
                    
                    if len(start_parts) >= 2 and len(end_parts) >= 2:
                        start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
                        end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
                        
                        # 勤務時間が短すぎる場合
                        work_hours = (end_minutes - start_minutes) / 60
                        if work_hours < 0.5:  # 30分未満
                            warnings.append(f"行{row_num}: 勤務時間が短すぎます: {work_hours:.1f}時間")
                        elif work_hours > 24:  # 24時間超過
                            warnings.append(f"行{row_num}: 勤務時間が長すぎます: {work_hours:.1f}時間")
                        
                        # 開始時刻が終了時刻より後の場合
                        if start_minutes >= end_minutes:
                            errors.append(f"行{row_num}: 開始時刻が終了時刻より後です: {start_time} > {end_time}")
                    
                except Exception as e:
                    warnings.append(f"行{row_num}: 勤務時間の計算に失敗しました: {e}")
            
        else:
            # openpyxlを使用した検証
            ws = data_source.active
            if ws.max_row <= 1:
                errors.append("Excelファイルにデータが含まれていません")
                return errors, warnings
            
            # 各行のデータを検証
            for row in range(2, ws.max_row + 1):
                row_num = row
                
                # 日付の検証
                date_value = ws[f'A{row}'].value
                if date_value is None:
                    errors.append(f"行{row_num}: 日付が空です")
                    continue
                
                # 時刻の検証
                start_time = ws[f'B{row}'].value
                end_time = ws[f'C{row}'].value
                
                if start_time is None or end_time is None:
                    errors.append(f"行{row_num}: 開始時刻または終了時刻が空です")
                    continue
                
                # 時刻形式の検証
                for time_value, time_name in [(start_time, "開始時刻"), (end_time, "終了時刻")]:
                    try:
                        if isinstance(time_value, str):
                            # 時刻形式の正規化
                            time_str = str(time_value).strip()
                            if not re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', time_str):
                                errors.append(f"行{row_num}: {time_name}の形式が無効です: {time_value}")
                                continue
                        elif hasattr(time_value, 'time'):
                            # datetimeオブジェクトの場合
                            pass
                        else:
                            errors.append(f"行{row_num}: {time_name}の形式が無効です: {time_value}")
                            continue
                    except Exception as e:
                        errors.append(f"行{row_num}: {time_name}の解析に失敗しました: {time_value}")
                        continue
                
                # 勤務時間の妥当性チェック
                try:
                    start_str = str(start_time)
                    end_str = str(end_time)
                    
                    # 時刻を分に変換
                    start_parts = start_str.split(':')
                    end_parts = end_str.split(':')
                    
                    if len(start_parts) >= 2 and len(end_parts) >= 2:
                        start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
                        end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
                        
                        # 勤務時間が短すぎる場合
                        work_hours = (end_minutes - start_minutes) / 60
                        if work_hours < 0.5:  # 30分未満
                            warnings.append(f"行{row_num}: 勤務時間が短すぎます: {work_hours:.1f}時間")
                        elif work_hours > 24:  # 24時間超過
                            warnings.append(f"行{row_num}: 勤務時間が長すぎます: {work_hours:.1f}時間")
                        
                        # 開始時刻が終了時刻より後の場合
                        if start_minutes >= end_minutes:
                            errors.append(f"行{row_num}: 開始時刻が終了時刻より後です: {start_time} > {end_time}")
                    
                except Exception as e:
                    warnings.append(f"行{row_num}: 勤務時間の計算に失敗しました: {e}")
    
    except Exception as e:
        errors.append(f"データ検証中にエラーが発生しました: {e}")
    
    return errors, warnings

def allowed_file(filename):
    """アップロードされたファイルの拡張子をチェック"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls'}

def add_job_log(job_id: str, message: str, jobs: dict):
    """ジョブのログを追加"""
    if job_id in jobs:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sanitized_message = sanitize_log_message(message)
        jobs[job_id]['logs'].append(f"[{timestamp}] {sanitized_message}")

def sanitize_log_message(message):
    """ログメッセージから個人情報を除去"""
    # メールアドレスを除去
    message = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', message)
    
    # パスワードを除去
    message = re.sub(r'password["\']?\s*[:=]\s*["\']?[^"\s]+["\']?', 'password="[PASSWORD]"', message, flags=re.IGNORECASE)
    
    # クレジットカード番号を除去
    message = re.sub(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', '[CARD_NUMBER]', message)
    
    return message

def update_progress(job_id: str, step: int, step_name: str, jobs: dict, current_data: int = 0, total_data: int = 0):
    """ジョブの進捗を更新"""
    if job_id in jobs:
        jobs[job_id]['step'] = step
        jobs[job_id]['step_name'] = step_name
        jobs[job_id]['current_data'] = current_data
        jobs[job_id]['total_data'] = total_data

def create_template_excel():
    """今月の平日のテンプレートExcelファイルを作成"""
    try:
        # 今月の平日を取得
        weekdays = get_weekdays_in_current_month()
        
        if not weekdays:
            return None, "今月の平日が見つかりませんでした"
        
        # サンプルデータを作成
        sample_data = []
        for weekday in weekdays:
            # 9:00-18:00の勤務時間をサンプルとして設定
            sample_data.append({
                '日付': weekday,
                '開始時刻': '09:00',
                '終了時刻': '18:00'
            })
        
        # テンプレートファイルを作成
        if openpyxl_available:
            wb = Workbook()
            ws = wb.active
            ws.title = "勤怠データ"
            
            # ヘッダー行を追加
            ws['A1'] = '日付'
            ws['B1'] = '開始時刻'
            ws['C1'] = '終了時刻'
            
            # データ行を追加
            for i, data in enumerate(sample_data, start=2):
                ws[f'A{i}'] = data['日付']
                ws[f'B{i}'] = data['開始時刻']
                ws[f'C{i}'] = data['終了時刻']
            
            # 本番環境に対応した一時ファイルの生成
            # /tmpディレクトリを使用（Renderなどの本番環境で安全）
            temp_dir = '/tmp' if os.path.exists('/tmp') else tempfile.gettempdir()
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix='.xlsx',
                dir=temp_dir
            )
            
            try:
                wb.save(temp_file.name)
                temp_file.close()
                
                # ファイルが正常に作成されたか確認
                if os.path.exists(temp_file.name) and os.path.getsize(temp_file.name) > 0:
                    return temp_file.name, None
                else:
                    return None, "テンプレートファイルの保存に失敗しました"
                    
            except Exception as save_error:
                # 一時ファイルのクリーンアップ
                try:
                    if os.path.exists(temp_file.name):
                        os.remove(temp_file.name)
                except:
                    pass
                return None, f"ファイル保存エラー: {str(save_error)}"
        else:
            return None, "openpyxlが利用できません"
    
    except Exception as e:
        return None, f"テンプレート作成中にエラーが発生しました: {e}"

def load_excel_data(file_path):
    """Excelファイルを読み込み"""
    try:
        if pandas_available:
            # pandasを使用して読み込み
            import pandas as pd
            data = pd.read_excel(file_path)
            return data, True
        elif openpyxl_available:
            # openpyxlを使用して読み込み
            from openpyxl import load_workbook
            wb = load_workbook(file_path)
            return wb, False
        else:
            return None, False
    except Exception as e:
        return None, False

def extract_date_info(date):
    """日付から年月日を抽出"""
    if hasattr(date, 'strftime'):
        date_str = date.strftime('%Y-%m-%d')
    else:
        date_str = str(date)
    
    if hasattr(date, 'year') and hasattr(date, 'month') and hasattr(date, 'day'):
        year = date.year
        month = date.month
        day = date.day
    else:
        date_str_clean = str(date_str).strip()
        separators = ['-', '/', '年', '月', '日']
        date_parts = None
        
        for sep in separators:
            if sep in date_str_clean:
                parts = date_str_clean.split(sep)
                if len(parts) >= 3:
                    try:
                        year_part = parts[0].strip()
                        month_part = parts[1].strip()
                        day_part = parts[2].strip()
                        if (year_part.isdigit() and len(year_part) == 4 and
                            month_part.isdigit() and 1 <= int(month_part) <= 12 and
                            day_part.isdigit() and 1 <= int(day_part) <= 31):
                            date_parts = [year_part, month_part, day_part]
                            break
                    except (ValueError, IndexError):
                        continue
        
        if date_parts:
            year = date_parts[0]
            month = date_parts[1]
            day = date_parts[2]
        else:
            year = month = day = "01"
    
    return date_str, year, month, day

def simulate_data_processing(job_id, data_source, total_data, pandas_available, jobs):
    """データ処理のシミュレーション"""
    for i in range(total_data):
        time.sleep(0.1)  # 処理時間をシミュレート
        progress = int((i + 1) / total_data * 100)
        update_progress(job_id, 6, f"データ処理中... ({i + 1}/{total_data})", jobs, i + 1, total_data)
        add_job_log(job_id, f"データ処理進捗: {progress}%", jobs)
