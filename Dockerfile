FROM python:3.9-slim

# Install system dependencies (C2-ready: wget, socat, iproute2)
RUN apt-get update && apt-get install -y \
    openssh-server \
    cron \
    e2fsprogs \
    curl \
    wget \
    socat \
    iproute2 \
    procps \
    netcat-traditional \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Create Users for Lateral Movement and Privilege Escalation labs
# atlasuser: The pivot target for root escalation via 'find'
# appuser: The restricted low-priv user that runs the Web App
RUN useradd -m -s /bin/bash atlasuser && echo "atlasuser:Atlas123!" | chpasswd
RUN useradd -m appuser

# Set up Sudo privilege for the 'find' bin exploit (The Escalation Goal)
RUN echo "atlasuser ALL=(root) NOPASSWD: /usr/bin/find" >> /etc/sudoers

# Setup App Directory
WORKDIR /app
COPY app.py /app/
COPY entrypoint.sh /app/
RUN pip install flask requests PyJWT flask-cors

# Ensure app runs as low-priv 'appuser'
USER appuser

# Setup Log Directory (Forensics Challenge)
USER root
RUN mkdir -p /app/logs && chown appuser:appuser /app/logs && chmod 755 /app/logs
RUN touch /app/logs/atlas.log && chown appuser:appuser /app/logs/atlas.log && chmod 644 /app/logs/atlas.log
USER appuser
# Set Append-Only attribute (Requires --cap-add LINUX_IMMUTABLE in docker run)
# RUN chattr +a /app/logs/atlas.log

# Credential Breadcrumb (T1552)
# Realistic Leaks for Lateral Movement:
# 1. Container User Credentials
RUN echo "ATLAS_USER_PASS=Atlas123!" > /app/.env
# 2. Host System Discovery (Simulated Backup/Discovery file)
# In a real Red Team scenario, finding a host-specific admin credential 
# inside a container is a "Critical" finding leading to Host Compromise.
RUN echo "HOST_ADMIN=atlas" >> /app/.env
RUN echo "HOST_RECOVERY_KEY=Atlas@2026" >> /app/.env
RUN chown appuser:appuser /app/.env /app/app.py /app/entrypoint.sh

# Initialize SQLite permissions
RUN touch /app/atlas_vault.db && chown appuser:appuser /app/atlas_vault.db

# SSH Setup
RUN mkdir -p /var/run/sshd
EXPOSE 5000 22

RUN chmod +x /app/entrypoint.sh
CMD ["/app/entrypoint.sh"]
