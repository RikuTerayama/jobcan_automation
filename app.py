#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jobcan勤怠申請Webアプリケーション
Flask + Playwright + Pandasを使用したWebインターフェース
Railwayデプロイ対応版
"""

import os
import json
import tempfile
import subprocess
import sys
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from werkzeug.utils import secure_filename
from playwright.sync_api import sync_playwright, Page, Browser
import threading
import queue
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# 設定
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# アップロードフォルダの作成
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 処理状態を管理するグローバル変数
processing_status = {}
status_queue = queue.Queue()

def allowed_file(filename):
    """アップロードされたファイルの拡張子をチェック"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_playwright_browser():
    """Playwrightブラウザがインストールされているか確認し、必要に応じてインストール"""
    try:
        print("Playwrightブラウザの確認を開始...")
        
        # システム依存関係をインストール
        print("システム依存関係をインストール中...")
        subprocess.run([
            "playwright", "install-deps"
        ], check=True, capture_output=True)
        
        # Playwrightブラウザのインストールを試行
        print("Playwrightブラウザをインストール中...")
        subprocess.run([
            sys.executable, "-m", "playwright", "install", "--force", "chromium"
        ], check=True, capture_output=True)
        
        print("Playwrightブラウザが正常にインストールされました")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Playwrightブラウザのインストールに失敗しました: {e}")
        print(f"エラー出力: {e.stderr.decode() if e.stderr else 'なし'}")
        raise Exception(f"Playwrightブラウザのインストールに失敗しました: {e}")
    except Exception as e:
        print(f"予期しないエラー: {e}")
        raise Exception(f"Playwrightブラウザの確認中にエラーが発生しました: {e}")

def load_excel_data(file_path: str) -> List[Dict[str, str]]:
    """Excelファイルから勤怠データを読み込み"""
    try:
        print(f"Excelファイルを読み込み中: {file_path}")
        df = pd.read_excel(file_path, header=0)
        
        # 列名を確認
        if len(df.columns) < 3:
            raise ValueError("Excelファイルには少なくとも3列（日付、始業時刻、終業時刻）が必要です")
        
        print(f"Excelファイルの列数: {len(df.columns)}")
        print(f"Excelファイルの行数: {len(df)}")
        
        # データを整形
        data = []
        for _, row in df.iterrows():
            date = row.iloc[0]  # A列：日付
            start_time = row.iloc[1]  # B列：始業時刻
            end_time = row.iloc[2]  # C列：終業時刻
            
            # 日付の形式を統一
            if isinstance(date, str):
                date_obj = datetime.strptime(date, "%Y/%m/%d")
            else:
                date_obj = pd.to_datetime(date)
            
            date_str = date_obj.strftime("%Y/%m/%d")
            
            # 時刻の形式を統一
            if isinstance(start_time, str):
                start_time_str = start_time
            else:
                start_time_str = start_time.strftime("%H:%M")
            
            if isinstance(end_time, str):
                end_time_str = end_time
            else:
                end_time_str = end_time.strftime("%H:%M")
            
            data.append({
                'date': date_str,
                'start_time': start_time_str,
                'end_time': end_time_str
            })
        
        print(f"処理されたデータ数: {len(data)}")
        return data
        
    except Exception as e:
        print(f"Excelファイルの読み込みエラー: {e}")
        raise ValueError(f"Excelファイルの読み込みに失敗しました: {e}")

class JobcanAutomation:
    """Jobcan勤怠自動入力クラス"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.status_queue = queue.Queue()
        
    def start_browser(self):
        """ブラウザを起動"""
        try:
            print("ブラウザ起動を開始...")
            
            # Playwrightブラウザの確認
            ensure_playwright_browser()
            
            print("Playwrightを初期化中...")
            self.playwright = sync_playwright().start()
            
            # より人間らしいブラウザ設定
            browser_args = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-extensions',
                '--disable-plugins',
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
                '--disable-ipc-flooding-protection',
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
            
            self.status_queue.put({"status": "browser_started", "message": "ブラウザを起動しました"})
            print("ブラウザ起動完了")
            
        except Exception as e:
            error_msg = f"ブラウザの起動に失敗しました: {e}"
            print(error_msg)
            self.status_queue.put({"status": "error", "message": error_msg})
            raise
        
    def login_to_jobcan_alternative(self, email: str, password: str) -> bool:
        """Jobcanにログイン（代替方法）"""
        try:
            print(f"代替ログイン方法を試行: {email}")
            self.status_queue.put({"status": "logging_in", "message": "代替ログイン方法を試行中..."})
            
            # 直接ログインページにアクセス（正しいURLを使用）
            print("直接ログインページにアクセス中...")
            self.page.goto("https://id.jobcan.jp/users/sign_in?app_key=atd")
            self.page.wait_for_load_state("networkidle")
            
            print("現在のURL:", self.page.url)
            print("ページタイトル:", self.page.title())
            
            # メールアドレスを入力
            print("メールアドレスを入力中...")
            email_input = self.page.locator('input[name="email"], input[name="staff_code"], input[type="email"]').first
            email_input.fill(email)
            print("メールアドレス入力完了")
            
            # パスワードを入力
            print("パスワードを入力中...")
            password_input = self.page.locator('input[name="password"], input[type="password"]').first
            password_input.fill(password)
            print("パスワード入力完了")
            
            # ログインボタンをクリック
            print("ログインボタンをクリック中...")
            login_button = self.page.locator('input[type="submit"], button[type="submit"]').first
            login_button.click()
            print("ログインボタンクリック完了")
            
            # ログイン後のページ読み込みを待機
            print("ログイン後のページ読み込みを待機中...")
            self.page.wait_for_load_state("networkidle")
            
            print("ログイン後のURL:", self.page.url)
            
            # ログイン成功の確認
            if "sign_in" in self.page.url or "login" in self.page.url:
                print("代替ログイン方法でも失敗")
                return False
            
            print("代替ログイン方法で成功")
            return True
            
        except Exception as e:
            print(f"代替ログイン方法でエラー: {e}")
            return False

    def check_for_captcha(self):
        """CAPTCHAの検出"""
        try:
            captcha_selectors = [
                'iframe[src*="recaptcha"]',
                'iframe[src*="captcha"]',
                'div[class*="recaptcha"]',
                'div[class*="captcha"]',
                'img[src*="captcha"]',
                'input[name*="captcha"]',
                'input[id*="captcha"]'
            ]
            
            for selector in captcha_selectors:
                if self.page.locator(selector).count() > 0:
                    print(f"CAPTCHAを検出: {selector}")
                    return True
            
            return False
        except Exception as e:
            print(f"CAPTCHA検出中にエラー: {e}")
            return False

    def login_to_jobcan(self, email: str, password: str) -> bool:
        """Jobcanにログイン"""
        try:
            print(f"Jobcanログインを開始: {email}")
            self.status_queue.put({"status": "logging_in", "message": "Jobcanにログイン中..."})
            
            # Jobcanログインページに移動（正しいURLを使用）
            print("Jobcanログインページに移動中...")
            self.page.goto("https://id.jobcan.jp/users/sign_in?app_key=atd")
            self.page.wait_for_load_state("networkidle")
            
            print("現在のURL:", self.page.url)
            print("ページタイトル:", self.page.title())
            
            # 人間らしい待機時間
            import random
            import time
            
            # ページが完全に読み込まれるまで待機
            time.sleep(random.uniform(2, 4))
            
            # CAPTCHAの検出
            if self.check_for_captcha():
                error_msg = "CAPTCHAが検出されました。手動でのログインが必要です。"
                print(error_msg)
                self.status_queue.put({"status": "error", "message": error_msg})
                return False
            
            # JavaScriptが有効かチェック
            js_enabled = self.page.evaluate("() => typeof window !== 'undefined'")
            print(f"JavaScript有効: {js_enabled}")
            
            # ページのHTMLを確認（デバッグ用）
            page_content = self.page.content()
            print("ページタイトル:", self.page.title())
            
            # フォーム要素の確認
            forms = self.page.locator('form')
            print(f"ページ内のフォーム数: {forms.count()}")
            
            for i in range(forms.count()):
                try:
                    form = forms.nth(i)
                    action = form.get_attribute('action') or 'なし'
                    method = form.get_attribute('method') or 'なし'
                    print(f"  フォーム[{i}]: action='{action}', method='{method}'")
                except:
                    pass
            
            # メールアドレス入力フィールドを探す（複数のパターンを試す）
            print("メールアドレス入力フィールドを探しています...")
            email_selectors = [
                'input[name="email"]',
                'input[name="staff_code"]',
                'input[name="login_id"]',
                'input[name="user_id"]',
                'input[type="email"]',
                'input[placeholder*="メール"]',
                'input[placeholder*="email"]',
                'input[placeholder*="Email"]',
                'input[id*="email"]',
                'input[id*="login"]',
                'input[id*="user"]',
                'input[name="username"]',
                'input[name="account"]'
            ]
            
            email_input = None
            for selector in email_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        email_input = self.page.locator(selector).first
                        print(f"メールアドレス入力フィールドを発見: {selector}")
                        break
                except Exception as e:
                    print(f"セレクター {selector} でエラー: {e}")
                    continue
            
            if not email_input:
                # ページのHTMLを出力してデバッグ
                print("利用可能なinput要素:")
                inputs = self.page.locator('input')
                for i in range(inputs.count()):
                    input_elem = inputs.nth(i)
                    try:
                        name = input_elem.get_attribute('name') or 'なし'
                        type_attr = input_elem.get_attribute('type') or 'なし'
                        placeholder = input_elem.get_attribute('placeholder') or 'なし'
                        id_attr = input_elem.get_attribute('id') or 'なし'
                        print(f"  input[{i}]: name='{name}', type='{type_attr}', placeholder='{placeholder}', id='{id_attr}'")
                    except:
                        pass
                raise Exception("メールアドレス入力フィールドが見つかりません")
            
            # メールアドレスを人間らしく入力
            print("メールアドレスを入力中...")
            email_input.click()
            time.sleep(random.uniform(0.5, 1.5))
            
            # 文字を一つずつ入力（人間らしく）
            for char in email:
                email_input.type(char)
                time.sleep(random.uniform(0.05, 0.15))
            
            print("メールアドレス入力完了")
            time.sleep(random.uniform(0.5, 1.0))
            
            # パスワード入力フィールドを探す（複数のパターンを試す）
            print("パスワード入力フィールドを探しています...")
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[placeholder*="パスワード"]',
                'input[placeholder*="password"]',
                'input[placeholder*="Password"]',
                'input[id*="password"]',
                'input[id*="pass"]'
            ]
            
            password_input = None
            for selector in password_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        password_input = self.page.locator(selector).first
                        print(f"パスワード入力フィールドを発見: {selector}")
                        break
                except Exception as e:
                    print(f"パスワードセレクター {selector} でエラー: {e}")
                    continue
            
            if not password_input:
                raise Exception("パスワード入力フィールドが見つかりません")
            
            # パスワードを人間らしく入力
            print("パスワードを入力中...")
            password_input.click()
            time.sleep(random.uniform(0.5, 1.5))
            
            # 文字を一つずつ入力（人間らしく）
            for char in password:
                password_input.type(char)
                time.sleep(random.uniform(0.05, 0.15))
            
            print("パスワード入力完了")
            time.sleep(random.uniform(1.0, 2.0))
            
            # 入力後の値を確認
            print(f"入力されたメールアドレス: {email_input.input_value()}")
            print(f"入力されたパスワード: {'*' * len(password_input.input_value())}")
            
            # ログインボタンを探す（複数のパターンを試す）
            print("ログインボタンを探しています...")
            login_selectors = [
                'input[type="submit"]',
                'button[type="submit"]',
                'button:has-text("ログイン")',
                'button:has-text("Login")',
                'button:has-text("サインイン")',
                'button:has-text("Sign In")',
                'input[value*="ログイン"]',
                'input[value*="Login"]',
                'input[value*="サインイン"]',
                'input[value*="Sign In"]',
                'button:has-text("送信")',
                'button:has-text("Submit")',
                'form button',
                'form input[type="submit"]'
            ]
            
            login_button = None
            for selector in login_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        login_button = self.page.locator(selector).first
                        print(f"ログインボタンを発見: {selector}")
                        break
                except Exception as e:
                    print(f"ログインボタンセレクター {selector} でエラー: {e}")
                    continue
            
            if not login_button:
                # 利用可能なボタンを出力してデバッグ
                print("利用可能なボタン要素:")
                buttons = self.page.locator('button, input[type="submit"]')
                for i in range(buttons.count()):
                    button_elem = buttons.nth(i)
                    try:
                        text = button_elem.text_content() or 'なし'
                        type_attr = button_elem.get_attribute('type') or 'なし'
                        value = button_elem.get_attribute('value') or 'なし'
                        print(f"  button[{i}]: text='{text}', type='{type_attr}', value='{value}'")
                    except:
                        pass
                raise Exception("ログインボタンが見つかりません")
            
            # ログインボタンを人間らしくクリック
            print("ログインボタンをクリック中...")
            login_button.hover()  # マウスオーバー
            time.sleep(random.uniform(0.3, 0.8))
            login_button.click()
            print("ログインボタンクリック完了")
            
            # ログイン後のページ読み込みを待機
            print("ログイン後のページ読み込みを待機中...")
            time.sleep(random.uniform(3, 5))  # 人間らしい待機時間
            self.page.wait_for_load_state("networkidle")
            
            print("ログイン後のURL:", self.page.url)
            print("ログイン後のページタイトル:", self.page.title())
            
            # ページの内容を確認
            print("ログイン後のページ内容を確認中...")
            page_text = self.page.text_content('body')
            print(f"ページテキスト（最初の500文字）: {page_text[:500]}")
            
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
                    if self.page.locator(error_selector).count() > 0:
                        error_text = self.page.locator(error_selector).first.text_content()
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
                    if self.page.locator(indicator).count() > 0:
                        print(f"ログイン成功の指標を発見: {indicator}")
                        success_found = True
                        break
                except:
                    continue
            
            # 追加のチェック：ログインフォームがまだ表示されているか
            if self.page.locator('input[name="email"], input[name="staff_code"], input[name="password"]').count() > 0:
                print("ログインフォームがまだ表示されているため、ログイン失敗と判断")
                login_success = False
            
            if not login_success or not success_found:
                print("通常のログイン方法が失敗したため、代替方法を試行")
                return self.login_to_jobcan_alternative(email, password)
            
            print("ログイン成功")
            self.status_queue.put({"status": "login_success", "message": "Jobcanにログインしました"})
            return True
            
        except Exception as e:
            error_msg = f"ログイン中にエラーが発生しました: {e}"
            print(error_msg)
            self.status_queue.put({"status": "error", "message": error_msg})
            return False
    
    def navigate_to_attendance(self):
        """出勤簿ページに移動"""
        try:
            print("出勤簿ページに移動中...")
            self.status_queue.put({"status": "navigating", "message": "出勤簿ページに移動中..."})
            
            # 出勤簿へのリンクを探す（複数のパターンを試す）
            attendance_selectors = [
                'a[href*="attendance"]',
                'a[href*="timecard"]',
                'a:has-text("出勤簿")',
                'a:has-text("勤怠")',
                'a:has-text("Attendance")',
                'a:has-text("勤怠管理")'
            ]
            
            for selector in attendance_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        print(f"出勤簿リンクを発見: {selector}")
                        self.page.click(selector)
                        break
                except:
                    continue
            
            self.page.wait_for_load_state("networkidle")
            print("出勤簿ページ移動完了")
            self.status_queue.put({"status": "attendance_loaded", "message": "出勤簿ページに移動しました"})
            
        except Exception as e:
            error_msg = f"出勤簿ページへの移動に失敗しました: {e}"
            print(error_msg)
            self.status_queue.put({"status": "error", "message": error_msg})
            raise
    
    def select_date(self, date_str: str):
        """指定された日付を選択"""
        try:
            date_obj = datetime.strptime(date_str, "%Y/%m/%d")
            formatted_date = date_obj.strftime("%Y-%m-%d")
            
            print(f"日付を選択中: {date_str}")
            self.status_queue.put({"status": "processing", "message": f"日付 {date_str} を選択中..."})
            
            # 日付セレクターを探す（複数のパターンを試す）
            date_selectors = [
                f'[data-date="{formatted_date}"]',
                f'[data-date="{date_str}"]',
                f'td[data-date="{formatted_date}"]',
                f'td[data-date="{date_str}"]',
                f'a[href*="{formatted_date}"]',
                f'a[href*="{date_str}"]',
                f'td:has-text("{date_str}")',
                f'a:has-text("{date_str}")'
            ]
            
            for selector in date_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        print(f"日付セレクターを発見: {selector}")
                        self.page.click(selector)
                        break
                except:
                    continue
            
            self.page.wait_for_load_state("networkidle")
            print(f"日付選択完了: {date_str}")
            self.status_queue.put({"status": "date_selected", "message": f"日付 {date_str} を選択しました"})
            
        except Exception as e:
            error_msg = f"日付選択に失敗しました: {e}"
            print(error_msg)
            self.status_queue.put({"status": "error", "message": error_msg})
            raise
    
    def click_stamp_correction(self):
        """打刻修正ボタンをクリック"""
        try:
            print("打刻修正ボタンをクリック中...")
            self.status_queue.put({"status": "processing", "message": "打刻修正ボタンをクリック中..."})
            
            # 打刻修正ボタンを探す（複数のパターンを試す）
            correction_selectors = [
                'button:has-text("打刻修正")',
                'a:has-text("打刻修正")',
                'input[value*="打刻修正"]',
                'button:has-text("修正")',
                'a:has-text("修正")',
                'button:has-text("編集")',
                'a:has-text("編集")'
            ]
            
            for selector in correction_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        print(f"打刻修正ボタンを発見: {selector}")
                        self.page.click(selector)
                        break
                except:
                    continue
            
            self.page.wait_for_load_state("networkidle")
            print("打刻修正ボタンクリック完了")
            self.status_queue.put({"status": "correction_clicked", "message": "打刻修正ボタンをクリックしました"})
            
        except Exception as e:
            error_msg = f"打刻修正ボタンのクリックに失敗しました: {e}"
            print(error_msg)
            self.status_queue.put({"status": "error", "message": error_msg})
            raise
    
    def input_time(self, time_type: str, time_str: str):
        """時刻を入力して打刻"""
        try:
            print(f"{time_type}時刻を入力中: {time_str}")
            self.status_queue.put({"status": "processing", "message": f"{time_type}時刻 {time_str} を入力中..."})
            
            # 時刻入力フィールドを探す
            time_input_selectors = [
                f'input[name*="{time_type.lower()}"]',
                f'input[name*="{time_type}"]',
                f'input[placeholder*="{time_type}"]',
                f'input[type="time"]',
                f'input[name*="start"]',
                f'input[name*="end"]'
            ]
            
            time_input = None
            for selector in time_input_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        time_input = self.page.locator(selector).first
                        print(f"時刻入力フィールドを発見: {selector}")
                        break
                except:
                    continue
            
            if not time_input:
                raise Exception(f"{time_type}時刻の入力フィールドが見つかりません")
            
            # 時刻を入力
            time_input.fill(time_str)
            print(f"{time_type}時刻入力完了: {time_str}")
            
            # 打刻ボタンをクリック
            stamp_selectors = [
                'button:has-text("打刻")',
                'input[value*="打刻"]',
                'button:has-text("登録")',
                'input[value*="登録"]',
                'button:has-text("保存")',
                'input[value*="保存"]'
            ]
            
            for selector in stamp_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        print(f"打刻ボタンを発見: {selector}")
                        self.page.click(selector)
                        break
                except:
                    continue
            
            self.page.wait_for_load_state("networkidle")
            print(f"{time_type}時刻打刻完了: {time_str}")
            self.status_queue.put({"status": "time_inputted", "message": f"{time_type}時刻 {time_str} を入力しました"})
            
        except Exception as e:
            error_msg = f"{time_type}時刻の入力に失敗しました: {e}"
            print(error_msg)
            self.status_queue.put({"status": "error", "message": error_msg})
            raise
    
    def process_attendance_data(self, data: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """勤怠データを処理"""
        processed_data = []
        
        for i, row in enumerate(data):
            try:
                date = row['date']
                start_time = row['start_time']
                end_time = row['end_time']
                
                print(f"{date} の勤怠データを処理中... ({i+1}/{len(data)})")
                self.status_queue.put({"status": "processing", "message": f"{date} の勤怠データを処理中... ({i+1}/{len(data)})"})
                
                # 日付を選択
                self.select_date(date)
                
                # 打刻修正ボタンをクリック
                self.click_stamp_correction()
                
                # 始業時刻を入力
                self.input_time("始業", start_time)
                
                # 終業時刻を入力
                self.input_time("終業", end_time)
                
                # 出勤簿に戻る
                self.navigate_to_attendance()
                
                processed_data.append({
                    'date': date,
                    'start_time': start_time,
                    'end_time': end_time,
                    'status': 'success'
                })
                
                print(f"{date} の勤怠データを正常に処理しました")
                self.status_queue.put({"status": "success", "message": f"{date} の勤怠データを正常に処理しました"})
                
            except Exception as e:
                error_msg = f"{date} の勤怠データ処理に失敗しました: {e}"
                print(error_msg)
                self.status_queue.put({"status": "error", "message": error_msg})
                processed_data.append({
                    'date': date,
                    'start_time': start_time,
                    'end_time': end_time,
                    'status': 'error',
                    'error': str(e)
                })
        
        return processed_data
    
    def close(self):
        """ブラウザを閉じる"""
        if self.browser:
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()
        print("ブラウザを閉じました")
        self.status_queue.put({"status": "completed", "message": "ブラウザを閉じました"})

def process_jobcan_automation(job_id: str, email: str, password: str, file_path: str):
    """バックグラウンドでJobcan自動化処理を実行"""
    try:
        print(f"処理開始: {job_id}")
        print(f"ログイン情報: email={email}, password={'*' * len(password)}")
        processing_status[job_id] = {"status": "starting", "message": "処理を開始しています..."}
        
        # 自動化クラスを初期化
        print("自動化クラスを初期化中...")
        automation = JobcanAutomation(headless=True)
        
        # ブラウザを起動
        print("ブラウザ起動を開始...")
        automation.start_browser()
        processing_status[job_id] = {"status": "browser_started", "message": "ブラウザを起動しました"}
        
        # Jobcanにログイン
        print("Jobcanログインを開始...")
        login_result = automation.login_to_jobcan(email, password)
        print(f"ログイン結果: {login_result}")
        
        if not login_result:
            error_msg = "ログインに失敗しました。メールアドレスとパスワードを確認してください"
            print(error_msg)
            processing_status[job_id] = {"status": "error", "message": error_msg}
            automation.close()
            return
        
        # 出勤簿ページに移動
        print("出勤簿ページに移動中...")
        automation.navigate_to_attendance()
        
        # Excelデータを読み込み
        print("Excelデータを読み込み中...")
        attendance_data = load_excel_data(file_path)
        processing_status[job_id] = {"status": "data_loaded", "message": f"{len(attendance_data)}件の勤怠データを読み込みました"}
        
        # 勤怠データを処理
        print("勤怠データを処理中...")
        processed_data = automation.process_attendance_data(attendance_data)
        
        # 結果を集計
        success_count = sum(1 for r in processed_data if r['status'] == 'success')
        error_count = len(processed_data) - success_count
        
        print(f"処理完了 - 成功: {success_count}件, 失敗: {error_count}件")
        processing_status[job_id] = {
            "status": "completed",
            "message": f"処理完了 - 成功: {success_count}件, 失敗: {error_count}件",
            "results": processed_data
        }
        
        # ブラウザを閉じる
        automation.close()
        
        # 一時ファイルを削除
        os.remove(file_path)
        
    except Exception as e:
        error_msg = f"予期しないエラーが発生しました: {e}"
        print(error_msg)
        processing_status[job_id] = {"status": "error", "message": error_msg}
        # 一時ファイルを削除
        if os.path.exists(file_path):
            os.remove(file_path)

@app.route('/')
def index():
    """メインページ"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """ファイルアップロードと処理開始"""
    try:
        print("ファイルアップロード処理を開始...")
        
        # フォームデータの取得
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        print(f"メールアドレス: {email}")
        
        # 必須項目の確認
        if not email:
            return jsonify({'error': 'メールアドレスを入力してください'}), 400
        
        if not password:
            return jsonify({'error': 'パスワードを入力してください'}), 400
        
        # ファイルの確認
        if 'file' not in request.files:
            return jsonify({'error': 'ファイルが選択されていません'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'ファイルが選択されていません'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Excelファイル（.xlsx, .xls）のみアップロード可能です'}), 400
        
        print(f"アップロードされたファイル: {file.filename}")
        
        # ファイルを一時保存
        filename = secure_filename(file.filename)
        temp_path = os.path.join(UPLOAD_FOLDER, f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
        file.save(temp_path)
        
        print(f"一時ファイル保存完了: {temp_path}")
        
        # 処理IDを生成
        job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"処理ID生成: {job_id}")
        
        # バックグラウンドで処理を開始
        thread = threading.Thread(
            target=process_jobcan_automation,
            args=(job_id, email, password, temp_path)
        )
        thread.daemon = True
        thread.start()
        
        print("バックグラウンド処理を開始しました")
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': '処理を開始しました'
        })
        
    except Exception as e:
        error_msg = f'エラーが発生しました: {e}'
        print(error_msg)
        return jsonify({'error': error_msg}), 500

@app.route('/status/<job_id>')
def get_status(job_id):
    """処理状況を取得"""
    if job_id in processing_status:
        return jsonify(processing_status[job_id])
    else:
        return jsonify({'error': '処理が見つかりません'}), 404

@app.route('/health')
def health_check():
    """ヘルスチェック用エンドポイント"""
    return jsonify({'status': 'healthy', 'message': 'Jobcan Web App is running'})

if __name__ == '__main__':
    # Railway環境用のポート設定
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port) 
