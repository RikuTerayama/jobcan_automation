import time
import random
import pandas as pd
from playwright.sync_api import sync_playwright
from typing import List, Dict, Optional


class JobcanAutomation:
    """Jobcan勤怠自動化クラス（同期版）"""
    
    def __init__(self, headless: bool = True):
        self.playwright = None
        self.browser = None
        self.page = None
        self.headless = headless
        self.diagnosis_data = {}
    
    def get_diagnosis_data(self):
        """診断データを取得"""
        return self.diagnosis_data
    
    def start_browser(self):
        """ブラウザを起動"""
        try:
            print("Playwrightを初期化中...")
            self.playwright = sync_playwright().start()
            
            # ブラウザの起動オプションを設定
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
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection',
                '--disable-background-networking',
                '--disable-default-apps',
                '--disable-sync',
                '--disable-translate',
                '--hide-scrollbars',
                '--mute-audio',
                '--no-first-run',
                '--safebrowsing-disable-auto-update',
                '--disable-client-side-phishing-detection',
                '--disable-component-update',
                '--disable-domain-reliability',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection'
            ]
            
            print("Chromiumブラウザを起動中...")
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=browser_args
            )
            
            print("新しいページを作成中...")
            self.page = self.browser.new_page()
            
            # より人間らしいユーザーエージェントを設定
            self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'ja-JP,ja;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
            
            # JavaScriptを有効化（ログインに必要）
            print("JavaScriptを有効化")
            
            # ボット検出を回避するための設定
            self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ja-JP', 'ja', 'en'],
                });
            """)
            
            print("ブラウザ起動完了")
            
        except Exception as e:
            error_msg = f"ブラウザの起動に失敗しました: {e}"
            print(error_msg)
            raise
    
    def login_to_jobcan_alternative(self, email: str, password: str) -> bool:
        """Jobcanにログイン（代替方法）"""
        try:
            print("=== 代替ログイン方法を試行 ===")
            
            # 異なるURLを試行
            print("代替URLでログイン試行: https://ssl.jobcan.jp/employee")
            self.page.goto("https://ssl.jobcan.jp/employee")
            time.sleep(2)
            self.page.wait_for_load_state("networkidle")
            
            # ログイン処理を再試行
            return self.perform_login_action(email, password)
            
        except Exception as e:
            print(f"代替ログイン方法でエラー: {e}")
            return False

    def perform_login_action(self, email: str, password: str):
        """ログインアクションを実行"""
        try:
            # メールアドレス入力
            email_input = self.page.locator('input[name="email"], input[name="staff_code"], input[type="email"]').first
            email_input.fill(email)
            
            # パスワード入力
            password_input = self.page.locator('input[name="password"], input[type="password"]').first
            password_input.fill(password)
            
            # ログインボタンクリック
            login_button = self.page.locator('input[type="submit"], button[type="submit"]').first
            login_button.click()
            
            time.sleep(3)
            self.page.wait_for_load_state("networkidle")
            
            return "sign_in" not in self.page.url and "login" not in self.page.url
            
        except Exception as e:
            print(f"ログインアクションでエラー: {e}")
            return False
    
    def check_for_captcha(self):
        """CAPTCHAの検出"""
        try:
            captcha_selectors = [
                'iframe[src*="recaptcha"]',
                'iframe[src*="captcha"]',
                '.g-recaptcha',
                '.recaptcha',
                '[class*="captcha"]',
                'img[src*="captcha"]',
                'input[name*="captcha"]',
                'input[id*="captcha"]'
            ]
            
            for selector in captcha_selectors:
                try:
                    captcha_element = self.page.locator(selector)
                    if captcha_element.count() > 0:
                        print(f"CAPTCHAを検出: {selector}")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            print(f"CAPTCHA検出でエラー: {e}")
            return False
    
    def diagnose_login_page(self):
        """ログインページの詳細診断"""
        try:
            print("=== ログインページ診断開始 ===")
            
            # 診断データを初期化
            self.diagnosis_data = {
                'url': self.page.url,
                'title': self.page.title(),
                'forms': [],
                'inputs': [],
                'buttons': [],
                'error_messages': [],
                'page_text': self.page.text_content('body')[:1000],
                'html_content': self.page.content()[:2000],
                'screenshot_base64': None,
                'page_info': {
                    'content_length': len(self.page.content()),
                    'text_length': len(self.page.text_content('body')),
                    'js_enabled': self.page.evaluate("() => typeof window !== 'undefined'"),
                    'ready_state': self.page.evaluate("() => document.readyState"),
                    'viewport_size': self.page.evaluate("() => ({width: window.innerWidth, height: window.innerHeight})"),
                    'body_children_count': self.page.evaluate("() => document.body.children.length"),
                    'form_count': self.page.evaluate("() => document.forms.length"),
                    'input_count': self.page.evaluate("() => document.querySelectorAll('input').length"),
                    'password_input_count': self.page.evaluate("() => document.querySelectorAll('input[type=\"password\"]').length"),
                    'text_input_count': self.page.evaluate("() => document.querySelectorAll('input[type=\"text\"]').length"),
                    'email_input_count': self.page.evaluate("() => document.querySelectorAll('input[type=\"email\"]').length"),
                    'iframe_count': self.page.evaluate("() => document.querySelectorAll('iframe').length"),
                    'textarea_count': self.page.evaluate("() => document.querySelectorAll('textarea').length"),
                    'contenteditable_count': self.page.evaluate("() => document.querySelectorAll('[contenteditable=\"true\"]').length")
                }
            }
            
            # スクリーンショットを取得（デバッグ用）
            try:
                screenshot_bytes = self.page.screenshot()
                import base64
                self.diagnosis_data['screenshot_base64'] = base64.b64encode(screenshot_bytes).decode('utf-8')
                print("スクリーンショットを取得しました")
            except Exception as e:
                print(f"スクリーンショット取得エラー: {e}")
            
            # ページの基本情報
            print(f"現在のURL: {self.page.url}")
            print(f"ページタイトル: {self.page.title()}")
            
            # ページのHTML要素を詳細に分析
            print("\n=== ページ要素分析 ===")
            
            # フォーム要素の詳細
            forms = self.page.locator('form')
            forms_count = forms.count()
            print(f"フォーム数: {forms_count}")
            
            for i in range(forms_count):
                try:
                    form = forms.nth(i)
                    form_data = {
                        'index': i,
                        'action': form.get_attribute('action') or 'なし',
                        'method': form.get_attribute('method') or 'なし',
                        'id': form.get_attribute('id') or 'なし',
                        'class': form.get_attribute('class') or 'なし',
                        'visible': form.is_visible(),
                        'display': form.evaluate("el => window.getComputedStyle(el).display"),
                    }
                    self.diagnosis_data['forms'].append(form_data)
                    print(f"  フォーム[{i}]: action='{form_data['action']}', method='{form_data['method']}', id='{form_data['id']}', class='{form_data['class']}', visible={form_data['visible']}, display='{form_data['display']}'")
                except Exception as e:
                    print(f"  フォーム[{i}]分析エラー: {e}")
            
            # 入力フィールドの詳細
            inputs = self.page.locator('input')
            inputs_count = inputs.count()
            print(f"\n入力フィールド数: {inputs_count}")
            
            for i in range(inputs_count):
                try:
                    input_elem = inputs.nth(i)
                    input_data = {
                        'index': i,
                        'name': input_elem.get_attribute('name') or 'なし',
                        'type': input_elem.get_attribute('type') or 'なし',
                        'placeholder': input_elem.get_attribute('placeholder') or 'なし',
                        'id': input_elem.get_attribute('id') or 'なし',
                        'class': input_elem.get_attribute('class') or 'なし',
                        'value': input_elem.get_attribute('value') or 'なし',
                        'autocomplete': input_elem.get_attribute('autocomplete') or 'なし',
                        'visible': input_elem.is_visible(),
                        'display': input_elem.evaluate("el => window.getComputedStyle(el).display"),
                        'position': input_elem.evaluate("el => window.getComputedStyle(el).position"),
                    }
                    self.diagnosis_data['inputs'].append(input_data)
                    print(f"  input[{i}]: name='{input_data['name']}', type='{input_data['type']}', placeholder='{input_data['placeholder']}', id='{input_data['id']}', class='{input_data['class']}', value='{input_data['value']}', autocomplete='{input_data['autocomplete']}', visible={input_data['visible']}, display='{input_data['display']}', position='{input_data['position']}'")
                except Exception as e:
                    print(f"  input[{i}]分析エラー: {e}")
            
            # ボタン要素の詳細
            buttons = self.page.locator('button, input[type="submit"]')
            buttons_count = buttons.count()
            print(f"\nボタン要素数: {buttons_count}")
            
            for i in range(buttons_count):
                try:
                    button_elem = buttons.nth(i)
                    button_data = {
                        'index': i,
                        'text': button_elem.text_content() or 'なし',
                        'type': button_elem.get_attribute('type') or 'なし',
                        'value': button_elem.get_attribute('value') or 'なし',
                        'id': button_elem.get_attribute('id') or 'なし',
                        'class': button_elem.get_attribute('class') or 'なし'
                    }
                    self.diagnosis_data['buttons'].append(button_data)
                    print(f"  button[{i}]: text='{button_data['text']}', type='{button_data['type']}', value='{button_data['value']}', id='{button_data['id']}', class='{button_data['class']}'")
                except Exception as e:
                    print(f"  button[{i}]分析エラー: {e}")
            
            # エラーメッセージの検索
            print("\n=== エラーメッセージ検索 ===")
            error_texts = [
                'ログインに失敗しました',
                'Login failed',
                'メールアドレスまたはパスワードが正しくありません',
                'Invalid email or password',
                '認証に失敗しました',
                'Authentication failed',
                'ログインできませんでした',
                'Could not login',
                'エラー',
                'Error',
                '失敗',
                'Failed'
            ]
            
            for error_text in error_texts:
                try:
                    error_locator = self.page.locator(f'text={error_text}')
                    if error_locator.count() > 0:
                        print(f"エラーメッセージを発見: '{error_text}'")
                        self.diagnosis_data['error_messages'].append(error_text)
                except:
                    pass
            
            print("=== ログインページ診断完了 ===")
            print(f"診断データ: {self.diagnosis_data}")
            
        except Exception as e:
            print(f"診断中にエラー: {e}")
            import traceback
            traceback.print_exc()
    
    def try_different_login_methods(self, email: str, password: str):
        """異なるログイン方法を試行"""
        print("=== 異なるログイン方法を試行 ===")
        
        # 方法1: 異なるURLを試行
        try:
            print("方法1: 異なるURLを試行")
            self.page.goto("https://ssl.jobcan.jp/employee")
            time.sleep(3)
            self.page.wait_for_load_state("networkidle")
            
            # ログイン処理を再試行
            if self.perform_login_action(email, password):
                return True
        except Exception as e:
            print(f"方法1でエラー: {e}")
        
        # 方法2: 直接的なセレクターを使用
        try:
            print("方法2: 直接的なセレクターを使用")
            self.page.goto("https://id.jobcan.jp/users/sign_in?app_key=atd")
            time.sleep(3)
            self.page.wait_for_load_state("networkidle")
            
            # より直接的なセレクターを使用
            email_input = self.page.locator('input[type="text"], input[type="email"]').first
            password_input = self.page.locator('input[type="password"]').first
            
            email_input.fill(email)
            password_input.fill(password)
            
            login_button = self.page.locator('input[type="submit"], button[type="submit"]').first
            login_button.click()
            
            time.sleep(3)
            self.page.wait_for_load_state("networkidle")
            
            return "sign_in" not in self.page.url and "login" not in self.page.url
            
        except Exception as e:
            print(f"方法2でエラー: {e}")
        
        return False
    
    def login_to_jobcan(self, email: str, password: str) -> bool:
        """Jobcanにログイン"""
        try:
            print(f"Jobcanログインを開始: {email}")
            
            # Jobcanログインページに移動
            print("Jobcanログインページに移動中...")
            self.page.goto("https://id.jobcan.jp/users/sign_in?app_key=atd")
            self.page.wait_for_load_state("networkidle")
            
            # 人間らしい待機時間
            time.sleep(random.uniform(2, 4))
            
            # 詳細診断を実行
            self.diagnose_login_page()
            
            # CAPTCHAの検出
            if self.check_for_captcha():
                error_msg = "CAPTCHAが検出されました。手動でのログインが必要です。"
                print(error_msg)
                return False
            
            # メールアドレス入力フィールドを探す
            print("メールアドレス入力フィールドを探しています...")
            email_input = None
            
            # 複数のセレクターを試行
            email_selectors = [
                'input[name="email"]',
                'input[name="staff_code"]',
                'input[type="email"]',
                'input[placeholder*="メール"]',
                'input[placeholder*="email"]',
                'input[placeholder*="Email"]',
                'input[id*="email"]',
                'input[id*="login"]',
                'input[id*="user"]',
                'input[name="username"]',
                'input[name="account"]',
                'input[type="text"]',
                'form input:first-of-type',
                'input:not([type="password"]):not([type="submit"]):not([type="button"])'
            ]
            
            for selector in email_selectors:
                try:
                    email_locator = self.page.locator(selector)
                    if email_locator.count() > 0:
                        email_input = email_locator.first
                        print(f"メールアドレス入力フィールドを発見: {selector}")
                        break
                except Exception as e:
                    print(f"セレクター {selector} でエラー: {e}")
                    continue
            
            if not email_input:
                print("メールアドレス入力フィールドが見つからないため、異なるログイン方法を試行")
                return self.try_different_login_methods(email, password)
            
            # パスワード入力フィールドを探す
            print("パスワード入力フィールドを探しています...")
            password_input = None
            
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[placeholder*="パスワード"]',
                'input[placeholder*="password"]',
                'input[placeholder*="Password"]',
                'input[id*="password"]',
                'input[id*="pass"]',
                'input[autocomplete="current-password"]',
                'input[autocomplete="new-password"]',
                'form input[type="password"]',
                'form input:nth-of-type(2)'
            ]
            
            for selector in password_selectors:
                try:
                    password_locator = self.page.locator(selector)
                    if password_locator.count() > 0:
                        password_input = password_locator.first
                        print(f"パスワード入力フィールドを発見: {selector}")
                        break
                except Exception as e:
                    print(f"パスワードセレクター {selector} でエラー: {e}")
                    continue
            
            if not password_input:
                print("パスワード入力フィールドが見つからないため、異なるログイン方法を試行")
                return self.try_different_login_methods(email, password)
            
            # 人間らしい入力
            print("メールアドレスを入力中...")
            email_input.click()
            time.sleep(random.uniform(0.1, 0.3))
            
            # 文字を1文字ずつ入力
            for char in email:
                email_input.type(char)
                time.sleep(random.uniform(0.05, 0.15))
            
            print("メールアドレス入力完了")
            time.sleep(random.uniform(0.5, 1.0))
            
            print("パスワードを入力中...")
            password_input.click()
            time.sleep(random.uniform(0.1, 0.3))
            
            # 文字を1文字ずつ入力
            for char in password:
                password_input.type(char)
                time.sleep(random.uniform(0.05, 0.15))
            
            print("パスワード入力完了")
            time.sleep(random.uniform(0.5, 1.0))
            
            # ログインボタンをクリック
            print("ログインボタンをクリック中...")
            login_button = self.page.locator('input[type="submit"], button[type="submit"], button:has-text("ログイン"), button:has-text("Login")').first
            login_button.click()
            
            # ログイン後の待機
            time.sleep(random.uniform(3, 5))
            self.page.wait_for_load_state("networkidle")
            
            # ログイン成功の確認
            print("ログイン後のページタイトル:", self.page.title())
            
            # ログイン後の診断
            print("=== ログイン後診断 ===")
            self.diagnose_login_page()
            
            # ログイン成功の確認（複数の方法でチェック）
            login_success = True
            
            # URLベースのチェック
            if "sign_in" in self.page.url or "login" in self.page.url:
                print("URLベースでログイン失敗を検出")
                login_success = False
            
            # エラーメッセージのチェック
            error_selectors = [
                'text=ログインに失敗しました',
                'text=Login failed',
                'text=メールアドレスまたはパスワードが正しくありません',
                'text=Invalid email or password',
                'text=認証に失敗しました',
                'text=Authentication failed',
                'text=ログインできませんでした',
                'text=Could not login',
                '.error',
                '.alert',
                '[class*="error"]',
                '[class*="alert"]',
                '[class*="danger"]',
                '[class*="warning"]'
            ]
            
            for error_selector in error_selectors:
                try:
                    error_locator = self.page.locator(error_selector)
                    if error_locator.count() > 0:
                        error_text = error_locator.first.text_content()
                        print(f"エラーメッセージを検出: {error_text}")
                        login_success = False
                        break
                except:
                    continue
            
            # ログイン成功の指標をチェック
            success_indicators = [
                'text=ダッシュボード',
                'text=Dashboard',
                'text=勤怠',
                'text=Attendance',
                'text=出勤簿',
                'text=Timecard',
                'text=マイページ',
                'text=My Page',
                'a[href*="attendance"]',
                'a[href*="timecard"]',
                'a[href*="mypage"]'
            ]
            
            success_found = False
            for indicator in success_indicators:
                try:
                    indicator_locator = self.page.locator(indicator)
                    if indicator_locator.count() > 0:
                        print(f"ログイン成功の指標を発見: {indicator}")
                        success_found = True
                        break
                except:
                    continue
            
            # 追加のチェック：ログインフォームがまだ表示されているか
            login_form_locator = self.page.locator('input[name="email"], input[name="staff_code"], input[name="password"]')
            if login_form_locator.count() > 0:
                print("ログインフォームがまだ表示されているため、ログイン失敗と判断")
                login_success = False
            
            if not login_success or not success_found:
                print("通常のログイン方法が失敗したため、代替方法を試行")
                alternative_result = self.login_to_jobcan_alternative(email, password)
                
                if not alternative_result:
                    error_msg = f"ログインに失敗しました。メールアドレスとパスワードを確認してください"
                    print(error_msg)
                    return False
                
                return alternative_result
            
            print("ログイン成功")
            return True
            
        except Exception as e:
            error_msg = f"ログイン中にエラーが発生しました: {e}"
            print(error_msg)
            return False
    
    def navigate_to_attendance(self):
        """勤怠ページに移動"""
        try:
            print("勤怠ページに移動中...")
            
            # 勤怠関連のリンクを探す
            attendance_selectors = [
                'a[href*="attendance"]',
                'a[href*="timecard"]',
                'a[href*="勤怠"]',
                'a[href*="出勤"]',
                'a:has-text("勤怠")',
                'a:has-text("Attendance")',
                'a:has-text("出勤簿")',
                'a:has-text("Timecard")',
                'button:has-text("勤怠")',
                'button:has-text("Attendance")'
            ]
            
            for selector in attendance_selectors:
                try:
                    attendance_link = self.page.locator(selector)
                    if attendance_link.count() > 0:
                        print(f"勤怠リンクを発見: {selector}")
                        attendance_link.first.click()
                        time.sleep(3)
                        self.page.wait_for_load_state("networkidle")
                        return True
                except Exception as e:
                    print(f"勤怠リンク {selector} でエラー: {e}")
                    continue
            
            print("勤怠リンクが見つからないため、直接URLにアクセス")
            self.page.goto("https://ssl.jobcan.jp/employee/attendance")
            time.sleep(3)
            self.page.wait_for_load_state("networkidle")
            
            return True
            
        except Exception as e:
            print(f"勤怠ページへの移動でエラー: {e}")
            return False
    
    def select_date(self, date_str: str):
        """日付を選択"""
        try:
            print(f"📅 日付を選択中: {date_str}")
            
            # 日付文字列を解析
            from datetime import datetime
            date_obj = datetime.strptime(date_str, "%Y/%m/%d")
            year = date_obj.year
            month = date_obj.month
            day = date_obj.day
            
            # 曜日を取得（日本語）
            weekday_jp = ['月', '火', '水', '木', '金', '土', '日']
            weekday = weekday_jp[date_obj.weekday()]
            
            # Jobcanの実際の日付形式に変換（例：07/01(火)）
            jobcan_date_format = f"{month:02d}/{day:02d}({weekday})"
            jobcan_date_simple = f"{month:02d}/{day:02d}"
            print(f"📅 Jobcan日付形式: {jobcan_date_format}")
            
            # 日付セレクターを探す（Jobcanの実際の形式に基づく）
            date_selectors = [
                f'td:has-text("{jobcan_date_format}")',
                f'a:has-text("{jobcan_date_format}")',
                f'td:has-text("{jobcan_date_simple}")',
                f'a:has-text("{jobcan_date_simple}")',
                f'[data-date="{date_str}"]',
                f'[data-date="{year}-{month:02d}-{day:02d}"]',
                f'td[data-date="{date_str}"]',
                f'td[data-date="{year}-{month:02d}-{day:02d}"]',
                f'a[href*="{year}/{month:02d}/{day:02d}"]',
                f'a[href*="{year}-{month:02d}-{day:02d}"]',
                f'input[type="date"]',
                f'input[name*="date"]',
                f'input[id*="date"]',
                f'input[placeholder*="日付"]',
                f'input[placeholder*="date"]',
                f'select[name*="date"]',
                f'select[id*="date"]'
            ]
            
            print(f"🔍 日付セレクターを検索中...")
            for i, selector in enumerate(date_selectors):
                try:
                    count = self.page.locator(selector).count()
                    print(f"🔍 セレクター {i+1}/{len(date_selectors)}: {selector} → {count}個発見")
                    if count > 0:
                        print(f"✅ 日付セレクターを発見: {selector}")
                        self.page.click(selector)
                        time.sleep(2)
                        self.page.wait_for_load_state("networkidle")
                        return True
                except Exception as e:
                    print(f"❌ セレクター {selector} でエラー: {e}")
                    continue
            
            # 日付が見つからない場合は、カレンダーから探す
            print(f"🔍 カレンダーから日付を検索中...")
            calendar_success = self.select_date_from_calendar(date_str)
            if calendar_success:
                return True
            
            print(f"❌ 日付 {date_str} が見つかりませんでした")
            return False
            
        except Exception as e:
            print(f"❌ 日付選択でエラー: {e}")
            return False
    
    def click_stamp_correction(self):
        """打刻修正ボタンをクリック"""
        try:
            print("打刻修正ボタンをクリック中...")
            
            # 打刻修正関連のセレクターを試行
            correction_selectors = [
                'button:has-text("打刻修正")',
                'button:has-text("修正")',
                'a:has-text("打刻修正")',
                'a:has-text("修正")',
                'input[value*="打刻修正"]',
                'input[value*="修正"]',
                '[class*="correction"]',
                '[id*="correction"]'
            ]
            
            for selector in correction_selectors:
                try:
                    correction_button = self.page.locator(selector)
                    if correction_button.count() > 0:
                        print(f"打刻修正ボタンを発見: {selector}")
                        correction_button.first.click()
                        time.sleep(2)
                        self.page.wait_for_load_state("networkidle")
                        return True
                except Exception as e:
                    print(f"打刻修正セレクター {selector} でエラー: {e}")
                    continue
            
            print("打刻修正ボタンが見つかりません")
            return False
            
        except Exception as e:
            print(f"打刻修正ボタンクリックでエラー: {e}")
            return False
    
    def input_time(self, time_type: str, time_str: str):
        """時間を入力"""
        try:
            print(f"{time_type}時間を入力中: {time_str}")
            
            # 時間入力フィールドを探す
            time_selectors = [
                f'input[name*="{time_type.lower()}"]',
                f'input[id*="{time_type.lower()}"]',
                f'input[placeholder*="{time_type}"]',
                f'input[placeholder*="{time_type.lower()}"]',
                'input[type="time"]',
                'input[name*="time"]',
                'input[id*="time"]'
            ]
            
            for selector in time_selectors:
                try:
                    time_input = self.page.locator(selector)
                    if time_input.count() > 0:
                        print(f"{time_type}時間入力フィールドを発見: {selector}")
                        time_input.first.fill(time_str)
                        time.sleep(1)
                        return True
                except Exception as e:
                    print(f"{time_type}時間セレクター {selector} でエラー: {e}")
                    continue
            
            print(f"{time_type}時間入力フィールドが見つかりません")
            return False
            
        except Exception as e:
            print(f"{time_type}時間入力でエラー: {e}")
            return False
    
    def process_attendance_data(self, data: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """勤怠データを処理"""
        try:
            print("=== 勤怠データ処理開始 ===")
            print(f"📊 処理対象データ数: {len(data)}")
            
            processed_data = []
            success_count = 0
            error_count = 0
            
            for i, row in enumerate(data):
                try:
                    print(f"\n=== データ {i+1}/{len(data)} の処理開始 ===")
                    
                    date = row.get('date', '')
                    start_time = row.get('start_time', '')
                    end_time = row.get('end_time', '')
                    
                    print(f"📋 処理データ: 日付={date}, 開始時間={start_time}, 終了時間={end_time}")
                    
                    if not date or not start_time or not end_time:
                        print(f"❌ データ {i+1} に必要な情報が不足しています")
                        error_count += 1
                        processed_data.append({
                            'date': date,
                            'start_time': start_time,
                            'end_time': end_time,
                            'status': 'error',
                            'error': '必要な情報が不足'
                        })
                        continue
                    
                    # 現在のページ状態をデバッグ
                    print(f"🔍 現在のページ状態を確認中...")
                    current_url = self.page.url
                    page_title = self.page.title()
                    print(f"🔗 現在のURL: {current_url}")
                    print(f"📄 ページタイトル: {page_title}")
                    
                    # 日付を選択
                    print(f"📅 ステップ1: 日付 {date} を選択中...")
                    date_success = self.select_date(date)
                    print(f"📅 日付選択結果: {'✅ 成功' if date_success else '❌ 失敗'}")
                    
                    if not date_success:
                        print(f"❌ 日付 {date} の選択に失敗しました")
                        error_count += 1
                        processed_data.append({
                            'date': date,
                            'start_time': start_time,
                            'end_time': end_time,
                            'status': 'error',
                            'error': '日付選択に失敗'
                        })
                        continue
                    
                    # 打刻修正ボタンをクリック
                    print(f"🔧 ステップ2: 打刻修正ボタンをクリック中...")
                    correction_success = self.click_stamp_correction()
                    print(f"🔧 打刻修正結果: {'✅ 成功' if correction_success else '❌ 失敗'}")
                    
                    if not correction_success:
                        print(f"❌ 打刻修正ボタンのクリックに失敗しました")
                        error_count += 1
                        processed_data.append({
                            'date': date,
                            'start_time': start_time,
                            'end_time': end_time,
                            'status': 'error',
                            'error': '打刻修正ボタンクリックに失敗'
                        })
                        continue
                    
                    # 開始時間を入力
                    print(f"⏰ ステップ3: 開始時間 {start_time} を入力中...")
                    start_success = self.input_time("開始", start_time)
                    print(f"⏰ 開始時間入力結果: {'✅ 成功' if start_success else '❌ 失敗'}")
                    
                    if not start_success:
                        print(f"❌ 開始時間 {start_time} の入力に失敗しました")
                        error_count += 1
                        processed_data.append({
                            'date': date,
                            'start_time': start_time,
                            'end_time': end_time,
                            'status': 'error',
                            'error': '開始時間入力に失敗'
                        })
                        continue
                    
                    # 終了時間を入力
                    print(f"⏰ ステップ4: 終了時間 {end_time} を入力中...")
                    end_success = self.input_time("終了", end_time)
                    print(f"⏰ 終了時間入力結果: {'✅ 成功' if end_success else '❌ 失敗'}")
                    
                    if not end_success:
                        print(f"❌ 終了時間 {end_time} の入力に失敗しました")
                        error_count += 1
                        processed_data.append({
                            'date': date,
                            'start_time': start_time,
                            'end_time': end_time,
                            'status': 'error',
                            'error': '終了時間入力に失敗'
                        })
                        continue
                    
                    # 保存ボタンをクリック
                    print(f"💾 ステップ5: 保存ボタンをクリック中...")
                    save_selectors = [
                        'button:has-text("保存")',
                        'button:has-text("Save")',
                        'button:has-text("登録")',
                        'button:has-text("確定")',
                        'input[type="submit"]',
                        'input[value*="保存"]',
                        'input[value*="Save"]',
                        'input[value*="登録"]',
                        'input[value*="確定"]'
                    ]
                    
                    saved = False
                    for selector in save_selectors:
                        try:
                            save_button = self.page.locator(selector)
                            if save_button.count() > 0:
                                print(f"✅ 保存ボタンを発見: {selector}")
                                save_button.first.click()
                                time.sleep(2)
                                self.page.wait_for_load_state("networkidle")
                                saved = True
                                break
                        except Exception as e:
                            print(f"❌ 保存セレクター {selector} でエラー: {e}")
                            continue
                    
                    if not saved:
                        print(f"❌ 保存ボタンが見つかりません")
                        error_count += 1
                        processed_data.append({
                            'date': date,
                            'start_time': start_time,
                            'end_time': end_time,
                            'status': 'error',
                            'error': '保存ボタンが見つからない'
                        })
                        continue
                    
                    # 勤怠ページに戻る
                    print(f"🏠 ステップ6: 勤怠ページに戻る中...")
                    return_success = self.navigate_to_attendance()
                    print(f"🏠 ページ戻り結果: {'✅ 成功' if return_success else '❌ 失敗'}")
                    
                    # 処理結果を記録
                    overall_success = start_success and end_success and saved and return_success
                    if overall_success:
                        success_count += 1
                        print(f"✅ データ {i+1} の処理が成功しました")
                        processed_data.append({
                            'date': date,
                            'start_time': start_time,
                            'end_time': end_time,
                            'status': 'success'
                        })
                    else:
                        error_count += 1
                        print(f"❌ データ {i+1} の処理が失敗しました")
                        processed_data.append({
                            'date': date,
                            'start_time': start_time,
                            'end_time': end_time,
                            'status': 'error',
                            'error': '処理の一部が失敗'
                        })
                    
                    print(f"⏳ 次のデータまで待機中...")
                    time.sleep(2)  # 処理間隔
                    
                except Exception as e:
                    print(f"❌ データ {i+1} の処理でエラー: {e}")
                    error_count += 1
                    processed_data.append({
                        'date': row.get('date', ''),
                        'start_time': row.get('start_time', ''),
                        'end_time': row.get('end_time', ''),
                        'status': 'error',
                        'error': str(e)
                    })
            
            print(f"\n=== 処理結果サマリー ===")
            print(f"📊 処理対象データ数: {len(data)}")
            print(f"✅ 成功件数: {success_count}")
            print(f"❌ エラー件数: {error_count}")
            print(f"📈 成功率: {success_count/len(data)*100:.1f}%" if len(data) > 0 else "処理対象なし")
            print("=== 勤怠データ処理完了 ===")
            
            return processed_data
            
        except Exception as e:
            print(f"❌ 勤怠データ処理でエラー: {e}")
            return []
    
    def close(self):
        """ブラウザを閉じる"""
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            print("ブラウザを閉じました")
        except Exception as e:
            print(f"ブラウザ終了でエラー: {e}") 
