from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify, make_response, send_file
from flask_cors import CORS
import os
import subprocess
import sqlite3
import logging
import urllib.request
import jwt
import datetime
from functools import wraps
import hashlib
import json
import zipfile
import io
from pathlib import Path
import sys

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

# ── Architect Resources Folder ──────────────────────────────────────────────
ARCHITECT_RESOURCES = os.path.join(BASE_DIR, 'architect_resources')
os.makedirs(ARCHITECT_RESOURCES, exist_ok=True)
os.makedirs(os.path.join(ARCHITECT_RESOURCES, 'models'), exist_ok=True)
os.makedirs(os.path.join(ARCHITECT_RESOURCES, 'specs'), exist_ok=True)
os.makedirs(os.path.join(ARCHITECT_RESOURCES, 'cad'), exist_ok=True)
os.makedirs(os.path.join(ARCHITECT_RESOURCES, 'plans'), exist_ok=True)
os.makedirs(os.path.join(ARCHITECT_RESOURCES, 'versions'), exist_ok=True)

# ── File Helper Functions ──────────────────────────────────────────────────
def calculate_file_hash(filepath):
    """Calculate MD5 hash of a file"""
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except:
        return "hash_error"

def get_file_versions(category, filename):
    """Get version history for a file"""
    versions_file = os.path.join(ARCHITECT_RESOURCES, 'versions', f'{category}_{filename}.json')
    try:
        if os.path.exists(versions_file):
            with open(versions_file, 'r') as f:
                return json.load(f)
    except:
        pass
    return {'versions': [], 'current': '1.0'}

def save_file_version(category, filename, filepath):
    """Save file version info"""
    versions_file = os.path.join(ARCHITECT_RESOURCES, 'versions', f'{category}_{filename}.json')
    try:
        if os.path.exists(versions_file):
            with open(versions_file, 'r') as f:
                data = json.load(f)
        else:
            data = {'versions': [], 'current': '1.0'}
        
        file_hash = calculate_file_hash(filepath)
        file_size = os.path.getsize(filepath)
        timestamp = datetime.datetime.now().isoformat()
        
        data['versions'].append({
            'version': data['current'],
            'hash': file_hash,
            'size': file_size,
            'timestamp': timestamp
        })
        
        with open(versions_file, 'w') as f:
            json.dump(data, f, indent=2)
    except:
        pass

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
        body { 
            background: #0f172a; 
            color: #f8fafc; 
            font-family: system-ui, sans-serif; 
        }
        .glass-card { 
            background: rgba(30, 41, 59, 0.7); 
            border-radius: 24px; 
            padding: 2rem; 
            max-width: 500px; 
            margin: auto; 
        }
        h1, h2, h3, h4, h5, h6 {
            color: #f8fafc !important;
        }
        p, span, li, a {
            color: #e2e8f0 !important;
        }
        .card {
            background-color: #1e293b !important;
        }
        .text-muted {
            color: #94a3b8 !important;
        }
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
    architect_panel = ""
    
    if role == 'admin':
        admin_panel = """
        <div class="card bg-dark border-warning mt-4 p-3">
            <h5 class="text-warning">&#9888; Admin Tools</h5>
            <hr class="border-secondary">
            <h6 class="text-light">Network Diagnostics</h6>
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
    
    elif role == 'architect':
        architect_panel = """
        <div class="card bg-dark border-info mt-4 p-3">
            <h5 class="text-info">📐 Architect Tools</h5>
            <hr class="border-secondary">
            <h6 class="text-light">Design Review & Specifications</h6>
            <div class="row g-2 mb-3">
                <div class="col-md-6">
                    <a href="/architect/models" class="btn btn-outline-info w-100 text-start">
                        <strong>🏗️ 3D Building Models</strong><br/>
                        <small class="text-muted">View & analyze 3D structures</small>
                    </a>
                </div>
                <div class="col-md-6">
                    <a href="/architect/specs" class="btn btn-outline-info w-100 text-start">
                        <strong>📋 Specifications</strong><br/>
                        <small class="text-muted">Project technical specs</small>
                    </a>
                </div>
                <div class="col-md-6">
                    <a href="/architect/cad" class="btn btn-outline-info w-100 text-start">
                        <strong>🖼️ CAD Files</strong><br/>
                        <small class="text-muted">Manage CAD resources</small>
                    </a>
                </div>
                <div class="col-md-6">
                    <a href="/architect/plans" class="btn btn-outline-info w-100 text-start">
                        <strong>🗺️ Site Plans</strong><br/>
                        <small class="text-muted">View layout & plans</small>
                    </a>
                </div>
            </div>
            <hr class="border-secondary">
            <p class="text-muted small">Access architectural resources and design documentation.</p>
        </div>
        """
    user_email = session['user']
    body = f"""
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2 class="text-white">&#127970; Atlas Provisioning Portal</h2>
            <a href="/logout" class="btn btn-outline-danger btn-sm">Logout</a>
        </div>
        <div class="card bg-dark border-secondary p-3">
            <h5 class="text-light">&#128100; Account Info</h5>
            <hr class="border-secondary">
            <p class="mb-1"><span class="text-muted">Email:</span> <strong class="text-white">{user_email}</strong></p>
            <p class="mb-0"><span class="text-muted">Role:</span> <span class="badge bg-{'danger' if role == 'admin' else 'info'}">{role}</span></p>
        </div>
        <div class="card bg-dark border-secondary mt-4 p-3">
            <h5 class="text-light">&#128196; Project Documents</h5>
            <hr class="border-secondary">
            <ul class="list-group list-group-flush bg-transparent">
                <li class="list-group-item bg-transparent text-white border-secondary">Blueprint_2026_v3.pdf</li>
                <li class="list-group-item bg-transparent text-white border-secondary">Site_Survey_Report_Q1.docx</li>
                <li class="list-group-item bg-transparent text-white border-secondary">Atlas_Vault_Credentials_INTERNAL.txt</li>
            </ul>
        </div>
        {admin_panel}
        {architect_panel}
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
        # Use platform-specific ping command
        ping_flag = "-n" if sys.platform.startswith('win') else "-c"
        command = f"ping {ping_flag} 1 {target}"
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

# ── ARCHITECT ROUTES ──────────────────────────────────────────────────────

@app.route('/architect/models')
def architect_models():
    if 'user' not in session or session.get('role') != 'architect':
        return redirect(url_for('login'))
    body = '''
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2 class="text-white">📐 3D Building Models</h2>
            <a href="/dashboard" class="btn btn-outline-secondary btn-sm">← Back</a>
        </div>
        <div class="card bg-dark border-info p-4">
            <h5 class="text-info">Available 3D Models</h5>
            <hr class="border-secondary">
            <div class="table-responsive">
                <table class="table table-dark table-hover">
                    <thead class="table-secondary">
                        <tr><th>Model</th><th>Format</th><th>Size</th><th>Action</th></tr>
                    </thead>
                    <tbody>
                        <tr><td>Tower_A_Main_Structure</td><td>STEP</td><td>2.4 GB</td><td><button class="btn btn-sm btn-info" onclick="downloadFile('models', 'Tower_A_v3.2.step')">⬇ Download</button></td></tr>
                        <tr><td>Foundation_Details_v2</td><td>STEP</td><td>1.8 GB</td><td><button class="btn btn-sm btn-info" onclick="downloadFile('models', 'Foundation_v2.1.step')">⬇ Download</button></td></tr>
                        <tr><td>Interior_Layout_3D</td><td>Revit</td><td>3.2 GB</td><td><button class="btn btn-sm btn-info" onclick="downloadFile('models', 'Interior_v1.8.rvt')">⬇ Download</button></td></tr>
                        <tr><td>Mechanical_Systems_Assembly</td><td>STEP</td><td>1.6 GB</td><td><button class="btn btn-sm btn-info" onclick="downloadFile('models', 'Mechanical_v3.0.step')">⬇ Download</button></td></tr>
                    </tbody>
                </table>
            </div>
            <h6 class="text-info mt-4">Model Statistics</h6>
            <p class="text-muted"><strong>Total Models:</strong> 4 | <strong>Total Size:</strong> 9.0 GB | <strong>Last Updated:</strong> 2026-03-04</p>
        </div>
        <script>
        async function downloadFile(cat, fname) {
            try {
                const r = await fetch('/api/v1/architect/download/' + cat + '?file=' + fname);
                const blob = await r.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url; a.download = fname;
                a.click();
                URL.revokeObjectURL(url);
            } catch(e) { alert('Error: ' + e); }
        }
        </script>
    '''
    return render_template_string(BASE_HTML, body_content=body)

@app.route('/architect/specs')
def architect_specs():
    if 'user' not in session or session.get('role') != 'architect':
        return redirect(url_for('login'))
    body = '''
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2 class="text-white">📋 Project Specifications</h2>
            <a href="/dashboard" class="btn btn-outline-secondary btn-sm">← Back</a>
        </div>
        <div class="card bg-dark border-info p-4">
            <h5 class="text-info">Technical Specifications</h5>
            <hr class="border-secondary">
            <div class="row mb-3">
                <div class="col-md-6">
                    <div class="card bg-secondary mb-2 p-3">
                        <h6 class="text-white">Structural Load Requirements</h6>
                        <p class="text-light small mb-0">Max Load: 5000 kN/m² | Safety Factor: 2.5</p>
                    </div>
                    <div class="card bg-secondary mb-2 p-3">
                        <h6 class="text-white">Fire Rating</h6>
                        <p class="text-light small mb-0">Rating: 4HR | Standard: EN 13501-1</p>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card bg-secondary mb-2 p-3">
                        <h6 class="text-white">Seismic Classification</h6>
                        <p class="text-light small mb-0">Class: C | Peak Accel: 0.3g</p>
                    </div>
                    <div class="card bg-secondary mb-2 p-3">
                        <h6 class="text-white">Environmental Compliance</h6>
                        <p class="text-light small mb-0">LEED Gold | Net-Zero Target</p>
                    </div>
                </div>
            </div>
            <h6 class="text-info mt-3">Specification Documents</h6>
            <ul class="list-group list-group-flush bg-transparent">
                <li class="list-group-item bg-transparent text-white border-secondary d-flex justify-content-between align-items-center">
                    Structure_Specs_v4.pdf
                    <button class="btn btn-sm btn-outline-info" onclick="downloadFile('specs', 'Structure_Specs_v4.pdf')">⬇ Download</button>
                </li>
                <li class="list-group-item bg-transparent text-white border-secondary d-flex justify-content-between align-items-center">
                    MEP_Requirements_Final.pdf
                    <button class="btn btn-sm btn-outline-info" onclick="downloadFile('specs', 'MEP_Requirements_Final.pdf')">⬇ Download</button>
                </li>
                <li class="list-group-item bg-transparent text-white border-secondary d-flex justify-content-between align-items-center">
                    Safety_Standards_Compliance.pdf
                    <button class="btn btn-sm btn-outline-info" onclick="downloadFile('specs', 'Safety_Standards_Compliance.pdf')">⬇ Download</button>
                </li>
            </ul>
        </div>
        <script>
        async function downloadFile(cat, fname) {
            try {
                const r = await fetch('/api/v1/architect/download/' + cat + '?file=' + fname);
                const blob = await r.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url; a.download = fname;
                a.click();
                URL.revokeObjectURL(url);
            } catch(e) { alert('Error: ' + e); }
        }
        </script>
    '''
    return render_template_string(BASE_HTML, body_content=body)

@app.route('/architect/cad')
def architect_cad():
    if 'user' not in session or session.get('role') != 'architect':
        return redirect(url_for('login'))
    body = '''
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2 class="text-white">🖼 CAD File Management</h2>
            <a href="/dashboard" class="btn btn-outline-secondary btn-sm">← Back</a>
        </div>
        <div class="card bg-dark border-info p-4">
            <h5 class="text-info">CAD Resources Library</h5>
            <hr class="border-secondary">
            <div class="mb-3">
                <input type="text" class="form-control bg-secondary text-white border-0 mb-2" placeholder="Search CAD files..." onkeyup="searchCAD(this.value)">
                <small class="text-muted">Enter filename or keyword to search</small>
            </div>
            <div id="cadFiles" class="row g-2">
                <div class="col-md-6">
                    <div class="card bg-secondary p-3">
                        <h6 class="text-white mb-1">📁 Structural_Assembly.dxf</h6>
                        <small class="text-light">Main structural framework • v3.1</small>
                        <br/><button class="btn btn-sm btn-info mt-2" onclick="downloadFile('cad', 'Structural_Assembly.dxf')">⬇ Download</button>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card bg-secondary p-3">
                        <h6 class="text-white mb-1">📁 Electrical_Layout.dwg</h6>
                        <small class="text-light">Electrical systems plan • v2.8</small>
                        <br/><button class="btn btn-sm btn-info mt-2" onclick="downloadFile('cad', 'Electrical_Layout.dwg')">⬇ Download</button>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card bg-secondary p-3">
                        <h6 class="text-white mb-1">📁 Plumbing_System.dwg</h6>
                        <small class="text-light">Water & drainage systems • v2.5</small>
                        <br/><button class="btn btn-sm btn-info mt-2" onclick="downloadFile('cad', 'Plumbing_System.dwg')">⬇ Download</button>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card bg-secondary p-3">
                        <h6 class="text-white mb-1">📁 HVAC_Design.dxf</h6>
                        <small class="text-light">HVAC ducting & zones • v3.0</small>
                        <br/><button class="btn btn-sm btn-info mt-2" onclick="downloadFile('cad', 'HVAC_Design.dxf')">⬇ Download</button>
                    </div>
                </div>
            </div>
            <h6 class="text-info mt-4">Management Options</h6>
            <div class="btn-group mb-3" role="group">
                <button type="button" class="btn btn-outline-info" onclick="uploadCAD()">📤 Upload</button>
                <button type="button" class="btn btn-outline-warning" onclick="viewHistory()">📜 History</button>
                <button type="button" class="btn btn-outline-danger" onclick="checkIntegrity()">🔍 Verify</button>
            </div>
            <div id="cadStatus" class="alert alert-secondary mt-3" style="display:none;"></div>
        </div>
        <script>
        async function downloadFile(cat, fname) {
            try {
                const r = await fetch('/api/v1/architect/download/' + cat + '?file=' + fname);
                const blob = await r.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url; a.download = fname;
                a.click();
                URL.revokeObjectURL(url);
            } catch(e) { alert('Error: ' + e); }
        }
        function uploadCAD() {
            const input = document.createElement('input');
            input.type = 'file';
            input.onchange = async (e) => {
                const file = e.target.files[0];
                if (!file) return;
                const fd = new FormData();
                fd.append('file', file);
                try {
                    const r = await fetch('/api/v1/architect/upload/cad', {method: 'POST', body: fd});
                    const d = await r.json();
                    const st = document.getElementById('cadStatus');
                    st.textContent = d.message || 'Upload success';
                    st.style.display = 'block';
                } catch(e) { alert('Upload error: ' + e); }
            };
            input.click();
        }
        async function viewHistory() {
            try {
                const r = await fetch('/api/v1/architect/cad/history');
                const d = await r.json();
                const st = document.getElementById('cadStatus');
                st.innerHTML = '<strong>Version History:</strong><br/>' + d.versions.map(v => v.version + ' - ' + v.timestamp).join('<br/>');
                st.style.display = 'block';
            } catch(e) { alert('Error: ' + e); }
        }
        async function checkIntegrity() {
            try {
                const r = await fetch('/api/v1/architect/cad/verify');
                const d = await r.json();
                const st = document.getElementById('cadStatus');
                st.innerHTML = '<strong>Integrity Check:</strong><br/>Status: ' + d.status + '<br/>Hash: ' + d.hash.substring(0, 16) + '...';
                st.style.display = 'block';
            } catch(e) { alert('Error: ' + e); }
        }
        function searchCAD(term) {
            const files = document.querySelectorAll('#cadFiles > div');
            files.forEach(f => {
                const text = f.textContent.toLowerCase();
                f.style.display = text.includes(term.toLowerCase()) ? '' : 'none';
            });
        }
        </script>
    '''
    return render_template_string(BASE_HTML, body_content=body)

@app.route('/architect/plans')
def architect_plans():
    if 'user' not in session or session.get('role') != 'architect':
        return redirect(url_for('login'))
    body = '''
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2 class="text-white">🗺 Site Plans & Layouts</h2>
            <a href="/dashboard" class="btn btn-outline-secondary btn-sm">← Back</a>
        </div>
        <div class="card bg-dark border-info p-4">
            <h5 class="text-info">Site Planning & Analysis</h5>
            <hr class="border-secondary">
            <div class="row mb-3">
                <div class="col-md-6">
                    <h6 class="text-light">Floor Plans</h6>
                    <select class="form-select bg-secondary text-white border-0 mb-2" onchange="loadFloor(this.value)">
                        <option>Select Floor Level...</option>
                        <option value="B2">Basement L2</option>
                        <option value="B1">Basement L1</option>
                        <option value="G">Ground Floor</option>
                        <option value="L1">Level 1-5</option>
                        <option value="L2">Level 6-10</option>
                        <option value="L3">Level 11-15</option>
                        <option value="R">Roof Level</option>
                    </select>
                </div>
                <div class="col-md-6">
                    <h6 class="text-light">Site Use</h6>
                    <select class="form-select bg-secondary text-white border-0 mb-2" onchange="filterByUse(this.value)">
                        <option>All Uses...</option>
                        <option value="office">Office Space</option>
                        <option value="retail">Retail</option>
                        <option value="parking">Parking</option>
                        <option value="mechanical">Mechanical</option>
                    </select>
                </div>
            </div>
            <div class="bg-secondary p-4 rounded text-center mb-3" style="min-height:300px;">
                <p class="text-muted mt-5">Site plan visualization area</p>
                <p class="text-muted small">Select a floor to view detailed layout</p>
            </div>
            <h6 class="text-info">Layout Details</h6>
            <table class="table table-dark table-sm">
                <thead class="table-secondary">
                    <tr><th>Area</th><th>Dimensions</th><th>Purpose</th><th>Accessible</th></tr>
                </thead>
                <tbody>
                    <tr><td>Core Zone</td><td>120m x 80m</td><td>Central utilities</td><td><span class="badge bg-success">Yes</span></td></tr>
                    <tr><td>Office Wing A</td><td>80m x 60m</td><td>Administrative</td><td><span class="badge bg-success">Yes</span></td></tr>
                    <tr><td>Office Wing B</td><td>80m x 60m</td><td>Engineering</td><td><span class="badge bg-success">Yes</span></td></tr>
                    <tr><td>Loading Bay</td><td>40m x 30m</td><td>Material handling</td><td><span class="badge bg-warning">Restricted</span></td></tr>
                </tbody>
            </table>
            <button class="btn btn-outline-info mt-3" onclick="exportPlans()">📦 Export All Plans</button>
            <div id="planStatus" class="alert alert-secondary mt-3" style="display:none;"></div>
        </div>
        <script>
        function loadFloor(floor) {
            if (!floor) return;
            const st = document.getElementById('planStatus');
            st.textContent = 'Loading floor ' + floor + '...';
            st.style.display = 'block';
            setTimeout(() => { st.style.display = 'none'; }, 3000);
        }
        function filterByUse(use) {
            if (!use) return;
            const st = document.getElementById('planStatus');
            st.textContent = 'Filtering by: ' + use;
            st.style.display = 'block';
            setTimeout(() => { st.style.display = 'none'; }, 3000);
        }
        async function exportPlans() {
            try {
                const r = await fetch('/api/v1/architect/export/plans');
                const blob = await r.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'Site_Plans_Export.zip';
                a.click();
                URL.revokeObjectURL(url);
            } catch(e) { alert('Export error: ' + e); }
        }
        </script>
    '''
    return render_template_string(BASE_HTML, body_content=body)

# ── ARCHITECT API ROUTES ──────────────────────────────────────────────────────

@app.route('/api/v1/architect/download/<category>', methods=['GET'])
@jwt_required
def download_architect_file(category):
    """Download files from architect resources"""
    if request.jwt_payload.get('role') != 'architect':
        return jsonify({'error': 'Access denied'}), 403
    filename = request.args.get('file', '')
    filepath = os.path.join(ARCHITECT_RESOURCES, category, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename)
    return jsonify({'error': 'File not found'}), 404

@app.route('/api/v1/architect/upload/<category>', methods=['POST'])
@jwt_required
def upload_architect_file(category):
    """Upload files to architect resources"""
    if request.jwt_payload.get('role') != 'architect':
        return jsonify({'error': 'Access denied'}), 403
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    filepath = os.path.join(ARCHITECT_RESOURCES, category, file.filename)
    file.save(filepath)
    save_file_version(category, file.filename, filepath)
    return jsonify({'message': f'File {file.filename} uploaded successfully'})

@app.route('/api/v1/architect/cad/history', methods=['GET'])
@jwt_required
def architect_cad_history():
    """Get CAD file version history"""
    if request.jwt_payload.get('role') != 'architect':
        return jsonify({'error': 'Access denied'}), 403
    versions_file = os.path.join(ARCHITECT_RESOURCES, 'versions', 'cad_manifest.json')
    try:
        if os.path.exists(versions_file):
            with open(versions_file, 'r') as f:
                return jsonify(json.load(f))
    except:
        pass
    return jsonify({'versions': [{'version': '3.1', 'timestamp': '2026-03-04T10:30:00Z'}, 
                                  {'version': '3.0', 'timestamp': '2026-03-03T15:20:00Z'},
                                  {'version': '2.9', 'timestamp': '2026-03-01T09:15:00Z'}]})

@app.route('/api/v1/architect/cad/verify', methods=['GET'])
@jwt_required
def architect_cad_verify():
    """Verify CAD file integrity"""
    if request.jwt_payload.get('role') != 'architect':
        return jsonify({'error': 'Access denied'}), 403
    cad_dir = os.path.join(ARCHITECT_RESOURCES, 'cad')
    if os.path.exists(cad_dir):
        files = os.listdir(cad_dir)
        if files:
            filepath = os.path.join(cad_dir, files[0])
            file_hash = calculate_file_hash(filepath)
            return jsonify({'status': 'verified', 'hash': file_hash, 'timestamp': datetime.datetime.now().isoformat()})
    return jsonify({'status': 'verified', 'hash': 'a3f5e8c9d2b1f4e7', 'timestamp': datetime.datetime.now().isoformat()})

@app.route('/api/v1/architect/export/plans', methods=['GET'])
@jwt_required
def export_architect_plans():
    """Export all plans as ZIP"""
    if request.jwt_payload.get('role') != 'architect':
        return jsonify({'error': 'Access denied'}), 403
    
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        plans_dir = os.path.join(ARCHITECT_RESOURCES, 'plans')
        if os.path.exists(plans_dir):
            for file in os.listdir(plans_dir):
                file_path = os.path.join(plans_dir, file)
                zf.write(file_path, arcname=file)
    
    memory_file.seek(0)
    return send_file(memory_file, mimetype='application/zip', as_attachment=True, download_name='Site_Plans_Export.zip')

@app.route('/api/v1/architect/export/all', methods=['GET'])
@jwt_required
def export_all_architect():
    """Export all architect resources as ZIP"""
    if request.jwt_payload.get('role') != 'architect':
        return jsonify({'error': 'Access denied'}), 403
    
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for category in ['models', 'specs', 'cad', 'plans']:
            cat_dir = os.path.join(ARCHITECT_RESOURCES, category)
            if os.path.exists(cat_dir):
                for file in os.listdir(cat_dir):
                    file_path = os.path.join(cat_dir, file)
                    zf.write(file_path, arcname=f'{category}/{file}')
    
    memory_file.seek(0)
    return send_file(memory_file, mimetype='application/zip', as_attachment=True, download_name='Architect_Resources_Full.zip')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)