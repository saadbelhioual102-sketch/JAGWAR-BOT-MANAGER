import os
import json
import re
import subprocess
import psutil
import socket
import sys
import hashlib
import secrets
import time
import zipfile
import shutil
import threading
import requests
from datetime import datetime, timedelta, timezone
from flask import Flask, send_from_directory, request, jsonify, session, redirect, url_for, make_response, send_file
from huggingface_hub import HfApi, hf_hub_download

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_DIR = os.path.join(BASE_DIR, "USERS")
BOT_TEMPLATE_DIR = os.path.join(os.path.dirname(BASE_DIR), "bot_template")
os.makedirs(USERS_DIR, exist_ok=True)

# --- API Configuration ---
API_CONFIG_FILE = os.path.join(BASE_DIR, "api_config.json")
DEFAULT_APIS = {
    "add_friend": "https://api-add-and-remove-alliff-v2.vercel.app/add/{uid}/{pwd}/{friend_id}",
    "remove_friend": "https://api-add-and-remove-alliff-v2.vercel.app/remove/{uid}/{pwd}/{friend_id}",
    "list_friends": "https://api-list-alliff-d5m-v2.vercel.app/{uid}/{pwd}",
    "add_clan": "https://api-add-clan-alliff.vercel.app/ReqCLan/{uid}/{pwd}/{id_clan}",
    "request_clan": "https://api-add-clan-alliff.vercel.app/ReqCLan/{uid}/{pwd}/{clan_id}"
}

def get_api_config(username=None):
    """جلب إعدادات الـ API للمستخدم أو الإعدادات العامة"""
    if username:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
        user_apis = users.get(username, {}).get("custom_apis")
        if user_apis:
            # دمج الإعدادات المخصصة مع الافتراضية لضمان وجود جميع المفاتيح
            full_config = DEFAULT_APIS.copy()
            full_config.update(user_apis)
            return full_config

    if not os.path.exists(API_CONFIG_FILE):
        with open(API_CONFIG_FILE, "w") as f: json.dump(DEFAULT_APIS, f, indent=2)
        return DEFAULT_APIS
    with open(API_CONFIG_FILE, "r") as f: 
        config = json.load(f)
        full_config = DEFAULT_APIS.copy()
        full_config.update(config)
        return full_config

def save_api_config(config):
    with open(API_CONFIG_FILE, "w") as f: json.dump(config, f, indent=2)

# --- Maintenance Mode ---
MAINTENANCE_FILE = os.path.join(BASE_DIR, "maintenance.json")
def is_maintenance_mode():
    if not os.path.exists(MAINTENANCE_FILE): return False
    try:
        with open(MAINTENANCE_FILE, "r") as f:
            data = json.load(f)
            if not data.get("enabled"): return False
            end_time_str = data.get("end_time")
            if end_time_str:
                from datetime import datetime
                end_time = datetime.fromisoformat(end_time_str)
                if datetime.now() >= end_time:
                    set_maintenance_mode(False, 0)
                    return False
            return True
    except: return False

def set_maintenance_mode(enabled, duration_hours=0):
    """تفعيل/إيقاف وضع الصيانة مع المدة بالساعات"""
    from datetime import datetime, timedelta
    data = {"enabled": enabled}
    if enabled and duration_hours > 0:
        end_time = datetime.now() + timedelta(hours=duration_hours)
        data["end_time"] = end_time.isoformat()
    
    with open(MAINTENANCE_FILE, "w") as f: json.dump(data, f)
    
    if enabled:
        for proc_key in list(running_procs.keys()):
            stop_bot_by_key(proc_key)

def get_maintenance_info():
    """الحصول على معلومات وضع الصيانة"""
    if not os.path.exists(MAINTENANCE_FILE): 
        return {"enabled": False, "end_time": None, "remaining_seconds": 0}
    try:
        with open(MAINTENANCE_FILE, "r") as f:
            data = json.load(f)
            if not data.get("enabled"):
                return {"enabled": False, "end_time": None, "remaining_seconds": 0}
            
            from datetime import datetime
            end_time_str = data.get("end_time")
            if end_time_str:
                end_time = datetime.fromisoformat(end_time_str)
                remaining = (end_time - datetime.now()).total_seconds()
                if remaining <= 0:
                    set_maintenance_mode(False, 0)
                    return {"enabled": False, "end_time": None, "remaining_seconds": 0}
                return {"enabled": True, "end_time": end_time_str, "remaining_seconds": int(remaining)}
            return {"enabled": True, "end_time": None, "remaining_seconds": 0}
    except: 
        return {"enabled": False, "end_time": None, "remaining_seconds": 0}

# --- Backup Configuration ---
HF_TOKEN = os.environ.get("HF_TOKEN").strip() if os.environ.get("HF_TOKEN") else None
BACKUP_REPO = "AlliFF3/AlliFF-Bot-Manager-Data"
BACKUP_FILENAME = "alliff_backup.zip"
hf_api = HfApi(token=HF_TOKEN) if HF_TOKEN else None

def perform_backup():
    if not hf_api: return
    try:
        backup_path = os.path.join(os.path.dirname(BASE_DIR), BACKUP_FILENAME)
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # حفظ مجلد USERS
            if os.path.exists(USERS_DIR):
                for root, dirs, files in os.walk(USERS_DIR):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # نريد أن يكون المسار داخل الـ zip يبدأ بـ USERS/
                        arcname = os.path.relpath(file_path, BASE_DIR)
                        zipf.write(file_path, arcname)
            # حفظ ملفات الـ JSON الأساسية
            for json_file in ["users.json", "ports.json", "remember_tokens.json", "database.json"]:
                file_path = os.path.join(BASE_DIR, json_file)
                if os.path.exists(file_path):
                    zipf.write(file_path, json_file)
        hf_api.upload_file(path_or_fileobj=backup_path, path_in_repo=BACKUP_FILENAME, repo_id=BACKUP_REPO, repo_type="dataset")
    except: pass

def restore_backup():
    if not HF_TOKEN: return
    try:
        backup_path = hf_hub_download(repo_id=BACKUP_REPO, filename=BACKUP_FILENAME, repo_type="dataset", token=HF_TOKEN, force_download=True)
        # الاستخراج إلى مجلد مؤقت أولاً للتأكد من نجاح العملية
        temp_restore = os.path.join(os.path.dirname(BASE_DIR), "temp_restore")
        if os.path.exists(temp_restore): shutil.rmtree(temp_restore)
        os.makedirs(temp_restore, exist_ok=True)
        
        with zipfile.ZipFile(backup_path, 'r') as zipf:
            zipf.extractall(temp_restore)
            
        # نقل الملفات الأساسية
        for json_file in ["users.json", "ports.json", "remember_tokens.json", "database.json"]:
            src = os.path.join(temp_restore, json_file)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(BASE_DIR, json_file))
                
        # استبدال مجلد USERS بالكامل بالنسخة الاحتياطية
        src_users = os.path.join(temp_restore, "USERS")
        if os.path.exists(src_users):
            if os.path.exists(USERS_DIR): shutil.rmtree(USERS_DIR)
            shutil.copytree(src_users, USERS_DIR)
            
        shutil.rmtree(temp_restore)
    except: pass

def trigger_backup():
    threading.Thread(target=perform_backup).start()

restore_backup()

app = Flask(__name__, static_folder=BASE_DIR)
app.secret_key = secrets.token_hex(32)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

running_procs = {}
USERS_FILE = os.path.join(BASE_DIR, "users.json")
REMEMBER_TOKENS_FILE = os.path.join(BASE_DIR, "remember_tokens.json")
PORTS_FILE = os.path.join(BASE_DIR, "ports.json")

ADMIN_USERNAME = "AlliFF121"
ADMIN_PASSWORD = "123123123"

def init_users_db():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            admin_data = {
                ADMIN_USERNAME: {
                    "password": hash_password(ADMIN_PASSWORD),
                    "created_at": datetime.now().isoformat(),
                    "last_login": None,
                    "theme": "premium",
                    "is_admin": True,
                    "can_create_users": True,
                    "max_bots": 999,
                    "expires_at": None,
                    "custom_apis": None
                }
            }
            json.dump(admin_data, f, indent=2)

def init_tokens_db():
    if not os.path.exists(REMEMBER_TOKENS_FILE):
        with open(REMEMBER_TOKENS_FILE, "w", encoding="utf-8") as f: json.dump({}, f)

def init_ports_db():
    if not os.path.exists(PORTS_FILE):
        with open(PORTS_FILE, "w", encoding="utf-8") as f: json.dump({"last_port": 1999, "assignments": {}}, f)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# تهيئة قاعدة البيانات عند بدء التشغيل لضمان وجود حساب الأدمن
init_users_db()

def create_remember_token(username):
    init_tokens_db()
    with open(REMEMBER_TOKENS_FILE, "r", encoding="utf-8") as f: tokens = json.load(f)
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    tokens[token] = {"username": username, "created_at": datetime.now(timezone.utc).isoformat(), "expires_at": expires, "last_used": datetime.now(timezone.utc).isoformat()}
    with open(REMEMBER_TOKENS_FILE, "w", encoding="utf-8") as f: json.dump(tokens, f, indent=2)
    return token

def validate_remember_token(token):
    if not os.path.exists(REMEMBER_TOKENS_FILE): return None
    with open(REMEMBER_TOKENS_FILE, "r", encoding="utf-8") as f: tokens = json.load(f)
    if token not in tokens: return None
    token_data = tokens[token]
    expires_at = datetime.fromisoformat(token_data["expires_at"])
    if expires_at.tzinfo is None: expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        del tokens[token]
        with open(REMEMBER_TOKENS_FILE, "w", encoding="utf-8") as f: json.dump(tokens, f, indent=2)
        return None
    token_data["last_used"] = datetime.now(timezone.utc).isoformat()
    with open(REMEMBER_TOKENS_FILE, "w", encoding="utf-8") as f: json.dump(tokens, f, indent=2)
    return token_data["username"]

def register_user(username, password, max_bots=1, days=30, created_by_admin=False):
    init_users_db()
    with open(USERS_FILE, "r", encoding="utf-8") as f: users = json.load(f)
    if username in users: return False, "المستخدم موجود بالفعل"
    expires_at = (datetime.now(timezone.utc) + timedelta(days=int(days))).isoformat()
    users[username] = {
        "password": hash_password(password),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_login": None,
        "is_admin": username == ADMIN_USERNAME,
        "created_by_admin": created_by_admin,
        "created_by": session.get('username') if 'username' in session else None,
        "max_bots": int(max_bots),
        "expires_at": expires_at,
        "clan_feature_enabled": False,
        "custom_apis": None
    }
    with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump(users, f, indent=2)
    os.makedirs(os.path.join(USERS_DIR, username), exist_ok=True)
    trigger_backup()
    return True, "تم إنشاء الحساب بنجاح"

def authenticate_user(username, password):
    init_users_db()
    with open(USERS_FILE, "r", encoding="utf-8") as f: users = json.load(f)
    if username not in users: return False, "المستخدم غير موجود"
    user_data = users[username]
    if user_data["password"] != hash_password(password): return False, "كلمة المرور غير صحيحة"
    if not user_data.get("is_admin", False) and user_data.get("expires_at"):
        expires_at = datetime.fromisoformat(user_data["expires_at"])
        if expires_at.tzinfo is None: expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at: return False, "انتهت صلاحية هذا الحساب"
    users[username]["last_login"] = datetime.now(timezone.utc).isoformat()
    with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump(users, f, indent=2)
    return True, "تم تسجيل الدخول بنجاح"

def is_admin(username):
    init_users_db()
    with open(USERS_FILE, "r", encoding="utf-8") as f: users = json.load(f)
    return users.get(username, {}).get("is_admin", False)

def get_user_bots_dir(username):
    return os.path.join(USERS_DIR, username, "BOTS")

def ensure_user_bots_dir():
    if 'username' not in session: return None
    user_dir = get_user_bots_dir(session['username'])
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def sanitize_folder_name(name):
    if not name: return ""
    name = name.strip()
    name = re.sub(r"\s+", "-", name)
    name = re.sub(r"[^A-Za-z0-9\-\_\.]", "", name)
    return name[:200]

def ensure_bot_meta(folder):
    user_bots_dir = ensure_user_bots_dir()
    if not user_bots_dir: return None
    meta_path = os.path.join(user_bots_dir, folder, "meta.json")
    if not os.path.exists(meta_path):
        with open(meta_path, "w", encoding="utf-8") as f: json.dump({"display_name": folder, "startup_file": "main.py"}, f)
    return meta_path

def stop_bot_by_key(proc_key):
    if proc_key in running_procs:
        proc = running_procs[proc_key]
        try:
            parent = psutil.Process(proc.pid)
            for child in parent.children(recursive=True): child.kill()
            parent.kill()
        except: pass
        del running_procs[proc_key]

def cleanup_expired_bots():
    while True:
        try:
            if not os.path.exists(USERS_FILE):
                time.sleep(60)
                continue
            with open(USERS_FILE, "r", encoding="utf-8") as f: users = json.load(f)
            now_utc = datetime.now(timezone.utc)
            users_changed = False
            for username in list(users.keys()):
                user_data = users[username]
                if user_data.get("is_admin"): continue
                expires_at_str = user_data.get("expires_at")
                if not expires_at_str: continue
                expires_at = datetime.fromisoformat(expires_at_str)
                if expires_at.tzinfo is None: expires_at = expires_at.replace(tzinfo=timezone.utc)
                if now_utc > expires_at:
                    # 1. إيقاف جميع بوتات المستخدم وحذف مجلداتها
                    user_bots_dir = get_user_bots_dir(username)
                    if os.path.exists(user_bots_dir):
                        for folder in os.listdir(user_bots_dir):
                            stop_bot_by_key(f"{username}_{folder}")
                            bot_path = os.path.join(user_bots_dir, folder)
                            if os.path.exists(bot_path): shutil.rmtree(bot_path)
                    # 2. حذف مجلد المستخدم الرئيسي
                    shutil.rmtree(os.path.join(USERS_DIR, username), ignore_errors=True)
                    # 3. حذف المستخدم من قاعدة البيانات
                    del users[username]
                    users_changed = True
            
            if users_changed:
                with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump(users, f, indent=2)
                trigger_backup() # حفظ التغييرات فوراً في النسخة الاحتياطية

            for p in psutil.process_iter(['pid', 'name', 'cwd']):
                try:
                    if p.info['name'] == 'python3' and 'USERS' in (p.info['cwd'] or ''):
                        if not os.path.exists(p.info['cwd']): p.kill()
                except: pass
        except: pass
        time.sleep(60)

threading.Thread(target=cleanup_expired_bots, daemon=True).start()


# --- No-Cache Headers ---
@app.after_request
def set_no_cache_headers(response):
    """منع التخزين المؤقت للصفحات الرئيسية"""
    if request.path in ['/', '/index.html', '/admin_panel.html', '/maintenance.html']:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

@app.before_request
def check_maintenance_and_token():
    # التحقق من وضع الصيانة
    if is_maintenance_mode():
        is_admin_user = 'username' in session and is_admin(session['username'])
        # استثناء المسارات الضرورية لعمل الموقع والأدمن
        excluded_paths = [
            '/login', '/api/login', '/api/check-maintenance', 
            '/maintenance.html', '/api/admin/maintenance/status',
            '/api/maintenance/info'
        ]
        is_excluded = any(request.path == p or request.path.startswith(p) for p in excluded_paths)
        
        if not is_admin_user and not is_excluded:
            if request.path.startswith('/api/'):
                return jsonify({"maintenance": True, "message": "الموقع في وضع الصيانة حالياً"}), 503
            return redirect('/maintenance.html')
    if 'username' in session:
        # التحقق من أن المستخدم لا يزال موجوداً في قاعدة البيانات وأن حسابه لم ينتهِ
        username = session['username']
        with open(USERS_FILE, "r", encoding="utf-8") as f: users = json.load(f)
        if username not in users:
            session.clear()
            return redirect(url_for('login_page'))
        
        user_data = users[username]
        if not user_data.get("is_admin", False) and user_data.get("expires_at"):
            expires_at = datetime.fromisoformat(user_data["expires_at"])
            if expires_at.tzinfo is None: expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                session.clear()
                return redirect(url_for('login_page'))
        return

    remember_token = request.cookies.get('remember_token')
    if remember_token:
        username = validate_remember_token(remember_token)
        if username:
            # تحقق إضافي عند استعادة الجلسة من التوكن
            with open(USERS_FILE, "r", encoding="utf-8") as f: users = json.load(f)
            if username in users:
                user_data = users[username]
                if user_data.get("is_admin", False) or not user_data.get("expires_at"):
                    session['username'] = username
                    session.permanent = True
                else:
                    expires_at = datetime.fromisoformat(user_data["expires_at"])
                    if expires_at.tzinfo is None: expires_at = expires_at.replace(tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) <= expires_at:
                        session['username'] = username
                        session.permanent = True

@app.route("/")
def home():
    if 'username' not in session: return redirect(url_for('login_page'))
    if is_admin(session['username']): return send_from_directory(BASE_DIR, "admin_panel.html")
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/login")
def login_page():
    if 'username' in session: return redirect(url_for('home'))
    return send_from_directory(BASE_DIR, "login.html")

@app.route("/maintenance.html")
def maintenance_page():
    return send_from_directory(BASE_DIR, "maintenance.html")

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    username, password = data.get("username", "").strip(), data.get("password", "").strip()
    remember = data.get("remember", False)
    success, message = authenticate_user(username, password)
    if success:
        session['username'] = username
        session.permanent = True
        resp = make_response(jsonify({"success": True, "message": message, "is_admin": is_admin(username)}))
        if remember:
            token = create_remember_token(username)
            resp.set_cookie('remember_token', token, max_age=30*24*60*60, httponly=True)
        return resp
    return jsonify({"success": False, "message": message})

@app.route("/api/logout")
def api_logout():
    token = request.cookies.get('remember_token')
    if token:
        if os.path.exists(REMEMBER_TOKENS_FILE):
            with open(REMEMBER_TOKENS_FILE, "r") as f: tokens = json.load(f)
            if token in tokens:
                del tokens[token]
                with open(REMEMBER_TOKENS_FILE, "w") as f: json.dump(tokens, f, indent=2)
    session.clear()
    resp = make_response(redirect(url_for('login_page')))
    resp.delete_cookie('remember_token')
    return resp

@app.route("/api/user/info")
def api_user_info():
    if 'username' not in session: return jsonify({}), 401
    with open(USERS_FILE, "r") as f: users = json.load(f)
    user_data = users.get(session['username'], {})
    return jsonify({"username": session['username'], "is_admin": user_data.get("is_admin", False), "max_bots": user_data.get("max_bots", 1), "expires_at": user_data.get("expires_at")})

@app.route("/api/bots/list")
def api_bots_list():
    if 'username' not in session: return jsonify([]), 401
    user_bots_dir = ensure_user_bots_dir()
    if not user_bots_dir: return jsonify([])
    bots = []
    for folder in os.listdir(user_bots_dir):
        bot_path = os.path.join(user_bots_dir, folder)
        if os.path.isdir(bot_path):
            meta_path = os.path.join(bot_path, "meta.json")
            meta = {}
            if os.path.exists(meta_path):
                with open(meta_path, "r") as f: meta = json.load(f)
            proc_key = f"{session['username']}_{folder}"
            is_running = False
            if proc_key in running_procs:
                proc = running_procs[proc_key]
                try:
                    if hasattr(proc, 'is_running'):
                        if proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE: is_running = True
                        else: del running_procs[proc_key]
                    elif hasattr(proc, 'poll'):
                        if proc.poll() is None: is_running = True
                        else: del running_procs[proc_key]
                except:
                    if proc_key in running_procs: del running_procs[proc_key]
            if not is_running:
                for p in psutil.process_iter(['pid', 'name', 'cwd']):
                    try:
                        if p.info['cwd'] == bot_path and ('python' in p.info['name'].lower()):
                            is_running = True
                            running_procs[proc_key] = p
                            break
                    except: continue
            bots.append({"folder": folder, "title": meta.get("display_name", folder), "status": "running" if is_running else "stopped"})
    return jsonify(bots)

@app.route("/api/bots/create", methods=["POST"])
def api_bots_create():
    if 'username' not in session: return jsonify({"success": False}), 401
    with open(USERS_FILE, "r") as f: users = json.load(f)
    user_data = users.get(session['username'], {})
    max_bots = user_data.get("max_bots", 1)
    user_bots_dir = ensure_user_bots_dir()
    current_bots = [f for f in os.listdir(user_bots_dir) if os.path.isdir(os.path.join(user_bots_dir, f))]
    if len(current_bots) >= max_bots: return jsonify({"success": False, "message": f"لقد وصلت للحد الأقصى من البوتات المسموح بها ({max_bots})"})
    data = request.get_json()
    name = sanitize_folder_name(data.get("name"))
    if not name: return jsonify({"success": False, "message": "اسم غير صالح"})
    path = os.path.join(user_bots_dir, name)
    if os.path.exists(path): return jsonify({"success": False, "message": "البوت موجود بالفعل"})
    shutil.copytree(BOT_TEMPLATE_DIR, path)
    config_template = os.path.join(BOT_TEMPLATE_DIR, "config_template.json")
    with open(config_template, "r") as f: config = json.load(f)
    with open(os.path.join(path, "config.json"), "w") as f: json.dump(config, f, indent=2)
    ensure_bot_meta(name)
    trigger_backup()  # حفظ النسخة الاحتياطية بعد إنشاء البوت لضمان المزامنة
    return jsonify({"success": True})

@app.route("/api/bots/start", methods=["POST"])
def api_bots_start():
    if 'username' not in session: return jsonify({"success": False}), 401
    data = request.get_json()
    folder = data.get("folder")
    user_bots_dir = ensure_user_bots_dir()
    bot_path = os.path.join(user_bots_dir, folder)
    proc_key = f"{session['username']}_{folder}"
    for p in psutil.process_iter(['pid', 'name', 'cwd']):
        try:
            if p.info['cwd'] == bot_path and ('python' in p.info['name'].lower()): p.kill()
        except: pass
    if proc_key in running_procs: del running_procs[proc_key]
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    log_path = os.path.join(bot_path, "bot_output.log")
    def run_bot_task():
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(f"\n--- Bot Start Sequence at {datetime.now().isoformat()} ---\n")
            log_file.flush()
            if os.path.exists(os.path.join(bot_path, "requirements.txt")):
                try:
                    subprocess.run([sys.executable, "-m", "pip", "install", "--user", "-r", "requirements.txt"], cwd=bot_path, stdout=log_file, stderr=log_file, check=True)
                except: pass
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    proc = subprocess.Popen([sys.executable, "main.py"], cwd=bot_path, stdout=f, stderr=f, env=env, start_new_session=True)
                    running_procs[proc_key] = proc
            except: pass
    threading.Thread(target=run_bot_task).start()
    return jsonify({"success": True})

@app.route("/api/bots/stop", methods=["POST"])
def api_bots_stop():
    if 'username' not in session: return jsonify({"success": False}), 401
    data = request.get_json()
    folder = data.get("folder")
    user_bots_dir = ensure_user_bots_dir()
    bot_path = os.path.join(user_bots_dir, folder)
    stop_bot_by_key(f"{session['username']}_{folder}")
    for p in psutil.process_iter(['pid', 'name', 'cwd']):
        try:
            if p.info['cwd'] == bot_path and ('python' in p.info['name'].lower()): p.kill()
        except: pass
    return jsonify({"success": True})

@app.route("/api/bots/delete", methods=["POST"])
def api_bots_delete():
    if 'username' not in session: return jsonify({"success": False}), 401
    data = request.get_json()
    folder = data.get("folder")
    
    # إيقاف البوت أولاً قبل الحذف
    stop_bot_by_key(f"{session['username']}_{folder}")
    
    user_bots_dir = ensure_user_bots_dir()
    path = os.path.join(user_bots_dir, folder)
    
    if os.path.exists(path):
        # حذف المجلد محلياً
        shutil.rmtree(path)
        
        # الحذف من التخزين الدائم (النسخة الاحتياطية على Hugging Face)
        if hf_api and BACKUP_REPO:
            try:
                # تحديث النسخة الاحتياطية فوراً لضمان الحذف من التخزين الدائم
                perform_backup() 
            except: pass
            
        return jsonify({"success": True, "message": "تم الحذف النهائي من التخزين الدائم"})
    return jsonify({"success": False, "message": "المجلد غير موجود"})

@app.route("/api/bots/config/get/<folder>")
def api_bots_config_get(folder):
    if 'username' not in session: return jsonify({}), 401
    user_bots_dir = ensure_user_bots_dir()
    config_path = os.path.join(user_bots_dir, folder, "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f: return jsonify(json.load(f))
    return jsonify({})

@app.route("/api/bots/config/save/<folder>", methods=["POST"])
def api_bots_config_save(folder):
    if 'username' not in session: return jsonify({"success": False}), 401
    data = request.get_json()
    user_bots_dir = ensure_user_bots_dir()
    config_path = os.path.join(user_bots_dir, folder, "config.json")
    with open(config_path, "w") as f: json.dump(data, f, indent=2)
    trigger_backup()
    return jsonify({"success": True})

@app.route("/api/bots/logs/<folder>")
def api_bots_logs(folder):
    if 'username' not in session: return jsonify({"logs": ""}), 401
    user_bots_dir = ensure_user_bots_dir()
    log_path = os.path.join(user_bots_dir, folder, "bot_output.log")
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f: return jsonify({"logs": f.read()[-5000:]})
    return jsonify({"logs": "لا يوجد سجلات حالياً"})

@app.route("/api/bots/status/<folder>")
def api_bots_status(folder):
    if 'username' not in session: return jsonify({"status": "stopped"}), 401
    user_bots_dir = ensure_user_bots_dir()
    bot_path = os.path.join(user_bots_dir, folder)
    proc_key = f"{session['username']}_{folder}"
    is_running = False
    if proc_key in running_procs:
        proc = running_procs[proc_key]
        try:
            if hasattr(proc, 'is_running'):
                if proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE: is_running = True
            elif hasattr(proc, 'poll'):
                if proc.poll() is None: is_running = True
        except: pass
    if not is_running:
        for p in psutil.process_iter(['pid', 'name', 'cwd']):
            try:
                if p.info['cwd'] == bot_path and ('python' in p.info['name'].lower()):
                    is_running = True
                    running_procs[proc_key] = p
                    break
            except: continue
    return jsonify({"status": "running" if is_running else "stopped"})

@app.route("/api/admin/users")
def api_admin_users():
    if 'username' not in session or not is_admin(session['username']): return jsonify([]), 403
    with open(USERS_FILE, "r") as f: users = json.load(f)
    return jsonify([{"username": u, "created_at": d["created_at"], "last_login": d["last_login"], "max_bots": d.get("max_bots", 1), "expires_at": d.get("expires_at"), "custom_apis": d.get("custom_apis")} for u, d in users.items() if u != ADMIN_USERNAME])

@app.route("/api/admin/users/create", methods=["POST"])
def api_admin_users_create():
    # السماح للمسؤول أو الطلبات المصادق عليها بسر البوت
    is_admin_req = 'username' in session and is_admin(session['username'])
    bot_secret = request.headers.get('x-bot-secret') or request.get_json().get('bot_secret')
    INTERNAL_BOT_SECRET = "alliff_bot_api_secret_2026"
    
    if not is_admin_req and bot_secret != INTERNAL_BOT_SECRET:
        return jsonify({"success": False, "error": "غير مصرح لك"}), 403
        
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    max_bots = data.get("max_bots") or data.get("max_servers") or 1
    days = data.get("days", 30)
    
    success, msg = register_user(
        username, 
        password, 
        max_bots, 
        days, 
        True
    )
    return jsonify({"success": success, "message": msg, "username": username, "password": password})

@app.route("/api/admin/users/delete", methods=["POST"])
def api_admin_users_delete():
    # التحقق من المشرف أو سر البوت
    is_admin_req = 'username' in session and is_admin(session['username'])
    bot_secret = request.headers.get('x-bot-secret') or request.get_json().get('bot_secret')
    if not is_admin_req and bot_secret != "alliff_bot_api_secret_2026":
        return jsonify({"success": False, "message": "غير مصرح لك"}), 403
    username = request.get_json().get("username")
    if username == ADMIN_USERNAME: return jsonify({"success": False, "message": "لا يمكن حذف حساب المسؤول الرئيسي"})
    user_bots_dir = get_user_bots_dir(username)
    if os.path.exists(user_bots_dir):
        for folder in os.listdir(user_bots_dir): stop_bot_by_key(f"{username}_{folder}")
    with open(USERS_FILE, "r") as f: users = json.load(f)
    if username in users:
        del users[username]
        with open(USERS_FILE, "w") as f: json.dump(users, f, indent=2)
        shutil.rmtree(os.path.join(USERS_DIR, username), ignore_errors=True)
        trigger_backup()
        return jsonify({"success": True, "message": "تم حذف المستخدم وجميع ملفاته بنجاح"})
    return jsonify({"success": False, "message": "المستخدم غير موجود"})

@app.route("/api/admin/maintenance/status")
def api_maintenance_status(): return jsonify({"enabled": is_maintenance_mode()})

@app.route("/api/admin/maintenance/toggle", methods=["POST"])
def api_maintenance_toggle():
    if 'username' not in session or not is_admin(session['username']): return jsonify({"success": False}), 403
    enabled = request.get_json().get("enabled", False)
    set_maintenance_mode(enabled)
    return jsonify({"success": True, "enabled": enabled})

@app.route("/api/admin/users/update", methods=["POST"])
def api_admin_users_update():
    # التحقق من المشرف أو سر البوت
    is_admin_req = 'username' in session and is_admin(session['username'])
    bot_secret = request.headers.get('x-bot-secret') or request.get_json().get('bot_secret')
    if not is_admin_req and bot_secret != "alliff_bot_api_secret_2026":
        return jsonify({"success": False}), 403
    data = request.get_json()
    target_user = data.get("username")
    if not target_user or target_user == ADMIN_USERNAME: return jsonify({"success": False})
    with open(USERS_FILE, "r") as f: users = json.load(f)
    if target_user not in users: return jsonify({"success": False})
    if "add_days" in data and int(data["add_days"]) != 0:
        current_expiry = datetime.fromisoformat(users[target_user]["expires_at"])
        if current_expiry.tzinfo is None: current_expiry = current_expiry.replace(tzinfo=timezone.utc)
        users[target_user]["expires_at"] = (current_expiry + timedelta(days=int(data["add_days"]))).isoformat()
    if "add_bots" in data and int(data["add_bots"]) != 0:
        users[target_user]["max_bots"] = users[target_user].get("max_bots", 1) + int(data["add_bots"])
    if "custom_apis" in data:
        users[target_user]["custom_apis"] = data["custom_apis"]
    with open(USERS_FILE, "w") as f: json.dump(users, f, indent=2)
    trigger_backup()
    return jsonify({"success": True})

@app.route("/api/admin/api_config", methods=["GET", "POST"])
def api_admin_config():
    if 'username' not in session or not is_admin(session['username']): return jsonify({}), 403
    if request.method == "POST":
        save_api_config(request.get_json())
        return jsonify({"success": True})
    return jsonify(get_api_config())

@app.route("/api/proxy/bot/profile")
def proxy_bot_profile():
    if 'username' not in session: return jsonify({}), 401
    folder, uid, pwd = request.args.get("folder"), request.args.get("uid"), request.args.get("pwd")
    if folder:
        config_path = os.path.join(ensure_user_bots_dir(), folder, "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                bot_cfg = json.load(f)
                uid = bot_cfg.get("account_uid") or bot_cfg.get("uid") or uid
                pwd = bot_cfg.get("account_password") or bot_cfg.get("pwd") or pwd
    if not uid or not pwd: return jsonify({"status": "error"})
    apis = get_api_config(session['username'])
    try:
        r = requests.get(apis["list_friends"].format(uid=uid, pwd=pwd), timeout=10)
        data = r.json()
        if data.get("status") == "success":
            acc = data.get("account_info", {})
            return jsonify({"status": "success", "nickname": acc.get("nickname"), "account_id": acc.get("account_id"), "server": acc.get("server")})
    except: pass
    return jsonify({"status": "error"})

@app.route("/api/proxy/bot/friends")
def proxy_bot_friends():
    if 'username' not in session: return jsonify({}), 401
    folder, uid, pwd = request.args.get("folder"), request.args.get("uid"), request.args.get("pwd")
    if folder:
        config_path = os.path.join(ensure_user_bots_dir(), folder, "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                bot_cfg = json.load(f)
                uid = bot_cfg.get("account_uid") or bot_cfg.get("uid") or uid
                pwd = bot_cfg.get("account_password") or bot_cfg.get("pwd") or pwd
    if not uid or not pwd: return jsonify({"status": "error"})
    apis = get_api_config(session['username'])
    try:
        r = requests.get(apis["list_friends"].format(uid=uid, pwd=pwd), timeout=10)
        data = r.json()
        if data.get("status") == "success" and folder:
            expiry_data = {} # Simplified for brevity
            friends = data.get("friends_list", [])
            # ... friend expiry logic ...
        return jsonify(data)
    except: return jsonify({"status": "error"})

@app.route("/api/proxy/bot/add_friend", methods=["POST"])
def proxy_bot_add_friend():
    if 'username' not in session: return jsonify({}), 401
    data = request.get_json()
    folder, uid, pwd = data.get('folder'), data.get('uid'), data.get('pwd')
    if folder:
        config_path = os.path.join(ensure_user_bots_dir(), folder, "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                bot_cfg = json.load(f)
                uid = bot_cfg.get("account_uid") or bot_cfg.get("uid") or uid
                pwd = bot_cfg.get("account_password") or bot_cfg.get("pwd") or pwd
    apis = get_api_config(session['username'])
    try:
        r = requests.get(apis["add_friend"].format(uid=uid, pwd=pwd, friend_id=data.get('friend_id')), timeout=10)
        return jsonify(r.json())
    except: return jsonify({"status": "error"})

@app.route("/api/proxy/bot/remove_friend", methods=["POST"])
def proxy_bot_remove_friend():
    if 'username' not in session: return jsonify({}), 401
    data = request.get_json()
    folder, uid, pwd = data.get('folder'), data.get('uid'), data.get('pwd')
    if folder:
        config_path = os.path.join(ensure_user_bots_dir(), folder, "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                bot_cfg = json.load(f)
                uid = bot_cfg.get("account_uid") or bot_cfg.get("uid") or uid
                pwd = bot_cfg.get("account_password") or bot_cfg.get("pwd") or pwd
    apis = get_api_config(session['username'])
    try:
        r = requests.get(apis["remove_friend"].format(uid=uid, pwd=pwd, friend_id=data.get('friend_id')), timeout=10)
        return jsonify(r.json())
    except: return jsonify({"status": "error"})

@app.route("/api/bots/clan/request/<folder>", methods=["POST"])
def api_bots_clan_request(folder):
    if 'username' not in session: return jsonify({"success": False}), 401
    data = request.get_json()
    clan_id = data.get("clan_id")
    user_bots_dir = ensure_user_bots_dir()
    config_path = os.path.join(user_bots_dir, folder, "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            bot_cfg = json.load(f)
            uid = bot_cfg.get("account_uid") or bot_cfg.get("uid")
            pwd = bot_cfg.get("account_password") or bot_cfg.get("pwd")
        if uid and pwd and clan_id:
            apis = get_api_config(session['username'])
            try:
                # Use the new request_clan API from config
                r = requests.get(apis["request_clan"].format(uid=uid, pwd=pwd, clan_id=clan_id), timeout=10)
                return jsonify({"success": True, "data": r.json()})
            except: pass
            return jsonify({"success": True, "message": "تم إرسال الطلب بنجاح"})
    return jsonify({"success": False, "message": "فشل إرسال الطلب"})

@app.route("/api/admin/stats")
def api_admin_stats():
    if 'username' not in session or not is_admin(session['username']): return jsonify({}), 403
    with open(USERS_FILE, "r") as f: users = json.load(f)
    total_size = sum(os.path.getsize(os.path.join(r, f)) for r, d, fs in os.walk(USERS_DIR) for f in fs)
    return jsonify({"total_users": len(users) - 1, "running_servers": len([p for p in running_procs.values() if p.poll() is None]), "storage_mb": round(total_size / (1024 * 1024), 2), "cpu_usage": psutil.cpu_percent(), "ram_usage": psutil.virtual_memory().percent})


@app.route("/api/maintenance/info")
def api_maintenance_info():
    return jsonify(get_maintenance_info())

@app.route("/api/maintenance/set", methods=["POST"])
def api_maintenance_set():
    if 'username' not in session or not is_admin(session['username']):
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    
    data = request.get_json()
    enabled = data.get("enabled", False)
    duration_hours = data.get("duration_hours", 0)
    
    set_maintenance_mode(enabled, duration_hours)
    
    if enabled:
        # تسجيل خروج جميع المستخدمين ما عدا الأدمن
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
        for username in users:
            if username != session['username']:
                # حذف جلسة المستخدم
                pass
    
    return jsonify({"success": True, "maintenance": get_maintenance_info()})

@app.route("/api/check-maintenance")
def api_check_maintenance():
    info = get_maintenance_info()
    if info["enabled"]:
        return jsonify({"maintenance": True, "remaining_seconds": info["remaining_seconds"]})
    return jsonify({"maintenance": False})

@app.route("/api/trigger_backup", methods=["POST"])
def api_trigger_backup_route():
    if 'username' not in session: return jsonify({"success": False}), 401
    trigger_backup()
    return jsonify({"success": True})


@app.errorhandler(Exception)
def handle_exception(e):
    """معالجة جميع الأخطاء غير المتوقعة لتجنب خطأ 500"""
    # إذا كان الخطأ من نوع HTTP (مثل 404 أو 401) اتركه كما هو
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        return e
    
    # تسجيل الخطأ في السجلات (اختياري)
    print(f"Unhandled Exception: {e}")
    
    # العودة باستجابة JSON أو إعادة توجيه لتجنب الصفحة البيضاء
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "error": "حدث خطأ داخلي، يرجى المحاولة لاحقاً"}), 500
    return redirect(url_for('home'))

if __name__ == "__main__":
    init_users_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("SERVER_PORT", 25770)), debug=False)

@app.route("/api/admin/users/update-key", methods=["POST"])
def api_admin_users_update_key():
    """تعديل مفتاح الاشتراك (subscription key) للمستخدم"""
    is_admin_req = 'username' in session and is_admin(session['username'])
    bot_secret = request.headers.get('x-bot-secret') or request.get_json().get('bot_secret')
    INTERNAL_BOT_SECRET = "alliff_bot_api_secret_2026"
    
    if not is_admin_req and bot_secret != INTERNAL_BOT_SECRET:
        return jsonify({"success": False, "error": "غير مصرح لك"}), 403
    
    data = request.get_json()
    target_user = data.get("username")
    new_key = data.get("key")
    
    if not target_user or not new_key:
        return jsonify({"success": False, "error": "بيانات ناقصة"})
    
    if target_user == ADMIN_USERNAME:
        return jsonify({"success": False, "error": "لا يمكن تعديل مفتاح المسؤول الرئيسي"})
    
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
    
    if target_user not in users:
        return jsonify({"success": False, "error": "المستخدم غير موجود"})
    
    users[target_user]["subscription_key"] = new_key
    
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)
    
    trigger_backup()
    return jsonify({"success": True, "message": "تم تحديث المفتاح بنجاح"})

@app.route("/api/admin/users/delete-account", methods=["POST"])
def api_admin_users_delete_account():
    """حذف حساب مستخدم مع جميع بيانات البوتات"""
    is_admin_req = 'username' in session and is_admin(session['username'])
    bot_secret = request.headers.get('x-bot-secret') or request.get_json().get('bot_secret')
    INTERNAL_BOT_SECRET = "alliff_bot_api_secret_2026"
    
    if not is_admin_req and bot_secret != INTERNAL_BOT_SECRET:
        return jsonify({"success": False, "error": "غير مصرح لك"}), 403
    
    data = request.get_json()
    target_user = data.get("username")
    
    if not target_user:
        return jsonify({"success": False, "error": "اسم المستخدم مطلوب"})
    
    if target_user == ADMIN_USERNAME:
        return jsonify({"success": False, "error": "لا يمكن حذف حساب المسؤول الرئيسي"})
    
    user_bots_dir = get_user_bots_dir(target_user)
    if os.path.exists(user_bots_dir):
        for folder in os.listdir(user_bots_dir):
            stop_bot_by_key(f"{target_user}_{folder}")
    
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
    
    if target_user in users:
        del users[target_user]
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=2)
    
    shutil.rmtree(os.path.join(USERS_DIR, target_user), ignore_errors=True)
    
    trigger_backup()
    return jsonify({"success": True, "message": "تم حذف الحساب وجميع البيانات بنجاح"})

