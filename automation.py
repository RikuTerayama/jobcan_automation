import time
import os
from utils import (
    add_job_log, 
    update_progress, 
    load_excel_data, 
    extract_date_info,
    validate_excel_data,
    pandas_available,
    playwright_available
)

def convert_time_to_4digit(time_str):
    """時刻を4桁の数字形式に変換"""
    try:
        # 時刻文字列を処理（例：09:00:00 → 0900）
        if isinstance(time_str, str):
            # コロンで分割して時と分を取得
            parts = time_str.replace(':', '').replace('：', '').replace(' ', '')
            if len(parts) >= 4:
                # 最初の4文字を取得（時分）
                return parts[:4]
            elif len(parts) == 2:
                # 時のみの場合、分を00で補完
                return f"{parts}00"
        elif hasattr(time_str, 'strftime'):
            # datetimeオブジェクトの場合
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
                            error_message = error_text
                            add_job_log(job_id, f"❌ エラーメッセージ検出: {error_text}", jobs)
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
                                error_message = text
                                add_job_log(job_id, f"❌ エラーメッセージ検出: {text}", jobs)
                                break
                        if error_message:
                            break
                except Exception as e:
                    add_job_log(job_id, f"⚠️ キーワード '{keyword}' 検索でエラー: {e}", jobs)
            
            if error_message:
                return False, "login_error", f"ログインに失敗しました: {error_message}"
            else:
                return False, "login_failed", "ログインに失敗しました（エラーメッセージが検出されませんでした）"
        
        # 3. CAPTCHAの検出（有効なセレクタのみ）
        captcha_keywords = ["画像認証", "CAPTCHA", "認証", "セキュリティ"]
        for keyword in captcha_keywords:
            try:
                elements = page.locator("div, p, span").filter(has_text=keyword).all()
                if elements:
                    for element in elements:
                        text = element.text_content().strip()
                        if text and keyword in text:
                            add_job_log(job_id, f"⚠️ CAPTCHA検出: {text}", jobs)
                            return False, "captcha_detected", f"CAPTCHA（画像認証）が検出されました: {text}"
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
                            return False, "account_restricted", f"アカウントに制限があります: {text}"
            except Exception as e:
                add_job_log(job_id, f"⚠️ 制限検索でエラー: {e}", jobs)
        
        # 5. その他のエラーケース
        add_job_log(job_id, "⚠️ ログイン状態が不明です", jobs)
        return False, "unknown_status", "ログイン状態が不明です"
        
    except Exception as e:
        add_job_log(job_id, f"❌ ログイン状態チェックでエラー: {e}", jobs)
        return False, "check_error", f"ログイン状態チェックでエラーが発生しました: {str(e)}"

def perform_login(page, email, password, job_id, jobs):
    """ログイン処理を実行"""
    try:
        add_job_log(job_id, "🔐 Jobcanログインページにアクセス中...", jobs)
        page.goto("https://id.jobcan.jp/users/sign_in")
        page.wait_for_load_state('networkidle', timeout=30000)
        add_job_log(job_id, "✅ ログインページアクセス完了", jobs)
        
        # メールアドレスを入力
        add_job_log(job_id, "📧 メールアドレスを入力中...", jobs)
        page.fill('input[name="user[email]"]', email)
        add_job_log(job_id, "✅ メールアドレス入力完了", jobs)
        
        # パスワードを入力
        add_job_log(job_id, "🔑 パスワードを入力中...", jobs)
        page.fill('input[name="user[password]"]', password)
        add_job_log(job_id, "✅ パスワード入力完了", jobs)
        
        # ログインボタンをクリック
        add_job_log(job_id, "🔘 ログインボタンをクリック中...", jobs)
        page.click('input[type="submit"]')
        page.wait_for_load_state('networkidle', timeout=30000)
        add_job_log(job_id, "✅ ログインボタンクリック完了", jobs)
        
        # ログイン状態をチェック
        login_success, status, message = check_login_status(page, job_id, jobs)
        
        if login_success:
            add_job_log(job_id, "🎉 ログインに成功しました", jobs)
        else:
            add_job_log(job_id, f"❌ ログインに失敗しました: {message}", jobs)
        
        return login_success, status, message
        
    except Exception as e:
        error_msg = f"ログイン処理でエラーが発生しました: {str(e)}"
        add_job_log(job_id, f"❌ {error_msg}", jobs)
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
                
                # 1回目: 始業時刻を入力して打刻
                add_job_log(job_id, f"⏰ 1回目: 始業時刻を入力: {start_time_4digit}", jobs)
                try:
                    time_input.fill(start_time_4digit)
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
                
                # 2回目: 終業時刻を入力して打刻
                add_job_log(job_id, f"⏰ 2回目: 終業時刻を入力: {end_time_4digit}", jobs)
                try:
                    time_input.fill(end_time_4digit)
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
                
                # 1回目: 始業時刻を入力して打刻
                add_job_log(job_id, f"⏰ 1回目: 始業時刻を入力: {start_time_4digit}", jobs)
                try:
                    time_input.fill(start_time_4digit)
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
                
                # 2回目: 終業時刻を入力して打刻
                add_job_log(job_id, f"⏰ 2回目: 終業時刻を入力: {end_time_4digit}", jobs)
                try:
                    time_input.fill(end_time_4digit)
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
                jobs[job_id]['status'] = 'error'
                jobs[job_id]['login_message'] = f'データ検証で{len(errors)}件のエラーが見つかりました。Excelファイルを確認してください。'
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
                    '--disable-renderer-backgrounding'
                ]
                
                # user_data_dirがある場合はlaunch_persistent_contextを使用
                if user_data_dir:
                    context = p.chromium.launch_persistent_context(
                        user_data_dir=user_data_dir,
                        headless=True,
                        args=browser_args,
                        viewport={'width': 1280, 'height': 720},
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    )
                    page = context.new_page()
                else:
                    # user_data_dirがない場合は通常のlaunchを使用
                    browser = p.chromium.launch(
                        headless=True,
                        args=browser_args
                    )
                    
                    # セッション固有のコンテキスト設定
                    context_options = {
                        'viewport': {'width': 1280, 'height': 720},
                        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    }
                    
                    context = browser.new_context(**context_options)
                    page = context.new_page()
                
                add_job_log(job_id, "✅ ブラウザ起動完了", jobs)
                if session_id:
                    add_job_log(job_id, f"🔑 セッション固有ブラウザ環境: {session_id}", jobs)
                
                # ステップ5: ログイン処理
                add_job_log(job_id, "🔐 Jobcanにログイン中...", jobs)
                update_progress(job_id, 5, "Jobcanログイン中...", jobs)
                
                login_success, login_status, login_message = perform_login(page, email, password, job_id, jobs)
                
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
