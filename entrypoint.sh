#!/bin/bash
# Initialize DB
python3 -c "import sqlite3; conn = sqlite3.connect('/app/atlas_vault.db'); cursor = conn.cursor(); cursor.execute('CREATE TABLE IF NOT EXISTS users (email TEXT, password TEXT, role TEXT)'); cursor.execute(\"INSERT OR IGNORE INTO users VALUES ('john.architect@atlas-construction.com','Johan@123','architect')\"); conn.commit(); conn.close()"

# Run the app as appuser
exec python3 app.py
# Set Append-Only attribute (Requires --cap-add LINUX_IMMUTABLE in docker run)
# RUN chattr +a /app/logs/atlas.log

# Credential Breadcrumb (T1552)
RUN echo "ATLAS_USER_PASS=Atlas123!" > /app/.env
RUN chown appuser:appuser /app/.env /app/app.py /app/entrypoint.sh

# Initialize SQLite permissions
RUN touch /app/atlas_vault.db && chown appuser:appuser /app/atlas_vault.db

# SSH Setup
RUN mkdir -p /var/run/sshd
EXPOSE 5000 22

RUN chmod +x /app/entrypoint.sh
CMD ["/app/entrypoint.sh"]
