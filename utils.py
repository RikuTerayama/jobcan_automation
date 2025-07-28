import os
import subprocess
import sys
from typing import List, Dict
import pandas as pd


def allowed_file(filename):
    """ファイル拡張子をチェック"""
    ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def ensure_playwright_browser():
    """Playwrightブラウザを確保"""
    try:
        print("Playwrightブラウザを確認中...")
        
        # Playwrightがインストールされているかチェック
        try:
            import playwright
            print("Playwrightがインストールされています")
        except ImportError:
            print("Playwrightがインストールされていません。インストール中...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
            print("Playwrightのインストールが完了しました")
        
        # ブラウザをインストール
        try:
            subprocess.check_call([sys.executable, "-m", "playwright", "install", "--force", "chromium"])
            print("Chromiumブラウザのインストールが完了しました")
        except subprocess.CalledProcessError as e:
            print(f"ブラウザのインストールでエラー: {e}")
            # システム依存関係をインストール
            try:
                subprocess.check_call([sys.executable, "-m", "playwright", "install-deps"])
                print("システム依存関係のインストールが完了しました")
            except subprocess.CalledProcessError as e2:
                print(f"システム依存関係のインストールでエラー: {e2}")
        
    except Exception as e:
        print(f"Playwrightブラウザの確保でエラー: {e}")


def load_excel_data(file_path: str) -> List[Dict[str, str]]:
    """Excelファイルからデータを読み込み"""
    try:
        print(f"📁 Excelファイルを読み込み中: {file_path}")
        
        # ファイルの存在確認
        if not os.path.exists(file_path):
            print(f"❌ ファイルが存在しません: {file_path}")
            return []
        
        print(f"✅ ファイルが存在します")
        
        # Excelファイルを読み込み
        print(f"📊 Excelファイルを読み込み中...")
        df = pd.read_excel(file_path)
        
        # データの形式を確認
        print(f"📊 データ形状: {df.shape}")
        print(f"📊 列名: {list(df.columns)}")
        print(f"📊 最初の5行:")
        print(df.head())
        
        # 最初の行がヘッダーかどうかを確認
        print(f"📋 列名の設定を確認中...")
        if len(df.columns) >= 3:
            # 列名を設定
            df.columns = ['date', 'start_time', 'end_time']
            print(f"✅ 3列以上のデータを検出、列名を設定")
        else:
            # 最初の行をヘッダーとして扱う
            df.columns = ['date', 'start_time', 'end_time']
            df = df.iloc[1:]  # 最初の行をスキップ
            print(f"⚠️ 3列未満のデータ、最初の行をヘッダーとしてスキップ")
        
        print(f"📊 処理後のデータ形状: {df.shape}")
        print(f"📊 処理後の列名: {list(df.columns)}")
        
        # データを辞書のリストに変換
        data = []
        print(f"📋 データの変換を開始...")
        for index, row in df.iterrows():
            try:
                print(f"📋 行 {index + 1} を処理中...")
                print(f"📋 生データ: {row.tolist()}")
                
                # 日付を文字列に変換
                date_str = str(row['date'])
                if pd.isna(row['date']):
                    print(f"⚠️ 行 {index + 1}: 日付が空です")
                    continue
                
                # 時間を文字列に変換
                start_time = str(row['start_time'])
                end_time = str(row['end_time'])
                
                if pd.isna(row['start_time']) or pd.isna(row['end_time']):
                    print(f"⚠️ 行 {index + 1}: 時間が空です")
                    continue
                
                data.append({
                    'date': date_str,
                    'start_time': start_time,
                    'end_time': end_time
                })
                
                print(f"✅ 行 {index + 1}: 日付={date_str}, 開始={start_time}, 終了={end_time}")
                
            except Exception as e:
                print(f"❌ 行 {index + 1} の処理でエラー: {e}")
                continue
        
        print(f"✅ 読み込み完了: {len(data)} 件のデータ")
        return data
        
    except Exception as e:
        print(f"Excelファイルの読み込みでエラー: {e}")
        return []


def create_sample_excel():
    """サンプルExcelファイルを作成"""
    try:
        import pandas as pd
        from datetime import datetime, timedelta
        
        # 今月の平日の日付を生成
        today = datetime.now()
        start_of_month = today.replace(day=1)
        
        # 今月の平日の日付を取得
        dates = []
        current_date = start_of_month
        
        while current_date.month == today.month:
            if current_date.weekday() < 5:  # 月曜日から金曜日
                dates.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
        
        # サンプルデータを作成
        data = []
        for date in dates:
            # ランダムな時間を生成（8:00-9:00の間で開始、17:00-18:00の間で終了）
            import random
            
            start_hour = random.randint(8, 9)
            start_minute = random.randint(0, 59)
            end_hour = random.randint(17, 18)
            end_minute = random.randint(0, 59)
            
            start_time = f"{start_hour:02d}:{start_minute:02d}"
            end_time = f"{end_hour:02d}:{end_minute:02d}"
            
            data.append({
                'date': date,
                'start_time': start_time,
                'end_time': end_time
            })
        
        # DataFrameを作成
        df = pd.DataFrame(data)
        
        # Excelファイルに保存
        filename = 'sample_attendance.xlsx'
        df.to_excel(filename, index=False)
        
        print(f"サンプルファイルを作成しました: {filename}")
        print(f"データ件数: {len(data)} 件")
        
        return filename
        
    except Exception as e:
        print(f"サンプルファイルの作成でエラー: {e}")
        return None 
