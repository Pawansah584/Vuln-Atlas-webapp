# Setup Instructions for Atlas WebApp

## Quick Reference

| OS | Command |
|----|---------|
| Windows | `venv\Scripts\activate.ps1` then `python app.py` |
| Linux/Kali | `source venv/bin/activate` then `python app.py` |
| Docker All | `docker-compose up --build` |

---

## Detailed Setup Steps

### 1. Clone Repository
```bash
git clone https://github.com/YOUR-USERNAME/atlas-webapp.git
cd atlas-webapp
```

### 2. Choose Your Setup Method

#### **Option A: Native (Recommended for Training)**

**Windows (PowerShell):**
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate.ps1

# If you get an execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Install dependencies
pip install -r requirements.txt

# Run application
python app.py
```

**Linux/Kali/Ubuntu:**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run application
python app.py
```

#### **Option B: Docker (All Platforms)**

```bash
# Build and run containers
docker-compose up --build

# Access at http://localhost:5000
```

---

## 3. Verify Installation

Run the test suite:
```bash
python test_suite.py
```

Expected output:
- ✅ All dependencies found
- ✅ All files present
- ✅ All routes/endpoints found
- ✅ All vulnerabilities confirmed

---

## 4. Access Application

**URL:** `http://localhost:5000`

**Architect Login:**
- Email: `john.architect@atlas-construction.com`
- Password: `ArchitectPass123!`

**Admin Login** (for RCE testing):
- Email: `sarah.admin@atlas-construction.com`
- Password: `AdminSecure99!`

---

## 5. Run Exploitation POC

In a separate terminal (with server still running):
```bash
python exploit_poc.py
```

This demonstrates a complete 6-step attack chain:
1. Login as architect
2. Path traversal to download app.py
3. Database exfiltration  
4. JWT secret extraction
5. Token forgery to become admin
6. RCE via command injection

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'flask'"
**Solution:** Make sure virtual environment is activated and dependencies are installed
```bash
source venv/bin/activate      # Linux/Kali
pip install -r requirements.txt
```

### "Address already in use" (Port 5000)
**Solution:** Change Flask port in app.py or kill process using port 5000
```bash
# Windows
Get-Process -Name python | Stop-Process

# Linux
lsof -i :5000 | xargs kill -9
```

### "flask_cors not found" warning
**Solution:** Install flask-cors
```bash
pip install flask-cors
```

---

## File Descriptions

- **app.py** - Main Flask application (800 lines, fully functional)
- **requirements.txt** - Dependencies for `pip install`
- **exploit_poc.py** - Complete attack demonstration
- **test_suite.py** - Automated testing & compatibility checks
- **architect_resources/** - Sample files used by the application
- **Dockerfile** - Docker container image definition
- **docker-compose.yml** - Multi-container orchestration

---

## Next Steps

1. ✅ Start the application
2. ✅ Login with test credentials
3. ✅ Explore the Architect panel features
4. ✅ Review vulnerabilities in app.py
5. ✅ Run test_suite.py to validate
6. ✅ Execute exploit_poc.py to see attacks
7. ✅ Study how to fix each vulnerability

---

## Support

For issues:
1. Check README.md for architecture details
2. Check test_suite.py output for diagnostic info
3. Review inline comments in app.py
4. See exploit_poc.py for attack examples

