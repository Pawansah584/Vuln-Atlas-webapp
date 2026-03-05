# Atlas Web App - Red Team Training & Vulnerability Assessment Platform

> **⚠️ CRITICAL: EDUCATIONAL & AUTHORIZED TESTING USE ONLY**
> 
> This application contains **intentional security vulnerabilities** and insecure configurations designed for red team training, penetration testing labs, and cybersecurity education.
> 
> **NEVER** deploy to production.  
> **NEVER** use against unauthorized systems.  
> **ONLY** use in controlled, authorized training environments.
> 
> Unauthorized access to computer systems is illegal. Users are solely responsible for ensuring compliance with all applicable laws.

## 📋 Overview

**Atlas WebApp** is a deliberately vulnerable Flask-based web application simulating an industrial construction/architecture portal. It's designed for:

- 🎓 Red team training exercises
- 🔍 Penetration testing practice
- 📚 Cybersecurity education & research
- 🎯 Vulnerability assessment demonstrations
- 🔐 Authentication/JWT exploitation studies

The application features a complete **Architect Panel** with working file management, upload/download capabilities, and multiple intentional vulnerabilities for exploitation.

---

## 🚀 Quick Start

### Prerequisites

**Windows/Linux/Kali:**
- Python 3.7+
- Git
- (Optional) Docker & Docker Compose

### Local Setup (Recommended for Training)

```bash
# Clone repository
git clone https://github.com/YOUR-USERNAME/atlas-webapp.git
cd atlas-webapp

# Create virtual environment
python -m venv venv
source venv/bin/activate          # Linux/Kali
# OR
venv\Scripts\activate.ps1          # Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

**Access the application:** http://localhost:5000

### Docker Setup

```bash
docker-compose up --build
```

---

## 🔑 Test Credentials

| Role | Email | Password |
|------|-------|----------|
| **Architect** | john.architect@atlas-construction.com | ArchitectPass123! |
| **Admin** | sarah.admin@atlas-construction.com | AdminSecure99! |

---

## ✨ Features

### Architect Panel (Full-Featured)
- **📐 3D Building Models** - Download/manage STEP & REVIT files
- **📋 Specifications** - Access PDF specifications & requirements
- **🎨 CAD Management** - Upload, download, and version control CAD files
- **📍 Site Plans** - Browse floor plans with filtering and ZIP export
- **📊 File Integrity** - SHA256 hash verification
- **📜 Version History** - Track file modifications with timestamps
- **💾 Bulk Export** - ZIP file export for site plans

### Admin Panel
- 🔧 System diagnostics
- 💻 Remote command execution (vulnerable)
- 📊 Database access
- ⚙️ Configuration management

---

## 🚨 Intentional Vulnerabilities

This application contains the following vulnerabilities for educational purposes:

### Critical Issues

| # | Vulnerability | Location | CVSS | Details |
|---|---|---|---|---|
| 1 | **Path Traversal** (CWE-22) | `/api/v1/architect/download/<category>` | 7.5 | Download arbitrary files via `../` directory traversal |
| 2 | **Command Injection** (CWE-78) | `/api/v1/admin/diagnostics` | 9.8 | RCE via unsanitized subprocess execution |
| 3 | **JWT Secret Hardcoded** (CWE-798) | `app.py` line ~23 | 7.5 | Can extract secret and forge admin tokens |
| 4 | **Plaintext Passwords** (CWE-256) | Database initialization | 8.2 | All credentials stored in plaintext |
| 5 | **Missing Access Control** (CWE-269) | Multiple routes | 8.1 | Insufficient role-based access validation |
| 6 | **Plaintext Logging** (CWE-532) | File logging | 5.3 | Credentials logged to files unencrypted |

### How to Exploit (Educational)

**Example: Extract Database via Path Traversal**
```python
import requests
import json

url = "http://localhost:5000/api/v1/architect/download/models"
params = {"file": "../../atlas_vault.db"}
response = requests.get(url, params=params)
```

**See [exploit_poc.py](exploit_poc.py) for complete 6-step attack chain demonstrating full system compromise.**

---

## 📁 Project Structure

```
atlas-webapp/
├── app.py                          # Main Flask application (800+ lines)
├── exploit_poc.py                  # Complete exploitation proof-of-concept
├── test_suite.py                   # Cross-platform compatibility tests
├── requirements.txt                # Python dependencies for pip install
├── Dockerfile                      # Docker container definition
├── docker-compose.yml              # Multi-container orchestration
├── entrypoint.sh                   # Container startup script
├── architect_resources/            # Sample files for Architect panel
│   ├── models/                     # 3D building models (STEP, REVIT)
│   ├── specs/                      # PDF specifications
│   ├── cad/                        # CAD drawings (DWG, DXF)
│   └── plans/                      # Site plans & layouts
├── README.md                       # This file
├── LICENSE                         # MIT License + Disclaimer
└── .gitignore                      # Git exclusions
```

---

## 🧪 Testing & Validation

### Run Compatibility Tests
```bash
python test_suite.py
```

**Tests include:**
- Dependency verification
- File structure validation
- Route/endpoint existence checks
- Vulnerability presence confirmation
- Cross-platform compatibility (Windows/Linux/Kali/Ubuntu)

### Execute Exploitation POC
```bash
# With server running (in another terminal)
python exploit_poc.py
```

**Attack chain demonstrates:**
1. ✅ Architect login & credential recovery
2. ✅ Path traversal to download app.py
3. ✅ Database exfiltration
4. ✅ JWT secret extraction & token forgery
5. ✅ RCE via command injection
6. ✅ Full system compromise

---

## 📊 Application Architecture

```
┌─────────────────────────────────────────┐
│       Flask Web Application             │
│  (5 Pages + 9 API Endpoints)            │
└────────────┬────────────────────────────┘
             │
      ┌──────┴──────┐
      │             │
   SQLite DB   File System
  (atlas_vault)  (architect_resources)
```

**Key Routes:**
- `POST /login` - User authentication
- `GET /architect/{models,specs,cad,plans}` - Architect panel pages
- `POST /api/v1/architect/upload/<category>` - Insecure file upload
- `GET /api/v1/architect/download/<category>` - Vulnerable file download
- `POST /api/v1/admin/diagnostics` - RCE endpoint
- `GET /api/v1/admin/console` - Blind command execution

---

## 🛡️ Security Intentional Design Decisions

This application deliberately includes insecure patterns:

| What | Why | Real-World Impact |
|------|-----|------------------|
| Hardcoded JWT Secret | Teach token forgery | Attackers can impersonate any user |
| Path Traversal | Teach input validation | Arbitrary file access/disclosure |
| Command Injection | Teach subprocess dangers | Remote code execution |
| Plaintext Passwords | Teach storage best practices | Credential compromise |
| Minimal CORS | Teach origin validation | Cross-origin attacks |

---

## 📋 Installation Troubleshooting

### Windows
```powershell
# Virtual environment activation
python -m venv venv
venv\Scripts\activate.ps1

# If activation fails, try:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Linux/Kali/Ubuntu
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

---

## 🔗 Files Included

| File | Purpose |
|------|---------|
| `app.py` | Complete Flask application (800 lines) |
| `exploit_poc.py` | Full exploitation PoC (6-step attack) |
| `test_suite.py` | Automated testing suite |
| `requirements.txt` | `pip install` dependency list |
| `Dockerfile` | Container image definition |
| `docker-compose.yml` | Orchestration config |
| `entrypoint.sh` | Container startup script |
| `architect_resources/` | Sample files for training |

---

## 📚 Learning Objectives

After completing exercises with this application, you should understand:

✅ How path traversal attacks work  
✅ Command injection exploitation techniques  
✅ JWT token forgery and secret extraction  
✅ Database exfiltration methods  
✅ Privilege escalation vectors  
✅ Remote code execution (RCE) methods  
✅ Defense mechanisms & mitigation strategies  

---

## 🤝 Contributing

For bug reports, improvements, or feature suggestions:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Commit changes (`git commit -am 'Add improvement'`)
4. Push to branch (`git push origin feature/improvement`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License with an **educational use disclaimer**. See [LICENSE](LICENSE) for details.

**Key terms:**
- ✅ Educational use in authorized environments
- ❌ NO warranty or liability
- ❌ Unauthorized testing is illegal
- ❌ Users are responsible for legal compliance

---

## ⚖️ Legal Disclaimer

**THIS SOFTWARE IS PROVIDED FOR EDUCATIONAL PURPOSES IN AUTHORIZED ENVIRONMENTS ONLY.**

- Users assume full responsibility for their actions
- Unauthorized access to computer systems is illegal under the Computer Fraud and Abuse Act (CFAA) and equivalent international laws
- Authors provide no warranty and will not be liable for misuse
- Ensure proper authorization before conducting any security testing

---

## 📞 Support & Questions

For issues, questions, or labs:
- Submit issues on GitHub
- Check [exploit_poc.py](exploit_poc.py) for attack examples
- Review [test_suite.py](test_suite.py) for validation
- Refer to inline code comments for vulnerability details

---

**Happy hunting! 🔍**

*Last updated: March 5, 2026*  
*Platform compatibility: Windows, Linux, Kali Linux, Ubuntu*
