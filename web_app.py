#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jobcan勤怠申請Webアプリケーション
Flask + Playwrightで勤怠自動入力Webサービス
"""

import os
import json
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
import pandas as pd
from playwright.sync_api import sync_playwright, Page, Browser
from colorama import init, Fore, Style
from typing import Optional

# Colorama初期化
init(autoreset=True)

app = Flask(__name__)
app.secret_key = 'jobcan_automation_secret_key_2025'

# 設定
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# アップロードフォルダの作成
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class JobcanWebBot:
    """Jobcan勤怠打刻自動申請Webボット"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
    def start_browser(self, headless: bool = True):
        """ブラウザを起動"""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=headless,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            self.page = self.browser.new_page()
            print(f"{Fore.BLUE}✓ ブラウザを起動しました{Style.RESET_ALL}")
            return True
        except Exception as e:
            print(f"{Fore.RED}✗ ブラウザの起動に失敗しました: {e}{Style.RESET_ALL}")
            return False
    
    def navigate_to_url(self, url: str) -> bool:
        """指定されたURLに移動（ログイン済み状態を想定）"""
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
    
    def process_attendance_data(self, data: list, url: str) -> dict:
        """勤怠データを処理"""
        results = {
            'success_count': 0,
            'error_count': 0,
            'details': []
        }
        
        try:
            # URLに移動
            if not self.navigate_to_url(url):
                return {
                    'success_count': 0,
                    'error_count': len(data),
                    'details': [{'date': row['date'], 'status': 'error', 'error': 'URLへの移動に失敗'} for row in data]
                }
            
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
                    self.navigate_to_url(url)
                    
                    results['success_count'] += 1
                    results['details'].append({
                        'date': date,
                        'start_time': start_time,
                        'end_time': end_time,
                        'status': 'success'
                    })
                    
                    print(f"{Fore.GREEN}✓ {date} の勤怠データを正常に処理しました{Style.RESET_ALL}")
                    
                except Exception as e:
                    print(f"{Fore.RED}✗ {date} の勤怠データ処理に失敗しました: {e}{Style.RESET_ALL}")
                    results['error_count'] += 1
                    results['details'].append({
                        'date': date,
                        'start_time': start_time,
                        'end_time': end_time,
                        'status': 'error',
                        'error': str(e)
                    })
            
        except Exception as e:
            print(f"{Fore.RED}✗ 処理中にエラーが発生しました: {e}{Style.RESET_ALL}")
            results['error_count'] = len(data)
            results['details'] = [{'date': row['date'], 'status': 'error', 'error': str(e)} for row in data]
        
        return results
    
    def close(self):
        """ブラウザを閉じる"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        print(f"{Fore.BLUE}✓ ブラウザを閉じました{Style.RESET_ALL}")


def allowed_file(filename):
    """アップロードされたファイルの拡張子をチェック"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def load_excel_data(file_path: str) -> list:
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


@app.route('/')
def index():
    """メインページ"""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """ファイルアップロードと勤怠処理"""
    try:
        # セッションIDを生成
        session_id = f"session_{int(time.time())}"
        session['session_id'] = session_id
        
        # ファイルのチェック
        if 'file' not in request.files:
            return jsonify({'error': 'ファイルが選択されていません'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'ファイルが選択されていません'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Excelファイル（.xlsx, .xls）を選択してください'}), 400
        
        # URLのチェック
        jobcan_url = request.form.get('jobcan_url', '').strip()
        if not jobcan_url:
            return jsonify({'error': 'JobcanのURLを入力してください'}), 400
        
        if 'jobcan.jp' not in jobcan_url:
            return jsonify({'error': '有効なJobcanのURLを入力してください'}), 400
        
        # ファイルを保存
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_{filename}")
        file.save(file_path)
        
        # Excelデータを読み込み
        attendance_data = load_excel_data(file_path)
        
        # バックグラウンドで処理を実行
        def process_in_background():
            bot = JobcanWebBot()
            try:
                if bot.start_browser(headless=True):
                    results = bot.process_attendance_data(attendance_data, jobcan_url)
                    # 結果をセッションに保存
                    session['results'] = results
                    session['processing_complete'] = True
                else:
                    session['results'] = {
                        'success_count': 0,
                        'error_count': len(attendance_data),
                        'details': [{'date': row['date'], 'status': 'error', 'error': 'ブラウザの起動に失敗'} for row in attendance_data]
                    }
                    session['processing_complete'] = True
            except Exception as e:
                session['results'] = {
                    'success_count': 0,
                    'error_count': len(attendance_data),
                    'details': [{'date': row['date'], 'status': 'error', 'error': str(e)} for row in attendance_data]
                }
                session['processing_complete'] = True
            finally:
                bot.close()
                # 一時ファイルを削除
                try:
                    os.remove(file_path)
                except:
                    pass
        
        # バックグラウンドスレッドを開始
        thread = threading.Thread(target=process_in_background)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'message': '処理を開始しました',
            'session_id': session_id,
            'data_count': len(attendance_data)
        })
        
    except Exception as e:
        return jsonify({'error': f'エラーが発生しました: {str(e)}'}), 500


@app.route('/status/<session_id>')
def get_status(session_id):
    """処理状況を確認"""
    if session.get('session_id') != session_id:
        return jsonify({'error': '無効なセッションID'}), 400
    
    if session.get('processing_complete'):
        results = session.get('results', {})
        return jsonify({
            'complete': True,
            'results': results
        })
    else:
        return jsonify({
            'complete': False,
            'message': '処理中...'
        })


if __name__ == '__main__':
    print(f"{Fore.CYAN}Jobcan勤怠申請Webアプリケーションを起動中...{Style.RESET_ALL}")
    print(f"{Fore.GREEN}✓ サーバーを起動しました: http://localhost:5000{Style.RESET_ALL}")
    app.run(debug=True, host='0.0.0.0', port=5000) 
