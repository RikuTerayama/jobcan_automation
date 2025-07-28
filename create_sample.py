#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
サンプルExcelファイルを作成するスクリプト
"""

import pandas as pd
from datetime import datetime, timedelta

def create_sample_excel():
    """サンプルの勤怠データExcelファイルを作成"""
    
    # サンプルデータの作成（今月の平日のみ）
    today = datetime.now()
    start_of_month = today.replace(day=1)
    
    # 今月の平日を取得
    workdays = []
    current_date = start_of_month
    
    while current_date.month == today.month:
        # 平日（月曜日=0, 火曜日=1, ..., 金曜日=4）のみ
        if current_date.weekday() < 5:
            workdays.append(current_date)
        current_date += timedelta(days=1)
    
    # 勤怠データを作成
    data = []
    for i, date in enumerate(workdays[:10]):  # 最初の10日間
        # ランダムな勤務時間（9:00-10:00の間で出勤、18:00-19:00の間で退勤）
        start_hour = 9
        start_minute = 0 + (i * 5) % 60  # 少しずつ時間をずらす
        
        end_hour = 18
        end_minute = 0 + (i * 3) % 60  # 少しずつ時間をずらす
        
        data.append({
            '日付': date.strftime('%Y/%m/%d'),
            '始業時刻': f'{start_hour:02d}:{start_minute:02d}',
            '終業時刻': f'{end_hour:02d}:{end_minute:02d}'
        })
    
    # DataFrameを作成
    df = pd.DataFrame(data)
    
    # Excelファイルとして保存
    filename = 'sample_attendance.xlsx'
    df.to_excel(filename, index=False)
    
    print(f"サンプルExcelファイルを作成しました: {filename}")
    print("データ内容:")
    print(df.to_string(index=False))
    
    return filename

if __name__ == "__main__":
    create_sample_excel() 
