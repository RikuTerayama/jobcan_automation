#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jobcan勤怠打刻自動申請ツール - GUI版
将来的なGUI化を想定したPyQt5ベースのアプリケーション
"""

import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QFileDialog, QTextEdit, QProgressBar, QCheckBox,
                             QMessageBox, QGroupBox, QGridLayout)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QIcon
import pandas as pd
from jobcan_bot import JobcanBot

class JobcanWorker(QThread):
    """バックグラウンドでJobcan処理を実行するワーカースレッド"""
    
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    
    def __init__(self, excel_file, email=None, password=None, headless=True):
        super().__init__()
        self.excel_file = excel_file
        self.email = email
        self.password = password
        self.headless = headless
        
    def run(self):
        try:
            self.progress_signal.emit("ブラウザを起動中...")
            bot = JobcanBot(headless=self.headless)
            bot.start_browser()
            
            self.progress_signal.emit("ログイン中...")
            if self.email and self.password:
                login_success = bot.login(self.email, self.password)
            else:
                login_success = bot.login()
            
            if not login_success:
                self.error_signal.emit("ログインに失敗しました")
                return
            
            self.progress_signal.emit("出勤簿ページに移動中...")
            bot.navigate_to_attendance()
            
            self.progress_signal.emit("Excelデータを読み込み中...")
            attendance_data = bot.load_excel_data(self.excel_file)
            
            self.progress_signal.emit("勤怠データを処理中...")
            processed_data = bot.process_attendance_data(attendance_data)
            
            bot.close()
            self.finished_signal.emit(processed_data)
            
        except Exception as e:
            self.error_signal.emit(f"エラーが発生しました: {str(e)}")


class JobcanGUI(QMainWindow):
    """Jobcan自動申請ツールのGUI"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """UIの初期化"""
        self.setWindowTitle("Jobcan勤怠打刻自動申請ツール")
        self.setGeometry(100, 100, 800, 600)
        
        # メインウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # メインレイアウト
        layout = QVBoxLayout(central_widget)
        
        # タイトル
        title_label = QLabel("Jobcan勤怠打刻自動申請ツール")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # ファイル選択セクション
        file_group = QGroupBox("Excelファイル選択")
        file_layout = QHBoxLayout()
        
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Excelファイルを選択してください")
        file_layout.addWidget(self.file_path_edit)
        
        browse_button = QPushButton("参照...")
        browse_button.clicked.connect(self.browse_file)
        file_layout.addWidget(browse_button)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # ログイン情報セクション
        login_group = QGroupBox("ログイン情報")
        login_layout = QGridLayout()
        
        login_layout.addWidget(QLabel("メールアドレス:"), 0, 0)
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("your-email@example.com")
        login_layout.addWidget(self.email_edit, 0, 1)
        
        login_layout.addWidget(QLabel("パスワード:"), 1, 0)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("パスワードを入力")
        login_layout.addWidget(self.password_edit, 1, 1)
        
        self.save_credentials_check = QCheckBox("ログイン情報を保存")
        login_layout.addWidget(self.save_credentials_check, 2, 1)
        
        login_group.setLayout(login_layout)
        layout.addWidget(login_group)
        
        # オプションセクション
        options_group = QGroupBox("オプション")
        options_layout = QHBoxLayout()
        
        self.headless_check = QCheckBox("ヘッドレスモード（ブラウザを表示しない）")
        self.headless_check.setChecked(True)
        options_layout.addWidget(self.headless_check)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # 実行ボタン
        self.run_button = QPushButton("勤怠データを自動入力")
        self.run_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.run_button.clicked.connect(self.run_automation)
        layout.addWidget(self.run_button)
        
        # プログレスバー
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # ログ表示エリア
        log_group = QGroupBox("処理ログ")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # ステータスバー
        self.statusBar().showMessage("準備完了")
        
    def browse_file(self):
        """ファイル選択ダイアログ"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Excelファイルを選択", "", "Excel Files (*.xlsx *.xls)"
        )
        if file_path:
            self.file_path_edit.setText(file_path)
            
    def run_automation(self):
        """自動化処理を実行"""
        # 入力チェック
        if not self.file_path_edit.text():
            QMessageBox.warning(self, "警告", "Excelファイルを選択してください")
            return
            
        if not os.path.exists(self.file_path_edit.text()):
            QMessageBox.warning(self, "警告", "指定されたファイルが存在しません")
            return
            
        # UIを無効化
        self.run_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不定プログレスバー
        
        # ワーカースレッドを開始
        self.worker = JobcanWorker(
            excel_file=self.file_path_edit.text(),
            email=self.email_edit.text() if self.email_edit.text() else None,
            password=self.password_edit.text() if self.password_edit.text() else None,
            headless=self.headless_check.isChecked()
        )
        
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.error_signal.connect(self.on_error)
        
        self.worker.start()
        
    def update_progress(self, message):
        """プログレス更新"""
        self.log_text.append(f"[INFO] {message}")
        self.statusBar().showMessage(message)
        
    def on_finished(self, results):
        """処理完了"""
        self.progress_bar.setVisible(False)
        self.run_button.setEnabled(True)
        
        # 結果を表示
        success_count = sum(1 for r in results if r['status'] == 'success')
        error_count = len(results) - success_count
        
        self.log_text.append(f"\n=== 処理完了 ===")
        self.log_text.append(f"成功: {success_count}件")
        self.log_text.append(f"失敗: {error_count}件")
        self.log_text.append(f"合計: {len(results)}件")
        
        # 詳細結果を表示
        for result in results:
            if result['status'] == 'success':
                self.log_text.append(f"✓ {result['date']}: {result['start_time']} - {result['end_time']}")
            else:
                self.log_text.append(f"✗ {result['date']}: エラー - {result.get('error', 'Unknown')}")
        
        self.statusBar().showMessage(f"処理完了 - 成功: {success_count}件, 失敗: {error_count}件")
        
        QMessageBox.information(self, "完了", f"処理が完了しました\n成功: {success_count}件\n失敗: {error_count}件")
        
    def on_error(self, error_message):
        """エラー処理"""
        self.progress_bar.setVisible(False)
        self.run_button.setEnabled(True)
        
        self.log_text.append(f"[ERROR] {error_message}")
        self.statusBar().showMessage("エラーが発生しました")
        
        QMessageBox.critical(self, "エラー", error_message)


def main():
    """メイン関数"""
    app = QApplication(sys.argv)
    
    # アプリケーション情報
    app.setApplicationName("Jobcan勤怠打刻自動申請ツール")
    app.setApplicationVersion("1.0.0")
    
    # メインウィンドウ
    window = JobcanGUI()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 