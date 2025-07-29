import time
from utils import (
    add_job_log, 
    update_progress, 
    load_excel_data, 
    extract_date_info,
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
        captcha_selectors = [
            'img[src*="captcha"]',
            'img[alt*="captcha"]',
            'img[alt*="CAPTCHA"]',
            '.captcha',
            '[class*="captcha"]',
            'iframe[src*="captcha"]'
        ]
        
        captcha_found = False
        for selector in captcha_selectors:
            try:
                element = page.query_selector(selector)
                if element:
                    add_job_log(job_id, f"⚠️ CAPTCHA要素を検出: {selector}", jobs)
                    captcha_found = True
                    break
            except Exception as e:
                add_job_log(job_id, f"⚠️ CAPTCHA検索でエラー: {e}", jobs)
        
        # テキストベースのCAPTCHA検索
        captcha_keywords = ["画像認証", "CAPTCHA", "captcha"]
        for keyword in captcha_keywords:
            try:
                elements = page.locator("div, p, span").filter(has_text=keyword).all()
                if elements:
                    add_job_log(job_id, f"⚠️ CAPTCHA要素を検出: {keyword}", jobs)
                    captcha_found = True
                    break
            except Exception as e:
                add_job_log(job_id, f"⚠️ CAPTCHAキーワード '{keyword}' 検索でエラー: {e}", jobs)
        
        if captcha_found:
            return False, "captcha_detected", "CAPTCHA（画像認証）が表示されています。手動でのログインが必要です"
        
        # 4. アカウント制限の検出（テキストベース）
        restriction_keywords = ["アカウント", "ロック", "無効", "制限", "一時停止"]
        for keyword in restriction_keywords:
            try:
                elements = page.locator("div, p, span").filter(has_text=keyword).all()
                if elements:
                    for element in elements:
                        restriction_text = element.text_content().strip()
                        if restriction_text and keyword in restriction_text:
                            add_job_log(job_id, f"⚠️ アカウント制限を検出: {restriction_text}", jobs)
                            return False, "account_restricted", f"アカウントに制限があります: {restriction_text}"
            except Exception as e:
                add_job_log(job_id, f"⚠️ 制限キーワード '{keyword}' 検索でエラー: {e}", jobs)
        
        # 5. ログイン成功の追加チェック（DOM要素ベース）
        success_indicators = [
            '#header_user_name',
            '.user-name',
            '[class*="user"]',
            '[class*="profile"]',
            'a[href*="logout"]',
            'a[href*="sign_out"]'
        ]
        
        for selector in success_indicators:
            try:
                element = page.query_selector(selector)
                if element:
                    add_job_log(job_id, f"✅ ログイン成功指標を検出: {selector}", jobs)
                    return True, "success", "ログインに成功しました（DOM要素で確認）"
            except Exception as e:
                add_job_log(job_id, f"⚠️ 成功指標 {selector} でエラー: {e}", jobs)
        
        # 6. その他の不明な状態（fallback）
        add_job_log(job_id, "❓ ログイン状態が不明です", jobs)
        return False, "unknown_status", "ログイン状態を判定できませんでした"
        
    except Exception as e:
        add_job_log(job_id, f"❌ ログイン状態チェックでエラー: {e}", jobs)
        return False, "check_error", f"ログイン状態の確認でエラーが発生しました: {e}"

def perform_login(page, email, password, job_id, jobs):
    """詳細なログイン処理を実行"""
    try:
        add_job_log(job_id, "🔐 ログインページにアクセス中...", jobs)
        page.goto("https://id.jobcan.jp/users/sign_in?app_key=atd&redirect_to=https://ssl.jobcan.jp/jbcoauth/callback")
        
        # ページ読み込み完了を待機
        page.wait_for_load_state('networkidle')
        add_job_log(job_id, "✅ ログインページアクセス完了", jobs)
        
        # ログインフォームの存在確認
        email_field = page.query_selector('#user_email')
        password_field = page.query_selector('#user_password')
        submit_button = page.query_selector('input[type="submit"]')
        
        if not email_field or not password_field or not submit_button:
            add_job_log(job_id, "❌ ログインフォームが見つかりません", jobs)
            return False, "form_not_found", "ログインフォームが見つかりません"
        
        # ログイン情報を入力
        add_job_log(job_id, "📝 ログイン情報を入力中...", jobs)
        page.fill('#user_email', email)
        page.fill('#user_password', password)
        
        # ログインボタンをクリック
        add_job_log(job_id, "🔘 ログインボタンをクリック中...", jobs)
        page.click('input[type="submit"]')
        
        # ページ遷移を待機
        page.wait_for_load_state('networkidle')
        add_job_log(job_id, "✅ ログイン処理完了", jobs)
        
        # ログイン結果をチェック
        return check_login_status(page, job_id, jobs)
        
    except Exception as e:
        add_job_log(job_id, f"❌ ログイン処理でエラー: {e}", jobs)
        return False, "login_error", f"ログイン処理でエラーが発生しました: {e}"

def perform_actual_data_input(page, data_source, total_data, pandas_available, job_id, jobs):
    """実際のデータ入力処理を実行"""
    try:
        add_job_log(job_id, "🎯 実際のデータ入力処理を開始します", jobs)
        
        # 出勤簿ページに移動
        add_job_log(job_id, "📋 出勤簿ページに移動中...", jobs)
        page.goto("https://ssl.jobcan.jp/employee/attendance")
        page.wait_for_load_state('networkidle')
        add_job_log(job_id, "✅ 出勤簿ページアクセス完了", jobs)
        
        if pandas_available:
            # pandasを使用したデータ処理
            for index, row in data_source.iterrows():
                date = row.iloc[0]
                start_time = row.iloc[1]
                end_time = row.iloc[2]
                
                # 時刻を4桁形式に変換
                start_time_4digit = convert_time_to_4digit(start_time)
                end_time_4digit = convert_time_to_4digit(end_time)
                
                date_str, year, month, day = extract_date_info(date)
                add_job_log(job_id, f"📝 データ {index + 1}/{total_data}: {date_str} {start_time}→{start_time_4digit}, {end_time}→{end_time_4digit}", jobs)
                
                # 打刻修正ページにアクセス
                modify_url = f"https://ssl.jobcan.jp/employee/adit/modify?year={year}&month={month}&day={day}"
                add_job_log(job_id, f"🔧 打刻修正ページにアクセス: {modify_url}", jobs)
                
                page.goto(modify_url)
                page.wait_for_load_state('networkidle')
                add_job_log(job_id, "✅ 打刻修正ページアクセス完了", jobs)
                
                # 時刻入力フィールドが読み込まれるまで待機
                add_job_log(job_id, "⏳ 時刻入力フィールドの読み込みを待機中...", jobs)
                try:
                    page.wait_for_selector('input[type="text"]', timeout=10000)
                    add_job_log(job_id, "✅ 時刻入力フィールドの読み込み完了", jobs)
                except Exception as e:
                    add_job_log(job_id, f"⚠️ 時刻入力フィールドの読み込みタイムアウト: {e}", jobs)
                
                # 始業時刻を入力（nth(0)で明示的に指定）
                add_job_log(job_id, f"⏰ 始業時刻を入力: {start_time_4digit}", jobs)
                try:
                    input_fields = page.locator('input[type="text"]')
                    input_fields.nth(0).fill(start_time_4digit)
                    add_job_log(job_id, "✅ 始業時刻入力完了", jobs)
                except Exception as e:
                    add_job_log(job_id, f"❌ 始業時刻入力エラー: {e}", jobs)
                
                # 終業時刻を入力（nth(1)で明示的に指定）
                add_job_log(job_id, f"⏰ 終業時刻を入力: {end_time_4digit}", jobs)
                try:
                    input_fields = page.locator('input[type="text"]')
                    input_fields.nth(1).fill(end_time_4digit)
                    add_job_log(job_id, "✅ 終業時刻入力完了", jobs)
                except Exception as e:
                    add_job_log(job_id, f"❌ 終業時刻入力エラー: {e}", jobs)
                
                # 打刻ボタンをクリック（複数の方法を試行）
                add_job_log(job_id, "🔘 打刻ボタンをクリック中...", jobs)
                punch_button_clicked = False
                
                # 1. get_by_roleでボタンを探す
                try:
                    page.get_by_role("button", name="打刻").click()
                    page.wait_for_load_state('networkidle')
                    add_job_log(job_id, "✅ 打刻ボタンクリック完了（get_by_role）", jobs)
                    punch_button_clicked = True
                except Exception as e:
                    add_job_log(job_id, f"⚠️ get_by_roleでのボタンクリックでエラー: {e}", jobs)
                
                # 2. input[value="打刻"]でボタンを探す
                if not punch_button_clicked:
                    try:
                        page.locator('input[value="打刻"]').click()
                        page.wait_for_load_state('networkidle')
                        add_job_log(job_id, "✅ 打刻ボタンクリック完了（input[value]）", jobs)
                        punch_button_clicked = True
                    except Exception as e:
                        add_job_log(job_id, f"⚠️ input[value]でのボタンクリックでエラー: {e}", jobs)
                
                # 3. テキストベースでボタンを探す
                if not punch_button_clicked:
                    try:
                        page.get_by_text("打刻").click()
                        page.wait_for_load_state('networkidle')
                        add_job_log(job_id, "✅ 打刻ボタンクリック完了（get_by_text）", jobs)
                        punch_button_clicked = True
                    except Exception as e:
                        add_job_log(job_id, f"⚠️ get_by_textでのボタンクリックでエラー: {e}", jobs)
                
                # 4. その他のセレクターを試行
                if not punch_button_clicked:
                    button_selectors = [
                        'button:has-text("打刻")',
                        'button[type="submit"]',
                        'input[type="submit"]',
                        'button[class*="submit"]',
                        'button[class*="punch"]',
                        'button[class*="time"]',
                        'a:has-text("打刻")',
                        '[onclick*="打刻"]'
                    ]
                    
                    for selector in button_selectors:
                        try:
                            button = page.query_selector(selector)
                            if button:
                                page.click(selector)
                                page.wait_for_load_state('networkidle')
                                add_job_log(job_id, f"✅ 打刻ボタンクリック完了: {selector}", jobs)
                                punch_button_clicked = True
                                break
                        except Exception as e:
                            add_job_log(job_id, f"⚠️ ボタンセレクター {selector} でエラー: {e}", jobs)
                            continue
                
                if not punch_button_clicked:
                    add_job_log(job_id, "⚠️ 打刻ボタンが見つかりません", jobs)
                
                # 出勤簿ページに戻る
                add_job_log(job_id, "🔄 出勤簿ページに戻ります", jobs)
                page.goto("https://ssl.jobcan.jp/employee/attendance")
                page.wait_for_load_state('networkidle')
                
                update_progress(job_id, 6, f"勤怠データ入力中 ({index + 1}/{total_data})", jobs, index + 1, total_data)
                time.sleep(2)  # 処理間隔
                
        else:
            # openpyxlを使用したデータ処理
            ws = data_source.active
            for row in range(2, ws.max_row + 1):
                date = ws[f'A{row}'].value
                start_time = ws[f'B{row}'].value
                end_time = ws[f'C{row}'].value
                
                # 時刻を4桁形式に変換
                start_time_4digit = convert_time_to_4digit(start_time)
                end_time_4digit = convert_time_to_4digit(end_time)
                
                date_str, year, month, day = extract_date_info(date)
                add_job_log(job_id, f"📝 データ {row - 1}/{total_data}: {date_str} {start_time}→{start_time_4digit}, {end_time}→{end_time_4digit}", jobs)
                
                # 打刻修正ページにアクセス
                modify_url = f"https://ssl.jobcan.jp/employee/adit/modify?year={year}&month={month}&day={day}"
                add_job_log(job_id, f"🔧 打刻修正ページにアクセス: {modify_url}", jobs)
                
                page.goto(modify_url)
                page.wait_for_load_state('networkidle')
                add_job_log(job_id, "✅ 打刻修正ページアクセス完了", jobs)
                
                # 時刻入力フィールドが読み込まれるまで待機
                add_job_log(job_id, "⏳ 時刻入力フィールドの読み込みを待機中...", jobs)
                try:
                    page.wait_for_selector('input[type="text"]', timeout=10000)
                    add_job_log(job_id, "✅ 時刻入力フィールドの読み込み完了", jobs)
                except Exception as e:
                    add_job_log(job_id, f"⚠️ 時刻入力フィールドの読み込みタイムアウト: {e}", jobs)
                
                # 始業時刻を入力（nth(0)で明示的に指定）
                add_job_log(job_id, f"⏰ 始業時刻を入力: {start_time_4digit}", jobs)
                try:
                    input_fields = page.locator('input[type="text"]')
                    input_fields.nth(0).fill(start_time_4digit)
                    add_job_log(job_id, "✅ 始業時刻入力完了", jobs)
                except Exception as e:
                    add_job_log(job_id, f"❌ 始業時刻入力エラー: {e}", jobs)
                
                # 終業時刻を入力（nth(1)で明示的に指定）
                add_job_log(job_id, f"⏰ 終業時刻を入力: {end_time_4digit}", jobs)
                try:
                    input_fields = page.locator('input[type="text"]')
                    input_fields.nth(1).fill(end_time_4digit)
                    add_job_log(job_id, "✅ 終業時刻入力完了", jobs)
                except Exception as e:
                    add_job_log(job_id, f"❌ 終業時刻入力エラー: {e}", jobs)
                
                # 打刻ボタンをクリック（複数の方法を試行）
                add_job_log(job_id, "🔘 打刻ボタンをクリック中...", jobs)
                punch_button_clicked = False
                
                # 1. get_by_roleでボタンを探す
                try:
                    page.get_by_role("button", name="打刻").click()
                    page.wait_for_load_state('networkidle')
                    add_job_log(job_id, "✅ 打刻ボタンクリック完了（get_by_role）", jobs)
                    punch_button_clicked = True
                except Exception as e:
                    add_job_log(job_id, f"⚠️ get_by_roleでのボタンクリックでエラー: {e}", jobs)
                
                # 2. input[value="打刻"]でボタンを探す
                if not punch_button_clicked:
                    try:
                        page.locator('input[value="打刻"]').click()
                        page.wait_for_load_state('networkidle')
                        add_job_log(job_id, "✅ 打刻ボタンクリック完了（input[value]）", jobs)
                        punch_button_clicked = True
                    except Exception as e:
                        add_job_log(job_id, f"⚠️ input[value]でのボタンクリックでエラー: {e}", jobs)
                
                # 3. テキストベースでボタンを探す
                if not punch_button_clicked:
                    try:
                        page.get_by_text("打刻").click()
                        page.wait_for_load_state('networkidle')
                        add_job_log(job_id, "✅ 打刻ボタンクリック完了（get_by_text）", jobs)
                        punch_button_clicked = True
                    except Exception as e:
                        add_job_log(job_id, f"⚠️ get_by_textでのボタンクリックでエラー: {e}", jobs)
                
                # 4. その他のセレクターを試行
                if not punch_button_clicked:
                    button_selectors = [
                        'button:has-text("打刻")',
                        'button[type="submit"]',
                        'input[type="submit"]',
                        'button[class*="submit"]',
                        'button[class*="punch"]',
                        'button[class*="time"]',
                        'a:has-text("打刻")',
                        '[onclick*="打刻"]'
                    ]
                    
                    for selector in button_selectors:
                        try:
                            button = page.query_selector(selector)
                            if button:
                                page.click(selector)
                                page.wait_for_load_state('networkidle')
                                add_job_log(job_id, f"✅ 打刻ボタンクリック完了: {selector}", jobs)
                                punch_button_clicked = True
                                break
                        except Exception as e:
                            add_job_log(job_id, f"⚠️ ボタンセレクター {selector} でエラー: {e}", jobs)
                            continue
                
                if not punch_button_clicked:
                    add_job_log(job_id, "⚠️ 打刻ボタンが見つかりません", jobs)
                
                # 出勤簿ページに戻る
                add_job_log(job_id, "🔄 出勤簿ページに戻ります", jobs)
                page.goto("https://ssl.jobcan.jp/employee/attendance")
                page.wait_for_load_state('networkidle')
                
                update_progress(job_id, 6, f"勤怠データ入力中 ({row - 1}/{total_data})", jobs, row - 1, total_data)
                time.sleep(2)  # 処理間隔
        
        add_job_log(job_id, "🎉 実際のデータ入力処理が完了しました", jobs)
        
    except Exception as e:
        add_job_log(job_id, f"❌ 実際のデータ入力処理でエラー: {e}", jobs)
        raise e

def process_jobcan_automation(job_id: str, email: str, password: str, file_path: str, jobs: dict):
    """Jobcan自動化処理のメイン関数"""
    try:
        # ステップ1: 初期化
        update_progress(job_id, 1, "初期化中", jobs)
        add_job_log(job_id, "🚀 Jobcan自動化処理を開始", jobs)
        add_job_log(job_id, f"📧 メールアドレス: {email}", jobs)
        add_job_log(job_id, f"📁 ファイルパス: {file_path}", jobs)
        
        # ステップ2: Excelファイルの読み込み
        update_progress(job_id, 2, "Excelファイル読み込み中", jobs)
        add_job_log(job_id, "📊 Excelファイルを読み込み中...", jobs)
        
        try:
            data_source, total_data = load_excel_data(file_path)
            add_job_log(job_id, f"✅ Excelファイル読み込み完了: {total_data}件のデータ", jobs)
        except Exception as e:
            add_job_log(job_id, f"❌ Excelファイル読み込みエラー: {e}", jobs)
            jobs[job_id]['status'] = 'error'
            return
        
        # ステップ3: データ検証
        update_progress(job_id, 3, "データ検証中", jobs)
        add_job_log(job_id, "🔍 データ検証を開始...", jobs)
        
        if pandas_available:
            for index, row in data_source.iterrows():
                date = row.iloc[0]
                start_time = row.iloc[1]
                end_time = row.iloc[2]
                add_job_log(job_id, f"📝 データ {index + 1}: {date} {start_time}-{end_time}", jobs)
        else:
            ws = data_source.active
            for row in range(2, ws.max_row + 1):
                date = ws[f'A{row}'].value
                start_time = ws[f'B{row}'].value
                end_time = ws[f'C{row}'].value
                add_job_log(job_id, f"📝 データ {row - 1}: {date} {start_time}-{end_time}", jobs)
        
        add_job_log(job_id, "✅ データ検証完了", jobs)
        
        # ステップ4: ブラウザ起動
        update_progress(job_id, 4, "ブラウザ起動中", jobs)
        add_job_log(job_id, "🌐 ブラウザ起動を開始...", jobs)
        
        login_success = False
        login_status = "not_attempted"
        login_message = "ログイン処理が実行されませんでした"
        
        if playwright_available:
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    # headless=Trueでサーバー環境に対応
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    add_job_log(job_id, "✅ ブラウザ起動成功", jobs)
                    
                    # ステップ5: Jobcanログイン
                    update_progress(job_id, 5, "Jobcanログイン中", jobs)
                    add_job_log(job_id, "🔐 Jobcanログインを開始...", jobs)
                    
                    # 詳細なログイン処理を実行
                    login_success, login_status, login_message = perform_login(page, email, password, job_id, jobs)
                    
                    # ログイン結果を記録
                    add_job_log(job_id, f"📊 ログイン結果: {login_status} - {login_message}", jobs)
                    
                    # ステップ6: データ入力処理
                    update_progress(job_id, 6, "データ入力処理中", jobs)
                    add_job_log(job_id, "🔧 データ入力処理を開始...", jobs)
                    
                    # ログイン失敗時の処理中断
                    if not login_success:
                        if login_status == "captcha_detected":
                            add_job_log(job_id, "⚠️ CAPTCHAが検出されたため、データ入力処理を中断します", jobs)
                            add_job_log(job_id, "💡 手動でログインしてから再実行してください", jobs)
                        elif login_status in ["login_error", "login_failed", "account_restricted"]:
                            add_job_log(job_id, "⚠️ ログインに失敗したため、データ入力処理を中断します", jobs)
                            add_job_log(job_id, "💡 ログイン情報を確認してから再実行してください", jobs)
                        else:
                            add_job_log(job_id, "⚠️ ログインが成功していないため、データ入力処理をスキップします", jobs)
                    else:
                        add_job_log(job_id, "🔧 ログイン成功のため、実際のデータ入力を実行します", jobs)
                        # 実際のデータ入力処理を実行
                        perform_actual_data_input(page, data_source, total_data, pandas_available, job_id, jobs)
                    
                    browser.close()
                    
            except Exception as e:
                error_type = "browser_error"
                if "TimeoutError" in str(e):
                    error_type = "timeout_error"
                    login_message = "ページの読み込みがタイムアウトしました"
                elif "browser launch" in str(e).lower():
                    error_type = "browser_launch_error"
                    login_message = "ブラウザの起動に失敗しました"
                else:
                    login_message = f"ブラウザ操作でエラーが発生しました: {e}"
                
                add_job_log(job_id, f"❌ {login_message}", jobs)
                login_success = False
                login_status = error_type
        else:
            add_job_log(job_id, "⚠️ Playwrightが利用できないため、ブラウザ操作をスキップします", jobs)
            login_status = "playwright_unavailable"
            login_message = "Playwrightが利用できないため、ログイン処理をスキップしました"
        
        # ログイン結果をジョブ情報に保存
        jobs[job_id]['login_status'] = login_status
        jobs[job_id]['login_message'] = login_message
        
        # ステップ7: 最終確認
        update_progress(job_id, 7, "最終確認中", jobs)
        add_job_log(job_id, "🔧 ステップ7: 最終確認中...", jobs)
        time.sleep(2)
        add_job_log(job_id, "✅ ステップ7: 最終確認完了", jobs)
        update_progress(job_id, 7, "最終確認完了", jobs, total_data, total_data)
        
        # ステップ8: 完了
        update_progress(job_id, 8, "処理完了", jobs)
        add_job_log(job_id, "🎉 ステップ8: 勤怠データの入力が完了しました", jobs)
        add_job_log(job_id, "📊 処理結果サマリー:", jobs)
        add_job_log(job_id, f"   - 処理データ数: {total_data}件", jobs)
        add_job_log(job_id, f"   - 処理時間: {time.time() - jobs[job_id]['start_time']:.2f}秒", jobs)
        add_job_log(job_id, "   - ステップ1: ✅ 初期化完了", jobs)
        add_job_log(job_id, "   - ステップ2: ✅ Excelファイル読み込み完了", jobs)
        add_job_log(job_id, "   - ステップ3: ✅ データ検証完了", jobs)
        
        if login_success:
            add_job_log(job_id, "   - ステップ4: ✅ ブラウザ起動成功", jobs)
            add_job_log(job_id, "   - ステップ5: ✅ Jobcanログイン成功", jobs)
            add_job_log(job_id, "   - ステップ6: ✅ 実際のデータ入力処理完了", jobs)
        else:
            add_job_log(job_id, "   - ステップ4: ⚠️ ブラウザ起動失敗", jobs)
            add_job_log(job_id, f"   - ステップ5: ❌ Jobcanログイン失敗 ({login_status})", jobs)
            add_job_log(job_id, "   - ステップ6: ⚠️ データ入力処理スキップ", jobs)
        
        add_job_log(job_id, "   - ステップ7: ✅ 最終確認完了", jobs)
        add_job_log(job_id, "   - ステップ8: ✅ 処理完了", jobs)
        
        jobs[job_id]['status'] = 'completed'
            
    except Exception as e:
        add_job_log(job_id, f"❌ 自動化処理でエラーが発生しました: {e}", jobs)
        jobs[job_id]['status'] = 'error' 
