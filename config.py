#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jobcan自動申請ツールの設定ファイル
"""

# JobcanのURL設定
JABCAN_URLS = {
    "login": "https://id.jobcan.jp/users/sign_in",
    "dashboard": "https://ssl.jobcan.jp/employee",
    "attendance": "https://ssl.jobcan.jp/employee/attendance"
}

# ページ要素のセレクター設定
SELECTORS = {
    "login": {
        "email_input": 'input[name="user[email]"]',
        "password_input": 'input[name="user[password]"]',
        "submit_button": 'input[type="submit"]'
    },
    "attendance": {
        "attendance_link": [
            'a[href*="attendance"]',
            'a[href*="timecard"]',
            'a:has-text("出勤簿")',
            'a:has-text("勤怠")',
            'a:has-text("Attendance")'
        ],
        "date_cell": [
            '[data-date]',
            'td[data-date]',
            'a[href*="date"]'
        ],
        "correction_button": [
            'button:has-text("打刻修正")',
            'a:has-text("打刻修正")',
            'input[value*="打刻修正"]',
            'button:has-text("修正")',
            'a:has-text("修正")'
        ],
        "time_input": [
            'input[name*="time"]',
            'input[type="time"]',
            'input[placeholder*="時刻"]'
        ],
        "stamp_button": [
            'button:has-text("打刻")',
            'input[value*="打刻"]',
            'button:has-text("登録")',
            'input[value*="登録"]'
        ]
    }
}

# 待機時間設定（秒）
WAIT_TIMES = {
    "page_load": 3,
    "element_wait": 2,
    "network_idle": 5
}

# ファイル設定
FILES = {
    "credentials": "credentials.enc",
    "key": "key.key",
    "log": "jobcan_bot.log"
}

# Excel設定
EXCEL_CONFIG = {
    "date_column": 0,  # A列
    "start_time_column": 1,  # B列
    "end_time_column": 2,  # C列
    "date_format": "%Y/%m/%d",
    "time_format": "%H:%M"
} 