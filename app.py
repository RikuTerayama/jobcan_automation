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
# Render本番では同時実行を直列化（512MB/0.5CPUで複数Playwrightは高リスク）。未設定時はRENDER検知で1に寄せる
_default_sessions = "1" if os.getenv("RENDER") else "20"
MAX_ACTIVE_SESSIONS = int(os.getenv("MAX_ACTIVE_SESSIONS", _default_sessions))
# ジョブ全体のハードタイムアウト（秒）。超過でstatus=timeoutに遷移
JOB_TIMEOUT_SEC = int(os.getenv("JOB_TIMEOUT_SEC", "300"))  # 5分

app = Flask(__name__)

# 起動時の検証（恒久対策：テンプレートとモジュールの存在確認）
def validate_startup():
    """アプリケーション起動時に主要リソースの存在を確認"""
    errors = []
    
    # 主要テンプレートの存在確認
    required_templates = [
        'landing.html',
        'error.html',
        'includes/header.html',
        'includes/footer.html',
        'includes/head_meta.html',
        'includes/structured_data.html'
    ]
    for template in required_templates:
        try:
            app.jinja_env.get_template(template)
        except Exception as e:
            errors.append(f"Template not found or invalid: {template} - {str(e)}")
    
    # 製品カタログ（products_catalog）のインポート確認（LP/500 根本対策）
    try:
        from lib.products_catalog import PRODUCTS
        if not isinstance(PRODUCTS, list):
            errors.append("products_catalog.PRODUCTS is not a list")
        elif len(PRODUCTS) == 0:
            errors.append("products_catalog.PRODUCTS is empty")
    except Exception as e:
        errors.append(f"Failed to import products_catalog.PRODUCTS: {type(e).__name__}: {str(e)}")
    
    if errors:
        logger.error(f"startup_validation_failed errors={errors}")
        # エラーがあっても起動は続行（本番環境で起動できないのを防ぐ）
    else:
        logger.info("startup_validation_passed all checks OK")

# 起動時に検証を実行
validate_startup()

# アップロードフォルダの設定
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# === リクエストロギングミドルウェア ===
# P1: prune_jobs実行頻度制御（メモリ最適化）
_last_prune_time = 0
PRUNE_INTERVAL_SECONDS = 300  # 5分ごとにprune_jobsを実行

@app.before_request
def before_request():
    """リクエスト開始時の処理"""
    global _last_prune_time
    
    g.start_time = time.time()
    g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4())[:8])
    
    # P1: 定期的にprune_jobsを実行（メモリ最適化）
    # ヘルスチェックや静的ファイルリクエストは除外
    if not request.path.startswith(('/healthz', '/livez', '/readyz', '/static')):
        current_time = time.time()
        if current_time - _last_prune_time >= PRUNE_INTERVAL_SECONDS:
            try:
                prune_jobs(current_time=current_time)
                _last_prune_time = current_time
            except Exception as prune_error:
                # prune_jobsのエラーはログに記録するが、リクエスト処理は続行
                logger.warning(f"prune_jobs_error in before_request: {prune_error}")
    
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
def _generate_error_id():
    """エラーIDを生成（短いUUID）"""
    return str(uuid.uuid4())[:8]

def _render_error_page(status_code, error_message, error_id=None):
    """エラーページをレンダリング（共通関数）"""
    if error_id is None:
        error_id = _generate_error_id()
    
    try:
        response = render_template(
            'error.html',
            error_message=error_message,
            error_id=error_id,
            status_code=status_code
        ), status_code
        # レスポンスヘッダにX-Error-Idを付与（恒久対策：エラーIDの追跡強化）
        from flask import make_response
        resp = make_response(response)
        resp.headers['X-Error-Id'] = error_id
        return resp
    except Exception as render_error:
        # エラーテンプレートもレンダリングできない場合はシンプルなHTMLを返す
        import traceback
        logger.exception(f"error_page_render_failed error_id={error_id} render_error={str(render_error)}")
        from flask import make_response
        html_content = f'''<html><head><meta charset="utf-8"><title>エラー {status_code}</title></head>
<body><h1>エラーが発生しました</h1>
<p>{error_message}</p>
<p>エラーID: {error_id}</p>
<p>お問い合わせの際は、このエラーIDをお伝えください。</p>
</body></html>'''
        resp = make_response((html_content, status_code))
        resp.headers['X-Error-Id'] = error_id
        return resp

@app.errorhandler(404)
def not_found(error):
    """404エラーのハンドリング"""
    error_id = _generate_error_id()
    request_id = getattr(g, 'request_id', 'unknown')
    logger.warning(
        f"not_found error_id={error_id} rid={request_id} "
        f"path={request.path} method={request.method} "
        f"user_agent={request.headers.get('User-Agent', 'Unknown')} error={str(error)}"
    )
    return _render_error_page(
        404,
        'お探しのページが見つかりませんでした。URLを確認してください。',
        error_id
    )

@app.errorhandler(500)
def internal_error(error):
    """500エラーのハンドリング"""
    error_id = _generate_error_id()
    request_id = getattr(g, 'request_id', 'unknown')
    
    # スタックトレースをログに記録（恒久対策：例外ログの強化）
    # logger.exception()を使用してスタックトレースを確実に記録
    # user-agent、remote_addr、例外型も含める
    try:
        path = request.path if request else 'unknown'
        method = request.method if request else 'unknown'
        user_agent = request.headers.get('User-Agent', 'Unknown') if request else 'Unknown'
        remote_addr = request.remote_addr if request else 'unknown'
    except Exception:
        path = 'unknown'
        method = 'unknown'
        user_agent = 'Unknown'
        remote_addr = 'unknown'
    
    logger.exception(
        f"internal_server_error error_id={error_id} rid={request_id} "
        f"path={path} method={method} "
        f"user_agent={user_agent} remote_addr={remote_addr} "
        f"exception_type={type(error).__name__} error={str(error)}"
    )
    
    return _render_error_page(
        500,
        'サーバー側でエラーが発生しました。しばらく待ってから再試行してください。',
        error_id
    )

@app.errorhandler(503)
def service_unavailable(error):
    """503エラーのハンドリング"""
    error_id = _generate_error_id()
    request_id = getattr(g, 'request_id', 'unknown')
    try:
        path = request.path if request else 'unknown'
        method = request.method if request else 'unknown'
    except Exception:
        path, method = 'unknown', 'unknown'
    logger.exception(
        f"service_unavailable error_id={error_id} rid={request_id} path={path} method={method} error={str(error)}"
    )
    return _render_error_page(
        503,
        'サービスが一時的に利用できません。しばらく待ってから再試行してください。',
        error_id
    )

@app.errorhandler(Exception)
def handle_exception(e):
    """未処理例外のハンドリング（404以外）"""
    from werkzeug.exceptions import HTTPException
    
    # HTTPException（404, 500等）は適切なハンドラーに委譲
    if isinstance(e, HTTPException):
        # FlaskのHTTPExceptionはそのまま通す（適切なハンドラーが処理する）
        return e
    
    # 404エラーは上記のハンドラーで処理されるため、ここでは処理しない
    if hasattr(e, 'code') and e.code == 404:
        raise e  # 404エラーハンドラーに委譲
    
    error_id = _generate_error_id()
    request_id = getattr(g, 'request_id', 'unknown')
    
    # 詳細なエラー情報をログに記録（恒久対策：例外ログの強化）
    # logger.exception()を使用してスタックトレースを確実に記録
    # user-agent、remote_addr、例外型も含める
    try:
        path = request.path if request else 'unknown'
        method = request.method if request else 'unknown'
        user_agent = request.headers.get('User-Agent', 'Unknown') if request else 'Unknown'
        remote_addr = request.remote_addr if request else 'unknown'
    except Exception:
        path = 'unknown'
        method = 'unknown'
        user_agent = 'Unknown'
        remote_addr = 'unknown'
    
    logger.exception(
        f"unhandled_exception error_id={error_id} rid={request_id} "
        f"path={path} method={method} "
        f"user_agent={user_agent} remote_addr={remote_addr} "
        f"exception_type={type(e).__name__} error={str(e)}"
    )
    
    # HTMLエラーページを返す（APIエンドポイントでもHTMLを返す）
    return _render_error_page(
        500,
        '予期しないエラーが発生しました。しばらく待ってから再試行してください。',
        error_id
    )

# 環境変数をテンプレートコンテキストに注入（AdSense設定用）
@app.context_processor
def inject_env_vars():
    """環境変数をテンプレートで使えるようにする。製品一覧は products_catalog から取得（外部依存なし）。"""
    try:
        import json
        from lib.products_catalog import PRODUCTS

        app_version = '1.0.0'
        try:
            with open('package.json', 'r', encoding='utf-8') as f:
                package_data = json.load(f)
                app_version = package_data.get('version', '1.0.0')
        except Exception:
            pass

        products_list = PRODUCTS
        if not isinstance(products_list, list):
            logger.warning(
                f"context_processor products_catalog not a list type={type(products_list).__name__} - using []"
            )
            products_list = []
        products_catalog = [p for p in products_list if isinstance(p, dict) and p.get('status') == 'available']

        from lib.nav import get_nav_sections, get_footer_columns
        nav_sections = get_nav_sections()
        footer_columns = get_footer_columns()

        return {
            'ADSENSE_ENABLED': os.getenv('ADSENSE_ENABLED', 'false').lower() == 'true',
            'app_version': app_version,
            'products': products_list,
            'products_catalog': products_catalog,
            'nav_sections': nav_sections,
            'footer_columns': footer_columns,
            'GA_MEASUREMENT_ID': os.getenv('GA_MEASUREMENT_ID', ''),
            'GSC_VERIFICATION_CONTENT': os.getenv('GSC_VERIFICATION_CONTENT', ''),
            'OPERATOR_NAME': os.getenv('OPERATOR_NAME', ''),
            'OPERATOR_EMAIL': os.getenv('OPERATOR_EMAIL', ''),
            'OPERATOR_LOCATION': os.getenv('OPERATOR_LOCATION', ''),
            'OPERATOR_NOTE': os.getenv('OPERATOR_NOTE', '')
        }
    except Exception as e:
        request_id = getattr(g, 'request_id', 'unknown') if hasattr(g, 'request_id') else 'unknown'
        import traceback
        logger.exception(
            f"context_processor_error rid={request_id} products_empty_reason={type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        )
        from lib.nav import get_nav_sections_fallback, get_footer_columns
        return {
            'ADSENSE_ENABLED': False,
            'app_version': '1.0.0',
            'products': [],
            'products_catalog': [],
            'nav_sections': get_nav_sections_fallback(),
            'footer_columns': get_footer_columns(),
            'GA_MEASUREMENT_ID': '',
            'GSC_VERIFICATION_CONTENT': '',
            'OPERATOR_NAME': '',
            'OPERATOR_EMAIL': '',
            'OPERATOR_LOCATION': '',
            'OPERATOR_NOTE': ''
        }

# ジョブの状態を管理（スレッドセーフな辞書）
jobs = {}
jobs_lock = threading.Lock()

# 直列実行＋待機キュー（インメモリFIFO）。サーバ再起動でキューは消える
from collections import deque
job_queue = deque()
# queued ジョブの実行用パラメータ（start時にpopして使用。資格情報はstart後即参照しない）
queued_job_params = {}
# queued の最大待機時間（超過でtimeout扱い・ファイル削除）
QUEUED_MAX_WAIT_SEC = int(os.getenv("QUEUED_MAX_WAIT_SEC", "1800"))  # 30分
MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", "50"))  # キュー上限（メモリ保護）

# P0-3: 完了ジョブの保持期間（秒）
JOB_RETENTION_SECONDS = 1800  # 30分

# P1: ジョブログの上限設定（メモリ最適化）。utils.MAX_JOB_LOGSと同期（500）
MAX_JOB_LOGS = 500  # 1ジョブあたりの最大ログ件数

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

def count_running_jobs():
    """statusがrunningのジョブ数（同時実行数）を返す。"""
    with jobs_lock:
        return sum(1 for j in jobs.values() if j.get('status') == 'running')

def check_resource_limits():
    """リソース制限のチェック。上限判定はrunningジョブ数に統一（sessionと二重系統にしない）。"""
    resources = get_system_resources()
    running_count = count_running_jobs()
    session_count = resources['active_sessions']
    warnings = []
    
    # メモリ使用量の警告（環境変数で設定可能）
    if resources['memory_mb'] > MEMORY_LIMIT_MB:
        raise RuntimeError(f"メモリ制限を超過しました: {resources['memory_mb']:.1f}MB > {MEMORY_LIMIT_MB}MB")
    elif resources['memory_mb'] > MEMORY_WARNING_MB:
        warnings.append(f"メモリ使用量が高いです: {resources['memory_mb']:.1f}MB")
    
    # 同時実行数はrunningジョブ数で判定（OOM防止）。session数は参考ログのみ
    if running_count >= MAX_ACTIVE_SESSIONS:
        raise RuntimeError(
            f"同時処理数の上限に達しています（実行中: {running_count}/{MAX_ACTIVE_SESSIONS}）。"
            f"しばらく待ってから再試行してください。"
        )
    elif running_count > MAX_ACTIVE_SESSIONS * 0.8:
        warnings.append(f"実行中ジョブが多いです: {running_count}/{MAX_ACTIVE_SESSIONS}件")
    if session_count != running_count:
        logger.warning(f"jobs_session_mismatch running_jobs={running_count} active_sessions={session_count}")
    
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


def maybe_start_next_job():
    """running が 0 のときキュー先頭を running にしてスレッド起動。jobs_lock は内部で取得。"""
    with jobs_lock:
        running_count = sum(1 for j in jobs.values() if j.get('status') == 'running')
        if running_count >= MAX_ACTIVE_SESSIONS:
            return
        if not job_queue:
            return
        job_id = job_queue.popleft()
        params = queued_job_params.pop(job_id, None)
        if not params or job_id not in jobs:
            return
        # ジョブを running に更新
        jobs[job_id]['status'] = 'running'
        jobs[job_id]['step_name'] = 'initializing'
        jobs[job_id]['login_status'] = 'initializing'
        jobs[job_id]['login_message'] = '🔄 処理を初期化中...'
        jobs[job_id]['start_time'] = time.time()
        jobs[job_id]['last_updated'] = time.time()
        email = params['email']
        password = params['password']
        file_path = params['file_path']
        session_dir = params['session_dir']
        session_id = params['session_id']
        company_id = params.get('company_id', '')
        file_size = params.get('file_size', 0)
    # ロック外でスレッド起動（run_automation_impl 内で process が重い）
    thread = threading.Thread(
        target=run_automation_impl,
        args=(job_id, email, password, file_path, session_dir, session_id, company_id, file_size)
    )
    thread.daemon = True
    thread.start()
    logger.info(f"queue_started job_id={job_id} from_queue=1")


def run_automation_impl(job_id, email, password, file_path, session_dir, session_id, company_id, file_size):
    """1ジョブ分の自動化実行。完了後 maybe_start_next_job で次を起動。"""
    from automation import process_jobcan_automation
    bg_start_time = time.time()
    logger.info(f"bg_job_start job_id={job_id} session_id={session_id} file_size={file_size}")
    try:
        process_jobcan_automation(
            job_id, email, password, file_path, jobs, session_dir, session_id, company_id,
            job_timeout_sec=JOB_TIMEOUT_SEC
        )
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
                from utils import add_job_log
                add_job_log(job_id, f"❌ {error_message}", jobs)
                jobs[job_id]['last_updated'] = time.time()
                jobs[job_id]['end_time'] = time.time()
    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"cleanup_file job_id={job_id} path={file_path}")
            cleanup_user_session(session_id)
            unregister_session(session_id)
            prune_jobs()
        except Exception as cleanup_error:
            logger.error(f"cleanup_error job_id={job_id} session_id={session_id} error={str(cleanup_error)}")
            try:
                prune_jobs()
            except Exception:
                pass
        maybe_start_next_job()


def prune_jobs(current_time=None, retention_sec=JOB_RETENTION_SECONDS):
    """P0-3: 完了/エラー/timeout のジョブを一定時間保持後に削除。queued の最大待機超過は timeout 化してクリーンアップ。"""
    if current_time is None:
        current_time = time.time()
    
    # フェーズ1: queued の最大待機超過を timeout 扱いし、ファイル・セッションを削除
    cleanup_queued = []
    with jobs_lock:
        for job_id, job_info in list(jobs.items()):
            if job_info.get('status') != 'queued':
                continue
            queued_at = job_info.get('queued_at') or job_info.get('start_time') or 0
            if current_time - queued_at <= QUEUED_MAX_WAIT_SEC:
                continue
            # キューから除去
            global job_queue
            job_queue = deque([x for x in job_queue if x != job_id])
            queued_job_params.pop(job_id, None)
            jobs[job_id]['status'] = 'timeout'
            jobs[job_id]['end_time'] = current_time
            jobs[job_id]['login_message'] = '待機時間が上限を超えたためキャンセルされました。'
            fp = job_info.get('file_path')
            sid = job_info.get('session_id')
            if fp or sid:
                cleanup_queued.append((fp, sid))
    for fp, sid in cleanup_queued:
        try:
            if fp and os.path.exists(fp):
                os.remove(fp)
            if sid:
                cleanup_user_session(sid)
                unregister_session(sid)
        except Exception as e:
            logger.error(f"prune_queued_cleanup job_id cleanup_error={e}")
    
    removed_count = 0
    removed_job_ids = []
    
    with jobs_lock:
        jobs_to_remove = []
        
        for job_id, job_info in list(jobs.items()):
            # completed / error / timeout を削除対象（timeoutはend_timeを_check_job_timeoutで設定済み）
            if job_info.get('status') not in ('completed', 'error', 'timeout'):
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
    # 恒久対策：トップページを絶対に落とさない（依存データが取れない場合でも劣化表示で耐える）
    # context_processorで既にproductsが注入されているため、明示的に渡す必要はない
    # ただし、テンプレートでproductsが未定義の場合に備えて、明示的に渡す
    
    # ステップ1: 製品一覧は products_catalog から取得（外部依存なし・落ちない）
    products = []
    try:
        from lib.products_catalog import PRODUCTS
        products = list(PRODUCTS) if isinstance(PRODUCTS, list) else []
    except Exception as import_error:
        request_id = getattr(g, 'request_id', 'unknown')
        logger.warning(
            f"landing_page_products_empty rid={request_id} reason=import_failed "
            f"exception={type(import_error).__name__} error={str(import_error)}"
        )
    
    # ステップ2: テンプレートレンダリング（失敗しても劣化表示を返す）
    try:
        # テンプレートに明示的に渡す（context_processorのフォールバック）
        # productsが空のリストでも、テンプレートで安全に処理される
        return render_template('landing.html', products=products)
    except Exception as render_error:
        # テンプレートレンダリング時の例外をログに記録
        request_id = getattr(g, 'request_id', 'unknown')
        logger.exception(
            f"landing_page_render_failed rid={request_id} path={request.path if request else 'unknown'} "
            f"error={str(render_error)} exception_type={type(render_error).__name__}"
        )
        
        # 恒久対策：エラーページではなく、劣化表示のHTMLを直接返す
        # これにより、トップページは常に200を返す
        from flask import make_response
        degraded_html = f'''<!doctype html>
<html lang="ja">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>業務効率化ツール集</title>
    <style>
        body {{
            font-family: 'Noto Sans JP', sans-serif;
            margin: 0;
            padding: 40px 20px;
            background: linear-gradient(135deg, #121212 0%, #1A1A1A 50%, #0F0F0F 100%);
            color: #FFFFFF;
            line-height: 1.8;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(0, 0, 0, 0.35);
            border-radius: 20px;
            padding: 40px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        h1 {{
            color: #FFFFFF;
            font-size: 2.5em;
            margin-bottom: 20px;
        }}
        p {{
            color: rgba(255, 255, 255, 0.9);
            margin-bottom: 20px;
        }}
        .warning {{
            background: rgba(255, 152, 0, 0.1);
            border-left: 4px solid #FF9800;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        a {{
            color: #4A9EFF;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 業務効率化ツール集</h1>
        <p>日々の業務を効率化する、シンプルで強力なツールを提供しています。</p>
        
        <div class="warning">
            <p><strong>⚠️ 一時的な表示の問題</strong></p>
            <p>現在、製品情報の読み込みに問題が発生しています。しばらく待ってから再度お試しください。</p>
            <p>以下のリンクから直接アクセスできます：</p>
            <ul>
                <li><a href="/autofill">Jobcan自動入力</a></li>
                <li><a href="/tools">ツール一覧</a></li>
                <li><a href="/about">サイトについて</a></li>
            </ul>
        </div>
        
        <p style="margin-top: 40px; font-size: 0.9em; color: rgba(255, 255, 255, 0.7);">
            問題が解決しない場合は、<a href="/contact">お問い合わせ</a>からご連絡ください。
        </p>
    </div>
</body>
</html>'''
        resp = make_response(degraded_html, 200)
        resp.headers['X-Degraded-Mode'] = 'true'
        return resp

@app.route('/autofill')
def autofill():
    """Jobcan自動入力ツール（旧ホームページ）"""
    try:
        return render_template('autofill.html')
    except Exception as e:
        # 例外をログに記録してから、エラーハンドラに委譲（例外を再発生）
        request_id = getattr(g, 'request_id', 'unknown')
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(
            f"autofill_page_error rid={request_id} path={request.path} "
            f"error={str(e)}\n{error_traceback}"
        )
        # 例外を再発生させて、エラーハンドラに処理させる
        raise

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

@app.route('/guide')
def guide_index():
    """ガイド一覧ページ（Jobcan / Tools の2セクション）"""
    try:
        from lib.products_catalog import PRODUCTS
        products = [p for p in PRODUCTS if isinstance(p, dict) and p.get('status') == 'available']
    except Exception:
        products = []
    return render_template('guide/index.html', products=products)


@app.route('/guide/autofill')
def guide_autofill():
    """Jobcan AutoFill 統合ガイド（他ツールと同粒度の1ツール=1ガイド）"""
    return render_template('guide/autofill.html')


@app.route('/guide/getting-started')
def guide_getting_started():
    """はじめての使い方ガイド"""
    return render_template('guide/getting-started.html')


@app.route('/guide/excel-format')
def guide_excel_format():
    """Excelファイルの作成方法ガイド"""
    return render_template('guide/excel-format.html')


@app.route('/guide/troubleshooting')
def guide_troubleshooting():
    """トラブルシューティングガイド"""
    return render_template('guide/troubleshooting.html')

@app.route('/guide/complete')
def guide_complete():
    """完全ガイド"""
    return render_template('guide/complete-guide.html')

@app.route('/guide/comprehensive-guide')
def guide_comprehensive_guide():
    """Jobcan勤怠管理を効率化する総合ガイド"""
    return render_template('guide/comprehensive-guide.html')

@app.route('/guide/image-batch')
def guide_image_batch():
    """画像一括変換ツールガイド"""
    return render_template('guide/image-batch.html')

@app.route('/guide/pdf')
def guide_pdf():
    """PDFユーティリティガイド"""
    return render_template('guide/pdf.html')

@app.route('/guide/image-cleanup')
def guide_image_cleanup():
    """画像ユーティリティガイド"""
    return render_template('guide/image-cleanup.html')

@app.route('/guide/minutes')
def guide_minutes():
    """議事録整形ツールガイド"""
    return render_template('guide/minutes.html')

@app.route('/guide/seo')
def guide_seo():
    """Web/SEOユーティリティガイド"""
    return render_template('guide/seo.html')

@app.route('/tools/image-batch')
def tools_image_batch():
    """画像一括変換ツール"""
    from lib.routes import get_product_by_path
    product = get_product_by_path('/tools/image-batch')
    return render_template('tools/image-batch.html', product=product)

@app.route('/tools/pdf')
def tools_pdf():
    """PDFユーティリティ"""
    from lib.routes import get_product_by_path
    product = get_product_by_path('/tools/pdf')
    return render_template('tools/pdf.html', product=product)

@app.route('/tools/image-cleanup')
def tools_image_cleanup():
    """画像ユーティリティ"""
    from lib.routes import get_product_by_path
    product = get_product_by_path('/tools/image-cleanup')
    return render_template('tools/image-cleanup.html', product=product)

@app.route('/tools/minutes')
def tools_minutes():
    """議事録整形ツール"""
    from lib.routes import get_product_by_path
    product = get_product_by_path('/tools/minutes')
    return render_template('tools/minutes.html', product=product)


@app.route('/api/minutes/format', methods=['POST'])
def api_minutes_format():
    """議事録整形API（将来のLLM連携用スタブ）。現時点では未実装で501を返す。"""
    return jsonify(success=False, error='Not implemented'), 501


@app.route('/tools/seo')
def tools_seo():
    """Web/SEOユーティリティ"""
    from lib.routes import get_product_by_path
    product = get_product_by_path('/tools/seo')
    return render_template('tools/seo.html', product=product)


# 簡易レート制限: /api/seo/crawl-urls を IP ごとに 60 秒に 1 回まで
_crawl_rate_by_ip = {}
_crawl_rate_lock = threading.Lock()
_CRAWL_RATE_SEC = 60


def _is_valid_ip(s):
    """妥当な IPv4/IPv6 形式なら True。"""
    if not s or not isinstance(s, str):
        return False
    s = s.strip()
    try:
        import ipaddress
        ipaddress.ip_address(s)
        return True
    except (ValueError, TypeError):
        return False


def _get_client_ip_for_crawl():
    """request.access_route / X-Forwarded-For から妥当なIPを採用し、なければ remote_addr。"""
    candidates = []
    if getattr(request, 'access_route', None):
        candidates.extend(request.access_route)
    xff = request.headers.get('X-Forwarded-For', '')
    if xff:
        candidates.extend(p.strip() for p in xff.split(',') if p.strip())
    if request.remote_addr:
        candidates.append(request.remote_addr)
    for c in candidates:
        if _is_valid_ip(c):
            return c
    return request.remote_addr or 'unknown'


@app.route('/api/seo/crawl-urls', methods=['POST'])
def api_seo_crawl_urls():
    """同一ホスト内でURLをクロールし、URL一覧を返す。sitemap用。SSRF対策・レート制限あり。"""
    client_ip = _get_client_ip_for_crawl()
    now = time.time()
    with _crawl_rate_lock:
        last = _crawl_rate_by_ip.get(client_ip, 0)
        if now - last < _CRAWL_RATE_SEC:
            resp = jsonify(
                success=False,
                error='しばらく待ってから再度お試しください（1分に1回まで）',
                retry_after_sec=_CRAWL_RATE_SEC
            )
            resp.status_code = 429
            resp.headers['Retry-After'] = str(_CRAWL_RATE_SEC)
            return resp
        _crawl_rate_by_ip[client_ip] = now

    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception:
        data = {}
    start_url = (data.get('start_url') or '').strip()
    if not start_url:
        return jsonify(success=False, error='start_url を指定してください'), 400

    from lib.seo_crawler import crawl, is_url_safe_for_crawl
    safe, err_msg = is_url_safe_for_crawl(start_url)
    if not safe:
        return jsonify(success=False, error=err_msg or 'このURLは許可されていません'), 400

    max_urls = data.get('max_urls', 300)
    max_depth = data.get('max_depth', 3)
    try:
        max_urls = int(max_urls)
        max_depth = int(max_depth)
    except (TypeError, ValueError):
        max_urls = 300
        max_depth = 3
    max_urls = max(1, min(1000, max_urls))
    max_depth = max(0, min(10, max_depth))

    urls, warnings = crawl(
        start_url=start_url,
        max_urls=max_urls,
        max_depth=max_depth,
        request_timeout=5,
        total_timeout=60
    )
    return jsonify(success=True, urls=urls, warnings=warnings)


@app.route('/tools')
def tools_index():
    """ツール一覧ページ"""
    try:
        from lib.products_catalog import PRODUCTS
        products = list(PRODUCTS) if isinstance(PRODUCTS, list) else []
    except Exception as import_error:
        logger.warning(
            f"tools_page_products_empty reason=import_failed exception={type(import_error).__name__} error={str(import_error)}"
        )
        products = []
    return render_template('tools/index.html', products=products)

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
        
        # 同時実行数チェック（runningジョブ数で判定）
        running_count = count_running_jobs()
        if running_count > MAX_ACTIVE_SESSIONS:
            logger.error(f"max_sessions_exceeded running={running_count} limit={MAX_ACTIVE_SESSIONS}")
            return Response(f'max sessions exceeded: {running_count}/{MAX_ACTIVE_SESSIONS}', status=503, mimetype='text/plain')
        
        # リソース使用率をログに記録（詳細版）
        memory_usage_percent = (resources['memory_mb'] / MEMORY_LIMIT_MB) * 100
        logger.info(f"system_resources memory={resources['memory_mb']:.1f}MB/{MEMORY_LIMIT_MB}MB ({memory_usage_percent:.1f}%) cpu={resources['cpu_percent']:.1f}% running_jobs={running_count}/{MAX_ACTIVE_SESSIONS}")
        
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

@app.route('/health/memory', methods=['GET'])
def health_memory():
    """
    メモリ計測用エンドポイント（DEBUG時のみ有効、本番影響なし）
    ローカル/ステージング環境でメモリ使用状況を確認するためのエンドポイント
    """
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        rss_mb = memory_info.rss / 1024 / 1024
        vms_mb = memory_info.vms / 1024 / 1024
        
        # システム全体のメモリ情報も取得
        system_memory = psutil.virtual_memory()
        
        # ジョブとセッションの統計
        with jobs_lock:
            jobs_count = len(jobs)
            jobs_status = {}
            for job_id, job_info in jobs.items():
                status = job_info.get('status', 'unknown')
                jobs_status[status] = jobs_status.get(status, 0) + 1
        
        with session_manager['session_lock']:
            sessions_count = len(session_manager['active_sessions'])
        
        from diagnostics.runtime_metrics import get_browser_count
        browser_count = get_browser_count()
        
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'process_memory': {
                'rss_mb': round(rss_mb, 2),
                'vms_mb': round(vms_mb, 2),
                'percent': round(process.memory_percent(), 2)
            },
            'system_memory': {
                'total_mb': round(system_memory.total / 1024 / 1024, 2),
                'available_mb': round(system_memory.available / 1024 / 1024, 2),
                'used_mb': round(system_memory.used / 1024 / 1024, 2),
                'percent': round(system_memory.percent, 2)
            },
            'limits': {
                'memory_limit_mb': MEMORY_LIMIT_MB,
                'memory_warning_mb': MEMORY_WARNING_MB,
                'max_file_size_mb': MAX_FILE_SIZE_MB,
                'max_active_sessions': MAX_ACTIVE_SESSIONS
            },
            'resources': {
                'jobs_count': jobs_count,
                'jobs_by_status': jobs_status,
                'sessions_count': sessions_count,
                'browser_count': browser_count
            },
            'config': {
                'web_concurrency': os.getenv('WEB_CONCURRENCY', 'unknown'),
                'web_threads': os.getenv('WEB_THREADS', 'unknown'),
                'web_timeout': os.getenv('WEB_TIMEOUT', 'unknown')
            }
        })
    except ImportError:
        return jsonify({
            'status': 'error',
            'error': 'psutil not available'
        }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

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
        
        # P0-P1: メモリガード（新規ジョブ開始前チェック）。job_idは未生成のためログには含めない
        try:
            resources = get_system_resources()
            if resources['memory_mb'] > MEMORY_WARNING_MB:
                logger.warning(f"memory_guard_blocked memory_mb={resources['memory_mb']:.1f} warning_threshold={MEMORY_WARNING_MB}")
                return jsonify({
                    'error': f'メモリ使用量が高いため、現在新しい処理を開始できません。',
                    'message': f'現在のメモリ使用量: {resources["memory_mb"]:.1f}MB（警告閾値: {MEMORY_WARNING_MB}MB）',
                    'retry_after': 60,  # 60秒後にリトライを推奨
                    'status_code': 503
                }), 503
        except Exception as memory_check_error:
            # メモリチェックのエラーはログに記録するが、処理は続行（安全側に倒す）
            logger.error(f"memory_guard_check_error: {memory_check_error}")
            # エラー時は警告のみ（処理は継続）
        
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
        
        # P0-P1: ファイルアップロード直後のメモリ計測（重要イベント）
        if metrics_available:
            log_memory("upload_done", job_id=job_id, session_id=session_id, extra={
                'jobs_count': len(jobs),
                'sessions_count': len(session_manager['active_sessions'])
            })
        
        # 直列実行＋キュー: running が上限なら queued に積み、そうでなければ即 running で開始
        with jobs_lock:
            running_count = sum(1 for j in jobs.values() if j.get('status') == 'running')
            if running_count >= MAX_ACTIVE_SESSIONS:
                if len(job_queue) >= MAX_QUEUE_SIZE:
                    cleanup_user_session(session_id)
                    unregister_session(session_id)
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except Exception:
                            pass
                    return jsonify({
                        'error': 'キューが満杯です。しばらく待ってから再試行してください。',
                        'error_code': 'QUEUE_FULL',
                        'status_code': 503
                    }), 503
                # キューに登録
                jobs[job_id] = {
                    'status': 'queued',
                    'logs': deque(maxlen=MAX_JOB_LOGS),
                    'progress': 0,
                    'step_name': '待機中',
                    'current_data': 0,
                    'total_data': 0,
                    'start_time': time.time(),
                    'queued_at': time.time(),
                    'end_time': None,
                    'login_status': 'initializing',
                    'login_message': '現在、他ユーザーが作業中。順番に処理します。',
                    'session_id': session_id,
                    'session_dir': session_dir,
                    'file_path': file_path,
                    'email_hash': hash(email),
                    'company_id': company_id,
                    'resource_warnings': [],
                    'last_updated': time.time()
                }
                job_queue.append(job_id)
                queued_job_params[job_id] = {
                    'email': email,
                    'password': password,
                    'file_path': file_path,
                    'session_dir': session_dir,
                    'session_id': session_id,
                    'company_id': company_id,
                    'file_size': file_size
                }
                queue_position = len(job_queue)
                return jsonify({
                    'job_id': job_id,
                    'session_id': session_id,
                    'status': 'queued',
                    'queue_position': queue_position,
                    'message': '現在、他ユーザーが作業中です。順番に処理します。このまま開いておくと自動で開始します。',
                    'status_url': f'/status/{job_id}'
                }), 202
            
            # 即時開始
            jobs[job_id] = {
                'status': 'running',
                'logs': deque(maxlen=MAX_JOB_LOGS),
                'progress': 0,
                'step_name': 'initializing',
                'current_data': 0,
                'total_data': 0,
                'start_time': time.time(),
                'end_time': None,
                'login_status': 'initializing',
                'login_message': '🔄 処理を初期化中...',
                'session_id': session_id,
                'session_dir': session_dir,
                'file_path': file_path,
                'email_hash': hash(email),
                'company_id': company_id,
                'resource_warnings': [],
                'last_updated': time.time()
            }
        
        resource_warnings = check_resource_limits()
        if resource_warnings:
            print(f"リソース警告: {', '.join(resource_warnings)}")
        with jobs_lock:
            if job_id in jobs:
                jobs[job_id]['resource_warnings'] = resource_warnings
        
        thread = threading.Thread(
            target=run_automation_impl,
            args=(job_id, email, password, file_path, session_dir, session_id, company_id, file_size)
        )
        thread.daemon = True
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
            
            # P1: ログページングパラメータを取得
            last_n = request.args.get('last_n', type=int)
            if last_n is not None and (last_n < 1 or last_n > 1000):
                last_n = 1000  # 最大値に制限
            
            # P1: ログを取得（dequeの場合はlistに変換、ページング対応）
            job_logs = job.get('logs', [])
            from collections import deque
            if isinstance(job_logs, deque):
                job_logs = list(job_logs)
            elif not isinstance(job_logs, list):
                job_logs = list(job_logs) if job_logs else []
            
            # P1: ページング対応（最新last_n件のみ返す）
            if last_n is not None and len(job_logs) > last_n:
                job_logs = job_logs[-last_n:]
            
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
            
            # P0-4: 経過秒数を含める（止まった原因の切り分け用）
            start_ts = job.get('start_time') or 0
            elapsed_sec = round(time.time() - start_ts, 1) if start_ts else 0
            # queued のときキュー内位置を付与
            queue_position = None
            if job.get('status') == 'queued':
                try:
                    qlist = list(job_queue)
                    if job_id in qlist:
                        queue_position = 1 + qlist.index(job_id)
                except Exception:
                    pass
            response_data = {
                'status': job['status'],
                'progress': job.get('progress', 0),
                'step_name': job.get('step_name', ''),
                'current_data': job.get('current_data', 0),
                'total_data': job.get('total_data', 0),
                'logs': job_logs,
                'start_time': start_ts,
                'elapsed_sec': elapsed_sec,
                'login_status': login_status,
                'login_message': login_message,
                'user_message': user_message,
                'session_id': job.get('session_id', ''),
                'resources': resources,
                'resource_warnings': job.get('resource_warnings', [])
            }
            if queue_position is not None:
                response_data['queue_position'] = queue_position
            
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
    """ユーザー向けメッセージを生成（二重表示防止: processing時はlogin_messageが「ログイン処理中」系なら1文のみ返す）"""
    if status == 'running':
        if login_status == 'success':
            return f"✅ ログイン成功 - {login_message}"
        elif login_status == 'failed':
            return f"❌ ログイン失敗 - {login_message}"
        elif login_status == 'captcha':
            return f"🔄 画像認証が必要です - {login_message}"
        elif login_status == 'processing':
            # 監査対応: login_messageがすでに「ログイン処理中」系ならprefixを付けず重複を防ぐ
            if login_message and 'ログイン処理中' in (login_message or ''):
                return login_message.strip()
            return f"🔄 ログイン処理中... - {login_message}" if login_message else "🔄 ログイン処理中..."
        else:
            return f"🔄 処理中... - {login_message}" if login_message else "🔄 処理中..."
    elif status == 'completed':
        return "✅ 処理完了 勤怠データの入力が完了しました。"
    elif status == 'error':
        return f"❌ エラーが発生しました: {login_message}"
    elif status == 'timeout':
        return f"⏱ タイムアウト - {login_message}" if login_message else "⏱ 処理が時間切れになりました"
    elif status == 'queued':
        return login_message or "現在、他ユーザーが作業中。順番に処理します。"
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
    """XMLサイトマップを動的生成（P0-1: PRODUCTSから自動生成）"""
    from flask import url_for
    from datetime import datetime
    
    # PRODUCTSのインポート（失敗しても続行）
    try:
        from lib.routes import PRODUCTS
    except Exception as import_error:
        logger.warning(f"sitemap_import_failed error={str(import_error)} - using empty list")
        PRODUCTS = []
    
    # ベースURL
    base_url = 'https://jobcan-automation.onrender.com'
    
    # 現在日付を取得（P1: lastmodを動的に設定）
    today = datetime.now().strftime('%Y-%m-%d')
    
    # サイトマップに含めるURLのリスト
    # 形式: (url_path, changefreq, priority, lastmod)
    # P0-1: 固定ページは維持
    urls = [
        # 主要ページ
        ('/', 'daily', '1.0', today),
        ('/autofill', 'daily', '1.0', today),
        ('/about', 'monthly', '0.9', today),
        ('/contact', 'monthly', '0.8', today),
        ('/privacy', 'yearly', '0.5', today),
        ('/terms', 'yearly', '0.5', today),
        ('/faq', 'weekly', '0.8', today),
        ('/glossary', 'monthly', '0.6', today),
        ('/best-practices', 'monthly', '0.8', today),
        ('/sitemap.html', 'monthly', '0.5', today),
        
        # ガイドページ（一覧＋固定）
        ('/guide', 'weekly', '0.9', today),
        ('/guide/autofill', 'weekly', '0.9', today),
        ('/guide/complete', 'weekly', '0.9', today),
        ('/guide/comprehensive-guide', 'weekly', '0.9', today),
        ('/guide/getting-started', 'weekly', '0.9', today),
        ('/guide/excel-format', 'weekly', '0.9', today),
        ('/guide/troubleshooting', 'weekly', '0.8', today),
        
        # ツール一覧ページ
        ('/tools', 'weekly', '0.9', today),
        
        # ブログ一覧
        ('/blog', 'daily', '0.8', today),
        
        # ブログ記事（固定リストを維持）
        ('/blog/implementation-checklist', 'monthly', '0.7', today),
        ('/blog/automation-roadmap', 'monthly', '0.7', today),
        ('/blog/workstyle-reform-automation', 'monthly', '0.7', today),
        ('/blog/excel-attendance-limits', 'monthly', '0.7', today),
        ('/blog/playwright-security', 'monthly', '0.7', today),
        ('/blog/month-end-closing-hell-and-automation', 'monthly', '0.7', today),
        ('/blog/excel-format-mistakes-and-design', 'monthly', '0.7', today),
        ('/blog/convince-it-and-hr-for-automation', 'monthly', '0.7', today),
        ('/blog/playwright-jobcan-challenges-and-solutions', 'monthly', '0.7', today),
        ('/blog/jobcan-auto-input-tools-overview', 'monthly', '0.7', today),
        ('/blog/reduce-manual-work-checklist', 'monthly', '0.7', today),
        ('/blog/jobcan-month-end-tips', 'monthly', '0.7', today),
        ('/blog/jobcan-auto-input-dos-and-donts', 'monthly', '0.7', today),
        ('/blog/month-end-closing-checklist', 'monthly', '0.7', today),
        
        # 導入事例（固定リストを維持）
        ('/case-study/contact-center', 'monthly', '0.8', today),
        ('/case-study/consulting-firm', 'monthly', '0.8', today),
        ('/case-study/remote-startup', 'monthly', '0.8', today),
    ]
    
    # P0-1: PRODUCTSから利用可能なツールページとガイドページを自動生成
    # URL重複を防ぐために、既存のURLパスを集合で管理
    seen_urls = {url_path for url_path, _, _, _ in urls}
    
    # PRODUCTSがリストであることを確認（恒久対策：型安全性）
    products_list = PRODUCTS if isinstance(PRODUCTS, list) else []
    for product in products_list:
        if product.get('status') == 'available':
            # product.pathを追加（重複チェック）
            product_path = product.get('path')
            if product_path and product_path not in seen_urls:
                # ツールページの優先度と更新頻度を設定
                changefreq = 'monthly'
                priority = '0.7'
                urls.append((product_path, changefreq, priority, today))
                seen_urls.add(product_path)
            
            # guide_pathを追加（重複チェック）
            guide_path = product.get('guide_path')
            if guide_path and guide_path not in seen_urls:
                urls.append((guide_path, 'monthly', '0.8', today))
                seen_urls.add(guide_path)
    
    # XMLサイトマップを生成
    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    
    for url_path, changefreq, priority, lastmod in urls:
        # 末尾スラッシュなしの方針を維持（既に末尾スラッシュなしで定義済み）
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
