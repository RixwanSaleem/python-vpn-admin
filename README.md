# 🛡️ VPN Admin Panel (FastAPI)

A secure VPN administration system built with **Python (FastAPI)** for managing VPN users, configurations, and system-level access control.  
This project is a modernization of a legacy PHP-based VPN admin panel into a fast, API-driven backend system.

---

## 📦 System Dependencies
Install the required system packages for Rocky Linux:
```bash
sudo dnf install ocserv sqlite certbot python3-certbot-apache bind-utils openssl gcc python3-devel -y
```

## 📂 Deployment Steps

### 1. Upload and Extract
If you have the project on a local machine, upload it:
```bash
scp vpn_admin_backup.tar.gz root@YOUR_SERVER_IP:/root/
```

Extract to the production directory:
```bash
mkdir -p /opt/vpn-panel
tar -xzvf /root/vpn_admin_backup.tar.gz -C /opt/vpn-panel/
# Clean up MacOS metadata files if present
find /opt/vpn-panel/ -name "._*" -delete
```

### 2. Python Environment Setup
```bash
cd /opt/vpn-panel/python_vpn_admin
rm -rf venv  # Remove old environment if exists
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configuration Setup
Create the environment file:
`nano /etc/vpn-panel.env`

```ini
SESSION_SECRET=CHANGE_THIS_LONG_RANDOM_SECRET
ADMIN_USER=admin
ADMIN_PASS=YOUR_STRONG_PASSWORD

DB_PATH=/opt/vpn-panel/python_vpn_admin/var/vpn.db
OCPASSWD_PATH=/usr/bin/ocpasswd
OC_PASSWD_DB=/var/lib/ocserv/ocpasswd
OCCTL_PATH=/usr/bin/occtl
SYSTEMCTL_PATH=/usr/bin/systemctl
OCSERV_SERVICE=ocserv
USER_CONFIG_DIR=/etc/ocserv/config-per-user
IPTABLES_BIN=/usr/sbin/iptables
OCCTL_SOCKET_FILE=/var/run/occtl.socket
```

### 4. Firewall & Permissions
```bash
# Open Panel Port
firewall-cmd --permanent --add-port=8443/tcp
firewall-cmd --reload

# Create Per-User Config Directory (For Static IPs)
mkdir -p /etc/ocserv/config-per-user
chown -R nobody:nobody /etc/ocserv/config-per-user
chmod 755 /etc/ocserv/config-per-user
```

### 5. Systemd Service Integration
Create the service file:
`nano /etc/systemd/system/vpn-panel.service`

```ini
[Unit]
Description=VPN Python Panel
After=network.target

[Service]
WorkingDirectory=/opt/vpn-panel/python_vpn_admin
EnvironmentFile=/etc/vpn-panel.env
ExecStart=/opt/vpn-panel/python_vpn_admin/venv/bin/uvicorn main:app \
    --host 0.0.0.0 \
    --port 8443 \
    --ssl-certfile /etc/letsencrypt/live/alfasolution.org/fullchain.pem \
    --ssl-keyfile /etc/letsencrypt/live/alfasolution.org/privkey.pem
Restart=always
User=root
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

### 6. OCserv Configuration (`/etc/ocserv/ocserv.conf`)
Ensure these lines are set correctly to enable the panel's features:
```ini
# User database
auth = "plain[/var/lib/ocserv/ocpasswd]"

# Socket for Live Status (Fixed Path)
use-occtl = true
occtl-socket-file = /var/run/occtl.socket

# Per-User Config for Static IPs
config-per-user = /etc/ocserv/config-per-user/
```

### 7. Start Services
```bash
systemctl daemon-reload
systemctl enable ocserv vpn-panel
systemctl restart ocserv
systemctl restart vpn-panel

# Fix socket permissions (Run after ocserv start)
chmod 666 /var/run/occtl.socket
```

---

## 🎯 Tech Stack
- **FastAPI**: Backend Framework
- **Uvicorn**: ASGI Server
- **OCserv**: OpenConnect VPN Server
- **SQLite**: Database for user management

## ⚠️ Security Notes
- Running as **root** is required to execute `ocpasswd` and `iptables`.
- Ensure SELinux is configured or disabled to allow the panel to read the SSL certs and the occtl socket.
