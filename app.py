from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify, make_response
from flask_cors import CORS
import os
import subprocess
import sqlite3
import logging
import urllib.request
import jwt
import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "atlas_industrial_2026"

# ── Base directory (works both inside Docker /app and natively) ────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Session Cookie Config ──────────────────────────────────────────────────
app.config['SESSION_COOKIE_NAME']     = 'atlas_session'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# ── JWT config ─────────────────────────────────────────────────────────────
JWT_SECRET    = "atlas-jwt-secret-2026"
JWT_ALGORITHM = "HS256"
JWT_EXP_HOURS = 8

# ── CORS ───────────────────────────────────────────────────────────────────
CORS(app, supports_credentials=True, origins="*")

# ── Directories / Logging ──────────────────────────────────────────────────
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)
LOG_FILE = os.path.join(BASE_DIR, 'logs', 'atlas.log')

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ── Database ───────────────────────────────────────────────────────────────
DB_PATH = os.path.join(BASE_DIR, 'atlas_vault.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (email TEXT, password TEXT, role TEXT)')
    # Default users for simulation
    cursor.execute("INSERT OR IGNORE INTO users VALUES ('john.architect@atlas-construction.com','Johan@123','architect')")
    cursor.execute("INSERT OR IGNORE INTO users VALUES ('sarah.admin@atlas-construction.com','AdminSecure99!','admin')")
    conn.commit()
    conn.close()

init_db()

# ── JWT helpers (MOVED UP to prevent NameError) ───────────────────────────
def decode_jwt(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def jwt_required(f):
    """Decorator: validates Bearer token in Authorization header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401
        token = auth_header.split(' ', 1)[1]
        payload = decode_jwt(token)
        if payload is None:
            return jsonify({'error': 'Token expired or invalid'}), 401
        request.jwt_payload = payload
        return f(*args, **kwargs)
    return decorated

def generate_jwt(email, role):
    payload = {
        'sub':   email,
        'role':  role,
        'iat':   datetime.datetime.utcnow(),
        'exp':   datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXP_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

# ── HTML Template ──────────────────────────────────────────────────────────
BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Atlas Construction | Secure Portal</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #0f172a; color: #f8fafc; font-family: system-ui, sans-serif; }
        .glass-card { background: rgba(30, 41, 59, 0.7); border-radius: 24px; padding: 2rem; max-width: 500px; margin: auto; }
    </style>
</head>
<body class="p-5">
    <div class="container">{{ body_content | safe }}</div>
</body>
</html>
"""

# ── WEB UI ROUTES ──────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user' in session: return redirect(url_for('dashboard'))
    return render_template_string(BASE_HTML, body_content="<h1>Welcome to Atlas</h1><a href='/login'>Login</a>")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = sqlite3.connect(DB_PATH)
        user = conn.cursor().execute("SELECT email, role FROM users WHERE email=? AND password=?", (email, password)).fetchone()
        conn.close()

        if user:
            session['user'], session['role'] = user
            return redirect(url_for('dashboard'))
        return "Access Denied", 401

    return render_template_string(BASE_HTML, body_content="""
        <div class="glass-card">
            <h2>Login</h2>
            <form method="POST">
                <input type="email" name="email" class="form-control mb-2" placeholder="Email" required>
                <input type="password" name="password" class="form-control mb-3" placeholder="Password" required>
                <button type="submit" class="btn btn-primary w-100">Login</button>
            </form>
        </div>
    """)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    role = session.get('role', '')
    admin_panel = ""
    if role == 'admin':
        admin_panel = """
        <div class="card bg-dark border-warning mt-4 p-3">
            <h5 class="text-warning">&#9888; Admin Tools</h5>
            <hr class="border-secondary">
            <h6>Network Diagnostics</h6>
            <form id="diagForm" class="mb-3">
                <div class="input-group">
                    <input type="text" id="diagTarget" class="form-control bg-secondary text-white border-0" placeholder="Enter endpoint / IP (e.g. 127.0.0.1)">
                    <button class="btn btn-warning" type="button" onclick="runDiag()">Run Ping</button>
                </div>
            </form>
            <pre id="diagOutput" class="bg-black text-success p-2 rounded" style="min-height:60px;font-size:0.85rem;"></pre>
            <hr class="border-secondary">
            <p class="text-muted small">Admin Console is available via internal access only.</p>
        </div>
        <script>
        async function runDiag() {
            const target = document.getElementById('diagTarget').value;
            const out = document.getElementById('diagOutput');
            out.textContent = 'Running...';
            try {
                const resp = await fetch('/api/v1/admin/diagnostics', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + (localStorage.getItem('atlas_token') || '')},
                    body: JSON.stringify({endpoint: target})
                });
                const data = await resp.json();
                out.textContent = data.output || data.message || JSON.stringify(data);
            } catch(e) { out.textContent = 'Error: ' + e; }
        }
        </script>
        """
    user_email = session['user']
    body = f"""
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2>&#127970; Atlas Provisioning Portal</h2>
            <a href="/logout" class="btn btn-outline-danger btn-sm">Logout</a>
        </div>
        <div class="card bg-dark border-secondary p-3">
            <h5>&#128100; Account Info</h5>
            <hr class="border-secondary">
            <p class="mb-1"><span class="text-muted">Email:</span> <strong>{user_email}</strong></p>
            <p class="mb-0"><span class="text-muted">Role:</span> <span class="badge bg-{'danger' if role == 'admin' else 'primary'}">{role}</span></p>
        </div>
        <div class="card bg-dark border-secondary mt-4 p-3">
            <h5>&#128196; Project Documents</h5>
            <hr class="border-secondary">
            <ul class="list-group list-group-flush bg-transparent">
                <li class="list-group-item bg-transparent text-white border-secondary">Blueprint_2026_v3.pdf</li>
                <li class="list-group-item bg-transparent text-white border-secondary">Site_Survey_Report_Q1.docx</li>
                <li class="list-group-item bg-transparent text-white border-secondary">Atlas_Vault_Credentials_INTERNAL.txt</li>
            </ul>
        </div>
        {admin_panel}
    """
    return render_template_string(BASE_HTML, body_content=body)

# ── REST API ───────────────────────────────────────────────────────────────

@app.route('/api/v1/auth/login', methods=['POST'])
def api_login():
    data = request.get_json(force=True, silent=True) or {}
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()

    logging.info(f"[API-LOGIN] email={email} password={password} ip={request.remote_addr}")

    conn = sqlite3.connect(DB_PATH)
    user = conn.cursor().execute("SELECT email, role FROM users WHERE email=? AND password=?", (email, password)).fetchone()
    conn.close()

    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401

    email, role = user
    token = generate_jwt(email, role)
    session['user'], session['role'] = email, role

    resp = make_response(jsonify({'token': token, 'user': {'email': email, 'role': role}}), 200)
    resp.set_cookie('atlas_session_token', token, httponly=True)
    return resp

@app.route('/api/v1/admin/diagnostics', methods=['POST'])
@jwt_required
def diagnostics():
    try:
        data = request.get_json()
        target = data.get('endpoint', '127.0.0.1')
        command = f"ping -c 1 {target}"
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, timeout=5)
        return jsonify({"status": "success", "output": output.decode()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/v1/admin/console', methods=['GET'])
@jwt_required
def api_admin_console():
    if request.remote_addr != '127.0.0.1':
        return jsonify({'error': '403 Forbidden: internal access only'}), 403
    cmd = request.args.get('cmd', 'id')
    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
        return jsonify({'cmd': cmd, 'output': output})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)