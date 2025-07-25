#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jobcan勤怠打刻自動申請ツール
Excelファイルから勤怠データを読み取り、Jobcanに自動入力するスクリプト
"""

import sys
import os
import json
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd
from playwright.sync_api import sync_playwright, Page, Browser
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from colorama import init, Fore, Style

# Colorama初期化
init(autoreset=True)

class JobcanBot:
    """Jobcan勤怠打刻自動申請ボット"""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.credentials_file = "credentials.enc"
        self.key_file = "key.key"
        self.fernet = self._load_or_create_key()
        self.base_url = "https://id.jobcan.jp"
        
    def _load_or_create_key(self) -> Fernet:
        """暗号化キーの読み込みまたは作成"""
        if os.path.exists(self.key_file):
            with open(self.key_file, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(key)
        return Fernet(key)
    
    def save_credentials(self, email: str, password: str):
        """ログイン情報を暗号化して保存"""
        credentials = {
            "email": email,
            "password": password
        }
        encrypted_data = self.fernet.encrypt(json.dumps(credentials).encode())
        with open(self.credentials_file, "wb") as f:
            f.write(encrypted_data)
        print(f"{Fore.GREEN}✓ ログイン情報を暗号化して保存しました{Style.RESET_ALL}")
    
    def load_credentials(self) -> Optional[Dict[str, str]]:
        """保存されたログイン情報を復号化して読み込み"""
        if not os.path.exists(self.credentials_file):
            return None
        
        try:
            with open(self.credentials_file, "rb") as f:
                encrypted_data = f.read()
            decrypted_data = self.fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            print(f"{Fore.RED}✗ ログイン情報の読み込みに失敗しました: {e}{Style.RESET_ALL}")
            return None
    
    def start_browser(self):
        """ブラウザを起動"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        self.page = self.browser.new_page()
        print(f"{Fore.BLUE}✓ ブラウザを起動しました{Style.RESET_ALL}")
    
    def login(self, email: str = None, password: str = None) -> bool:
        """Jobcanにログイン"""
        try:
            # 保存された認証情報を試す
            if not email or not password:
                credentials = self.load_credentials()
                if credentials:
                    email = credentials["email"]
                    password = credentials["password"]
                else:
                    print(f"{Fore.YELLOW}保存されたログイン情報が見つかりません{Style.RESET_ALL}")
                    return False
            
            print(f"{Fore.BLUE}ログイン中...{Style.RESET_ALL}")
            self.page.goto(f"{self.base_url}/users/sign_in")
            
            # ログインフォームに入力
            self.page.fill('input[name="user[email]"]', email)
            self.page.fill('input[name="user[password]"]', password)
            
            # ログインボタンをクリック
            self.page.click('input[type="submit"]')
            
            # ログイン成功の確認
            self.page.wait_for_load_state("networkidle")
            
            # ダッシュボードにリダイレクトされたかチェック
            if "dashboard" in self.page.url or "attendance" in self.page.url:
                print(f"{Fore.GREEN}✓ ログインに成功しました{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.RED}✗ ログインに失敗しました{Style.RESET_ALL}")
                return False
                
        except Exception as e:
            print(f"{Fore.RED}✗ ログイン中にエラーが発生しました: {e}{Style.RESET_ALL}")
            return False
    
    def navigate_to_url(self, url: str) -> bool:
        """指定されたURLに直接移動（ログイン済み状態を想定）"""
        try:
            print(f"{Fore.BLUE}指定されたURLに移動中: {url}{Style.RESET_ALL}")
            self.page.goto(url)
            self.page.wait_for_load_state("networkidle")
            
            # ログイン状態をチェック
            if "sign_in" in self.page.url or "login" in self.page.url:
                print(f"{Fore.RED}✗ ログインが必要です。URLが正しいか確認してください{Style.RESET_ALL}")
                return False
            
            print(f"{Fore.GREEN}✓ URLに正常に移動しました{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}✗ URLへの移動に失敗しました: {e}{Style.RESET_ALL}")
            return False
    
    def navigate_to_attendance(self):
        """出勤簿ページに移動"""
        try:
            print(f"{Fore.BLUE}出勤簿ページに移動中...{Style.RESET_ALL}")
            
            # 出勤簿へのリンクを探す（複数のパターンを試す）
            attendance_selectors = [
                'a[href*="attendance"]',
                'a[href*="timecard"]',
                'a:has-text("出勤簿")',
                'a:has-text("勤怠")',
                'a:has-text("Attendance")'
            ]
            
            for selector in attendance_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        self.page.click(selector)
                        break
                except:
                    continue
            
            self.page.wait_for_load_state("networkidle")
            print(f"{Fore.GREEN}✓ 出勤簿ページに移動しました{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.RED}✗ 出勤簿ページへの移動に失敗しました: {e}{Style.RESET_ALL}")
            raise
    
    def select_date(self, date_str: str):
        """指定された日付を選択"""
        try:
            date_obj = datetime.strptime(date_str, "%Y/%m/%d")
            formatted_date = date_obj.strftime("%Y-%m-%d")
            
            print(f"{Fore.BLUE}日付 {date_str} を選択中...{Style.RESET_ALL}")
            
            # 日付セレクターを探す（複数のパターンを試す）
            date_selectors = [
                f'[data-date="{formatted_date}"]',
                f'[data-date="{date_str}"]',
                f'td[data-date="{formatted_date}"]',
                f'td[data-date="{date_str}"]',
                f'a[href*="{formatted_date}"]',
                f'a[href*="{date_str}"]'
            ]
            
            for selector in date_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        self.page.click(selector)
                        break
                except:
                    continue
            
            self.page.wait_for_load_state("networkidle")
            print(f"{Fore.GREEN}✓ 日付 {date_str} を選択しました{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.RED}✗ 日付選択に失敗しました: {e}{Style.RESET_ALL}")
            raise
    
    def click_stamp_correction(self):
        """打刻修正ボタンをクリック"""
        try:
            print(f"{Fore.BLUE}打刻修正ボタンをクリック中...{Style.RESET_ALL}")
            
            # 打刻修正ボタンを探す（複数のパターンを試す）
            correction_selectors = [
                'button:has-text("打刻修正")',
                'a:has-text("打刻修正")',
                'input[value*="打刻修正"]',
                'button:has-text("修正")',
                'a:has-text("修正")'
            ]
            
            for selector in correction_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        self.page.click(selector)
                        break
                except:
                    continue
            
            self.page.wait_for_load_state("networkidle")
            print(f"{Fore.GREEN}✓ 打刻修正ボタンをクリックしました{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.RED}✗ 打刻修正ボタンのクリックに失敗しました: {e}{Style.RESET_ALL}")
            raise
    
    def input_time(self, time_type: str, time_str: str):
        """時刻を入力して打刻"""
        try:
            print(f"{Fore.BLUE}{time_type}時刻 {time_str} を入力中...{Style.RESET_ALL}")
            
            # 時刻入力フィールドを探す
            time_input_selectors = [
                f'input[name*="{time_type.lower()}"]',
                f'input[name*="{time_type}"]',
                f'input[placeholder*="{time_type}"]',
                f'input[type="time"]'
            ]
            
            time_input = None
            for selector in time_input_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        time_input = self.page.locator(selector).first
                        break
                except:
                    continue
            
            if not time_input:
                raise Exception(f"{time_type}時刻の入力フィールドが見つかりません")
            
            # 時刻を入力
            time_input.fill(time_str)
            
            # 打刻ボタンをクリック
            stamp_selectors = [
                'button:has-text("打刻")',
                'input[value*="打刻"]',
                'button:has-text("登録")',
                'input[value*="登録"]'
            ]
            
            for selector in stamp_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        self.page.click(selector)
                        break
                except:
                    continue
            
            self.page.wait_for_load_state("networkidle")
            print(f"{Fore.GREEN}✓ {time_type}時刻 {time_str} を入力しました{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.RED}✗ {time_type}時刻の入力に失敗しました: {e}{Style.RESET_ALL}")
            raise
    
    def process_attendance_data(self, data: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """勤怠データを処理"""
        processed_data = []
        
        for row in data:
            try:
                date = row['date']
                start_time = row['start_time']
                end_time = row['end_time']
                
                print(f"\n{Fore.CYAN}=== {date} の勤怠データを処理中 ==={Style.RESET_ALL}")
                
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
                
                print(f"{Fore.GREEN}✓ {date} の勤怠データを正常に処理しました{Style.RESET_ALL}")
                
            except Exception as e:
                print(f"{Fore.RED}✗ {date} の勤怠データ処理に失敗しました: {e}{Style.RESET_ALL}")
                processed_data.append({
                    'date': date,
                    'start_time': start_time,
                    'end_time': end_time,
                    'status': 'error',
                    'error': str(e)
                })
        
        return processed_data
    
    def load_excel_data(self, file_path: str) -> List[Dict[str, str]]:
        """Excelファイルから勤怠データを読み込み"""
        try:
            print(f"{Fore.BLUE}Excelファイルを読み込み中: {file_path}{Style.RESET_ALL}")
            
            df = pd.read_excel(file_path, header=0)
            
            # 列名を確認
            if len(df.columns) < 3:
                raise ValueError("Excelファイルには少なくとも3列（日付、始業時刻、終業時刻）が必要です")
            
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
            
            print(f"{Fore.GREEN}✓ {len(data)}件の勤怠データを読み込みました{Style.RESET_ALL}")
            return data
            
        except Exception as e:
            print(f"{Fore.RED}✗ Excelファイルの読み込みに失敗しました: {e}{Style.RESET_ALL}")
            raise
    
    def display_results(self, processed_data: List[Dict[str, str]]):
        """処理結果を表示"""
        print(f"\n{Fore.CYAN}=== 処理結果 ==={Style.RESET_ALL}")
        
        success_count = 0
        error_count = 0
        
        for data in processed_data:
            if data['status'] == 'success':
                print(f"{Fore.GREEN}✓ {data['date']}: {data['start_time']} - {data['end_time']}{Style.RESET_ALL}")
                success_count += 1
            else:
                print(f"{Fore.RED}✗ {data['date']}: {data['start_time']} - {data['end_time']} (エラー: {data.get('error', 'Unknown')}){Style.RESET_ALL}")
                error_count += 1
        
        print(f"\n{Fore.CYAN}=== サマリー ==={Style.RESET_ALL}")
        print(f"成功: {success_count}件")
        print(f"失敗: {error_count}件")
        print(f"合計: {len(processed_data)}件")
    
    def close(self):
        """ブラウザを閉じる"""
        if self.browser:
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()
        print(f"{Fore.BLUE}✓ ブラウザを閉じました{Style.RESET_ALL}")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="Jobcan勤怠打刻自動申請ツール")
    parser.add_argument("excel_file", help="入力Excelファイルのパス")
    parser.add_argument("--email", help="Jobcanのメールアドレス")
    parser.add_argument("--password", help="Jobcanのパスワード")
    parser.add_argument("--headless", action="store_true", help="ヘッドレスモードで実行")
    parser.add_argument("--save-credentials", action="store_true", help="ログイン情報を保存")
    parser.add_argument("--url", help="Jobcanログイン後のURL（ログイン済み状態で使用）")
    
    args = parser.parse_args()
    
    # Excelファイルの存在確認
    if not os.path.exists(args.excel_file):
        print(f"{Fore.RED}✗ 指定されたExcelファイルが見つかりません: {args.excel_file}{Style.RESET_ALL}")
        sys.exit(1)
    
    bot = JobcanBot(headless=args.headless)
    
    try:
        # ブラウザを起動
        bot.start_browser()
        
        # URLが指定されている場合は直接移動
        if args.url:
            if bot.navigate_to_url(args.url):
                print(f"{Fore.GREEN}✓ 指定されたURLに正常に移動しました{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ URLへの移動に失敗しました{Style.RESET_ALL}")
                sys.exit(1)
        else:
            # 通常のログイン処理
            if args.email and args.password:
                if args.save_credentials:
                    bot.save_credentials(args.email, args.password)
                login_success = bot.login(args.email, args.password)
            else:
                login_success = bot.login()
            
            if not login_success:
                print(f"{Fore.RED}✗ ログインに失敗しました。メールアドレスとパスワードを確認してください。{Style.RESET_ALL}")
                sys.exit(1)
        
        # 出勤簿ページに移動
        bot.navigate_to_attendance()
        
        # Excelデータを読み込み
        attendance_data = bot.load_excel_data(args.excel_file)
        
        # 勤怠データを処理
        processed_data = bot.process_attendance_data(attendance_data)
        
        # 結果を表示
        bot.display_results(processed_data)
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}処理が中断されました{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}✗ 予期しないエラーが発生しました: {e}{Style.RESET_ALL}")
    finally:
        bot.close()


if __name__ == "__main__":
    main() 
