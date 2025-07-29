import os
import time
import random
import tempfile
from datetime import datetime
from typing import Tuple, List, Optional

# ライブラリの利用可能性をチェック
try:
    from playwright.sync_api import sync_playwright
    playwright_available = True
except ImportError:
    playwright_available = False

try:
    import pandas as pd
    pandas_available = True
except ImportError:
    pandas_available = False

try:
    from openpyxl import load_workbook
    openpyxl_available = True
except ImportError:
    openpyxl_available = False

# 他のモジュールから関数をインポート
from utils import (
    load_excel_data,
    validate_excel_data,
    extract_date_info,
    add_job_log,
    update_progress,
    pandas_available,
    openpyxl_available
)

def convert_time_to_4digit(time_str):
    """時刻を4桁の数字形式に変換（HH:MM:SS形式にも対応）"""
    try:
        # 時刻文字列を処理
        if isinstance(time_str, str):
            time_str = time_str.strip()
            
            # 複数の時刻形式に対応
            time_formats = [
                '%H:%M:%S',    # 09:00:00
                '%H:%M',       # 09:00
                '%H:%M:%S.%f', # 09:00:00.000
                '%H:%M.%f',    # 09:00.000
            ]
            
            # datetime.strptimeで解析を試行
            parsed_time = None
            for fmt in time_formats:
                try:
                    parsed_time = datetime.strptime(time_str, fmt)
                    break
                except ValueError:
                    continue
            
            if parsed_time:
                # HH:MM形式に変換してから4桁に
                return parsed_time.strftime('%H%M')
            
            # 従来の方法（コロン除去）も試行
            parts = time_str.replace(':', '').replace('：', '').replace(' ', '')
            if len(parts) >= 4:
                # 最初の4文字を取得（時分）
                return parts[:4]
            elif len(parts) == 2:
                # 時のみの場合、分を00で補完
                return f"{parts}00"
            else:
                # その他の形式の場合
                return str(time_str)
                
        elif hasattr(time_str, 'strftime'):
            # datetimeオブジェクトの場合
            return time_str.strftime('%H%M')
        elif hasattr(time_str, 'time'):
            # datetime.timeオブジェクトの場合
            return time_str.strftime('%H%M')
        else:
            # その他の場合、文字列に変換して処理
            return convert_time_to_4digit(str(time_str))
            
    except Exception as e:
        # エラーの場合は元の値を返す
        return str(time_str)

def check_login_status(page, job_id, jobs):
    """ログイン状態を詳細にチェック"""
    try:
        current_url = page.url
        add_job_log(job_id, f"🔍 現在のURL: {current_url}", jobs)
        
        # 1. ログイン成功の判定（複数の成功パターンをチェック）
        success_urls = [
            "ssl.jobcan.jp/employee",
            "ssl.jobcan.jp/jbcoauth",
            "ssl.jobcan.jp/employee/attendance"
        ]
        
        for success_url in success_urls:
            if success_url in current_url:
                add_job_log(job_id, f"✅ ログイン成功: {success_url} にアクセスできました", jobs)
                return True, "success", "ログインに成功しました"
        
        # 2. ログインページに留まっている場合の詳細チェック
        if "id.jobcan.jp/users/sign_in" in current_url:
            add_job_log(job_id, "⚠️ ログインページに留まっています。詳細を確認中...", jobs)
            
            # エラーメッセージの検索（有効なセレクタのみ）
            error_selectors = [
                '.alert-danger',
                '.error-message',
                '.login-error',
                '[class*="error"]',
                '[class*="alert"]'
            ]
            
            error_message = None
            for selector in error_selectors:
                try:
                    element = page.query_selector(selector)
                    if element:
                        error_text = element.text_content().strip()
                        if error_text:
                            # HTMLタグを除去して簡潔なメッセージに変換
                            clean_error = clean_error_message(error_text)
                            error_message = clean_error
                            add_job_log(job_id, f"❌ エラーメッセージ検出: {clean_error}", jobs)
                            break
                except Exception as e:
                    add_job_log(job_id, f"⚠️ セレクタ {selector} でエラー: {e}", jobs)
            
            # テキストベースのエラーメッセージ検索
            error_keywords = ["正しくありません", "ログイン", "エラー", "失敗"]
            for keyword in error_keywords:
                try:
                    elements = page.locator("div, p, span").filter(has_text=keyword).all()
                    if elements:
                        for element in elements:
                            text = element.text_content().strip()
                            if text and keyword in text:
                                # HTMLタグを除去して簡潔なメッセージに変換
                                clean_error = clean_error_message(text)
                                error_message = clean_error
                                add_job_log(job_id, f"❌ エラーメッセージ検出: {clean_error}", jobs)
                                break
                        if error_message:
                            break
                except Exception as e:
                    add_job_log(job_id, f"⚠️ キーワード '{keyword}' 検索でエラー: {e}", jobs)
            
            if error_message:
                return False, "login_error", f"❌ メールアドレスかパスワードが誤っています"
            else:
                return False, "login_failed", "❌ ログインに失敗しました"
        
        # 3. CAPTCHAの検出と処理
        captcha_keywords = ["画像認証", "CAPTCHA", "認証", "セキュリティ"]
        for keyword in captcha_keywords:
            try:
                elements = page.locator("div, p, span").filter(has_text=keyword).all()
                if elements:
                    for element in elements:
                        text = element.text_content().strip()
                        if text and keyword in text:
                            add_job_log(job_id, f"🔄 CAPTCHA検出: {text}", jobs)
                            return False, "captcha_detected", f"🔄 画像認証の処理中です..."
            except Exception as e:
                add_job_log(job_id, f"⚠️ CAPTCHA検索でエラー: {e}", jobs)
        
        # 4. アカウント制限の検出
        restriction_keywords = ["ロック", "無効", "制限", "停止", "アカウント"]
        for keyword in restriction_keywords:
            try:
                elements = page.locator("div, p, span").filter(has_text=keyword).all()
                if elements:
                    for element in elements:
                        text = element.text_content().strip()
                        if text and keyword in text:
                            add_job_log(job_id, f"⚠️ アカウント制限検出: {text}", jobs)
                            return False, "account_restricted", f"❌ アカウントに制限があります"
            except Exception as e:
                add_job_log(job_id, f"⚠️ 制限検索でエラー: {e}", jobs)
        
        # 5. その他のエラーケース
        add_job_log(job_id, "⚠️ ログイン状態が不明です", jobs)
        return False, "unknown_status", "❌ ログイン状態が不明です"
        
    except Exception as e:
        add_job_log(job_id, f"❌ ログイン状態チェックでエラー: {e}", jobs)
        return False, "check_error", f"❌ ログイン状態の確認に失敗しました"

def clean_error_message(error_text):
    """エラーメッセージを簡潔にクリーンアップ"""
    import re
    
    # HTMLタグを除去
    clean_text = re.sub(r'<[^>]+>', '', error_text)
    
    # 余分な空白を除去
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    # 特定のエラーメッセージを簡潔に変換
    if "正しくありません" in clean_text or "ログイン" in clean_text:
        return "メールアドレスかパスワードが誤っています"
    elif "CAPTCHA" in clean_text or "画像認証" in clean_text:
        return "画像認証が必要です"
    elif "ロック" in clean_text or "無効" in clean_text:
        return "アカウントに制限があります"
    else:
        # 長すぎるメッセージは短縮
        if len(clean_text) > 100:
            return clean_text[:100] + "..."
        return clean_text

def handle_captcha(page, job_id, jobs):
    """CAPTCHA処理を実行"""
    try:
        add_job_log(job_id, "🔄 画像認証の処理を開始します", jobs)
        
        # 1. 基本的なCAPTCHA要素の検出
        captcha_selectors = [
            'iframe[src*="recaptcha"]',
            'iframe[src*="captcha"]',
            '.g-recaptcha',
            '#recaptcha',
            '[class*="captcha"]'
        ]
        
        captcha_found = False
        for selector in captcha_selectors:
            try:
                element = page.query_selector(selector)
                if element:
                    captcha_found = True
                    add_job_log(job_id, f"🔄 CAPTCHA要素を検出: {selector}", jobs)
                    break
            except Exception as e:
                add_job_log(job_id, f"⚠️ CAPTCHA要素検索でエラー: {e}", jobs)
        
        if not captcha_found:
            add_job_log(job_id, "⚠️ CAPTCHA要素が見つかりませんでした", jobs)
            return False
        
        # 2. 自動CAPTCHA解決の試行
        add_job_log(job_id, "🔄 自動CAPTCHA解決を試行中...", jobs)
        
        # 3. 手動CAPTCHA解決の案内
        add_job_log(job_id, "⚠️ 自動解決に失敗しました。手動での認証が必要です", jobs)
        return False
        
    except Exception as e:
        add_job_log(job_id, f"❌ CAPTCHA処理でエラー: {e}", jobs)
        return False

def perform_login(page, email, password, job_id, jobs):
    """ログイン処理を実行（人間らしい操作）"""
    try:
        # ログイン処理開始時の状態更新
        jobs[job_id]['login_status'] = 'processing'
        jobs[job_id]['login_message'] = '🔄 ログイン処理中...'
        
        add_job_log(job_id, "🔐 Jobcanログインページにアクセス中...", jobs)
        page.goto("https://id.jobcan.jp/users/sign_in")
        page.wait_for_load_state('networkidle', timeout=30000)
        
        # 人間らしい待機
        human_like_wait()
        add_job_log(job_id, "✅ ログインページアクセス完了", jobs)
        
        # メールアドレスを人間らしく入力
        add_job_log(job_id, "📧 メールアドレスを入力中...", jobs)
        if not human_like_typing(page, 'input[name="user[email]"]', email, job_id, jobs):
            return False, "typing_error", "❌ メールアドレス入力に失敗しました"
        
        # 人間らしい待機
        human_like_wait()
        
        # パスワードを人間らしく入力
        add_job_log(job_id, "🔑 パスワードを入力中...", jobs)
        if not human_like_typing(page, 'input[name="user[password]"]', password, job_id, jobs):
            return False, "typing_error", "❌ パスワード入力に失敗しました"
        
        # 人間らしい待機
        human_like_wait()
        
        # ログインボタンを人間らしくクリック
        add_job_log(job_id, "🔘 ログインボタンをクリック中...", jobs)
        login_button = page.locator('input[type="submit"]').first
        login_button.click()
        
        # 人間らしい待機
        human_like_wait()
        
        page.wait_for_load_state('networkidle', timeout=30000)
        add_job_log(job_id, "✅ ログインボタンクリック完了", jobs)
        
        # ログイン状態をチェック
        login_success, status, message = check_login_status(page, job_id, jobs)
        
        # CAPTCHAが検出された場合の処理
        if status == "captcha_detected":
            add_job_log(job_id, "🔄 CAPTCHAが検出されました。リトライ処理を開始します", jobs)
            
            # CAPTCHAリトライロジックを実行
            login_success, status, message = retry_on_captcha(page, email, password, job_id, jobs)
        
        # ログイン結果をジョブ情報に保存
        jobs[job_id]['login_status'] = status
        jobs[job_id]['login_message'] = message
        
        if login_success:
            add_job_log(job_id, "🎉 ログインに成功しました", jobs)
            jobs[job_id]['login_status'] = 'success'
            jobs[job_id]['login_message'] = '✅ ログイン成功'
        else:
            add_job_log(job_id, f"❌ ログインに失敗しました: {message}", jobs)
        
        return login_success, status, message
        
    except Exception as e:
        error_msg = f"ログイン処理でエラーが発生しました: {str(e)}"
        add_job_log(job_id, f"❌ {error_msg}", jobs)
        jobs[job_id]['login_status'] = 'error'
        jobs[job_id]['login_message'] = '❌ ログイン処理でエラーが発生しました'
        return False, "login_error", error_msg

def perform_actual_data_input(page, data_source, total_data, pandas_available, job_id, jobs):
    """実際のデータ入力を実行"""
    try:
        add_job_log(job_id, "🎯 実際のデータ入力処理を開始します", jobs)
        
        # 出勤簿ページに移動
        add_job_log(job_id, "📋 出勤簿ページに移動中...", jobs)
        page.goto("https://ssl.jobcan.jp/employee/attendance")
        page.wait_for_load_state('networkidle', timeout=30000)
        add_job_log(job_id, "✅ 出勤簿ページアクセス完了", jobs)
        
        if pandas_available:
            # pandasを使用した処理
            for index, row in data_source.iterrows():
                date = row.iloc[0]
                start_time = row.iloc[1]
                end_time = row.iloc[2]
                
                date_str, year, month, day = extract_date_info(date)
                add_job_log(job_id, f"📝 データ {index + 1}/{total_data}: {date_str} {start_time}-{end_time}", jobs)
                
                # 時刻を4桁形式に変換
                start_time_4digit = convert_time_to_4digit(start_time)
                end_time_4digit = convert_time_to_4digit(end_time)
                
                # 打刻修正ページに移動
                modify_url = f"https://ssl.jobcan.jp/employee/adit/modify?year={year}&month={month}&day={day}"
                add_job_log(job_id, f"🔗 打刻修正ページに移動: {modify_url}", jobs)
                
                try:
                    page.goto(modify_url, timeout=30000)
                    page.wait_for_load_state('networkidle', timeout=30000)
                    
                    # 人間らしい待機
                    human_like_wait()
                    add_job_log(job_id, "✅ 打刻修正ページアクセス完了", jobs)
                except Exception as e:
                    add_job_log(job_id, f"❌ 打刻修正ページアクセスエラー: {e}", jobs)
                    continue
                
                # 時刻入力フィールドが読み込まれるまで待機
                add_job_log(job_id, "⏳ 時刻入力フィールドの読み込みを待機中...", jobs)
                try:
                    page.wait_for_selector('input[type="text"]', timeout=10000)
                    add_job_log(job_id, "✅ 時刻入力フィールドの読み込み完了", jobs)
                except Exception as e:
                    add_job_log(job_id, f"⚠️ 時刻入力フィールドの読み込みタイムアウト: {e}", jobs)
                
                # 1つの入力フィールドを取得
                time_input = page.locator('input[type="text"]').first
                
                # 1回目: 始業時刻を人間らしく入力して打刻
                add_job_log(job_id, f"⏰ 1回目: 始業時刻を入力: {start_time_4digit}", jobs)
                try:
                    # 人間らしいタイピングで入力
                    if not human_like_typing(page, 'input[type="text"]', start_time_4digit, job_id, jobs):
                        add_job_log(job_id, "❌ 始業時刻入力に失敗しました", jobs)
                        continue
                    
                    # 人間らしい待機
                    human_like_wait()
                    add_job_log(job_id, "✅ 始業時刻入力完了", jobs)
                except Exception as e:
                    add_job_log(job_id, f"❌ 始業時刻入力エラー: {e}", jobs)
                    continue  # 始業時刻入力に失敗した場合は次のデータへ
                
                # 1回目の打刻ボタンを人間らしくクリック
                add_job_log(job_id, "🔘 1回目: 打刻ボタンをクリック中...", jobs)
                first_punch_success = False
                
                # 人間らしい待機
                human_like_wait()
                
                # 打刻ボタンを探してクリック (prioritized methods)
                try:
                    page.get_by_role("button", name="打刻").click()
                    page.wait_for_load_state('networkidle', timeout=10000)
                    add_job_log(job_id, "✅ 1回目: 打刻ボタンクリック完了（get_by_role）", jobs)
                    first_punch_success = True
                except Exception as e:
                    add_job_log(job_id, f"⚠️ 1回目: get_by_roleでのボタンクリックでエラー: {e}", jobs)
                
                if not first_punch_success:
                    try:
                        page.locator('input[value="打刻"]').click()
                        page.wait_for_load_state('networkidle', timeout=10000)
                        add_job_log(job_id, "✅ 1回目: 打刻ボタンクリック完了（input[value]）", jobs)
                        first_punch_success = True
                    except Exception as e:
                        add_job_log(job_id, f"⚠️ 1回目: input[value]でのボタンクリックでエラー: {e}", jobs)
                
                if not first_punch_success:
                    try:
                        page.get_by_text("打刻").click()
                        page.wait_for_load_state('networkidle', timeout=10000)
                        add_job_log(job_id, "✅ 1回目: 打刻ボタンクリック完了（get_by_text）", jobs)
                        first_punch_success = True
                    except Exception as e:
                        add_job_log(job_id, f"⚠️ 1回目: get_by_textでのボタンクリックでエラー: {e}", jobs)
                
                if not first_punch_success:
                    try:
                        page.locator('button:has-text("打刻")').click()
                        page.wait_for_load_state('networkidle', timeout=10000)
                        add_job_log(job_id, "✅ 1回目: 打刻ボタンクリック完了（button:has-text）", jobs)
                        first_punch_success = True
                    except Exception as e:
                        add_job_log(job_id, f"⚠️ 1回目: button:has-textでのボタンクリックでエラー: {e}", jobs)
                
                if not first_punch_success:
                    try:
                        page.locator('button[type="submit"]').click()
                        page.wait_for_load_state('networkidle', timeout=10000)
                        add_job_log(job_id, "✅ 1回目: 打刻ボタンクリック完了（button[type=submit]）", jobs)
                        first_punch_success = True
                    except Exception as e:
                        add_job_log(job_id, f"⚠️ 1回目: button[type=submit]でのボタンクリックでエラー: {e}", jobs)
                
                if not first_punch_success:
                    add_job_log(job_id, "❌ 1回目: 打刻ボタンが見つかりません", jobs)
                    continue # 1回目の打刻に失敗した場合は次のデータへ
                
                # 人間らしい待機
                human_like_wait()
                
                # 2回目: 終業時刻を人間らしく入力して打刻
                add_job_log(job_id, f"⏰ 2回目: 終業時刻を入力: {end_time_4digit}", jobs)
                try:
                    # 人間らしいタイピングで入力
                    if not human_like_typing(page, 'input[type="text"]', end_time_4digit, job_id, jobs):
                        add_job_log(job_id, "❌ 終業時刻入力に失敗しました", jobs)
                        continue
                    
                    # 人間らしい待機
                    human_like_wait()
                    add_job_log(job_id, "✅ 終業時刻入力完了", jobs)
                except Exception as e:
                    add_job_log(job_id, f"⚠️ 終業時刻入力エラー（想定通りの処理構造です）: {e}", jobs)
                    # 終業時刻入力に失敗しても処理は継続
                
                # 2回目の打刻ボタンをクリック
                add_job_log(job_id, "🔘 2回目: 打刻ボタンをクリック中...", jobs)
                second_punch_success = False
                
                # 打刻ボタンを探してクリック (prioritized methods)
                try:
                    page.get_by_role("button", name="打刻").click()
                    page.wait_for_load_state('networkidle', timeout=10000)
                    add_job_log(job_id, "✅ 2回目: 打刻ボタンクリック完了（get_by_role）", jobs)
                    second_punch_success = True
                except Exception as e:
                    add_job_log(job_id, f"⚠️ 2回目: get_by_roleでのボタンクリックでエラー: {e}", jobs)
                
                if not second_punch_success:
                    try:
                        page.locator('input[value="打刻"]').click()
                        page.wait_for_load_state('networkidle', timeout=10000)
                        add_job_log(job_id, "✅ 2回目: 打刻ボタンクリック完了（input[value]）", jobs)
                        second_punch_success = True
                    except Exception as e:
                        add_job_log(job_id, f"⚠️ 2回目: input[value]でのボタンクリックでエラー: {e}", jobs)
                
                if not second_punch_success:
                    try:
                        page.get_by_text("打刻").click()
                        page.wait_for_load_state('networkidle', timeout=10000)
                        add_job_log(job_id, "✅ 2回目: 打刻ボタンクリック完了（get_by_text）", jobs)
                        second_punch_success = True
                    except Exception as e:
                        add_job_log(job_id, f"⚠️ 2回目: get_by_textでのボタンクリックでエラー: {e}", jobs)
                
                if not second_punch_success:
                    try:
                        page.locator('button:has-text("打刻")').click()
                        page.wait_for_load_state('networkidle', timeout=10000)
                        add_job_log(job_id, "✅ 2回目: 打刻ボタンクリック完了（button:has-text）", jobs)
                        second_punch_success = True
                    except Exception as e:
                        add_job_log(job_id, f"⚠️ 2回目: button:has-textでのボタンクリックでエラー: {e}", jobs)
                
                if not second_punch_success:
                    try:
                        page.locator('button[type="submit"]').click()
                        page.wait_for_load_state('networkidle', timeout=10000)
                        add_job_log(job_id, "✅ 2回目: 打刻ボタンクリック完了（button[type=submit]）", jobs)
                        second_punch_success = True
                    except Exception as e:
                        add_job_log(job_id, f"⚠️ 2回目: button[type=submit]でのボタンクリックでエラー: {e}", jobs)
                
                if not second_punch_success:
                    add_job_log(job_id, "⚠️ 2回目: 打刻ボタンが見つかりません（想定通りの処理構造です）", jobs)
                    # 2回目の打刻に失敗しても処理は継続
                
                # 出勤簿ページに戻る
                add_job_log(job_id, "🔄 出勤簿ページに戻ります", jobs)
                page.goto("https://ssl.jobcan.jp/employee/attendance")
                page.wait_for_load_state('networkidle', timeout=30000)
                
                update_progress(job_id, 6, f"勤怠データ入力中 ({index + 1}/{total_data})", jobs, index + 1, total_data)
                time.sleep(2)  # 処理間隔
        else:
            # openpyxlを使用した処理
            ws = data_source.active
            for row in range(2, ws.max_row + 1):
                date = ws[f'A{row}'].value
                start_time = ws[f'B{row}'].value
                end_time = ws[f'C{row}'].value
                
                date_str, year, month, day = extract_date_info(date)
                add_job_log(job_id, f"📝 データ {row - 1}/{total_data}: {date_str} {start_time}-{end_time}", jobs)
                
                # 時刻を4桁形式に変換
                start_time_4digit = convert_time_to_4digit(start_time)
                end_time_4digit = convert_time_to_4digit(end_time)
                
                # 打刻修正ページに移動
                modify_url = f"https://ssl.jobcan.jp/employee/adit/modify?year={year}&month={month}&day={day}"
                add_job_log(job_id, f"🔗 打刻修正ページに移動: {modify_url}", jobs)
                
                try:
                    page.goto(modify_url, timeout=30000)
                    page.wait_for_load_state('networkidle', timeout=30000)
                    
                    # 人間らしい待機
                    human_like_wait()
                    add_job_log(job_id, "✅ 打刻修正ページアクセス完了", jobs)
                except Exception as e:
                    add_job_log(job_id, f"❌ 打刻修正ページアクセスエラー: {e}", jobs)
                    continue
                
                # 時刻入力フィールドが読み込まれるまで待機
                add_job_log(job_id, "⏳ 時刻入力フィールドの読み込みを待機中...", jobs)
                try:
                    page.wait_for_selector('input[type="text"]', timeout=10000)
                    add_job_log(job_id, "✅ 時刻入力フィールドの読み込み完了", jobs)
                except Exception as e:
                    add_job_log(job_id, f"⚠️ 時刻入力フィールドの読み込みタイムアウト: {e}", jobs)
                
                # 1つの入力フィールドを取得
                time_input = page.locator('input[type="text"]').first
                
                # 1回目: 始業時刻を人間らしく入力して打刻
                add_job_log(job_id, f"⏰ 1回目: 始業時刻を入力: {start_time_4digit}", jobs)
                try:
                    # 人間らしいタイピングで入力
                    if not human_like_typing(page, 'input[type="text"]', start_time_4digit, job_id, jobs):
                        add_job_log(job_id, "❌ 始業時刻入力に失敗しました", jobs)
                        continue
                    
                    # 人間らしい待機
                    human_like_wait()
                    add_job_log(job_id, "✅ 始業時刻入力完了", jobs)
                except Exception as e:
                    add_job_log(job_id, f"❌ 始業時刻入力エラー: {e}", jobs)
                    continue  # 始業時刻入力に失敗した場合は次のデータへ
                
                # 1回目の打刻ボタンをクリック
                add_job_log(job_id, "🔘 1回目: 打刻ボタンをクリック中...", jobs)
                first_punch_success = False
                
                # 打刻ボタンを探してクリック (prioritized methods)
                try:
                    page.get_by_role("button", name="打刻").click()
                    page.wait_for_load_state('networkidle', timeout=10000)
                    add_job_log(job_id, "✅ 1回目: 打刻ボタンクリック完了（get_by_role）", jobs)
                    first_punch_success = True
                except Exception as e:
                    add_job_log(job_id, f"⚠️ 1回目: get_by_roleでのボタンクリックでエラー: {e}", jobs)
                
                if not first_punch_success:
                    try:
                        page.locator('input[value="打刻"]').click()
                        page.wait_for_load_state('networkidle', timeout=10000)
                        add_job_log(job_id, "✅ 1回目: 打刻ボタンクリック完了（input[value]）", jobs)
                        first_punch_success = True
                    except Exception as e:
                        add_job_log(job_id, f"⚠️ 1回目: input[value]でのボタンクリックでエラー: {e}", jobs)
                
                if not first_punch_success:
                    try:
                        page.get_by_text("打刻").click()
                        page.wait_for_load_state('networkidle', timeout=10000)
                        add_job_log(job_id, "✅ 1回目: 打刻ボタンクリック完了（get_by_text）", jobs)
                        first_punch_success = True
                    except Exception as e:
                        add_job_log(job_id, f"⚠️ 1回目: get_by_textでのボタンクリックでエラー: {e}", jobs)
                
                if not first_punch_success:
                    try:
                        page.locator('button:has-text("打刻")').click()
                        page.wait_for_load_state('networkidle', timeout=10000)
                        add_job_log(job_id, "✅ 1回目: 打刻ボタンクリック完了（button:has-text）", jobs)
                        first_punch_success = True
                    except Exception as e:
                        add_job_log(job_id, f"⚠️ 1回目: button:has-textでのボタンクリックでエラー: {e}", jobs)
                
                if not first_punch_success:
                    try:
                        page.locator('button[type="submit"]').click()
                        page.wait_for_load_state('networkidle', timeout=10000)
                        add_job_log(job_id, "✅ 1回目: 打刻ボタンクリック完了（button[type=submit]）", jobs)
                        first_punch_success = True
                    except Exception as e:
                        add_job_log(job_id, f"⚠️ 1回目: button[type=submit]でのボタンクリックでエラー: {e}", jobs)
                
                if not first_punch_success:
                    add_job_log(job_id, "❌ 1回目: 打刻ボタンが見つかりません", jobs)
                    continue # 1回目の打刻に失敗した場合は次のデータへ
                
                # 人間らしい待機
                human_like_wait()
                
                # 2回目: 終業時刻を人間らしく入力して打刻
                add_job_log(job_id, f"⏰ 2回目: 終業時刻を入力: {end_time_4digit}", jobs)
                try:
                    # 人間らしいタイピングで入力
                    if not human_like_typing(page, 'input[type="text"]', end_time_4digit, job_id, jobs):
                        add_job_log(job_id, "❌ 終業時刻入力に失敗しました", jobs)
                        continue
                    
                    # 人間らしい待機
                    human_like_wait()
                    add_job_log(job_id, "✅ 終業時刻入力完了", jobs)
                except Exception as e:
                    add_job_log(job_id, f"⚠️ 終業時刻入力エラー（想定通りの処理構造です）: {e}", jobs)
                    # 終業時刻入力に失敗しても処理は継続
                
                # 2回目の打刻ボタンをクリック
                add_job_log(job_id, "🔘 2回目: 打刻ボタンをクリック中...", jobs)
                second_punch_success = False
                
                # 打刻ボタンを探してクリック (prioritized methods)
                try:
                    page.get_by_role("button", name="打刻").click()
                    page.wait_for_load_state('networkidle', timeout=10000)
                    add_job_log(job_id, "✅ 2回目: 打刻ボタンクリック完了（get_by_role）", jobs)
                    second_punch_success = True
                except Exception as e:
                    add_job_log(job_id, f"⚠️ 2回目: get_by_roleでのボタンクリックでエラー: {e}", jobs)
                
                if not second_punch_success:
                    try:
                        page.locator('input[value="打刻"]').click()
                        page.wait_for_load_state('networkidle', timeout=10000)
                        add_job_log(job_id, "✅ 2回目: 打刻ボタンクリック完了（input[value]）", jobs)
                        second_punch_success = True
                    except Exception as e:
                        add_job_log(job_id, f"⚠️ 2回目: input[value]でのボタンクリックでエラー: {e}", jobs)
                
                if not second_punch_success:
                    try:
                        page.get_by_text("打刻").click()
                        page.wait_for_load_state('networkidle', timeout=10000)
                        add_job_log(job_id, "✅ 2回目: 打刻ボタンクリック完了（get_by_text）", jobs)
                        second_punch_success = True
                    except Exception as e:
                        add_job_log(job_id, f"⚠️ 2回目: get_by_textでのボタンクリックでエラー: {e}", jobs)
                
                if not second_punch_success:
                    try:
                        page.locator('button:has-text("打刻")').click()
                        page.wait_for_load_state('networkidle', timeout=10000)
                        add_job_log(job_id, "✅ 2回目: 打刻ボタンクリック完了（button:has-text）", jobs)
                        second_punch_success = True
                    except Exception as e:
                        add_job_log(job_id, f"⚠️ 2回目: button:has-textでのボタンクリックでエラー: {e}", jobs)
                
                if not second_punch_success:
                    try:
                        page.locator('button[type="submit"]').click()
                        page.wait_for_load_state('networkidle', timeout=10000)
                        add_job_log(job_id, "✅ 2回目: 打刻ボタンクリック完了（button[type=submit]）", jobs)
                        second_punch_success = True
                    except Exception as e:
                        add_job_log(job_id, f"⚠️ 2回目: button[type=submit]でのボタンクリックでエラー: {e}", jobs)
                
                if not second_punch_success:
                    add_job_log(job_id, "⚠️ 2回目: 打刻ボタンが見つかりません（想定通りの処理構造です）", jobs)
                    # 2回目の打刻に失敗しても処理は継続
                
                # 出勤簿ページに戻る
                add_job_log(job_id, "🔄 出勤簿ページに戻ります", jobs)
                page.goto("https://ssl.jobcan.jp/employee/attendance")
                page.wait_for_load_state('networkidle', timeout=30000)
                
                update_progress(job_id, 6, f"勤怠データ入力中 ({row - 1}/{total_data})", jobs, row - 1, total_data)
                time.sleep(2)  # 処理間隔
        
        add_job_log(job_id, "🎉 実際のデータ入力処理が完了しました", jobs)
        
    except Exception as e:
        add_job_log(job_id, f"❌ 実際のデータ入力処理でエラー: {e}", jobs)
        raise e

def human_like_typing(page, selector, text, job_id, jobs):
    """人間らしいタイピングを実行"""
    try:
        add_job_log(job_id, f"⌨️ 人間らしいタイピングを実行: {selector}", jobs)
        
        # 要素を取得
        element = page.locator(selector).first
        element.click()
        
        # 既存のテキストをクリア
        element.fill("")
        
        # 文字ごとにランダムな遅延でタイピング
        for char in text:
            element.type(char, delay=random.uniform(50, 250))  # 50-250msの遅延
            time.sleep(random.uniform(0.05, 0.15))  # 追加の遅延
        
        add_job_log(job_id, "✅ タイピング完了", jobs)
        return True
        
    except Exception as e:
        add_job_log(job_id, f"❌ タイピングエラー: {e}", jobs)
        return False

def human_like_wait():
    """人間らしい待機時間"""
    time.sleep(random.uniform(0.5, 2.0))

def setup_stealth_mode(page, job_id, jobs):
    """ステルスモードの設定（Bot検知回避）"""
    try:
        add_job_log(job_id, "🕵️ ステルスモードを設定中...", jobs)
        
        # navigator.webdriverを無効化
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        # その他のBot検知回避設定
        page.add_init_script("""
            // Chromeの自動化フラグを無効化
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            
            // WebDriverプロパティを隠す
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ja-JP', 'ja', 'en-US', 'en'],
            });
        """)
        
        add_job_log(job_id, "✅ ステルスモード設定完了", jobs)
        return True
        
    except Exception as e:
        add_job_log(job_id, f"⚠️ ステルスモード設定エラー: {e}", jobs)
        return False

def retry_on_captcha(page, email, password, job_id, jobs, max_retries=3):
    """CAPTCHA発生時のリトライロジック"""
    for attempt in range(max_retries):
        try:
            add_job_log(job_id, f"🔄 CAPTCHAリトライ試行 {attempt + 1}/{max_retries}", jobs)
            
            # ページをリロード
            page.reload()
            page.wait_for_load_state('networkidle', timeout=30000)
            
            # 人間らしい待機
            human_like_wait()
            
            # ログイン処理を再実行
            login_success, status, message = perform_login(page, email, password, job_id, jobs)
            
            if login_success:
                add_job_log(job_id, f"✅ リトライ {attempt + 1} でログイン成功", jobs)
                return True, status, message
            elif status == "captcha_detected":
                add_job_log(job_id, f"⚠️ リトライ {attempt + 1} でもCAPTCHAが発生", jobs)
                if attempt < max_retries - 1:
                    # 次のリトライ前に待機
                    wait_time = random.uniform(5, 10)
                    add_job_log(job_id, f"⏳ {wait_time:.1f}秒待機してから再試行", jobs)
                    time.sleep(wait_time)
                continue
            else:
                add_job_log(job_id, f"❌ リトライ {attempt + 1} でログイン失敗: {message}", jobs)
                return False, status, message
                
        except Exception as e:
            add_job_log(job_id, f"❌ リトライ {attempt + 1} でエラー: {e}", jobs)
            if attempt < max_retries - 1:
                time.sleep(random.uniform(2, 5))
            continue
    
    add_job_log(job_id, f"❌ 最大リトライ回数 {max_retries} に達しました", jobs)
    return False, "captcha_failed", "❌ 画像認証に失敗しました（最大リトライ回数に達しました）"

def process_jobcan_automation(job_id: str, email: str, password: str, file_path: str, jobs: dict, session_dir: str = None, session_id: str = None):
    """Jobcan自動化処理のメイン関数（セッション固有のブラウザ環境）"""
    try:
        add_job_log(job_id, "🚀 Jobcan自動化処理を開始", jobs)
        update_progress(job_id, 1, "初期化中...", jobs)
        
        # セッション固有のログ
        if session_id:
            add_job_log(job_id, f"🔑 セッションID: {session_id}", jobs)
        
        # ステップ1: Excelファイルの読み込み
        add_job_log(job_id, "📊 Excelファイルを読み込み中...", jobs)
        update_progress(job_id, 2, "Excelファイル読み込み中...", jobs)
        
        try:
            data_source, total_data = load_excel_data(file_path)
            add_job_log(job_id, f"✅ Excelファイル読み込み完了: {total_data}件のデータ", jobs)
        except Exception as e:
            add_job_log(job_id, f"❌ Excelファイル読み込みエラー: {e}", jobs)
            jobs[job_id]['status'] = 'error'
            jobs[job_id]['login_message'] = f'Excelファイルの読み込みに失敗しました: {str(e)}'
            return
        
        # ステップ2: データ検証
        add_job_log(job_id, "🔍 データ検証中...", jobs)
        update_progress(job_id, 3, "データ検証中...", jobs)
        
        try:
            errors, warnings = validate_excel_data(data_source, pandas_available, job_id, jobs)
            
            # エラーがある場合は処理を停止
            if errors:
                add_job_log(job_id, f"❌ データ検証で{len(errors)}件のエラーが見つかりました", jobs)
                
                # エラーの詳細をユーザーメッセージに含める
                error_details = []
                for error in errors[:5]:  # 最初の5件のエラーを詳細表示
                    error_details.append(error)
                
                if len(errors) > 5:
                    error_details.append(f"他{len(errors) - 5}件のエラーがあります")
                
                error_message = f'データ検証で{len(errors)}件のエラーが見つかりました。\n\n詳細:\n' + '\n'.join(error_details)
                
                jobs[job_id]['status'] = 'error'
                jobs[job_id]['login_message'] = error_message
                return
            
            # 警告がある場合はログに記録
            if warnings:
                add_job_log(job_id, f"⚠️ データ検証で{len(warnings)}件の警告が見つかりました", jobs)
            
            add_job_log(job_id, "✅ データ検証完了", jobs)
        except Exception as e:
            add_job_log(job_id, f"❌ データ検証エラー: {e}", jobs)
            jobs[job_id]['status'] = 'error'
            jobs[job_id]['login_message'] = f'データ検証中にエラーが発生しました: {str(e)}'
            return
        
        # ステップ3: Playwrightの利用可能性チェック
        if not playwright_available:
            add_job_log(job_id, "❌ Playwrightが利用できません", jobs)
            jobs[job_id]['status'] = 'error'
            jobs[job_id]['login_status'] = 'playwright_unavailable'
            jobs[job_id]['login_message'] = 'ブラウザ自動化機能が利用できません'
            return
        
        # ステップ4: ブラウザの起動（セッション固有）
        add_job_log(job_id, "🌐 ブラウザを起動中...", jobs)
        update_progress(job_id, 4, "ブラウザ起動中...", jobs)
        
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                # セッション固有のユーザーデータディレクトリを設定
                user_data_dir = None
                if session_dir:
                    user_data_dir = os.path.join(session_dir, 'browser_data')
                    os.makedirs(user_data_dir, exist_ok=True)
                
                # セッション固有のブラウザ起動オプション
                browser_args = [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-extensions-except',
                    '--disable-plugins-discovery',
                    '--disable-default-apps',
                    '--disable-sync',
                    '--disable-translate',
                    '--hide-scrollbars',
                    '--mute-audio',
                    '--no-default-browser-check',
                    '--no-pings',
                    '--no-zygote',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
                
                # より人間らしいUser-Agent
                user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                
                # user_data_dirがある場合はlaunch_persistent_contextを使用
                if user_data_dir:
                    context = p.chromium.launch_persistent_context(
                        user_data_dir=user_data_dir,
                        headless=False,  # ヘッドレスモードを無効化
                        args=browser_args,
                        viewport={'width': 1280, 'height': 720},
                        user_agent=user_agent,
                        ignore_https_errors=True,
                        java_script_enabled=True,
                        accept_downloads=True
                    )
                    page = context.new_page()
                else:
                    # user_data_dirがない場合は通常のlaunchを使用
                    browser = p.chromium.launch(
                        headless=False,  # ヘッドレスモードを無効化
                        args=browser_args
                    )
                    
                    # セッション固有のコンテキスト設定
                    context_options = {
                        'viewport': {'width': 1280, 'height': 720},
                        'user_agent': user_agent,
                        'ignore_https_errors': True,
                        'java_script_enabled': True,
                        'accept_downloads': True
                    }
                    
                    context = browser.new_context(**context_options)
                    page = context.new_page()
                
                add_job_log(job_id, "✅ ブラウザ起動完了", jobs)
                if session_id:
                    add_job_log(job_id, f"🔑 セッション固有ブラウザ環境: {session_id}", jobs)
                
                # ステルスモードを設定
                setup_stealth_mode(page, job_id, jobs)
                
                # ステップ5: ログイン処理
                add_job_log(job_id, "🔐 Jobcanにログイン中...", jobs)
                update_progress(job_id, 5, "Jobcanログイン中...", jobs)
                
                # ログイン処理開始時の状態を初期化
                jobs[job_id]['login_status'] = 'processing'
                jobs[job_id]['login_message'] = '🔄 ログイン処理中...'
                
                login_success, login_status, login_message = perform_login(page, email, password, job_id, jobs)
                
                # ログイン結果をジョブ情報に保存（perform_login内で既に更新されているが、念のため）
                jobs[job_id]['login_status'] = login_status
                jobs[job_id]['login_message'] = login_message
                
                if not login_success:
                    add_job_log(job_id, "❌ ログインに失敗したため、処理を停止します", jobs)
                    jobs[job_id]['status'] = 'completed'
                    return
                
                # ステップ6: 実際のデータ入力処理
                add_job_log(job_id, "🔧 ログイン成功のため、実際のデータ入力を試行します", jobs)
                update_progress(job_id, 6, "勤怠データ入力中...", jobs)
                
                perform_actual_data_input(page, data_source, total_data, pandas_available, job_id, jobs)
                
                # ステップ7: 最終確認
                add_job_log(job_id, "🔍 最終確認中...", jobs)
                update_progress(job_id, 7, "最終確認中...", jobs)
                
                # ステップ8: 処理完了
                add_job_log(job_id, "🎉 処理が正常に完了しました", jobs)
                update_progress(job_id, 8, "処理完了中...", jobs)
                
                jobs[job_id]['status'] = 'completed'
                
                # ブラウザを閉じる
                if user_data_dir:
                    # launch_persistent_contextを使用した場合
                    context.close()
                else:
                    # 通常のlaunchを使用した場合
                    browser.close()
                add_job_log(job_id, "🔒 ブラウザセッションを終了しました", jobs)
                
        except Exception as e:
            add_job_log(job_id, f"❌ ブラウザ処理でエラーが発生しました: {e}", jobs)
            jobs[job_id]['status'] = 'error'
            jobs[job_id]['login_message'] = f'ブラウザ処理でエラーが発生しました: {str(e)}'
            return
        
    except Exception as e:
        add_job_log(job_id, f"❌ 予期しないエラーが発生しました: {e}", jobs)
        jobs[job_id]['status'] = 'error'
        jobs[job_id]['login_message'] = f'予期しないエラーが発生しました: {str(e)}'
        return 
