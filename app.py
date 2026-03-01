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

# ── Session Cookie Config (realistic for evilginx phishlet capture) ──────────
# evilginx will intercept Set-Cookie headers and strip HttpOnly/Secure flags
# to replay the stolen session on behalf of the attacker.
app.config['SESSION_COOKIE_NAME']     = 'atlas_session'
app.config['SESSION_COOKIE_HTTPONLY'] = True   # evilginx strips this → captured
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # evilginx bypasses this via MITM

# ── JWT config ─────────────────────────────────────────────────────────────────
# Also returned in API login response body — another credential artifact to steal
JWT_SECRET    = "atlas-jwt-secret-2026"
JWT_ALGORITHM = "HS256"
JWT_EXP_HOURS = 8

# ── CORS: allow any origin so the phishing page can make cross-origin API calls ─
CORS(app, supports_credentials=True, origins="*")

# ── Directories / Logging ──────────────────────────────────────────────────────
UPLOAD_FOLDER = '/app/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
LOG_FILE = '/app/logs/atlas.log'

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ── Database ───────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect('/app/atlas_vault.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (email TEXT, password TEXT, role TEXT)')
    cursor.execute("INSERT OR IGNORE INTO users VALUES ('john.architect@atlas-construction.com','Password123','architect')")
    cursor.execute("INSERT OR IGNORE INTO users VALUES ('sarah.admin@atlas-construction.com','AdminSecure99!','admin')")
    conn.commit()
    conn.close()

init_db()

# ── JWT helpers ────────────────────────────────────────────────────────────────
def generate_jwt(email, role):
    payload = {
        'sub':   email,
        'role':  role,
        'iat':   datetime.datetime.utcnow(),
        'exp':   datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXP_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

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

BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Atlas Construction | Secure Portal</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    <style>
        :root {
            --atlas-dark: #0f172a;
            --atlas-accent: #f59e0b; /* Construction Orange/Gold */
            --atlas-slate: #334155;
            --atlas-bg: #f8fafc;
        }
        body { background: var(--atlas-bg); color: #1e293b; font-family: 'Inter', system-ui, -apple-system, sans-serif; height: 100vh; display: flex; flex-direction: column; }
        
        .navbar { background: var(--atlas-dark) !important; border-bottom: 4px solid var(--atlas-accent); padding: 1rem 0; }
        .navbar-brand { font-weight: 800; letter-spacing: -0.5px; display: flex; align-items: center; gap: 12px; }
        .logo-box { background: var(--atlas-accent); color: var(--atlas-dark); padding: 4px 8px; border-radius: 4px; font-weight: 900; }
        
        .main-container { flex: 1; display: flex; align-items: center; justify-content: center; padding: 2rem; }
        
        .card { 
            border: none; 
            border-radius: 16px; 
            box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1); 
            overflow: hidden; 
            background: #ffffff;
            width: 100%;
            max-width: 800px;
        }
        
        .card-header-atlas { background: #f1f5f9; border-bottom: 1px solid #e2e8f0; padding: 1.5rem; }
        .card-body-atlas { padding: 2.5rem; }
        
        .btn-atlas { background: var(--atlas-dark); color: white; padding: 0.75rem 1.5rem; border-radius: 8px; font-weight: 600; transition: all 0.2s; border: none; }
        .btn-atlas:hover { background: var(--atlas-slate); transform: translateY(-1px); color: white; }
        
        .form-control { border-radius: 8px; padding: 0.75rem; border: 1px solid #cbd5e1; }
        .form-control:focus { border-color: var(--atlas-accent); box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.2); }
        
        .avatar-circle {
            width: 40px; height: 40px; background: var(--atlas-slate); color: white; 
            border-radius: 50%; display: flex; align-items: center; justify-content: center;
            font-weight: bold; border: 2px solid var(--atlas-accent);
        }
        
        .role-badge { 
            font-size: 0.7rem; text-transform: uppercase; font-weight: 700; 
            padding: 2px 8px; border-radius: 999px; background: #e2e8f0; color: #475569;
        }
        
        .footer-text { font-size: 0.85rem; color: #64748b; margin-top: 2rem; text-align: center; }
        
        /* Dashboard styling */
        .dashboard-grid .btn { text-align: left; padding: 1.25rem; border-radius: 12px; display: flex; align-items: center; gap: 15px; font-weight: 600; }
        .dashboard-grid .btn i { font-size: 1.5rem; width: 30px; }
    </style>
</head>
<body>
<nav class="navbar navbar-dark shadow-sm">
  <div class="container d-flex justify-content-between align-items-center">
    <a class="navbar-brand m-0" href="/">
        <div class="logo-box">A</div>
        <span>ATLAS<span style="color:var(--atlas-accent)">INDUSTRIAL</span></span>
    </a>
    
    {% if session.user %}
    <div class="d-flex align-items-center gap-3">
        <div class="text-end d-none d-sm-block">
            <div class="text-white small fw-bold">{{ session.user }}</div>
            <span class="role-badge">{{ session.role }}</span>
        </div>
        <div class="avatar-circle">
            {{ session.user[0]|upper }}
        </div>
        <a href="/logout" class="btn btn-outline-light btn-sm" title="Sign Out">
            <i class="fa-solid fa-right-from-bracket"></i>
        </a>
    </div>
    {% endif %}
  </div>
</nav>

<div class="main-container">
    <div class="card">
        {{ body_content | safe }}
    </div>
</div>

<footer class="footer-text pb-4">
    <p>&copy; 2026 Atlas Industrial Construction Group. Sensitive Internal System. <br> 
    <span class="badge bg-dark">Security Level: High (SOC-2)</span></p>
</footer>
</body>
</html>
"""


# ══════════════════════════════════════════════════════════════════════════════
#  WEB UI ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    if 'user' in session: return redirect(url_for('dashboard'))
    return render_template_string(BASE_HTML, body_content="""
        <div class="card-body-atlas text-center">
            <div class="mb-5">
                <i class="fa-solid fa-building-shield fa-4x mb-4 text-atlas"></i>
                <h2 class="fw-bold">Employee Access Portal</h2>
                <div class="mx-auto bg-warning" style="height:3px; width:40px;"></div>
                <p class="mt-3 text-secondary px-5">Welcome to the Atlas Industrial Internal Gateway. Please authorize your session to access blueprints, directories, and server controls.</p>
            </div>
            <div class="d-grid gap-2 col-lg-8 mx-auto">
                <a href="/login" class="btn btn-atlas btn-lg shadow-sm">
                   <i class="fa-solid fa-key me-2"></i> Authorized Staff Login
                </a>
            </div>
            <p class="mt-5 small text-danger"><i class="fa-solid fa-triangle-exclamation"></i> Monitoring Active: IP Addressing Recorded</p>
        </div>
    """)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    UI login — submits via JS fetch() to /api/v1/auth/login (JSON).
    This means evilginx captures:
      1. The POST body  → plaintext email + password
      2. The Set-Cookie header → atlas_session cookie value
      3. The JSON response body → JWT token
    """
    if request.method == 'POST':
        # Fallback: accept plain form-POST so the page works even without JS
        email    = request.form['email']
        password = request.form['password']
        logging.info(f"[UI-LOGIN] email={email} password={password}")

        conn   = sqlite3.connect('/app/atlas_vault.db')
        cursor = conn.cursor()
        user   = cursor.execute(
            "SELECT email, role FROM users WHERE email=? AND password=?", (email, password)
        ).fetchone()
        conn.close()

        if user:
            session['user'], session['role'] = user
            return redirect(url_for('dashboard'))
        return "Access Denied: Invalid Credentials", 401

    # ── GET: render login form (JS-powered fetch to /api/v1/auth/login) ──────
    return render_template_string(BASE_HTML, body_content="""
        <div class="card-body-atlas">
            <div class="text-center mb-4">
                <i class="fa-solid fa-user-gear fa-3x text-dark"></i>
                <h3 class="mt-3 fw-bold">Identity Verification</h3>
            </div>
            <div id="err-msg" class="alert alert-danger d-none animate__animated animate__headShake"></div>
            <form id="loginForm">
                <div class="mb-4">
                    <label class="form-label fw-semibold">Email Address</label>
                    <div class="input-group">
                        <span class="input-group-text bg-light border-end-0"><i class="fa-solid fa-envelope"></i></span>
                        <input id="email" name="email" type="email" class="form-control border-start-0" placeholder="user@atlas-construction.com" required>
                    </div>
                </div>
                <div class="mb-4">
                    <label class="form-label fw-semibold">Password</label>
                    <div class="input-group">
                        <span class="input-group-text bg-light border-end-0"><i class="fa-solid fa-lock"></i></span>
                        <input id="password" name="password" type="password" class="form-control border-start-0" placeholder="••••••••" required>
                    </div>
                </div>
                <button type="submit" class="btn btn-atlas w-100 py-3 shadow">
                    Authorize Session <i class="fa-solid fa-arrow-right-long ms-2"></i>
                </button>
            </form>
            <div class="text-center mt-4 border-top pt-4">
                <small class="text-secondary">Problems logging in? Contact <a href="#" class="text-decoration-none text-atlas">IT Support</a></small>
            </div>
        </div>
        <script>
        // fetch-based login: sends JSON so credentials appear in request body ──
        // (same JS logic as before, just styled differently)
        document.getElementById('loginForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const email    = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            try {
                const res = await fetch('/api/v1/auth/login', {
                    method: 'POST',
                    credentials: 'include',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                const data = await res.json();
                if (res.ok) {
                    localStorage.setItem('atlas_jwt', data.token);
                    window.location.href = '/dashboard';
                } else {
                    const msg = document.getElementById('err-msg');
                    msg.innerHTML = '<i class="fa-solid fa-circle-xmark me-2"></i>' + (data.error || 'Identity Verification Failed');
                    msg.classList.remove('d-none');
                }
            } catch(err) {
                document.getElementById('loginForm').method = 'POST';
                document.getElementById('loginForm').submit();
            }
        });
        </script>
    """)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    
    role = session.get('role', 'staff')
    content = f"""
    <div class="card-header-atlas d-flex justify-content-between align-items-center">
        <h4 class="fw-bold m-0"><i class="fa-solid fa-cloud-bolt me-2"></i>Active Workspaces</h4>
    </div>
    <div class="card-body-atlas dashboard-grid">
        <p class="text-secondary mb-4">Select a department workspace to manage assets. Your <b>{role}</b> permissions are currently active.</p>
        <div class="row g-3">
            <div class="col-md-12">
                <a href="/directory" class="btn btn-outline-primary w-100 border-2">
                   <div class="avatar-circle bg-primary"><i class="fa-solid fa-users text-white"></i></div>
                   <div>
                        <div class="text-dark">Atlas Global Directory</div>
                        <div class="text-muted small fw-normal">Search and manage staff records</div>
                   </div>
                   <i class="fa-solid fa-chevron-right ms-auto"></i>
                </a>
            </div>
    """
    
    if role == 'architect':
        content += """
            <div class="col-md-12">
                <a href="/upload" class="btn btn-outline-success w-100 border-2">
                   <div class="avatar-circle bg-success"><i class="fa-solid fa-file-arrow-up text-white"></i></div>
                   <div>
                        <div class="text-dark">CAD Blueprint Submissions</div>
                        <div class="text-muted small fw-normal">Upload structural design documentation</div>
                   </div>
                   <i class="fa-solid fa-chevron-right ms-auto"></i>
                </a>
            </div>
        """
    
    if role == 'admin':
        content += """
            <div class="col-md-12">
                <a href="/vault" class="btn btn-outline-dark w-100 border-2">
                   <div class="avatar-circle bg-dark"><i class="fa-solid fa-vault text-white"></i></div>
                   <div>
                        <div class="text-dark">Remote Blueprint Sync Tool</div>
                        <div class="text-muted small fw-normal">Admin: Import archives from remote sites</div>
                   </div>
                   <i class="fa-solid fa-chevron-right ms-auto"></i>
                </a>
            </div>
            <div class="col-md-12">
                <a href="/admin/system-logs" class="btn btn-outline-danger w-100 border-2">
                   <div class="avatar-circle bg-danger"><i class="fa-solid fa-terminal text-white"></i></div>
                   <div>
                        <div class="text-dark">Emergency Server Console</div>
                        <div class="text-muted small fw-normal">Critical: Direct kernel interaction via CIDR restriction</div>
                   </div>
                   <i class="fa-solid fa-chevron-right ms-auto"></i>
                </a>
            </div>
        """

    content += "</div></div>"
    return render_template_string(BASE_HTML, body_content=content)


@app.route('/directory')
def directory():
    if 'user' not in session: return redirect(url_for('login'))
    search = request.args.get('search', '')
    conn = sqlite3.connect('/app/atlas_vault.db')
    cursor = conn.cursor()
    # VULNERABLE: SQLi (UNION SELECT)
    query = f"SELECT email, role FROM users WHERE email LIKE '%{search}%'"
    try:
        results = cursor.execute(query).fetchall()
    except Exception as e:
        results = [("Query Error", str(e))]
    conn.close()

    return render_template_string(BASE_HTML, body_content=f"""
        <h3>Staff Directory</h3>
        <form class="input-group mb-3"><input name="search" class="form-control" placeholder="Search..."><button class="btn btn-dark">Find</button></form>
        <table class="table table-striped">
            <thead><tr><th>Email</th><th>Role</th></tr></thead>
            <tbody>{"".join([f"<tr><td>{r[0]}</td><td>{r[1]}</td></tr>" for r in results])}</tbody>
        </table>
    """)

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if 'user' not in session or session.get('role') != 'architect':
        return "Access Denied: Architects Only", 403
    
    msg = ""
    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            # VULNERABLE: No extension check + Path Traversal risk
            filename = file.filename 
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(save_path)
            msg = f"File successfully uploaded to: {save_path}"

    return render_template_string(BASE_HTML, body_content=f"""
        <h3>Blueprint Submission</h3>
        <p class="text-muted">Upload design documents (.pdf, .dwg) to the central archive.</p>
        <form method="POST" enctype="multipart/form-data">
            <input type="file" name="file" class="form-control mb-3">
            <button class="btn btn-success w-100">Upload to Archive</button>
        </form>
        <p class='mt-3'><b>{msg}</b></p>
    """)

@app.route('/vault', methods=['GET', 'POST'])
def vault():
    # Only Admin can access this now
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    data = ""
    if request.method == 'POST':
        url = request.form.get('url')
        try:
            # VULNERABLE: SSRF
            data = urllib.request.urlopen(url).read().decode('utf-8', errors='ignore')
        except Exception as e:
            data = str(e)

    return render_template_string(BASE_HTML, body_content=f"""
        <h3>Remote Blueprint Importer</h3>
        <form method="POST"><input name="url" class="form-control mb-2" placeholder="http://internal-archive.local/file.xml"><button class="btn btn-primary w-100">Sync</button></form>
        <div class="mt-3 p-2 border bg-light text-dark" style="max-height:200px; overflow:auto;"><pre>{data}</pre></div>
    """)

@app.route('/admin/system-logs')
def admin():
    if request.remote_addr != '127.0.0.1':
        return "403 Forbidden: Remote Access Prohibited", 403

    cmd = request.args.get('cmd', 'id')
    try:
        # VULNERABLE: Command Injection
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
    except Exception as e:
        output = str(e)
    return f"CONSOLE OUTPUT:\n{output}"

@app.route('/logout')
def logout():
    session.clear()
    resp = make_response(redirect('/'))
    resp.delete_cookie('atlas_session')
    return resp


# ══════════════════════════════════════════════════════════════════════════════
#  REST API  — /api/v1/
#
#  Evilginx phishlet capture points:
#    POST /api/v1/auth/login   → request body  : {"email":"..","password":".."}
#                               response body  : {"token":"<JWT>", ...}
#                               response header: Set-Cookie: atlas_session=<value>; HttpOnly
#    All subsequent API calls carry:
#      • Authorization: Bearer <JWT>   (captured by evilginx in request header)
#      • Cookie: atlas_session=<value> (captured by evilginx in request header)
# ══════════════════════════════════════════════════════════════════════════════

# ── /api/v1/auth/login ────────────────────────────────────────────────────────
@app.route('/api/v1/auth/login', methods=['POST'])
def api_login():
    """
    Accepts JSON { email, password }.
    Returns JWT token in body + sets session cookie.
    VULNERABLE: credentials are logged to atlas.log (T1552 – Credentials in Files).
    """
    data     = request.get_json(force=True, silent=True) or {}
    email    = data.get('email', '').strip()
    password = data.get('password', '').strip()

    # ── T1552: log credentials to file in plaintext ────────────────────────
    logging.info(f"[API-LOGIN] email={email} password={password} ip={request.remote_addr}")

    if not email or not password:
        return jsonify({'error': 'email and password are required'}), 400

    conn   = sqlite3.connect('/app/atlas_vault.db')
    cursor = conn.cursor()
    user   = cursor.execute(
        "SELECT email, role FROM users WHERE email=? AND password=?", (email, password)
    ).fetchone()
    conn.close()

    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401

    email, role = user
    token = generate_jwt(email, role)

    # Also populate Flask session so the UI routes work after API login
    session['user'] = email
    session['role'] = role

    resp = make_response(jsonify({
        'message':    'Authentication successful',
        'token':      token,
        'token_type': 'Bearer',
        'expires_in': JWT_EXP_HOURS * 3600,
        'user': {'email': email, 'role': role}
    }), 200)

    # The Set-Cookie header is what evilginx captures to hijack the session
    # HttpOnly is set here — evilginx strips it at the proxy layer
    resp.set_cookie(
        'atlas_session_token', token,
        httponly=True,
        samesite='Lax',
        max_age=JWT_EXP_HOURS * 3600
    )
    return resp


# ── /api/v1/auth/whoami ───────────────────────────────────────────────────────
@app.route('/api/v1/auth/whoami', methods=['GET'])
@jwt_required
def api_whoami():
    """Returns the identity of the caller from their JWT token."""
    p = request.jwt_payload
    return jsonify({
        'email': p['sub'],
        'role':  p['role'],
        'token_issued_at': p['iat'],
        'token_expires_at': p['exp']
    })


# ── /api/v1/auth/logout ───────────────────────────────────────────────────────
@app.route('/api/v1/auth/logout', methods=['POST'])
def api_logout():
    session.clear()
    resp = make_response(jsonify({'message': 'Logged out'}), 200)
    resp.delete_cookie('atlas_session')
    resp.delete_cookie('atlas_session_token')
    return resp


# ── /api/v1/directory ─────────────────────────────────────────────────────────
@app.route('/api/v1/directory', methods=['GET'])
@jwt_required
def api_directory():
    """
    Returns employee list as JSON.
    VULNERABLE: SQLi via ?search= parameter (T1190 – Exploit Public-Facing Application).
    Example payload: ?search=' UNION SELECT email,password FROM users--
    """
    search = request.args.get('search', '')
    conn   = sqlite3.connect('/app/atlas_vault.db')
    cursor = conn.cursor()
    # DELIBERATELY unsanitized — UNION SELECT SQLi works here
    query  = f"SELECT email, role FROM users WHERE email LIKE '%{search}%'"
    try:
        rows = cursor.execute(query).fetchall()
        results = [{'email': r[0], 'role': r[1]} for r in rows]
    except Exception as e:
        results = [{'error': str(e)}]
    conn.close()
    return jsonify({'count': len(results), 'results': results})


# ── /api/v1/blueprints/upload ─────────────────────────────────────────────────
@app.route('/api/v1/blueprints/upload', methods=['POST'])
@jwt_required
def api_upload():
    """
    Accepts multipart file upload.
    VULNERABLE:
      • No extension whitelist  → upload .php / .py / any executable
      • No path sanitization    → path traversal via filename
    (T1505.003 – Web Shell via File Upload)
    """
    if request.jwt_payload.get('role') != 'architect':
        return jsonify({'error': 'Architects only'}), 403

    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify({'error': 'No file provided'}), 400

    # VULNERABLE: raw filename used — directory traversal possible
    filename  = file.filename
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(save_path)

    logging.info(f"[UPLOAD] file={filename} saved_to={save_path} by={request.jwt_payload['sub']}")
    return jsonify({'message': 'Upload successful', 'path': save_path}), 201


# ── /api/v1/vault/fetch ───────────────────────────────────────────────────────
@app.route('/api/v1/vault/fetch', methods=['POST'])
@jwt_required
def api_vault_fetch():
    """
    Fetches a remote URL and returns its content.
    VULNERABLE: SSRF — attacker can point this at internal services.
    (T1090 – Proxy / Internal Network Probing)
    Example: {"url": "http://127.0.0.1:5000/admin/system-logs?cmd=id"}
    """
    if request.jwt_payload.get('role') != 'admin':
        return jsonify({'error': 'Admins only'}), 403

    data = request.get_json(force=True, silent=True) or {}
    url  = data.get('url', '')
    if not url:
        return jsonify({'error': 'url is required'}), 400

    try:
        # VULNERABLE: no URL scheme/host restriction
        content = urllib.request.urlopen(url).read().decode('utf-8', errors='ignore')
        return jsonify({'url': url, 'content': content})
    except Exception as e:
        return jsonify({'url': url, 'error': str(e)}), 502


# ── /api/v1/admin/console ─────────────────────────────────────────────────────
@app.route('/api/v1/admin/console', methods=['GET'])
@jwt_required
def api_admin_console():
    """
    Executes shell commands.
    VULNERABLE: Command Injection (T1059 – Command and Scripting Interpreter).
    Restricted to 127.0.0.1 by IP — but reachable via SSRF from /api/v1/vault/fetch.
    Chain: SSRF → RCE  (the intended kill-chain for this lab)
    """
    if request.remote_addr != '127.0.0.1':
        return jsonify({'error': '403 Forbidden: internal access only'}), 403

    cmd = request.args.get('cmd', 'id')
    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
    except Exception as e:
        output = str(e)

    logging.info(f"[CONSOLE] cmd={cmd} output_len={len(output)}")
    return jsonify({'cmd': cmd, 'output': output})


# ── /api/v1/status ────────────────────────────────────────────────────────────
@app.route('/api/v1/status', methods=['GET'])
def api_status():
    """Public health-check endpoint — reveals server info (T1592 – Gather Host Info)."""
    import platform
    return jsonify({
        'service':    'Atlas Industrial Portal API',
        'version':    'v1.4.2',
        'status':     'operational',
        'server':     platform.node(),
        'python':     platform.python_version(),
        'endpoints': [
            'POST /api/v1/auth/login',
            'GET  /api/v1/auth/whoami',
            'POST /api/v1/auth/logout',
            'GET  /api/v1/directory',
            'POST /api/v1/blueprints/upload',
            'POST /api/v1/vault/fetch',
            'GET  /api/v1/admin/console  [internal]',
        ]
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

