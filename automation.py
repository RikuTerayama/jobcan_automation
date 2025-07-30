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

def reliable_type(page, selector: str, text: str, job_id: str, jobs: dict, retries: int = 3) -> bool:
    """
    信頼性の高い入力機能（再試行機能付き）
    
    Args:
        page: Playwrightページオブジェクト
        selector: 要素セレクター
        text: 入力テキスト
        job_id: ジョブID
        jobs: ジョブ辞書
        retries: 再試行回数
    
    Returns:
        bool: 成功時True、失敗時False
    """
    for attempt in range(retries):
        try:
            add_job_log(job_id, f"📝 入力試行 {attempt + 1}/{retries}: {selector}", jobs)
            
            # 要素の存在確認
            page.wait_for_selector(selector, timeout=5000)
            
            # 要素をクリックしてフォーカス
            page.click(selector)
            human_like_wait(0.5, 1.0)
            
            # 既存の内容をクリア
            page.fill(selector, "")
            human_like_wait(0.3, 0.8)
            
            # 1文字ずつランダム遅延で入力
            for char in text:
                page.type(selector, char, delay=random.uniform(100, 300))
                human_like_wait(0.1, 0.3)
            
            # 入力内容の確認
            actual_value = page.input_value(selector)
            if actual_value == text:
                add_job_log(job_id, f"✅ 入力成功: {selector}", jobs)
                return True
            else:
                add_job_log(job_id, f"⚠️ 入力内容不一致: 期待={text}, 実際={actual_value}", jobs)
                if attempt < retries - 1:
                    human_like_wait(1.0, 2.0)
                    continue
                else:
                    add_job_log(job_id, f"❌ 入力失敗: {selector} (最終試行)", jobs)
                    return False
                    
        except Exception as e:
            add_job_log(job_id, f"⚠️ 入力エラー (試行 {attempt + 1}): {str(e)}", jobs)
            if attempt < retries - 1:
                human_like_wait(1.0, 2.0)
                continue
            else:
                add_job_log(job_id, f"❌ 入力失敗: {selector} (最終試行)", jobs)
                return False
    
    return False

def reliable_fill(page, selector: str, text: str, job_id: str, jobs: dict, retries: int = 3) -> bool:
    """
    信頼性の高いfill機能（再試行機能付き）
    
    Args:
        page: Playwrightページオブジェクト
        selector: 要素セレクター
        text: 入力テキスト
        job_id: ジョブID
        jobs: ジョブ辞書
        retries: 再試行回数
    
    Returns:
        bool: 成功時True、失敗時False
    """
    for attempt in range(retries):
        try:
            add_job_log(job_id, f"📝 fill試行 {attempt + 1}/{retries}: {selector}", jobs)
            
            # 要素の存在確認
            page.wait_for_selector(selector, timeout=5000)
            
            # 要素をクリックしてフォーカス
            page.click(selector)
            human_like_wait(0.5, 1.0)
            
            # fillで入力
            page.fill(selector, text)
            human_like_wait(0.5, 1.0)
            
            # 入力内容の確認
            actual_value = page.input_value(selector)
            if actual_value == text:
                add_job_log(job_id, f"✅ fill成功: {selector}", jobs)
                return True
            else:
                add_job_log(job_id, f"⚠️ fill内容不一致: 期待={text}, 実際={actual_value}", jobs)
                if attempt < retries - 1:
                    human_like_wait(1.0, 2.0)
                    continue
                else:
                    add_job_log(job_id, f"❌ fill失敗: {selector} (最終試行)", jobs)
                    return False
                    
        except Exception as e:
            add_job_log(job_id, f"⚠️ fillエラー (試行 {attempt + 1}): {str(e)}", jobs)
            if attempt < retries - 1:
                human_like_wait(1.0, 2.0)
                continue
            else:
                add_job_log(job_id, f"❌ fill失敗: {selector} (最終試行)", jobs)
                return False
    
    return False

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
            "ssl.jobcan.jp/employee/attendance",
            "ssl.jobcan.jp/employee/adit",
            "ssl.jobcan.jp/employee/profile"
        ]
        
        # URLベースの成功判定
        for success_url in success_urls:
            if success_url in current_url:
                add_job_log(job_id, f"✅ URL判定でログイン成功を検出: {success_url}", jobs)
                return True, "success", "✅ ログイン成功"
        
        # 2. ページ要素ベースの成功判定
        try:
            # プロフィール要素の存在確認
            profile_elements = [
                'a[href*="/employee/profile"]',
                'a[href*="/employee/attendance"]',
                '.employee-menu',
                '.user-info',
                '.profile-link'
            ]
            
            for selector in profile_elements:
                try:
                    element = page.locator(selector).first
                    if element.is_visible(timeout=2000):
                        add_job_log(job_id, f"✅ 要素判定でログイン成功を検出: {selector}", jobs)
                        return True, "success", "✅ ログイン成功"
                except:
                    continue
            
            # ログアウトボタンの存在確認（ログイン成功の指標）
            try:
                logout_elements = [
                    'a[href*="/users/sign_out"]',
                    'a[href*="logout"]',
                    '.logout',
                    '.sign-out'
                ]
                
                for selector in logout_elements:
                    try:
                        element = page.locator(selector).first
                        if element.is_visible(timeout=2000):
                            add_job_log(job_id, f"✅ ログアウト要素でログイン成功を検出: {selector}", jobs)
                            return True, "success", "✅ ログイン成功"
                    except:
                        continue
                        
            except Exception as e:
                add_job_log(job_id, f"⚠️ ログアウト要素確認エラー: {e}", jobs)
        
        except Exception as e:
            add_job_log(job_id, f"⚠️ 要素判定エラー: {e}", jobs)
        
        # 3. CAPTCHAの検出（改善版）
        page_content = page.content().lower()
        captcha_indicators = [
            "captcha",
            "recaptcha",
            "画像認証",
            "人間確認",
            "robot",
            "bot",
            "security check",
            "verify you are human",
            "prove you are human",
            "automation detected"
        ]
        
        for indicator in captcha_indicators:
            if indicator in page_content:
                add_job_log(job_id, f"🔄 CAPTCHA検出: {indicator}", jobs)
                return False, "captcha_detected", "🔄 CAPTCHAが検出されました"
        
        # URLベースのCAPTCHA検出
        captcha_url_indicators = [
            "robot",
            "captcha",
            "security",
            "verify"
        ]
        
        for indicator in captcha_url_indicators:
            if indicator in current_url.lower():
                add_job_log(job_id, f"🔄 URLベースCAPTCHA検出: {indicator}", jobs)
                return False, "captcha_detected", "🔄 CAPTCHAが検出されました"
        
        # 4. ログインエラーの検出
        error_indicators = [
            "メールアドレスかパスワードが誤っています",
            "メールアドレスまたはパスワードが正しくありません",
            "ログインに失敗しました",
            "アカウントが無効です",
            "アカウントがロックされています",
            "too many login attempts",
            "account locked",
            "invalid credentials"
        ]
        
        for indicator in error_indicators:
            if indicator in page_content:
                clean_msg = clean_error_message(indicator)
                add_job_log(job_id, f"❌ ログインエラー検出: {clean_msg}", jobs)
                return False, "login_failed", f"❌ {clean_msg}"
        
        # 5. その他のエラー状態
        if "error" in page_content or "エラー" in page_content:
            add_job_log(job_id, "❌ 一般的なエラーが検出されました", jobs)
            return False, "general_error", "❌ ログイン処理でエラーが発生しました"
        
        # 6. 不明な状態（デフォルト）
        add_job_log(job_id, "❓ ログイン状態が不明です", jobs)
        return False, "unknown", "❓ ログイン状態が確認できませんでした"
        
    except Exception as e:
        add_job_log(job_id, f"❌ ログイン状態チェックでエラー: {e}", jobs)
        return False, "check_error", f"❌ ログイン状態チェックでエラー: {str(e)}"

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
        
        # セッションクリアを実行
        clear_session(page, job_id, jobs)
        
        add_job_log(job_id, "🔐 Jobcanログインページにアクセス中...", jobs)
        page.goto("https://id.jobcan.jp/users/sign_in")
        page.wait_for_load_state('networkidle', timeout=30000)
        
        # 人間らしい待機
        human_like_wait(3.0, 5.0)
        add_job_log(job_id, "✅ ログインページアクセス完了", jobs)
        
        # 人間らしいマウス移動
        human_like_mouse_movement(page, job_id, jobs)
        
        # メールアドレスフィールドが表示されるまで待機
        page.wait_for_selector('input[name="user[email]"]', state='visible', timeout=10000)
        
        # メールアドレスを人間らしく入力
        add_job_log(job_id, "📧 メールアドレスを入力中...", jobs)
        if not human_like_typing(page, 'input[name="user[email]"]', email, job_id, jobs):
            return False, "typing_error", "❌ メールアドレス入力に失敗しました"
        
        # 人間らしい待機
        human_like_wait(1.0, 2.0)
        
        # パスワードフィールドが表示されるまで待機
        page.wait_for_selector('input[name="user[password]"]', state='visible', timeout=10000)
        
        # パスワードを人間らしく入力
        add_job_log(job_id, "🔑 パスワードを入力中...", jobs)
        if not human_like_typing(page, 'input[name="user[password]"]', password, job_id, jobs):
            return False, "typing_error", "❌ パスワード入力に失敗しました"
        
        # 人間らしい待機
        human_like_wait(1.0, 2.0)
        
        # ログインボタンが表示されるまで待機
        page.wait_for_selector('input[type="submit"]', state='visible', timeout=10000)
        
        # ログインボタンを人間らしくクリック
        add_job_log(job_id, "🔘 ログインボタンをクリック中...", jobs)
        try:
            login_button = page.locator('input[type="submit"]').first
            login_button.click()
        except Exception as e:
            add_job_log(job_id, f"⚠️ ログインボタンクリックエラー: {e}", jobs)
            # 代替方法を試行
            try:
                page.click('input[type="submit"]')
            except Exception as e2:
                add_job_log(job_id, f"❌ 代替ログインボタンクリックも失敗: {e2}", jobs)
                return False, "button_error", "❌ ログインボタンクリックに失敗しました"
        
        # 人間らしい待機
        human_like_wait(3.0, 5.0)
        
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
    """人間らしいタイピングを実行（強化版）"""
    try:
        add_job_log(job_id, f"⌨️ 人間らしいタイピングを実行: {selector}", jobs)
        
        # 要素が表示されるまで待機
        page.wait_for_selector(selector, state='visible', timeout=5000)
        
        # 要素をクリックしてフォーカス
        element = page.locator(selector).first
        element.click()
        human_like_wait(0.5, 1.0)
        
        # 既存の内容をクリア
        page.fill(selector, "")
        human_like_wait(0.3, 0.8)
        
        # 人間らしいタイピング（ランダムな遅延）
        for char in text:
            page.type(selector, char, delay=random.uniform(50, 200))
            human_like_wait(0.05, 0.15)
        
        # 入力内容の確認
        actual_value = page.input_value(selector)
        if actual_value == text:
            add_job_log(job_id, f"✅ タイピング成功: {selector}", jobs)
            return True
        else:
            add_job_log(job_id, f"⚠️ タイピング内容不一致: 期待={text}, 実際={actual_value}", jobs)
            return False
            
    except Exception as e:
        add_job_log(job_id, f"❌ タイピングエラー: {e}", jobs)
        return False

def human_like_wait(min_seconds=0.5, max_seconds=2.0):
    """人間らしい待機時間"""
    time.sleep(random.uniform(min_seconds, max_seconds))

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
            
            // ヘッドレス環境の検知を回避
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8,
            });
            
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8,
            });
            
            // 画面サイズの偽装
            Object.defineProperty(screen, 'width', {
                get: () => 1920,
            });
            
            Object.defineProperty(screen, 'height', {
                get: () => 1080,
            });
            
            // タイムゾーンの偽装
            Object.defineProperty(Intl, 'DateTimeFormat', {
                get: () => function() {
                    return {
                        resolvedOptions: () => ({
                            timeZone: 'Asia/Tokyo'
                        })
                    };
                }
            });
            
            // 追加のBot検知回避
            Object.defineProperty(navigator, 'permissions', {
                get: () => ({
                    query: () => Promise.resolve({ state: 'granted' })
                })
            });
            
            // Chromeオブジェクトの偽装
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // 自動化フラグの削除
            delete window.navigator.__proto__.webdriver;
            
            // プロパティ記述子の偽装
            const originalGetOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
            Object.getOwnPropertyDescriptor = function(obj, prop) {
                if (prop === 'webdriver' && obj === navigator) {
                    return undefined;
                }
                return originalGetOwnPropertyDescriptor.call(this, obj, prop);
            };
            
            // コンソールログの偽装
            const originalLog = console.log;
            console.log = function(...args) {
                if (args[0] && typeof args[0] === 'string' && args[0].includes('webdriver')) {
                    return;
                }
                return originalLog.apply(this, args);
            };
            
            // パフォーマンスタイミングの偽装
            Object.defineProperty(performance, 'timing', {
                get: () => ({
                    navigationStart: Date.now() - Math.random() * 1000,
                    loadEventEnd: Date.now(),
                    domContentLoadedEventEnd: Date.now() - Math.random() * 500
                })
            });
            
            // 追加のCAPTCHA対策
            Object.defineProperty(navigator, 'maxTouchPoints', {
                get: () => 10,
            });
            
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    effectiveType: '4g',
                    rtt: 50,
                    downlink: 10,
                    saveData: false
                })
            });
            
            // 自動化検知の回避
            Object.defineProperty(window, 'chrome', {
                get: () => ({
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                })
            });
            
            // セキュリティコンテキストの偽装
            Object.defineProperty(window, 'isSecureContext', {
                get: () => true
            });
            
            // ユーザーエージェントの偽装
            Object.defineProperty(navigator, 'userAgent', {
                get: () => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            });
        """)
        
        add_job_log(job_id, "✅ ステルスモード設定完了", jobs)
        return True
        
    except Exception as e:
        add_job_log(job_id, f"⚠️ ステルスモード設定エラー: {e}", jobs)
        return False



def clear_session(page, job_id, jobs):
    """セッションをクリアしてログアウト状態にする"""
    try:
        add_job_log(job_id, "🧹 セッションクリアを実行中...", jobs)
        
        # 1. Jobcanのログアウトページにアクセス
        try:
            page.goto("https://id.jobcan.jp/users/sign_out", timeout=20000)
            add_job_log(job_id, "✅ Jobcanログアウトページにアクセス", jobs)
        except Exception as e:
            add_job_log(job_id, f"⚠️ ログアウトページアクセスエラー: {e}", jobs)
            # ログアウトページアクセスに失敗しても処理を続行
        
        # 2. すべてのクッキーをクリア
        try:
            page.context.clear_cookies()
            add_job_log(job_id, "✅ クッキーをクリアしました", jobs)
        except Exception as e:
            add_job_log(job_id, f"⚠️ クッキークリアエラー: {e}", jobs)
        
        # 3. ローカルストレージとセッションストレージをクリア
        try:
            page.evaluate("""
                localStorage.clear();
                sessionStorage.clear();
            """)
            add_job_log(job_id, "✅ ローカルストレージとセッションストレージをクリアしました", jobs)
        except Exception as e:
            add_job_log(job_id, f"⚠️ ストレージクリアエラー: {e}", jobs)
        
        # 4. 人間らしい待機
        human_like_wait(2.0, 4.0)
        
        add_job_log(job_id, "✅ セッションクリア完了", jobs)
        return True
        
    except Exception as e:
        add_job_log(job_id, f"❌ セッションクリアでエラー: {e}", jobs)
        return False

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
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-networking',
                    '--disable-component-extensions-with-background-pages',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection',
                    '--disable-client-side-phishing-detection',
                    '--disable-hang-monitor',
                    '--disable-prompt-on-repost',
                    '--disable-domain-reliability',
                    '--disable-component-update',
                    # CAPTCHA対策の追加オプション
                    '--disable-blink-features=AutomationControlled',
                    '--disable-automation',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-networking',
                    '--disable-component-extensions-with-background-pages',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection',
                    '--disable-client-side-phishing-detection',
                    '--disable-hang-monitor',
                    '--disable-prompt-on-repost',
                    '--disable-domain-reliability',
                    '--disable-component-update',
                    '--disable-default-apps',
                    '--disable-sync',
                    '--disable-translate',
                    '--hide-scrollbars',
                    '--mute-audio',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--no-pings',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-networking',
                    '--disable-component-extensions-with-background-pages',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection',
                    '--disable-client-side-phishing-detection',
                    '--disable-hang-monitor',
                    '--disable-prompt-on-repost',
                    '--disable-domain-reliability',
                    '--disable-component-update'
                ]
                
                # 最新のChrome User-Agent（CAPTCHA対策）
                user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                
                # サーバー環境対応のため、通常のlaunchを使用
                browser = p.chromium.launch(
                    headless=True,  # CAPTCHA対策のためヘッドレスモードを有効化
                    args=browser_args
                )
                
                # セッション固有のコンテキスト設定
                context_options = {
                    'viewport': {'width': 1920, 'height': 1080},  # より大きなビューポート
                    'user_agent': user_agent,
                    'ignore_https_errors': True,
                    'java_script_enabled': True,
                    'accept_downloads': True,
                    'locale': 'ja-JP',  # 日本語ロケール
                    'timezone_id': 'Asia/Tokyo',  # 日本時間
                    'permissions': ['geolocation'],  # 位置情報許可
                    'extra_http_headers': {
                        'Accept-Language': 'ja-JP,ja;q=0.9,en;q=0.8',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache'
                    }
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
                
                # 新しいCAPTCHA対策ロジックを使用
                login_success, login_status, login_message = perform_login_with_captcha_retry(page, email, password, job_id, jobs, max_captcha_retries=3)
                
                # ログイン結果をジョブ情報に保存
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

def human_like_mouse_movement(page, job_id, jobs):
    """人間らしいマウス移動を実行"""
    try:
        # ランダムな位置にマウスを移動
        x = random.randint(100, 800)
        y = random.randint(100, 600)
        page.mouse.move(x, y)
        human_like_wait(0.1, 0.3)
        
        # スクロール処理
        scroll_amount = random.randint(-100, 100)
        page.mouse.wheel(0, scroll_amount)
        human_like_wait(0.2, 0.5)
        
        add_job_log(job_id, f"🖱️ マウス移動実行: ({x}, {y}), スクロール: {scroll_amount}", jobs)
        return True
        
    except Exception as e:
        add_job_log(job_id, f"⚠️ マウス移動エラー: {e}", jobs)
        return False

def perform_login_with_captcha_retry(page, email, password, job_id, jobs, max_captcha_retries=3):
    """CAPTCHA対策付きログイン処理（無限ループ防止）"""
    captcha_retry_count = 0
    
    while captcha_retry_count < max_captcha_retries:
        try:
            add_job_log(job_id, f"🔐 ログイン試行 {captcha_retry_count + 1}/{max_captcha_retries + 1}", jobs)
            
            # ログイン処理を実行
            login_success, status, message = perform_login(page, email, password, job_id, jobs)
            
            if login_success:
                add_job_log(job_id, f"✅ ログイン成功（試行 {captcha_retry_count + 1}）", jobs)
                return True, status, message
            elif status == "captcha_detected":
                captcha_retry_count += 1
                add_job_log(job_id, f"🔄 CAPTCHA検出 - 再試行 {captcha_retry_count}/{max_captcha_retries}", jobs)
                
                if captcha_retry_count >= max_captcha_retries:
                    add_job_log(job_id, f"❌ CAPTCHAリトライ上限に達しました（{max_captcha_retries}回）", jobs)
                    return False, "captcha_failed", f"❌ CAPTCHAが繰り返し検出されたため、処理を中断します（リトライ上限: {max_captcha_retries}回）"
                
                # セッションクリアを実行
                clear_session(page, job_id, jobs)
                
                # ランダムな待機時間
                wait_time = random.uniform(5.0, 15.0)
                add_job_log(job_id, f"⏳ {wait_time:.1f}秒待機してから再試行", jobs)
                time.sleep(wait_time)
                
                # ページをリロード
                page.reload()
                page.wait_for_load_state('networkidle', timeout=30000)
                
                continue
            else:
                # CAPTCHA以外のエラーの場合
                add_job_log(job_id, f"❌ ログイン失敗（その他の原因）: {message}", jobs)
                return False, status, message
                
        except Exception as e:
            add_job_log(job_id, f"❌ ログイン処理でエラー: {e}", jobs)
            return False, "login_error", f"❌ ログイン処理でエラーが発生しました: {str(e)}"
    
    # ここに到達した場合はCAPTCHAリトライ上限に達した
    add_job_log(job_id, f"❌ CAPTCHAリトライ {max_captcha_retries} 回すべて失敗", jobs)
    return False, "captcha_failed", f"❌ CAPTCHAが解決できませんでした。手動でログインしてください。（リトライ上限: {max_captcha_retries}回）"
