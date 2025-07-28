#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jobcan勤怠申請Webアプリケーション
Flask + Playwright + Pandasを使用したWebインターフェース
"""

import os
import json
import tempfile
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from werkzeug.utils import secure_filename
from playwright.sync_api import sync_playwright, Page, Browser
import threading
import queue

app = Flask(__name__)
app.secret_key = os.urandom(24)

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

def load_excel_data(file_path: str) -> List[Dict[str, str]]:
    """Excelファイルから勤怠データを読み込み"""
    try:
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
        
        return data
        
    except Exception as e:
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
        self.playwright = sync_playwright().start()
        
        # Railway環境用の設定
        browser_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor'
        ]
        
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=browser_args
        )
        self.page = self.browser.new_page()
        self.status_queue.put({"status": "browser_started", "message": "ブラウザを起動しました"})
        
    def navigate_to_url(self, url: str) -> bool:
        """指定されたURLに移動"""
        try:
            self.status_queue.put({"status": "navigating", "message": f"URLに移動中: {url}"})
            self.page.goto(url)
            self.page.wait_for_load_state("networkidle")
            
            # ログイン状態をチェック
            if "sign_in" in self.page.url or "login" in self.page.url:
                self.status_queue.put({"status": "error", "message": "ログインが必要です。URLが正しいか確認してください"})
                return False
            
            self.status_queue.put({"status": "url_loaded", "message": "URLに正常に移動しました"})
            return True
            
        except Exception as e:
            self.status_queue.put({"status": "error", "message": f"URLへの移動に失敗しました: {e}"})
            return False
    
    def navigate_to_attendance(self):
        """出勤簿ページに移動"""
        try:
            self.status_queue.put({"status": "navigating", "message": "出勤簿ページに移動中..."})
            
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
            self.status_queue.put({"status": "attendance_loaded", "message": "出勤簿ページに移動しました"})
            
        except Exception as e:
            self.status_queue.put({"status": "error", "message": f"出勤簿ページへの移動に失敗しました: {e}"})
            raise
    
    def select_date(self, date_str: str):
        """指定された日付を選択"""
        try:
            date_obj = datetime.strptime(date_str, "%Y/%m/%d")
            formatted_date = date_obj.strftime("%Y-%m-%d")
            
            self.status_queue.put({"status": "processing", "message": f"日付 {date_str} を選択中..."})
            
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
            self.status_queue.put({"status": "date_selected", "message": f"日付 {date_str} を選択しました"})
            
        except Exception as e:
            self.status_queue.put({"status": "error", "message": f"日付選択に失敗しました: {e}"})
            raise
    
    def click_stamp_correction(self):
        """打刻修正ボタンをクリック"""
        try:
            self.status_queue.put({"status": "processing", "message": "打刻修正ボタンをクリック中..."})
            
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
            self.status_queue.put({"status": "correction_clicked", "message": "打刻修正ボタンをクリックしました"})
            
        except Exception as e:
            self.status_queue.put({"status": "error", "message": f"打刻修正ボタンのクリックに失敗しました: {e}"})
            raise
    
    def input_time(self, time_type: str, time_str: str):
        """時刻を入力して打刻"""
        try:
            self.status_queue.put({"status": "processing", "message": f"{time_type}時刻 {time_str} を入力中..."})
            
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
            self.status_queue.put({"status": "time_inputted", "message": f"{time_type}時刻 {time_str} を入力しました"})
            
        except Exception as e:
            self.status_queue.put({"status": "error", "message": f"{time_type}時刻の入力に失敗しました: {e}"})
            raise
    
    def process_attendance_data(self, data: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """勤怠データを処理"""
        processed_data = []
        
        for i, row in enumerate(data):
            try:
                date = row['date']
                start_time = row['start_time']
                end_time = row['end_time']
                
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
                
                self.status_queue.put({"status": "success", "message": f"{date} の勤怠データを正常に処理しました"})
                
            except Exception as e:
                self.status_queue.put({"status": "error", "message": f"{date} の勤怠データ処理に失敗しました: {e}"})
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
        self.status_queue.put({"status": "completed", "message": "ブラウザを閉じました"})

def process_jobcan_automation(job_id: str, url: str, file_path: str):
    """バックグラウンドでJobcan自動化処理を実行"""
    try:
        processing_status[job_id] = {"status": "starting", "message": "処理を開始しています..."}
        
        # 自動化クラスを初期化
        automation = JobcanAutomation(headless=True)
        
        # ブラウザを起動
        automation.start_browser()
        processing_status[job_id] = {"status": "browser_started", "message": "ブラウザを起動しました"}
        
        # URLに移動
        if not automation.navigate_to_url(url):
            processing_status[job_id] = {"status": "error", "message": "URLへの移動に失敗しました"}
            return
        
        # 出勤簿ページに移動
        automation.navigate_to_attendance()
        
        # Excelデータを読み込み
        attendance_data = load_excel_data(file_path)
        processing_status[job_id] = {"status": "data_loaded", "message": f"{len(attendance_data)}件の勤怠データを読み込みました"}
        
        # 勤怠データを処理
        processed_data = automation.process_attendance_data(attendance_data)
        
        # 結果を集計
        success_count = sum(1 for r in processed_data if r['status'] == 'success')
        error_count = len(processed_data) - success_count
        
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
        processing_status[job_id] = {"status": "error", "message": f"予期しないエラーが発生しました: {e}"}
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
        # ファイルの確認
        if 'file' not in request.files:
            return jsonify({'error': 'ファイルが選択されていません'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'ファイルが選択されていません'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Excelファイル（.xlsx, .xls）のみアップロード可能です'}), 400
        
        # URLの確認
        url = request.form.get('jobcan_url', '').strip()
        if not url:
            return jsonify({'error': 'JobcanのURLを入力してください'}), 400
        
        # ファイルを一時保存
        filename = secure_filename(file.filename)
        temp_path = os.path.join(UPLOAD_FOLDER, f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
        file.save(temp_path)
        
        # 処理IDを生成
        job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # バックグラウンドで処理を開始
        thread = threading.Thread(
            target=process_jobcan_automation,
            args=(job_id, url, temp_path)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': '処理を開始しました'
        })
        
    except Exception as e:
        return jsonify({'error': f'エラーが発生しました: {e}'}), 500

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
