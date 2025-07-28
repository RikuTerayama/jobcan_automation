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
            
            # 1. 勤怠トップページに移動
            print("勤怠トップページに移動中...")
            await self.page.goto("https://ssl.jobcan.jp/employee", wait_until="networkidle")
            await asyncio.sleep(2)
            
            # 2. 「出勤簿」タブを選択
            print("出勤簿タブを選択中...")
            attendance_tab_selectors = [
                'a:has-text("出勤簿")',
                'a[href*="attendance"]',
                'a[href="/employee/attendance"]',
                'a:has-text("勤怠")',
                'a:has-text("Attendance")'
            ]
            
            tab_found = False
            for selector in attendance_tab_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        print(f"出勤簿タブを発見: {selector}")
                        await self.page.click(selector)
                        tab_found = True
                        break
                except:
                    continue
            
            if not tab_found:
                # 直接URLでアクセス
                print("タブが見つからないため、直接URLでアクセス")
                await self.page.goto("https://ssl.jobcan.jp/employee/attendance", wait_until="networkidle")
            
            await asyncio.sleep(3)
            await self.page.wait_for_load_state("networkidle")
            
            print(f"出勤簿ページ移動完了: {self.page.url}")
            
        except Exception as e:
            print(f"出勤簿ページへの移動に失敗しました: {e}")
            raise

    async def process_attendance_data(self, df):
        """勤怠データを処理"""
        try:
            print("勤怠データを処理中...")
            print(f"データフレームの形状: {df.shape}")
            print(f"データフレームの列名: {df.columns.tolist()}")
            print(f"データフレームの最初の5行:")
            print(df.head())
            
            # ヘッダー行をスキップするかチェック
            print(f"\n=== データ処理の詳細 ===")
            print(f"総行数: {len(df)}")
            
            processed_count = 0
            success_count = 0
            error_count = 0
            
            for index, row in df.iterrows():
                try:
                    print(f"\n=== 行 {index} の処理開始 ===")
                    print(f"行の内容: {row.tolist()}")
                    
                    # ヘッダー行のチェック
                    if index == 0:
                        print(f"⚠️ 行 {index}: ヘッダー行をスキップ")
                        continue
                    
                    date = row.iloc[0]  # A列：日付
                    start_time = row.iloc[1]  # B列：始業時刻
                    end_time = row.iloc[2]  # C列：終業時刻
                    
                    print(f"生データ: 日付={date} ({type(date)}), 始業={start_time} ({type(start_time)}), 終業={end_time} ({type(end_time)})")
                    
                    # データの妥当性チェック
                    if pd.isna(date) or pd.isna(start_time) or pd.isna(end_time):
                        print(f"⚠️ 行 {index}: 無効なデータ（NaN）をスキップ")
                        error_count += 1
                        continue
                    
                    # 日付の形式を統一
                    try:
                        if isinstance(date, str):
                            date_obj = datetime.strptime(date, "%Y/%m/%d")
                        else:
                            date_obj = pd.to_datetime(date)
                        
                        date_str = date_obj.strftime("%Y/%m/%d")
                        print(f"✅ 日付変換成功: {date} → {date_str}")
                    except Exception as e:
                        print(f"❌ 行 {index}: 日付の変換でエラー: {e}")
                        error_count += 1
                        continue
                    
                    # 時刻の形式を統一
                    try:
                        if isinstance(start_time, str):
                            start_time_str = start_time
                        else:
                            start_time_str = start_time.strftime("%H:%M")
                        
                        if isinstance(end_time, str):
                            end_time_str = end_time
                        else:
                            end_time_str = end_time.strftime("%H:%M")
                        
                        print(f"✅ 時刻変換成功: 始業={start_time} → {start_time_str}, 終業={end_time} → {end_time_str}")
                    except Exception as e:
                        print(f"❌ 行 {index}: 時刻の変換でエラー: {e}")
                        error_count += 1
                        continue
                    
                    print(f"変換後データ: 日付={date_str}, 始業={start_time_str}, 終業={end_time_str}")
                    
                    # 実際の勤怠入力処理を実行
                    print(f"🔄 勤怠入力処理を開始: {date_str}")
                    success = await self.input_attendance_for_date(date_str, start_time_str, end_time_str)
                    
                    if success:
                        success_count += 1
                        print(f"✅ 行 {index} の処理が成功しました")
                    else:
                        error_count += 1
                        print(f"❌ 行 {index} の処理が失敗しました")
                    
                    processed_count += 1
                    print(f"⏳ 次の行まで待機中...")
                    await asyncio.sleep(2)  # 処理間隔
                    
                except Exception as e:
                    print(f"❌ 行 {index} の処理でエラー: {e}")
                    error_count += 1
                    continue
            
            print(f"\n=== 処理結果サマリー ===")
            print(f"処理対象行数: {processed_count}")
            print(f"成功件数: {success_count}")
            print(f"エラー件数: {error_count}")
            print(f"成功率: {success_count/processed_count*100:.1f}%" if processed_count > 0 else "処理対象なし")
            print("勤怠データの処理が完了しました")
            
        except Exception as e:
            print(f"❌ 勤怠データ処理中にエラーが発生しました: {e}")
            raise

    async def input_attendance_for_date(self, date_str: str, start_time: str, end_time: str):
        """指定された日付の勤怠を入力"""
        try:
            print(f"🔄 日付 {date_str} の勤怠入力を開始...")
            
            # 現在のページの状態を確認
            print(f"📊 現在のページ状態を確認中...")
            await self.debug_page_state("勤怠入力開始前")
            
            # 1. 日付を選択
            print(f"📅 ステップ1: 日付 {date_str} を選択中...")
            date_success = await self.select_date(date_str)
            print(f"📅 日付選択結果: {'✅ 成功' if date_success else '❌ 失敗'}")
            await self.debug_page_state("日付選択後")
            
            if not date_success:
                print(f"❌ 日付 {date_str} の選択に失敗しました")
                return False
            
            # 2. 打刻修正ボタンをクリック
            print(f"🔧 ステップ2: 打刻修正ボタンをクリック中...")
            correction_success = await self.click_stamp_correction()
            print(f"🔧 打刻修正結果: {'✅ 成功' if correction_success else '❌ 失敗'}")
            await self.debug_page_state("打刻修正ボタンクリック後")
            
            if not correction_success:
                print(f"❌ 打刻修正ボタンのクリックに失敗しました")
                return False
            
            # 3. 始業時刻を入力して打刻
            print(f"⏰ ステップ3: 始業時刻 {start_time} を入力中...")
            start_success = await self.input_start_time(start_time)
            print(f"⏰ 始業時刻入力結果: {'✅ 成功' if start_success else '❌ 失敗'}")
            await self.debug_page_state("始業時刻入力後")
            
            # 4. 終業時刻を入力して打刻
            print(f"⏰ ステップ4: 終業時刻 {end_time} を入力中...")
            end_success = await self.input_end_time(end_time)
            print(f"⏰ 終業時刻入力結果: {'✅ 成功' if end_success else '❌ 失敗'}")
            await self.debug_page_state("終業時刻入力後")
            
            # 5. 出勤簿ページに戻る
            print(f"🏠 ステップ5: 出勤簿ページに戻る中...")
            return_success = await self.return_to_attendance_page()
            print(f"🏠 ページ戻り結果: {'✅ 成功' if return_success else '❌ 失敗'}")
            await self.debug_page_state("出勤簿ページ戻り後")
            
            # 6. 処理結果をログに出力
            overall_success = start_success and end_success and return_success
            if overall_success:
                print(f"✅ {date_str}の勤怠を登録しました（始業{start_time}／終業{end_time}）")
            else:
                print(f"❌ {date_str}の勤怠登録に失敗しました（始業{start_time}／終業{end_time}）")
                print(f"   - 日付選択: {'✅' if date_success else '❌'}")
                print(f"   - 打刻修正: {'✅' if correction_success else '❌'}")
                print(f"   - 始業時刻入力: {'✅' if start_success else '❌'}")
                print(f"   - 終業時刻入力: {'✅' if end_success else '❌'}")
                print(f"   - ページ戻り: {'✅' if return_success else '❌'}")
            
            print(f"📋 日付 {date_str} の勤怠入力が完了しました")
            return overall_success
            
        except Exception as e:
            print(f"❌ 日付 {date_str} の勤怠入力でエラー: {e}")
            await self.debug_page_state("エラー発生時")
            return False

    async def debug_page_state(self, stage: str):
        """ページの状態をデバッグ出力"""
        try:
            print(f"\n=== デバッグ情報 ({stage}) ===")
            print(f"現在のURL: {self.page.url}")
            print(f"ページタイトル: {await self.page.title()}")
            
            # ページ内の要素数を確認
            try:
                form_count = await self.page.evaluate("() => document.forms.length")
                input_count = await self.page.evaluate("() => document.querySelectorAll('input').length")
                button_count = await self.page.evaluate("() => document.querySelectorAll('button').length")
                table_count = await self.page.evaluate("() => document.querySelectorAll('table').length")
                td_count = await self.page.evaluate("() => document.querySelectorAll('td').length")
                
                print(f"フォーム数: {form_count}")
                print(f"入力フィールド数: {input_count}")
                print(f"ボタン数: {button_count}")
                print(f"テーブル数: {table_count}")
                print(f"TD要素数: {td_count}")
                
                # 日付関連の要素を確認
                print("日付関連の要素を確認中...")
                date_elements = await self.page.evaluate("""
                    () => {
                        const tds = document.querySelectorAll('td');
                        const results = [];
                        for (let i = 0; i < tds.length; i++) {
                            const td = tds[i];
                            const text = td.textContent || '';
                            if (text.match(/\\d{2}\\/\\d{2}/) || text.match(/\\d{2}\\/\\d{2}\\([月火水木金土日]\\)/)) {
                                results.push({
                                    index: i,
                                    text: text.trim(),
                                    className: td.className || '',
                                    id: td.id || '',
                                    visible: td.offsetWidth > 0 && td.offsetHeight > 0
                                });
                            }
                        }
                        return results;
                    }
                """)
                
                if date_elements:
                    print("日付要素を発見:")
                    for i, date_info in enumerate(date_elements):
                        print(f"  date[{i}]: {date_info}")
                else:
                    print("日付要素が見つかりませんでした")
                
                # 入力フィールドの詳細を確認
                if input_count > 0:
                    print("入力フィールドの詳細:")
                    inputs_info = await self.page.evaluate("""
                        () => {
                            const inputs = document.querySelectorAll('input');
                            const results = [];
                            for (let i = 0; i < inputs.length; i++) {
                                const input = inputs[i];
                                results.push({
                                    index: i,
                                    type: input.type || '',
                                    name: input.name || '',
                                    id: input.id || '',
                                    placeholder: input.placeholder || '',
                                    value: input.value || '',
                                    visible: input.offsetWidth > 0 && input.offsetHeight > 0
                                });
                            }
                            return results;
                        }
                    """)
                    
                    for i, input_info in enumerate(inputs_info):
                        print(f"  input[{i}]: {input_info}")
                
                # ボタンの詳細を確認
                if button_count > 0:
                    print("ボタンの詳細:")
                    buttons_info = await self.page.evaluate("""
                        () => {
                            const buttons = document.querySelectorAll('button');
                            const results = [];
                            for (let i = 0; i < buttons.length; i++) {
                                const button = buttons[i];
                                results.push({
                                    index: i,
                                    text: button.textContent || '',
                                    type: button.type || '',
                                    id: button.id || '',
                                    className: button.className || '',
                                    visible: button.offsetWidth > 0 && button.offsetHeight > 0
                                });
                            }
                            return results;
                        }
                    """)
                    
                    for i, button_info in enumerate(buttons_info):
                        print(f"  button[{i}]: {button_info}")
                
            except Exception as e:
                print(f"デバッグ情報取得でエラー: {e}")
            
            print("=== デバッグ情報終了 ===\n")
            
        except Exception as e:
            print(f"デバッグページ状態でエラー: {e}")

    async def select_date(self, date_str: str):
        """指定された日付を選択"""
        try:
            print(f"📅 日付 {date_str} を選択中...")
            
            # 日付文字列を解析
            date_obj = datetime.strptime(date_str, "%Y/%m/%d")
            year = date_obj.year
            month = date_obj.month
            day = date_obj.day
            
            # 曜日を取得（日本語）
            weekday_jp = ['月', '火', '水', '木', '金', '土', '日']
            weekday = weekday_jp[date_obj.weekday()]
            
            # Jobcanの実際の日付形式に変換（例：07/01(火)）
            jobcan_date_format = f"{month:02d}/{day:02d}({weekday})"
            print(f"📅 Jobcan日付形式: {jobcan_date_format}")
            
            # 日付セレクターを探す（Jobcanの実際の形式に基づく）
            date_selectors = [
                f'td:has-text("{jobcan_date_format}")',
                f'a:has-text("{jobcan_date_format}")',
                f'td:has-text("{month:02d}/{day:02d}")',
                f'a:has-text("{month:02d}/{day:02d}")',
                f'[data-date="{date_str}"]',
                f'[data-date="{year}-{month:02d}-{day:02d}"]',
                f'td[data-date="{date_str}"]',
                f'td[data-date="{year}-{month:02d}-{day:02d}"]',
                f'a[href*="{year}/{month:02d}/{day:02d}"]',
                f'a[href*="{year}-{month:02d}-{day:02d}"]'
            ]
            
            print(f"🔍 日付セレクターを検索中...")
            for i, selector in enumerate(date_selectors):
                try:
                    count = await self.page.locator(selector).count()
                    print(f"🔍 セレクター {i+1}/{len(date_selectors)}: {selector} → {count}個発見")
                    if count > 0:
                        print(f"✅ 日付セレクターを発見: {selector}")
                        await self.page.click(selector)
                        await asyncio.sleep(2)
                        return True
                except Exception as e:
                    print(f"❌ セレクター {selector} でエラー: {e}")
                    continue
            
            # 日付が見つからない場合は、カレンダーから探す
            print(f"🔍 カレンダーから日付を検索中...")
            calendar_success = await self.select_date_from_calendar(date_str)
            if calendar_success:
                return True
            
            print(f"❌ 日付 {date_str} が見つかりませんでした")
            return False
            
        except Exception as e:
            print(f"❌ 日付選択でエラー: {e}")
            return False

    async def select_date_from_calendar(self, date_str: str):
        """カレンダーから日付を選択"""
        try:
            print(f"カレンダーから日付 {date_str} を選択中...")
            
            # 日付文字列から日付オブジェクトを作成
            date_obj = datetime.strptime(date_str, "%Y/%m/%d")
            year = date_obj.year
            month = date_obj.month
            day = date_obj.day
            
            # 曜日を取得（日本語）
            weekday_jp = ['月', '火', '水', '木', '金', '土', '日']
            weekday = weekday_jp[date_obj.weekday()]
            
            # Jobcanの実際の日付形式
            jobcan_date_format = f"{month:02d}/{day:02d}({weekday})"
            jobcan_date_simple = f"{month:02d}/{day:02d}"
            
            # カレンダーのセレクターを探す
            calendar_selectors = [
                '.calendar',
                '.datepicker',
                '[class*="calendar"]',
                '[class*="datepicker"]',
                'table[class*="calendar"]',
                'div[class*="calendar"]',
                'table',
                'tbody'
            ]
            
            for selector in calendar_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        print(f"カレンダーを発見: {selector}")
                        
                        # カレンダー内で日付を探す（複数の形式に対応）
                        day_selectors = [
                            f'td:has-text("{jobcan_date_format}")',
                            f'a:has-text("{jobcan_date_format}")',
                            f'td:has-text("{jobcan_date_simple}")',
                            f'a:has-text("{jobcan_date_simple}")',
                            f'td:has-text("{day}")',
                            f'a:has-text("{day}")',
                            f'[data-day="{day}"]',
                            f'[data-date*="{day}"]',
                            f'[data-date="{date_str}"]',
                            f'[data-date="{year}-{month:02d}-{day:02d}"]'
                        ]
                        
                        for day_selector in day_selectors:
                            try:
                                if await self.page.locator(day_selector).count() > 0:
                                    print(f"日付 {jobcan_date_format} を発見: {day_selector}")
                                    await self.page.click(day_selector)
                                    await asyncio.sleep(2)
                                    return True
                            except Exception as e:
                                print(f"日付セレクター {day_selector} でエラー: {e}")
                                continue
                        break
                except Exception as e:
                    print(f"カレンダーセレクター {selector} でエラー: {e}")
                    continue
            
            print(f"❌ 日付 {date_str} が見つかりませんでした")
            return False
            
        except Exception as e:
            print(f"❌ カレンダーからの日付選択でエラー: {e}")
            return False

    async def click_stamp_correction(self):
        """打刻修正ボタンをクリック"""
        try:
            print("🔧 打刻修正ボタンをクリック中...")
            
            # 打刻修正ボタンを探す（Jobcanの実際のUIに基づく）
            correction_selectors = [
                'button:has-text("打刻修正")',
                'a:has-text("打刻修正")',
                'input[value*="打刻修正"]',
                'button:has-text("修正")',
                'a:has-text("修正")',
                'button:has-text("編集")',
                'a:has-text("編集")',
                '[class*="edit"]',
                '[class*="correction"]',
                '[class*="modify"]',
                'a[href*="modify"]',
                'a[href*="edit"]'
            ]
            
            print(f"🔍 打刻修正ボタンを検索中...")
            for i, selector in enumerate(correction_selectors):
                try:
                    count = await self.page.locator(selector).count()
                    print(f"🔍 セレクター {i+1}/{len(correction_selectors)}: {selector} → {count}個発見")
                    if count > 0:
                        print(f"✅ 打刻修正ボタンを発見: {selector}")
                        await self.page.click(selector)
                        await asyncio.sleep(3)
                        
                        # URLが打刻修正ページに変わったか確認
                        current_url = self.page.url
                        print(f"🔗 現在のURL: {current_url}")
                        if "modify" in current_url or "edit" in current_url:
                            print(f"✅ 打刻修正ページに遷移しました: {current_url}")
                            return True
                        else:
                            print(f"⚠️ 打刻修正ページへの遷移を確認できません: {current_url}")
                except Exception as e:
                    print(f"❌ セレクター {selector} でエラー: {e}")
                    continue
            
            print("❌ 打刻修正ボタンが見つかりませんでした")
            return False
            
        except Exception as e:
            print(f"❌ 打刻修正ボタンのクリックでエラー: {e}")
            return False

    async def input_start_time(self, start_time: str):
        """始業時刻を入力して打刻"""
        try:
            print(f"始業時刻 {start_time} を入力中...")
            
            # 始業時刻入力フィールドを探す（Jobcanの実際のUIに基づく）
            start_time_selectors = [
                'input[name*="start"]',
                'input[name*="begin"]',
                'input[placeholder*="始業"]',
                'input[placeholder*="開始"]',
                'input[id*="start"]',
                'input[id*="begin"]',
                'input[type="time"]:first-of-type',
                'input[type="time"]',
                'input[name="start_time"]',
                'input[name="begin_time"]'
            ]
            
            start_input = None
            for selector in start_time_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        print(f"始業時刻入力フィールドを発見: {selector}")
                        start_input = self.page.locator(selector).first
                        break
                except Exception as e:
                    print(f"セレクター {selector} でエラー: {e}")
                    continue
            
            if not start_input:
                print("始業時刻入力フィールドが見つかりませんでした")
                return False
            
            # 始業時刻を入力
            await start_input.click()
            await asyncio.sleep(1)
            await start_input.fill(start_time)
            await asyncio.sleep(1)
            
            # 始業時刻の打刻ボタンをクリック
            await self.click_start_stamp_button()
            
            return True
            
        except Exception as e:
            print(f"始業時刻入力でエラー: {e}")
            raise

    async def click_start_stamp_button(self):
        """始業時刻の打刻ボタンをクリック"""
        try:
            print("始業時刻の打刻ボタンをクリック中...")
            
            # 始業時刻の打刻ボタンを探す
            start_stamp_selectors = [
                'button:has-text("打刻")',
                'input[value*="打刻"]',
                'button:has-text("登録")',
                'input[value*="登録"]',
                'button[type="submit"]',
                'input[type="submit"]',
                '[class*="stamp"]',
                '[class*="submit"]'
            ]
            
            for selector in start_stamp_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        print(f"始業時刻打刻ボタンを発見: {selector}")
                        await self.page.click(selector)
                        await asyncio.sleep(2)
                        
                        # 打刻完了メッセージを確認
                        await self.check_stamp_completion_message("始業")
                        return True
                except Exception as e:
                    print(f"セレクター {selector} でエラー: {e}")
                    continue
            
            print("始業時刻の打刻ボタンが見つかりませんでした")
            return False
            
        except Exception as e:
            print(f"始業時刻打刻ボタンのクリックでエラー: {e}")
            return False

    async def input_end_time(self, end_time: str):
        """終業時刻を入力して打刻"""
        try:
            print(f"終業時刻 {end_time} を入力中...")
            
            # 終業時刻入力フィールドを探す（Jobcanの実際のUIに基づく）
            end_time_selectors = [
                'input[name*="end"]',
                'input[name*="finish"]',
                'input[placeholder*="終業"]',
                'input[placeholder*="終了"]',
                'input[id*="end"]',
                'input[id*="finish"]',
                'input[type="time"]:last-of-type',
                'input[type="time"]',
                'input[name="end_time"]',
                'input[name="finish_time"]'
            ]
            
            end_input = None
            for selector in end_time_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        print(f"終業時刻入力フィールドを発見: {selector}")
                        end_input = self.page.locator(selector).first
                        break
                except Exception as e:
                    print(f"セレクター {selector} でエラー: {e}")
                    continue
            
            if not end_input:
                print("終業時刻入力フィールドが見つかりませんでした")
                return False
            
            # 終業時刻を入力
            await end_input.click()
            await asyncio.sleep(1)
            await end_input.fill(end_time)
            await asyncio.sleep(1)
            
            # 終業時刻の打刻ボタンをクリック
            await self.click_end_stamp_button()
            
            return True
            
        except Exception as e:
            print(f"終業時刻入力でエラー: {e}")
            raise

    async def click_end_stamp_button(self):
        """終業時刻の打刻ボタンをクリック"""
        try:
            print("終業時刻の打刻ボタンをクリック中...")
            
            # 終業時刻の打刻ボタンを探す
            end_stamp_selectors = [
                'button:has-text("打刻")',
                'input[value*="打刻"]',
                'button:has-text("登録")',
                'input[value*="登録"]',
                'button[type="submit"]',
                'input[type="submit"]',
                '[class*="stamp"]',
                '[class*="submit"]'
            ]
            
            for selector in end_stamp_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        print(f"終業時刻打刻ボタンを発見: {selector}")
                        await self.page.click(selector)
                        await asyncio.sleep(2)
                        
                        # 打刻完了メッセージを確認
                        await self.check_stamp_completion_message("終業")
                        return True
                except Exception as e:
                    print(f"セレクター {selector} でエラー: {e}")
                    continue
            
            print("終業時刻の打刻ボタンが見つかりませんでした")
            return False
            
        except Exception as e:
            print(f"終業時刻打刻ボタンのクリックでエラー: {e}")
            return False

    async def click_save_button(self):
        """保存ボタンをクリック"""
        try:
            print("保存ボタンをクリック中...")
            
            # 保存ボタンを探す（複数のパターンを試す）
            save_selectors = [
                'button:has-text("保存")',
                'button:has-text("登録")',
                'button:has-text("確定")',
                'input[value*="保存"]',
                'input[value*="登録"]',
                'input[value*="確定"]',
                'button[type="submit"]',
                'input[type="submit"]',
                '[class*="save"]',
                '[class*="submit"]',
                '[class*="confirm"]'
            ]
            
            for selector in save_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        print(f"保存ボタンを発見: {selector}")
                        await self.page.click(selector)
                        await asyncio.sleep(2)
                        return
                except:
                    continue
            
            print("保存ボタンが見つかりませんでした")
            
        except Exception as e:
            print(f"保存ボタンのクリックでエラー: {e}")
            raise

    async def check_stamp_completion_message(self, stamp_type: str):
        """打刻完了メッセージを確認"""
        try:
            print(f"{stamp_type}打刻完了メッセージを確認中...")
            
            # 完了メッセージのセレクター
            completion_selectors = [
                'text=打刻が完了しました',
                'text=登録が完了しました',
                'text=保存が完了しました',
                'text=完了しました',
                'text=正常に処理されました',
                '[class*="success"]',
                '[class*="complete"]',
                '[class*="message"]'
            ]
            
            for selector in completion_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        message = await self.page.locator(selector).first.text_content()
                        print(f"{stamp_type}打刻完了メッセージ: {message}")
                        return True
                except:
                    continue
            
            print(f"{stamp_type}打刻完了メッセージは確認できませんでした")
            return False
            
        except Exception as e:
            print(f"打刻完了メッセージ確認でエラー: {e}")
            return False

    async def return_to_attendance_page(self):
        """出勤簿ページに戻る"""
        try:
            print("出勤簿ページに戻る中...")
            
            # 出勤簿ページに直接移動
            await self.page.goto("https://ssl.jobcan.jp/employee/attendance", wait_until="networkidle")
            await asyncio.sleep(3)
            
            # URLが正しいか確認
            current_url = self.page.url
            if "attendance" in current_url:
                print(f"✅ 出勤簿ページに戻りました: {current_url}")
                return True
            else:
                print(f"⚠️ 出勤簿ページへの戻りを確認できません: {current_url}")
                return False
            
        except Exception as e:
            print(f"❌ 出勤簿ページへの戻りでエラー: {e}")
            return False 
