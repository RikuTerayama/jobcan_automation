#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyInstallerで実行ファイルを作成するスクリプト
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def install_pyinstaller():
    """PyInstallerをインストール"""
    print("PyInstallerをインストール中...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    print("✓ PyInstallerのインストールが完了しました")

def build_cli_exe():
    """CLI版の実行ファイルを作成"""
    print("CLI版の実行ファイルを作成中...")
    
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name=jobcan_bot",
        "--add-data=config.py;.",
        "jobcan_bot.py"
    ]
    
    subprocess.run(cmd, check=True)
    print("✓ CLI版の実行ファイルが作成されました: dist/jobcan_bot.exe")

def build_gui_exe():
    """GUI版の実行ファイルを作成"""
    print("GUI版の実行ファイルを作成中...")
    
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=jobcan_gui",
        "--add-data=config.py;.",
        "--add-data=jobcan_bot.py;.",
        "jobcan_gui.py"
    ]
    
    subprocess.run(cmd, check=True)
    print("✓ GUI版の実行ファイルが作成されました: dist/jobcan_gui.exe")

def create_installer():
    """インストーラー用のファイルを作成"""
    print("インストーラー用のファイルを作成中...")
    
    # distディレクトリに必要なファイルをコピー
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)
    
    # READMEをコピー
    if Path("README.md").exists():
        shutil.copy("README.md", dist_dir / "README.md")
    
    # サンプルデータ作成スクリプトをコピー
    if Path("sample_data.py").exists():
        shutil.copy("sample_data.py", dist_dir / "sample_data.py")
    
    # サンプルExcelファイルを作成
    try:
        subprocess.run([sys.executable, "sample_data.py"], check=True)
        if Path("sample_attendance.xlsx").exists():
            shutil.copy("sample_attendance.xlsx", dist_dir / "sample_attendance.xlsx")
    except:
        print("⚠ サンプルExcelファイルの作成に失敗しました")
    
    print("✓ インストーラー用のファイルが作成されました")

def main():
    """メイン関数"""
    print("Jobcan勤怠打刻自動申請ツール - ビルドスクリプト")
    print("=" * 50)
    
    try:
        # PyInstallerをインストール
        install_pyinstaller()
        
        # CLI版を作成
        build_cli_exe()
        
        # GUI版を作成
        build_gui_exe()
        
        # インストーラー用ファイルを作成
        create_installer()
        
        print("\n🎉 ビルドが完了しました！")
        print("\n作成されたファイル:")
        print("- dist/jobcan_bot.exe (CLI版)")
        print("- dist/jobcan_gui.exe (GUI版)")
        print("- dist/README.md")
        print("- dist/sample_data.py")
        print("- dist/sample_attendance.xlsx")
        
        print("\n使用方法:")
        print("1. distフォルダ内のファイルを配布")
        print("2. ユーザーはjobcan_bot.exeまたはjobcan_gui.exeを実行")
        print("3. 初回実行時にサンプルデータを作成: python sample_data.py")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ ビルド中にエラーが発生しました: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 予期しないエラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 