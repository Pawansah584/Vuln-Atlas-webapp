#!/bin/bash
# Atlas Industrial - Secure Entrypoint Script

# 1. Start SSH Service (Requires Root)
mkdir -p /var/run/sshd
chmod 0755 /var/run/sshd
ssh-keygen -A
echo "[*] Starting SSH Service..."
/usr/sbin/sshd

# 2. Initialize the Atlas Vault Database
# Run as appuser to ensure correct file ownership
echo "[*] Initializing Atlas Vault Database..."
# This command uses base directory logic from app.py, but we'll manually ensure table existence here too.
su - appuser -c "python3 -c \"import sqlite3; import os; db_path = os.path.join(os.getcwd(), 'atlas_vault.db'); conn = sqlite3.connect(db_path); cursor = conn.cursor(); cursor.execute('CREATE TABLE IF NOT EXISTS users (email TEXT, password TEXT, role TEXT)'); cursor.execute(\\\"INSERT OR IGNORE INTO users VALUES ('john.architect@atlas-construction.com','Johan@123','architect')\\\"); cursor.execute(\\\"INSERT OR IGNORE INTO users VALUES ('sarah.admin@atlas-construction.com','AdminSecure99!','admin')\\\"); conn.commit(); conn.close()\""

# 3. Start the Flask Web Application
# Switch to appuser for the web application (Security Best Practice)
echo "[*] Starting Atlas Provisioning Portal on port 5000..."
exec su - appuser -c "python3 /app/app.py"