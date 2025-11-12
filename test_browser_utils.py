#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
新しい共通ユーティリティのテストファイル
既存のコードを破壊せずに動作確認を行う
"""

import asyncio
import os
import sys

# 環境変数を設定（テスト用）
os.environ["NAV_TIMEOUT_MS"] = "30000"  # テスト用に短縮
os.environ["STEP_TIMEOUT_MS"] = "20000"
os.environ["MAX_MEM_MB"] = "500"
os.environ["BROWSER_CONCURRENCY"] = "1"

async def test_browser_utils():
    """共通ユーティリティの基本動作をテスト"""
    try:
        print("=== 共通ユーティリティテスト開始 ===")
        
        # インポートテスト
        from browser_utils.browser_utils import (
            rss_mb, mem, guard_memory, 
            NAV_TIMEOUT_MS, STEP_TIMEOUT_MS, MAX_MEM_MB
        )
        from browser_utils.concurrency import browser_sem, get_concurrency_limit
        
        print(f"✅ インポート成功")
        print(f"   NAV_TIMEOUT_MS: {NAV_TIMEOUT_MS}ms")
        print(f"   STEP_TIMEOUT_MS: {STEP_TIMEOUT_MS}ms")
        print(f"   MAX_MEM_MB: {MAX_MEM_MB}MB")
        print(f"   BROWSER_CONCURRENCY: {get_concurrency_limit()}")
        
        # メモリ監視テスト
        current_mem = rss_mb()
        print(f"✅ メモリ監視: {current_mem:.1f} MB")
        
        mem("test_tag")
        
        # メモリガードテスト
        try:
            guard_memory()
            print("✅ メモリガード: 正常範囲")
        except RuntimeError as e:
            print(f"⚠️ メモリガード: {e}")
        
        # 同時実行制御テスト
        print(f"✅ 同時実行制御: {browser_sem._value} スロット利用可能")
        
        print("=== 基本テスト完了 ===")
        return True
        
    except Exception as e:
        print(f"❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_jobcan_flow():
    """Jobcanフローの基本動作をテスト（実際のブラウザは起動しない）"""
    try:
        print("=== Jobcanフローテスト開始 ===")
        
        # インポートテスト
        from browser_utils.flows.jobcan import (
            JobcanCredentials, 
            do_login_and_go_timesheet,
            LOGIN_URL, TIMESHEET_URL
        )
        
        print(f"✅ Jobcanフローインポート成功")
        print(f"   LOGIN_URL: {LOGIN_URL}")
        print(f"   TIMESHEET_URL: {TIMESHEET_URL}")
        
        # 認証情報クラステスト
        creds = JobcanCredentials("test@example.com", "password123", "company123")
        print(f"✅ 認証情報クラス: {creds.email}, {creds.company_id}")
        
        print("=== Jobcanフローテスト完了 ===")
        return True
        
    except Exception as e:
        print(f"❌ Jobcanフローテスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """メインテスト関数"""
    print("🚀 共通ユーティリティテスト開始")
    
    # 基本テスト
    basic_ok = await test_browser_utils()
    
    # Jobcanフローテスト
    flow_ok = await test_jobcan_flow()
    
    # 結果表示
    print("\n" + "="*50)
    if basic_ok and flow_ok:
        print("🎉 全テスト成功！")
        print("新しい共通ユーティリティが正常に動作しています。")
    else:
        print("❌ 一部のテストが失敗しました。")
        print("エラーログを確認してください。")
    
    print("="*50)

if __name__ == "__main__":
    # 非同期テストを実行
    asyncio.run(main())
