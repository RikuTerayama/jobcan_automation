#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import uuid
import threading
import tempfile
import shutil
import psutil
import time
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_file, Response, g

from utils import allowed_file, create_template_excel, create_previous_month_template_excel
from automation import process_jobcan_automation

# P1-1: 計測ログユーティリティ（循環import回避）
try:
    from diagnostics.runtime_metrics import log_memory
    metrics_available = True
except ImportError:
    metrics_available = False
    def log_memory(tag, job_id=None, session_id=None, extra=None):
        pass

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# メモリ制限設定（環境変数から取得、デフォルト値付き）
# P0-4: 閾値の整合性を修正（WARNING < LIMIT）
MEMORY_LIMIT_MB = int(os.getenv("MEMORY_LIMIT_MB", "450"))
MEMORY_WARNING_MB = int(os.getenv("MEMORY_WARNING_MB", "400"))

# P0-4: 起動時に閾値矛盾を検知して警告
if MEMORY_WARNING_MB >= MEMORY_LIMIT_MB:
    logger.warning(f"memory_threshold_mismatch WARNING_MB={MEMORY_WARNING_MB} >= LIMIT_MB={MEMORY_LIMIT_MB} - auto_correcting")
    # 自動補正: WARNINGをLIMITの90%に設定
    MEMORY_WARNING_MB = int(MEMORY_LIMIT_MB * 0.9)
    logger.warning(f"memory_threshold_auto_corrected WARNING_MB={MEMORY_WARNING_MB} LIMIT_MB={MEMORY_LIMIT_MB}")
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_ACTIVE_SESSIONS = int(os.getenv("MAX_ACTIVE_SESSIONS", "20"))

app = Flask(__name__)

# アップロードフォルダの設定
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# === リクエストロギングミドルウェア ===
@app.before_request
def before_request():
    """リクエスト開始時の処理"""
    g.start_time = time.time()
    g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4())[:8])
    
    # ヘルスチェック以外のリクエストをログ
    if not request.path.startswith(('/healthz', '/livez', '/readyz')):
        logger.info(f"req_start rid={g.request_id} method={request.method} path={request.path} ip={request.remote_addr}")

@app.after_request
def after_request(response):
    """リクエスト終了時の処理"""
    if hasattr(g, 'start_time') and hasattr(g, 'request_id'):
        duration_ms = (time.time() - g.start_time) * 1000
        response.headers['X-Request-ID'] = g.request_id
        
        # ヘルスチェック以外のリクエストをログ
        if not request.path.startswith(('/healthz', '/livez', '/readyz')):
            level = logging.WARNING if duration_ms > 1000 else logging.INFO
            logger.log(
                level,
                f"req_end rid={g.request_id} method={request.method} path={request.path} "
                f"status={response.status_code} ms={duration_ms:.1f}"
            )
            
            # 遅延警告
            if duration_ms > 5000:
                logger.warning(f"SLOW_REQUEST rid={g.request_id} path={request.path} ms={duration_ms:.1f}")
    
    return response

# グローバルエラーハンドラー
@app.errorhandler(404)
def not_found(error):
    """404エラーのハンドリング"""
    logger.warning(f"not_found rid={getattr(g, 'request_id', 'unknown')} path={request.path} method={request.method} user_agent={request.headers.get('User-Agent', 'Unknown')} error={str(error)}")
    return jsonify({'error': 'ページが見つかりません。URLを確認してください。'}), 404

@app.errorhandler(500)
def internal_error(error):
    """500エラーのハンドリング"""
    logger.error(f"internal_server_error rid={getattr(g, 'request_id', 'unknown')} error={str(error)}")
    return jsonify({'error': '内部サーバーエラーが発生しました。しばらく待ってから再試行してください。'}), 500

@app.errorhandler(503)
def service_unavailable(error):
    """503エラーのハンドリング"""
    logger.error(f"service_unavailable rid={getattr(g, 'request_id', 'unknown')} error={str(error)}")
    return jsonify({'error': 'サービスが一時的に利用できません。しばらく待ってから再試行してください。'}), 503

@app.errorhandler(Exception)
def handle_exception(e):
    """未処理例外のハンドリング（404以外）"""
    # 404エラーは上記のハンドラーで処理されるため、ここでは処理しない
    if hasattr(e, 'code') and e.code == 404:
        raise e  # 404エラーハンドラーに委譲
    
    # 詳細なエラー情報をログに記録
    import traceback
    error_traceback = traceback.format_exc()
    logger.error(f"unhandled_exception rid={getattr(g, 'request_id', 'unknown')} error={str(e)}\n{error_traceback}")
    
    # テンプレートレンダリングエラーの場合はHTMLエラーページを返す
    if 'TemplateNotFound' in str(type(e)) or 'TemplateSyntaxError' in str(type(e)) or 'render_template' in error_traceback:
        try:
            return render_template('error.html', error_message='ページの表示中にエラーが発生しました。'), 500
        except:
            # エラーテンプレートもレンダリングできない場合はシンプルなHTMLを返す
            return f'<html><body><h1>エラーが発生しました</h1><p>予期しないエラーが発生しました。しばらく待ってから再試行してください。</p></body></html>', 500
    
    # その他のエラーはJSONを返す（APIエンドポイント用）
    return jsonify({'error': '予期しないエラーが発生しました。しばらく待ってから再試行してください。'}), 500

# 環境変数をテンプレートコンテキストに注入（AdSense設定用）
@app.context_processor
def inject_env_vars():
    """環境変数をテンプレートで使えるようにする"""
    import json
    app_version = '1.0.0'
    try:
        with open('package.json', 'r', encoding='utf-8') as f:
            package_data = json.load(f)
            app_version = package_data.get('version', '1.0.0')
    except:
        pass
    
    return {
        'ADSENSE_ENABLED': os.getenv('ADSENSE_ENABLED', 'false').lower() == 'true',
        'app_version': app_version
    }

# ジョブの状態を管理（スレッドセーフな辞書）
jobs = {}
jobs_lock = threading.Lock()

# P0-3: 完了ジョブの保持期間（秒）
JOB_RETENTION_SECONDS = 1800  # 30分

# セッション管理とリソース監視
session_manager = {
    'active_sessions': {},
    'session_lock': threading.Lock(),
    'resource_monitor': {
        'last_check': time.time(),
        'memory_usage': 0,
        'cpu_usage': 0,
        'active_browsers': 0
    }
}

def get_system_resources():
    """システムリソースの使用状況を取得（強化版）"""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        cpu_percent = process.cpu_percent()
        
        # メモリ使用量が危険域の場合はログに記録
        if memory_mb > MEMORY_WARNING_MB:
            logger.warning(f"high_memory_usage memory_mb={memory_mb:.1f} warning_threshold={MEMORY_WARNING_MB}")
        if memory_mb > MEMORY_LIMIT_MB:
            logger.error(f"memory_limit_exceeded memory_mb={memory_mb:.1f} limit={MEMORY_LIMIT_MB}")
        
        return {
            'memory_mb': memory_mb,
            'cpu_percent': cpu_percent,
            'active_sessions': len(session_manager['active_sessions'])
        }
    except ImportError:
        logger.warning("psutil_not_available resource_monitoring_disabled")
        return {'memory_mb': 0, 'cpu_percent': 0, 'active_sessions': len(session_manager['active_sessions'])}
    except Exception as e:
        logger.error(f"resource_monitoring_error error={str(e)}")
        return {'memory_mb': 0, 'cpu_percent': 0, 'active_sessions': len(session_manager['active_sessions'])}

def check_resource_limits():
    """リソース制限のチェック（メモリ制限チェック強化）"""
    resources = get_system_resources()
    
    warnings = []
    
    # メモリ使用量の警告（環境変数で設定可能）
    if resources['memory_mb'] > MEMORY_LIMIT_MB:
        raise RuntimeError(f"メモリ制限を超過しました: {resources['memory_mb']:.1f}MB > {MEMORY_LIMIT_MB}MB")
    elif resources['memory_mb'] > MEMORY_WARNING_MB:
        warnings.append(f"メモリ使用量が高いです: {resources['memory_mb']:.1f}MB")
    
    # アクティブセッション数の制限（OOM防止）
    if resources['active_sessions'] >= MAX_ACTIVE_SESSIONS:
        raise RuntimeError(
            f"同時処理数の上限に達しています（{resources['active_sessions']}/{MAX_ACTIVE_SESSIONS}）。"
            f"しばらく待ってから再試行してください。"
        )
    elif resources['active_sessions'] > MAX_ACTIVE_SESSIONS * 0.8:
        warnings.append(f"アクティブセッション数が多いです: {resources['active_sessions']}/{MAX_ACTIVE_SESSIONS}個")
    
    return warnings

def create_unique_session_id():
    """ユニークなセッションIDを生成"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    session_id = f"session_{uuid.uuid4().hex}_{timestamp}"
    return session_id

def get_user_session_dir(session_id):
    """ユーザーごとの一時ディレクトリを取得（完全分離）"""
    session_dir = os.path.join(tempfile.gettempdir(), f'jobcan_session_{session_id}')
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
    return session_dir

def cleanup_user_session(session_id):
    """ユーザーセッションのクリーンアップ（完全削除）"""
    try:
        session_dir = get_user_session_dir(session_id)
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
            print(f"セッションクリーンアップ完了: {session_id}")
    except Exception as e:
        print(f"セッションクリーンアップエラー {session_id}: {e}")

def register_session(session_id, job_id):
    """セッションを登録"""
    with session_manager['session_lock']:
        session_manager['active_sessions'][session_id] = {
            'job_id': job_id,
            'start_time': time.time(),
            'status': 'active'
        }
        print(f"セッション登録: {session_id} (ジョブ: {job_id})")

def unregister_session(session_id):
    """セッションを登録解除"""
    with session_manager['session_lock']:
        if session_id in session_manager['active_sessions']:
            del session_manager['active_sessions'][session_id]
            print(f"セッション解除: {session_id}")

def prune_jobs(current_time=None, retention_sec=JOB_RETENTION_SECONDS):
    """P0-3: 完了/エラー状態のジョブを一定時間保持後に削除"""
    if current_time is None:
        current_time = time.time()
    
    removed_count = 0
    removed_job_ids = []
    
    with jobs_lock:
        jobs_to_remove = []
        
        for job_id, job_info in list(jobs.items()):
            # completed または error 状態のジョブのみ対象
            if job_info.get('status') not in ('completed', 'error'):
                continue
            
            # タイムスタンプを取得
            end_time = job_info.get('end_time')
            if end_time is None:
                # end_timeがない場合はstart_timeから推定（処理時間が長い場合のフォールバック）
                start_time = job_info.get('start_time', 0)
                if start_time > 0:
                    # 開始から30分以上経過していれば削除対象
                    if current_time - start_time > retention_sec:
                        jobs_to_remove.append(job_id)
                continue
            
            # 完了/エラーから一定時間経過したジョブを削除対象に
            if current_time - end_time > retention_sec:
                jobs_to_remove.append(job_id)
        
        # 削除実行
        for job_id in jobs_to_remove:
            job_info = jobs.get(job_id, {})
            log_count = len(job_info.get('logs', []))
            age_sec = current_time - job_info.get('end_time', current_time)
            
            del jobs[job_id]
            removed_count += 1
            removed_job_ids.append(job_id)
            
            logger.info(f"job_prune removed job_id={job_id} status={job_info.get('status')} log_count={log_count} age_sec={age_sec:.1f}")
    
    if removed_count > 0:
        logger.info(f"job_prune summary removed={removed_count} remaining={len(jobs)}")
        
        # P1-1: prune_jobs実行前後のメモリ計測（削除があった場合のみ）
        if metrics_available:
            jobs_count_before = len(jobs) + removed_count
            log_memory("prune_jobs_before", extra={
                'jobs_count': jobs_count_before,
                'sessions_count': len(session_manager['active_sessions']),
                'removed_count': removed_count
            })
            log_memory("prune_jobs_after", extra={
                'jobs_count': len(jobs),
                'sessions_count': len(session_manager['active_sessions']),
                'removed_count': removed_count
            })
    
    return removed_count

def validate_input_data(email, password, file):
    """入力データの検証"""
    errors = []
    
    # メールアドレスの検証
    if not email or '@' not in email or '.' not in email:
        errors.append("有効なメールアドレスを入力してください")
    
    # パスワードの検証
    if not password or len(password) < 1:
        errors.append("パスワードを入力してください")
    
    # ファイルサイズの検証（10MB制限）
    if file and hasattr(file, 'content_length'):
        if file.content_length > 10 * 1024 * 1024:  # 10MB
            errors.append("ファイルサイズが大きすぎます（10MB以下にしてください）")
    
    return errors

@app.route('/')
def index():
    """ランディングページ（製品ハブ）"""
    try:
        from lib.routes import PRODUCTS
        return render_template('landing.html', products=PRODUCTS)
    except Exception as e:
        logger.error(f"landing_page_error error={str(e)}")
        import traceback
        logger.error(f"traceback:\n{traceback.format_exc()}")
        # エラーが発生しても最低限のHTMLを返す
        try:
            return render_template('error.html', error_message='ページの表示中にエラーが発生しました。'), 500
        except:
            return '<html><head><meta charset="utf-8"><title>エラー</title></head><body><h1>エラーが発生しました</h1><p>予期しないエラーが発生しました。しばらく待ってから再試行してください。</p></body></html>', 500

@app.route('/autofill')
def autofill():
    """Jobcan自動入力ツール（旧ホームページ）"""
    try:
        return render_template('autofill.html')
    except Exception as e:
        logger.error(f"autofill_page_error error={str(e)}")
        import traceback
        logger.error(f"traceback:\n{traceback.format_exc()}")
        # エラーが発生しても最低限のHTMLを返す
        try:
            return render_template('error.html', error_message='ページの表示中にエラーが発生しました。'), 500
        except:
            return '<html><head><meta charset="utf-8"><title>エラー</title></head><body><h1>エラーが発生しました</h1><p>予期しないエラーが発生しました。しばらく待ってから再試行してください。</p></body></html>', 500

@app.route('/privacy')
def privacy():
    """プライバシーポリシーページ"""
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    """利用規約ページ"""
    return render_template('terms.html')

@app.route('/contact')
def contact():
    """お問い合わせページ"""
    return render_template('contact.html')

@app.route('/guide/getting-started')
def guide_getting_started():
    """はじめての使い方ガイド"""
    return render_template('guide_getting_started.html')

@app.route('/guide/excel-format')
def guide_excel_format():
    """Excelファイルの作成方法ガイド"""
    return render_template('guide_excel_format.html')

@app.route('/guide/troubleshooting')
def guide_troubleshooting():
    """トラブルシューティングガイド"""
    return render_template('guide_troubleshooting.html')

@app.route('/guide/complete')
def guide_complete():
    """完全ガイド"""
    return render_template('guide/complete-guide.html')

@app.route('/guide/comprehensive-guide')
def guide_comprehensive_guide():
    """Jobcan勤怠管理を効率化する総合ガイド"""
    return render_template('guide/comprehensive-guide.html')

@app.route('/tools/image-batch')
def tools_image_batch():
    """画像一括変換ツール"""
    return render_template('tools/image-batch.html')

@app.route('/tools/pdf')
def tools_pdf():
    """PDFユーティリティ"""
    return render_template('tools/pdf.html')

@app.route('/tools/image-cleanup')
def tools_image_cleanup():
    """画像ユーティリティ"""
    return render_template('tools/image-cleanup.html')

@app.route('/tools/minutes')
def tools_minutes():
    """議事録整形ツール"""
    return render_template('tools/minutes.html')

@app.route('/tools/seo')
def tools_seo():
    """Web/SEOユーティリティ"""
    return render_template('tools/seo.html')

@app.route('/tools')
def tools_index():
    """ツール一覧ページ"""
    from lib.routes import PRODUCTS
    return render_template('tools/index.html', products=PRODUCTS)

@app.route('/faq')
def faq():
    """よくある質問（FAQ）"""
    return render_template('faq.html')

@app.route('/glossary')
def glossary():
    """用語集"""
    return render_template('glossary.html')

@app.route('/about')
def about():
    """サイトについて"""
    return render_template('about.html')

@app.route('/best-practices')
def best_practices():
    """ベストプラクティス"""
    return render_template('best-practices.html')

@app.route('/case-study/contact-center')
def case_study_contact_center():
    """導入事例：コンタクトセンター"""
    return render_template('case-study-contact-center.html')

@app.route('/blog')
def blog_index():
    """ブログ一覧"""
    return render_template('blog/index.html')

@app.route('/blog/implementation-checklist')
def blog_implementation_checklist():
    """ブログ記事：導入チェックリスト"""
    return render_template('blog/implementation-checklist.html')

@app.route('/blog/automation-roadmap')
def blog_automation_roadmap():
    """ブログ記事：90日ロードマップ"""
    return render_template('blog/automation-roadmap.html')

@app.route('/blog/workstyle-reform-automation')
def blog_workstyle_reform_automation():
    """ブログ記事：働き方改革と自動化"""
    return render_template('blog/workstyle-reform-automation.html')

@app.route('/blog/excel-attendance-limits')
def blog_excel_attendance_limits():
    """ブログ記事：Excel管理の限界と自動化ツール"""
    return render_template('blog/excel-attendance-limits.html')

@app.route('/blog/playwright-security')
def blog_playwright_security():
    """ブログ記事：Playwrightによるブラウザ自動化のセキュリティ"""
    return render_template('blog/playwright-security.html')

@app.route('/blog/month-end-closing-hell-and-automation')
def blog_month_end_closing_hell_and_automation():
    """ブログ記事：月末締めが地獄になる理由と自動化"""
    return render_template('blog/month-end-closing-hell-and-automation.html')

@app.route('/blog/excel-format-mistakes-and-design')
def blog_excel_format_mistakes_and_design():
    """ブログ記事：Excelフォーマットのミス10選"""
    return render_template('blog/excel-format-mistakes-and-design.html')

@app.route('/blog/convince-it-and-hr-for-automation')
def blog_convince_it_and_hr_for_automation():
    """ブログ記事：情シス・人事を説得する5ステップ"""
    return render_template('blog/convince-it-and-hr-for-automation.html')

@app.route('/blog/playwright-jobcan-challenges-and-solutions')
def blog_playwright_jobcan_challenges_and_solutions():
    """ブログ記事：Playwrightでハマったポイント"""
    return render_template('blog/playwright-jobcan-challenges-and-solutions.html')

@app.route('/blog/jobcan-auto-input-tools-overview')
def blog_jobcan_auto_input_tools_overview():
    """ブログ記事：Jobcan自動入力ツールの全体像と選び方"""
    return render_template('blog/jobcan-auto-input-tools-overview.html')

@app.route('/blog/reduce-manual-work-checklist')
def blog_reduce_manual_work_checklist():
    """ブログ記事：勤怠管理の手入力を減らすための実務チェックリスト"""
    return render_template('blog/reduce-manual-work-checklist.html')

@app.route('/blog/jobcan-month-end-tips')
def blog_jobcan_month_end_tips():
    """ブログ記事：Jobcan月末締めをラクにするための7つの実践テクニック"""
    return render_template('blog/jobcan-month-end-tips.html')

@app.route('/blog/jobcan-auto-input-dos-and-donts')
def blog_jobcan_auto_input_dos_and_donts():
    """ブログ記事：Jobcan自動入力のやり方と、やってはいけないNG自動化"""
    return render_template('blog/jobcan-auto-input-dos-and-donts.html')

@app.route('/blog/month-end-closing-checklist')
def blog_month_end_closing_checklist():
    """ブログ記事：月末の勤怠締め地獄を減らすための現実的なチェックリスト"""
    return render_template('blog/month-end-closing-checklist.html')

@app.route('/case-study/consulting-firm')
def case_study_consulting_firm():
    """導入事例：コンサルティングファーム"""
    return render_template('case-study-consulting-firm.html')

@app.route('/case-study/remote-startup')
def case_study_remote_startup():
    """導入事例：小規模スタートアップ"""
    return render_template('case-study-remote-startup.html')

@app.route('/sitemap.html')
def sitemap_html():
    """HTMLサイトマップ"""
    return render_template('sitemap.html')

# === ヘルスチェックエンドポイント（Render用・超軽量） ===
@app.route('/healthz')
def healthz():
    """超軽量ヘルスチェック - Render Health Check用（堅牢化）"""
    try:
        # 最小限のチェック：アプリケーションが応答可能か
        return Response('ok', mimetype='text/plain', headers={'Cache-Control': 'no-store'})
    except Exception as e:
        # ログに記録してから503を返す
        logger.error(f"healthz_check_failed error={str(e)}")
        return Response(f'health check failed: {str(e)}', status=503, mimetype='text/plain')

@app.route('/livez')
def livez():
    """プロセス生存確認 - 即座にOK"""
    return Response('ok', mimetype='text/plain', headers={'Cache-Control': 'no-store'})

@app.route('/readyz')
def readyz():
    """準備完了確認 - 軽量チェックのみ（堅牢化）"""
    try:
        # 最小限のチェック：jobsディクショナリが存在するか
        _ = len(jobs)
        # 追加チェック：メモリ使用量が安全範囲内か
        resources = get_system_resources()
        if resources['memory_mb'] > MEMORY_LIMIT_MB:
            logger.error(f"memory_limit_exceeded current={resources['memory_mb']:.1f}MB limit={MEMORY_LIMIT_MB}MB")
            return Response(f'memory limit exceeded: {resources["memory_mb"]:.1f}MB', status=503, mimetype='text/plain')
        
        # 同時接続数チェック
        if len(jobs) > MAX_ACTIVE_SESSIONS:
            logger.error(f"max_sessions_exceeded current={len(jobs)} limit={MAX_ACTIVE_SESSIONS}")
            return Response(f'max sessions exceeded: {len(jobs)}/{MAX_ACTIVE_SESSIONS}', status=503, mimetype='text/plain')
        
        # リソース使用率をログに記録（詳細版）
        memory_usage_percent = (resources['memory_mb'] / MEMORY_LIMIT_MB) * 100
        logger.info(f"system_resources memory={resources['memory_mb']:.1f}MB/{MEMORY_LIMIT_MB}MB ({memory_usage_percent:.1f}%) cpu={resources['cpu_percent']:.1f}% active_sessions={len(jobs)}/{MAX_ACTIVE_SESSIONS}")
        
        # メモリ使用率が高い場合は警告
        if memory_usage_percent > 80:
            logger.warning(f"high_memory_usage memory={resources['memory_mb']:.1f}MB ({memory_usage_percent:.1f}%) - approaching limit")
        
        return Response('ok', mimetype='text/plain', headers={'Cache-Control': 'no-store'})
    except Exception as e:
        # ログに記録してから503を返す
        logger.error(f"readyz_check_failed error={str(e)}")
        return Response(f'not ready: {str(e)}', status=503, mimetype='text/plain')

# === 後方互換性のため既存エンドポイントを維持（ただし軽量化） ===
@app.route('/ping')
def ping():
    """後方互換 - UptimeRobot用"""
    return jsonify({'status': 'ok', 'message': 'pong', 'timestamp': datetime.now().isoformat()})

@app.route('/health')
def health():
    """詳細ヘルスチェック - デバッグ用（重いので監視には使わない）"""
    try:
        from utils import pandas_available, openpyxl_available, playwright_available
        resources = get_system_resources()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'dependencies': {
                'pandas': pandas_available,
                'openpyxl': openpyxl_available,
                'playwright': playwright_available
            },
            'resources': resources,
            'active_sessions': len(session_manager['active_sessions'])
        })
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.route('/ready')
def ready():
    """後方互換 - 既存依存関係チェック"""
    from utils import pandas_available, openpyxl_available, playwright_available
    return jsonify({
        'status': 'ready',
        'timestamp': datetime.now().isoformat(),
        'dependencies': {
            'pandas': pandas_available,
            'openpyxl': openpyxl_available,
            'playwright': playwright_available
        }
    })

@app.route('/test')
def test():
    return jsonify({
        'status': 'ok',
        'message': 'Test endpoint working',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/download-template')
def download_template():
    try:
        print("テンプレートダウンロード開始")
        template_file, error_message = create_template_excel()
        
        if error_message:
            print(f"テンプレート作成エラー: {error_message}")
            return jsonify({'error': f'テンプレートファイルの作成に失敗しました: {error_message}'}), 500
        
        if not template_file or not os.path.exists(template_file):
            print(f"テンプレートファイルが存在しません: {template_file}")
            return jsonify({'error': 'テンプレートファイルの生成に失敗しました'}), 500
        
        print(f"テンプレートファイル作成成功: {template_file}")
        return send_file(
            template_file,
            as_attachment=True,
            download_name='jobcan_template.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        print(f"テンプレートダウンロード例外: {str(e)}")
        return jsonify({'error': f'テンプレートファイルの作成に失敗しました: {str(e)}'}), 500

@app.route('/download-previous-template')
def download_previous_template():
    try:
        print("先月テンプレートダウンロード開始")
        template_file, error_message = create_previous_month_template_excel()
        
        if error_message:
            print(f"先月テンプレート作成エラー: {error_message}")
            return jsonify({'error': f'先月テンプレートファイルの作成に失敗しました: {error_message}'}), 500
        
        if not template_file or not os.path.exists(template_file):
            print(f"先月テンプレートファイルが存在しません: {template_file}")
            return jsonify({'error': '先月テンプレートファイルの生成に失敗しました'}), 500
        
        print(f"先月テンプレートファイル作成成功: {template_file}")
        return send_file(
            template_file,
            as_attachment=True,
            download_name='jobcan_previous_month_template.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        print(f"先月テンプレートダウンロード例外: {str(e)}")
        return jsonify({'error': f'先月テンプレートファイルの作成に失敗しました: {str(e)}'}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # 入力データの検証
        if 'file' not in request.files:
            return jsonify({'error': 'ファイルが選択されていません'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'ファイルが選択されていません'})
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Excelファイル（.xlsx, .xls）のみアップロード可能です'})
        
        # ファイルサイズ制限（環境変数で設定可能）
        file.seek(0, 2)  # ファイルの末尾に移動
        file_size = file.tell()  # ファイルサイズを取得
        file.seek(0)  # ファイルの先頭に戻す
        
        if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
            return jsonify({'error': f'ファイルサイズが{MAX_FILE_SIZE_MB}MBを超えています。より小さいファイルを使用してください。'})
        
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        company_id = request.form.get('company_id', '').strip()
        
        # 入力データの詳細検証
        validation_errors = validate_input_data(email, password, file)
        if validation_errors:
            return jsonify({'error': '入力エラー: ' + '; '.join(validation_errors)})
        
        # リソース監視と警告（処理は継続）
        resource_warnings = check_resource_limits()
        if resource_warnings:
            print(f"リソース警告: {', '.join(resource_warnings)}")
        
        # ユニークなセッションIDを生成
        session_id = create_unique_session_id()
        job_id = str(uuid.uuid4())
        
        # 完全分離されたセッションディレクトリを作成
        session_dir = get_user_session_dir(session_id)
        
        # ファイルを保存（セッションID付きで一意性を確保）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f"{session_id}_{timestamp}.xlsx"
        file_path = os.path.join(session_dir, filename)
        file.save(file_path)
        
        # セッションを登録
        register_session(session_id, job_id)
        
        # P1-1: ファイルアップロード直後のメモリ計測
        if metrics_available:
            log_memory("upload_done", job_id=job_id, session_id=session_id, extra={
                'jobs_count': len(jobs),
                'sessions_count': len(session_manager['active_sessions'])
            })
        
        # ジョブ情報を初期化（スレッドセーフ）
        with jobs_lock:
            jobs[job_id] = {
                'status': 'running',
                'logs': [],
                'progress': 0,
                'step_name': 'initializing',
                'current_data': 0,
                'total_data': 0,
                'start_time': datetime.now().timestamp(),
                'end_time': None,  # P0-3: 完了時に設定
                'login_status': 'initializing',
                'login_message': '🔄 処理を初期化中...',
                'session_id': session_id,
                'session_dir': session_dir,
                'file_path': file_path,
                'email_hash': hash(email),  # 個人情報はハッシュ化
                'company_id': company_id,  # 会社IDを保存
                'resource_warnings': resource_warnings,
                'last_updated': time.time()
            }
        
        # バックグラウンドで処理を実行（エラーハンドリング強化 + 観測性）
        def run_automation():
            bg_start_time = time.time()
            logger.info(f"bg_job_start job_id={job_id} session_id={session_id} file_size={file_size}")
            
            # P1-1: ジョブ開始時のメモリ計測
            if metrics_available:
                log_memory("job_start", job_id=job_id, session_id=session_id, extra={
                    'jobs_count': len(jobs),
                    'sessions_count': len(session_manager['active_sessions'])
                })
            
            try:
                # セッション固有のブラウザ環境で処理を実行
                process_jobcan_automation(job_id, email, password, file_path, jobs, session_dir, session_id, company_id)
                
                duration = time.time() - bg_start_time
                logger.info(f"bg_job_success job_id={job_id} duration_sec={duration:.1f}")
                
            except Exception as e:
                error_message = f'処理中にエラーが発生しました: {str(e)}'
                duration = time.time() - bg_start_time
                logger.error(f"bg_job_error job_id={job_id} duration_sec={duration:.1f} error={str(e)}")
                
                with jobs_lock:
                    if job_id in jobs:
                        jobs[job_id]['status'] = 'error'
                        jobs[job_id]['login_status'] = 'error'
                        jobs[job_id]['login_message'] = error_message
                        jobs[job_id]['logs'].append(f"❌ {error_message}")
                        jobs[job_id]['last_updated'] = time.time()
                        jobs[job_id]['end_time'] = time.time()  # P0-3: エラー時のend_timeを記録
            finally:
                # 処理完了後の完全クリーンアップ（エラーが発生しても必ず実行）
                try:
                    cleanup_start_time = time.time()
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info(f"cleanup_file job_id={job_id} path={file_path}")
                    
                    cleanup_user_session(session_id)
                    unregister_session(session_id)
                    
                    cleanup_time = time.time() - cleanup_start_time
                    logger.info(f"cleanup_complete job_id={job_id} session_id={session_id} cleanup_sec={cleanup_time:.2f}")
                    
                    # P0-3: 完了ジョブの間引きを実行
                    prune_jobs()
                    
                except Exception as cleanup_error:
                    logger.error(f"cleanup_error job_id={job_id} session_id={session_id} error={str(cleanup_error)}")
                    # クリーンアップエラーでも処理は継続
                    # P0-3: エラー時も間引きを試行
                    try:
                        prune_jobs()
                    except:
                        pass
                    # P0-3: エラー時も間引きを試行
                    try:
                        prune_jobs()
                    except:
                        pass
        
        thread = threading.Thread(target=run_automation)
        thread.daemon = True  # メインプロセス終了時に自動終了
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'session_id': session_id,
            'message': '処理を開始しました',
            'status_url': f'/status/{job_id}',
            'resource_warnings': resource_warnings
        })
        
    except Exception as e:
        return jsonify({'error': f'予期しないエラーが発生しました: {str(e)}'})

@app.route('/status/<job_id>')
def get_status(job_id):
    try:
        # P0-3: 参照エンドポイントの冒頭で完了ジョブを間引く
        prune_jobs()
        
        with jobs_lock:
            if job_id not in jobs:
                print(f"ジョブが見つかりません: {job_id}")
                print(f"現在のジョブ一覧: {list(jobs.keys())}")
                return jsonify({
                    'error': 'ジョブが見つかりません',
                    'job_id': job_id,
                    'available_jobs': list(jobs.keys())
                }), 404
            
            job = jobs[job_id]
            
            # ログイン結果の詳細情報を取得
            login_status = job.get('login_status', 'unknown')
            login_message = job.get('login_message', 'ログイン状態が不明です')
            
            # ユーザー向けの詳細メッセージを生成
            user_message = generate_user_message(job['status'], login_status, login_message, job.get('progress', 0))
            
            # リソース情報を追加（エラーが発生しても処理を続行）
            try:
                resources = get_system_resources()
            except Exception as resource_error:
                print(f"リソース情報取得エラー: {resource_error}")
                resources = {'memory_mb': 0, 'cpu_percent': 0, 'active_sessions': 0}
            
            # レスポンスデータを構築
            response_data = {
                'status': job['status'],
                'progress': job.get('progress', 0),
                'step_name': job.get('step_name', ''),
                'current_data': job.get('current_data', 0),
                'total_data': job.get('total_data', 0),
                'logs': job.get('logs', []),
                'start_time': job.get('start_time', 0),
                'login_status': login_status,
                'login_message': login_message,
                'user_message': user_message,
                'session_id': job.get('session_id', ''),
                'resources': resources,
                'resource_warnings': job.get('resource_warnings', [])
            }
            
            # ステータスに応じたHTTPステータスコードを設定
            if job['status'] == 'error':
                return jsonify(response_data), 500
            elif job['status'] == 'completed':
                return jsonify(response_data), 200
            else:
                return jsonify(response_data), 200
                
    except Exception as e:
        print(f"ステータス取得で予期しないエラー: {e}")
        return jsonify({
            'error': 'ステータス取得エラー',
            'status': 'error',
            'progress': 0,
            'login_status': 'error',
            'login_message': 'システムエラーが発生しました'
        }), 500

@app.route('/sessions')
def get_active_sessions():
    """アクティブセッション情報を取得"""
    try:
        with session_manager['session_lock']:
            active_sessions = session_manager['active_sessions'].copy()
        
        resources = get_system_resources()
        warnings = check_resource_limits()
        
        return jsonify({
            'active_sessions': len(active_sessions),
            'sessions': [
                {
                    'session_id': session_id,
                    'job_id': session_info['job_id'],
                    'start_time': session_info['start_time'],
                    'duration': time.time() - session_info['start_time']
                }
                for session_id, session_info in active_sessions.items()
            ],
            'resources': resources,
            'warnings': warnings
        })
    except Exception as e:
        return jsonify({'error': f'セッション情報取得エラー: {str(e)}'})

@app.route('/cleanup-sessions')
def cleanup_expired_sessions():
    """期限切れセッションのクリーンアップ"""
    try:
        current_time = time.time()
        expired_sessions = []
        
        with session_manager['session_lock']:
            for session_id, session_info in list(session_manager['active_sessions'].items()):
                # 30分以上経過したセッションを期限切れとする
                if current_time - session_info['start_time'] > 1800:
                    expired_sessions.append(session_id)
                    del session_manager['active_sessions'][session_id]
        
        # 期限切れセッションのクリーンアップ
        for session_id in expired_sessions:
            cleanup_user_session(session_id)
        
        return jsonify({
            'cleaned_sessions': len(expired_sessions),
            'remaining_sessions': len(session_manager['active_sessions']),
            'message': f'{len(expired_sessions)}個のセッションをクリーンアップしました'
        })
    except Exception as e:
        return jsonify({'error': f'セッションクリーンアップエラー: {str(e)}'})

def generate_user_message(status, login_status, login_message, progress):
    """ユーザー向けメッセージを生成"""
    if status == 'running':
        if login_status == 'success':
            return f"✅ ログイン成功 - {login_message}"
        elif login_status == 'failed':
            return f"❌ ログイン失敗 - {login_message}"
        elif login_status == 'captcha':
            return f"🔄 画像認証が必要です - {login_message}"
        elif login_status == 'processing':
            return f"🔄 ログイン処理中... - {login_message}"
        else:
            return f"🔄 処理中... - {login_message}"
    elif status == 'completed':
        return "✅ 処理完了 勤怠データの入力が完了しました。"
    elif status == 'error':
        return f"❌ エラーが発生しました: {login_message}"
    else:
        return "🔄 処理中..."

@app.route('/ads.txt')
def ads_txt():
    """ads.txt を配信（Google AdSense用）"""
    content = "google.com, pub-4232725615106709, DIRECT, f08c47fec0942fa0"
    return Response(content, mimetype='text/plain')

@app.route('/robots.txt')
def robots_txt():
    """robots.txt を配信"""
    try:
        return send_file('static/robots.txt', mimetype='text/plain')
    except Exception as e:
        # ファイルがない場合のフォールバック
        content = """User-agent: *
Allow: /

User-agent: Googlebot
Allow: /

User-agent: AdsBot-Google
Allow: /
"""
        return Response(content, mimetype='text/plain')

@app.route('/sitemap.xml')
def sitemap():
    """XMLサイトマップを動的生成"""
    from flask import url_for
    from datetime import datetime
    
    # ベースURL
    base_url = 'https://jobcan-automation.onrender.com'
    
    # サイトマップに含めるURLのリスト
    # 形式: (url_path, changefreq, priority, lastmod)
    urls = [
        # 主要ページ
        ('/', 'daily', '1.0', '2025-01-26'),
        ('/autofill', 'daily', '1.0', '2025-01-26'),
        ('/about', 'monthly', '0.9', '2025-01-26'),
        ('/contact', 'monthly', '0.8', '2025-01-26'),
        ('/privacy', 'yearly', '0.5', '2025-01-26'),
        ('/terms', 'yearly', '0.5', '2025-01-26'),
        ('/faq', 'weekly', '0.8', '2025-01-26'),
        ('/glossary', 'monthly', '0.6', '2025-01-26'),
        ('/best-practices', 'monthly', '0.8', '2025-01-26'),
        ('/sitemap.html', 'monthly', '0.5', '2025-01-26'),
        
        # ガイドページ
        ('/guide/complete', 'weekly', '0.9', '2025-01-26'),
        ('/guide/comprehensive-guide', 'weekly', '0.9', '2025-01-26'),
        ('/guide/getting-started', 'weekly', '0.9', '2025-01-26'),
        ('/guide/excel-format', 'weekly', '0.9', '2025-01-26'),
        ('/guide/troubleshooting', 'weekly', '0.8', '2025-01-26'),
        
        # ツールページ
        ('/tools', 'weekly', '0.9', '2025-01-26'),
        ('/tools/image-batch', 'monthly', '0.7', '2025-01-26'),
        ('/tools/pdf', 'monthly', '0.7', '2025-01-26'),
        ('/tools/image-cleanup', 'monthly', '0.7', '2025-01-26'),
        ('/tools/minutes', 'monthly', '0.7', '2025-01-26'),
        ('/tools/seo', 'monthly', '0.7', '2025-01-26'),
        
        # ブログ一覧
        ('/blog', 'daily', '0.8', '2025-01-26'),
        
        # ブログ記事（既存）
        ('/blog/implementation-checklist', 'monthly', '0.7', '2025-01-26'),
        ('/blog/automation-roadmap', 'monthly', '0.7', '2025-01-26'),
        ('/blog/workstyle-reform-automation', 'monthly', '0.7', '2025-01-26'),
        ('/blog/excel-attendance-limits', 'monthly', '0.7', '2025-01-26'),
        ('/blog/playwright-security', 'monthly', '0.7', '2025-01-26'),
        
        # ブログ記事（新規3本）
        ('/blog/month-end-closing-hell-and-automation', 'monthly', '0.7', '2025-01-26'),
        ('/blog/excel-format-mistakes-and-design', 'monthly', '0.7', '2025-01-26'),
        ('/blog/convince-it-and-hr-for-automation', 'monthly', '0.7', '2025-01-26'),
        ('/blog/playwright-jobcan-challenges-and-solutions', 'monthly', '0.7', '2025-01-26'),
        ('/blog/jobcan-auto-input-tools-overview', 'monthly', '0.7', '2025-01-26'),
        ('/blog/reduce-manual-work-checklist', 'monthly', '0.7', '2025-01-26'),
        ('/blog/jobcan-month-end-tips', 'monthly', '0.7', '2025-01-26'),
        ('/blog/jobcan-auto-input-dos-and-donts', 'monthly', '0.7', '2025-01-28'),
        ('/blog/month-end-closing-checklist', 'monthly', '0.7', '2025-01-29'),
        
        # 導入事例
        ('/case-study/contact-center', 'monthly', '0.8', '2025-01-26'),
        ('/case-study/consulting-firm', 'monthly', '0.8', '2025-01-26'),
        ('/case-study/remote-startup', 'monthly', '0.8', '2025-01-26'),
    ]
    
    # XMLサイトマップを生成
    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    
    for url_path, changefreq, priority, lastmod in urls:
        full_url = base_url + url_path
        xml_parts.append('  <url>')
        xml_parts.append(f'    <loc>{full_url}</loc>')
        xml_parts.append(f'    <changefreq>{changefreq}</changefreq>')
        xml_parts.append(f'    <priority>{priority}</priority>')
        xml_parts.append(f'    <lastmod>{lastmod}</lastmod>')
        xml_parts.append('  </url>')
    
    xml_parts.append('</urlset>')
    
    xml_content = '\n'.join(xml_parts)
    
    return Response(xml_content, mimetype='application/xml')

def monitor_processing_resources(data_index, total_data):
    """データ処理中のリソース監視（4番目以降で強化）"""
    try:
        resources = get_system_resources()
        memory_usage_percent = (resources['memory_mb'] / MEMORY_LIMIT_MB) * 100
        
        # 4番目のデータ以降はより厳密に監視
        if data_index >= 4:
            logger.info(f"processing_monitor data={data_index}/{total_data} memory={resources['memory_mb']:.1f}MB/{MEMORY_LIMIT_MB}MB ({memory_usage_percent:.1f}%) cpu={resources['cpu_percent']:.1f}%")
            
            # メモリ使用率が85%を超えた場合は警告
            if memory_usage_percent > 85:
                logger.warning(f"critical_memory_usage data={data_index} memory={resources['memory_mb']:.1f}MB ({memory_usage_percent:.1f}%) - approaching OOM")
                
                # メモリ使用率が90%を超えた場合は緊急停止
                if memory_usage_percent > 90:
                    logger.error(f"emergency_memory_stop data={data_index} memory={resources['memory_mb']:.1f}MB ({memory_usage_percent:.1f}%) - preventing OOM")
                    raise RuntimeError(f"メモリ使用率が危険域に達しました: {memory_usage_percent:.1f}%")
        
        return True
    except Exception as e:
        logger.error(f"processing_monitor_failed data={data_index} error={str(e)}")
        raise

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 