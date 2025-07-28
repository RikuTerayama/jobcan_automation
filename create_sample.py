#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
サンプル勤怠データExcelファイル作成スクリプト
"""

import pandas as pd
from datetime import datetime, timedelta
import calendar

def create_sample_attendance_data():
    """サンプル勤怠データを作成"""
    
    # 現在の年月を取得
    now = datetime.now()
    year = now.year
    month = now.month
    
    # 月の最初の日と最後の日を取得
    first_day = datetime(year, month, 1)
    last_day = datetime(year, month, calendar.monthrange(year, month)[1])
    
    # 勤怠データを格納するリスト
    attendance_data = []
    
    # 月の各日をループ
    current_date = first_day
    while current_date <= last_day:
        # 土日をスキップ（平日のみ）
        if current_date.weekday() < 5:  # 0=月曜日, 4=金曜日
            date_str = current_date.strftime("%Y/%m/%d")
            
            # ランダムな勤務時間を生成（8時間勤務を基本とする）
            start_hour = 9  # 9時開始
            start_minute = 0
            end_hour = 18   # 18時終了
            end_minute = 0
            
            # ランダムな変動を加える（±30分）
            import random
            start_minute = random.randint(-30, 30)
            end_minute = random.randint(-30, 30)
            
            # 時刻を正規化
            if start_minute < 0:
                start_hour -= 1
                start_minute += 60
            elif start_minute >= 60:
                start_hour += 1
                start_minute -= 60
                
            if end_minute < 0:
                end_hour -= 1
                end_minute += 60
            elif end_minute >= 60:
                end_hour += 1
                end_minute -= 60
            
            # 時刻文字列を作成
            start_time = f"{start_hour:02d}:{start_minute:02d}"
            end_time = f"{end_hour:02d}:{end_minute:02d}"
            
            attendance_data.append({
                '日付': date_str,
                '始業時刻': start_time,
                '終業時刻': end_time
            })
        
        current_date += timedelta(days=1)
    
    return attendance_data

def main():
    """メイン処理"""
    try:
        # サンプルデータを作成
        data = create_sample_attendance_data()
        
        # DataFrameに変換
        df = pd.DataFrame(data)
        
        # Excelファイルに保存
        filename = 'sample_attendance.xlsx'
        df.to_excel(filename, index=False)
        
        print(f"✅ サンプル勤怠データを作成しました: {filename}")
        print(f"📊 データ件数: {len(data)}件")
        print("\n📋 データ内容:")
        print(df.head(10).to_string(index=False))
        
        print(f"\n📝 使用方法:")
        print(f"1. {filename} をWebアプリにアップロード")
        print(f"2. Jobcanのログイン情報を入力")
        print(f"3. 自動処理を開始")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")

if __name__ == "__main__":
    main() 
