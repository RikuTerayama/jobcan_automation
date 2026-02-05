#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
スモークテスト: /, /autofill, /about, /tools を複数回アクセスし、
全て 200 かつエラーページ表示がないことを確認する。
使用例: python scripts/smoke_test.py
        BASE_URL=http://localhost:5000 python scripts/smoke_test.py
"""
import os
import sys

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_with_test_client():
    """Flask test client で実行（サーバー不要）"""
    from app import app
    app.config['TESTING'] = True
    client = app.test_client()
    paths = ['/', '/autofill', '/about', '/tools', '/healthz']
    error_phrase = '⚠️ エラーが発生しました'
    n_per_path = 10
    failed = []

    for path in paths:
        for i in range(n_per_path):
            response = client.get(path)
            body = response.data.decode('utf-8')
            if response.status_code != 200:
                failed.append(f"path={path} run={i+1} status={response.status_code}")
            elif path != '/healthz' and error_phrase in body:
                failed.append(f"path={path} run={i+1} body contains error page")

    if failed:
        for f in failed:
            print(f"FAIL: {f}")
        print(f"Total failures: {len(failed)}")
        return 1
    print(f"OK: {len(paths)} paths x {n_per_path} requests = all 200, no error page")
    return 0

if __name__ == '__main__':
    sys.exit(run_with_test_client())
