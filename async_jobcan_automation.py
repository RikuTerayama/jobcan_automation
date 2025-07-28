#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
非同期Jobcan勤怠自動化モジュール
"""

import asyncio
import queue
import time
import random
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
from playwright.async_api import async_playwright, Page, Browser
import subprocess
import sys

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

class AsyncJobcanAutomation:
    """非同期Jobcan勤怠自動入力クラス"""
    
    def __init__(self):
        self.browser = None
        self.page = None
        self.status_queue = queue.Queue()
        self.diagnosis_data = {}

    def get_diagnosis_data(self):
        """診断データを取得"""
        return self.diagnosis_data

    async def start_browser(self):
        """ブラウザを起動"""
        try:
            print("Playwrightブラウザを起動中...")
            
            # Playwrightブラウザのインストール確認
            ensure_playwright_browser()
            
            # 非同期Playwrightを使用
            from playwright.async_api import async_playwright
            
            self.playwright = await async_playwright().start()
            
            # ブラウザを起動（ヘッドレスモード）
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--single-process',
                    '--no-zygote',
                    '--disable-setuid-sandbox',
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
                    '--disable-blink-features=AutomationControlled',
                    '--enable-javascript',
                    '--enable-scripts',
                    '--allow-running-insecure-content',
                    '--disable-web-security',
                    '--allow-file-access-from-files',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            # ページを作成
            self.page = await self.browser.new_page()
            
            # ユーザーエージェントを設定
            await self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
            
            # ボット検出回避のためのスクリプトを追加
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ja-JP', 'ja', 'en-US', 'en'],
                });
            """)
            
            print("ブラウザ起動完了")
            return True
            
        except Exception as e:
            print(f"ブラウザ起動エラー: {e}")
            return False

    async def close(self):
        """ブラウザを閉じる"""
        try:
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
        except Exception as e:
            print(f"ブラウザ終了エラー: {e}")

    async def login_to_jobcan(self, email: str, password: str) -> bool:
        """Jobcanにログイン"""
        try:
            print(f"Jobcanログインを開始: {email}")
            
            # Jobcanログインページに移動
            print("Jobcanログインページに移動中...")
            await self.page.goto("https://id.jobcan.jp/users/sign_in?app_key=atd", wait_until="networkidle")
            
            # ページが完全に読み込まれるまで待機
            await asyncio.sleep(random.uniform(3, 5))
            
            # メールアドレス入力フィールドを探す
            print("メールアドレス入力フィールドを探しています...")
            email_selectors = [
                'input[name="email"]',
                'input[name="staff_code"]',
                'input[type="email"]',
                'input[placeholder*="メール"]',
                'input[placeholder*="email"]',
                'input[id*="email"]',
                'input[name="username"]',
                'input[type="text"]'
            ]
            
            email_input = None
            for selector in email_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        email_input = self.page.locator(selector).first
                        print(f"メールアドレス入力フィールドを発見: {selector}")
                        break
                except:
                    continue
            
            if not email_input:
                print("メールアドレス入力フィールドが見つかりません")
                return False
            
            # メールアドレスを入力
            print("メールアドレスを入力中...")
            await email_input.click()
            await asyncio.sleep(random.uniform(0.5, 1.0))
            await email_input.fill(email)
            
            # パスワード入力フィールドを探す
            print("パスワード入力フィールドを探しています...")
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[placeholder*="パスワード"]',
                'input[id*="password"]'
            ]
            
            password_input = None
            for selector in password_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        password_input = self.page.locator(selector).first
                        print(f"パスワード入力フィールドを発見: {selector}")
                        break
                except:
                    continue
            
            if not password_input:
                print("パスワード入力フィールドが見つかりません")
                return False
            
            # パスワードを入力
            print("パスワードを入力中...")
            await password_input.click()
            await asyncio.sleep(random.uniform(0.5, 1.0))
            await password_input.fill(password)
            
            # ログインボタンを探す
            print("ログインボタンを探しています...")
            login_selectors = [
                'input[type="submit"]',
                'button[type="submit"]',
                'button:has-text("ログイン")',
                'button:has-text("Login")'
            ]
            
            login_button = None
            for selector in login_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        login_button = self.page.locator(selector).first
                        print(f"ログインボタンを発見: {selector}")
                        break
                except:
                    continue
            
            if not login_button:
                print("ログインボタンが見つかりません")
                return False
            
            # ログインボタンをクリック
            print("ログインボタンをクリック中...")
            await login_button.click()
            
            # ログイン後のページ読み込みを待機
            await asyncio.sleep(random.uniform(3, 5))
            await self.page.wait_for_load_state("networkidle")
            
            # ログイン成功の確認
            current_url = self.page.url
            if "sign_in" not in current_url and "login" not in current_url:
                print("ログイン成功")
                return True
            else:
                print("ログイン失敗")
                return False
                
        except Exception as e:
            print(f"ログイン中にエラーが発生しました: {e}")
            return False

    async def navigate_to_attendance(self):
        """出勤簿ページに移動"""
        try:
            print("出勤簿ページに移動中...")
            
            # 出勤簿へのリンクを探す
            attendance_selectors = [
                'a[href*="attendance"]',
                'a[href*="timecard"]',
                'a:has-text("出勤簿")',
                'a:has-text("勤怠")',
                'a:has-text("Attendance")'
            ]
            
            for selector in attendance_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        print(f"出勤簿リンクを発見: {selector}")
                        await self.page.click(selector)
                        break
                except:
                    continue
            
            await self.page.wait_for_load_state("networkidle")
            print("出勤簿ページ移動完了")
            
        except Exception as e:
            print(f"出勤簿ページへの移動に失敗しました: {e}")
            raise

    async def process_attendance_data(self, df):
        """勤怠データを処理"""
        try:
            print("勤怠データの処理を開始...")
            
            for index, row in df.iterrows():
                try:
                    date = row.iloc[0]  # A列：日付
                    start_time = row.iloc[1]  # B列：始業時刻
                    end_time = row.iloc[2]  # C列：終業時刻
                    
                    print(f"{date} の勤怠データを処理中... ({index+1}/{len(df)})")
                    
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
                    
                    print(f"処理データ: 日付={date_str}, 始業={start_time_str}, 終業={end_time_str}")
                    
                    # ここで実際の勤怠入力処理を行う
                    # （実際のJobcanのUIに応じて実装）
                    
                    await asyncio.sleep(1)  # 処理間隔
                    
                except Exception as e:
                    print(f"{date} の処理でエラー: {e}")
                    continue
            
            print("勤怠データの処理が完了しました")
            
        except Exception as e:
            print(f"勤怠データ処理中にエラーが発生しました: {e}")
            raise 
