# 🛡️ VPN Admin Panel (FastAPI)

A secure VPN administration system built with **Python (FastAPI)** for managing VPN users, configurations, and system-level access control.  
This project is a modernization of a legacy PHP-based VPN admin panel into a fast, API-driven backend system.

---

## Packages to install
mod_ssl sqlite-libs php-common httpd-filesystem php-pdo httpd-tools php-cli php-mbstring php-fpm php-xml php-opcache httpd-core httpd php php-mysqlnd sqlite ocserv certbot python3-certbot-apache  bind-utils openssl -y

## if you download project to local machine 

scp vpn_admin_backup.tar.gz root@aYour-Server-Ip:/root/

## once project files uploaded run below to place  

mkdir -p /opt/vpn-panel && tar -xzvf /root/vpn_admin_backup.tar.gz -C /opt/vpn-panel/

## delete unnecessary files
find /opt/vpn-panel/ -name "._*" -delete

## remove old env
rm -rf /opt/vpn-panel/python_vpn_admin/.venv


## enter to env
cd /opt/vpn-panel/python_vpn_admin
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt


## 🚀 Project Highlights

- Modern FastAPI backend replacing legacy PHP system  
- REST API for VPN user and configuration management  
- Secure session-based authentication system  
- Integration with Linux services (`ocserv`, `iptables`, `systemctl`)  
- Environment-based configuration for flexibility and security  
- Compatible with existing PHP frontend routes (`index.php`, `dashboard.php`)  

---

## 🎯 Purpose

This project was built to modernize a legacy VPN administration system by replacing PHP-based endpoints with a scalable FastAPI backend while maintaining compatibility with existing frontend workflows and system tools.

---

## 🧰 Tech Stack

- Python 3.x  
- FastAPI  
- Uvicorn  
- Linux system tools (`occtl`, `ocpasswd`, `iptables`)  
- SQLite / system-based DB (depending on configuration)  

---

## 🚀 Run Locally

```bash
cd python_vpn_admin

export SESSION_SECRET="change-me"
export ADMIN_USER="admin"
export ADMIN_PASS="StrongPassword"

uvicorn main:app --host 0.0.0.0 --port 8000

Then open

http://localhost:8000


📁 Project Structure

 python_vpn_admin/

│── main.py

│── routes/

│── services/

│── utils/

│── config/

│── templates/

│── static/

│── requirements.txt

│── README.md



⚠️ Security Notes

* This application executes system-level commands (ocpasswd, occtl, iptables)
* Requires proper sudo permissions for the FastAPI process
* Should only be used in trusted or internal environments
* Not intended for public exposure without proper security hardening


📌 Status

✔ Active project
✔ PHP → FastAPI migration completed
✔ Backend fully functional
✔ Ready for production hardening and improvements

## Firewall Rules

firewall-cmd --permanent --add-port=8443/tcp
firewall-cmd --reload

## Create Services Environment 
nano /etc/vpn-panel.env


SESSION_SECRET=CHANGE_THIS_LONG_RANDOM_SECRET
ADMIN_USER=admin
ADMIN_PASS=PASS_FOR_PANEL

DB_PATH=/opt/vpn_admin_python/python_vpn_admin/var/vpn.db
OCPASSWD_PATH=/usr/bin/ocpasswd
OC_PASSWD_DB=/var/lib/ocserv/ocpasswd
OCCTL_PATH=/usr/bin/occtl
SYSTEMCTL_PATH=/usr/bin/systemctl
OCSERV_SERVICE=ocserv
USER_CONFIG_DIR=/etc/ocserv/config-per-user
IPTABLES_BIN=/usr/sbin/iptables
SUDO_BIN=
#OCCTL_SOCKET_FILE=/var/run/occtl.socket
OCCTL_SOCKET_FILE=/var/run/occtl.socket


## Create Services File

cat <<EOF > /etc/systemd/system/vpn-panel.service
[Unit]
Description=VPN Python Panel
After=network.target

[Service]
WorkingDirectory=/opt/vpn-panel/python_vpn_admin
# Ensure this matches where your .env file is actually located
EnvironmentFile=/etc/vpn-panel.env
ExecStart=/opt/vpn-panel/python_vpn_admin/venv/bin/uvicorn main:app \
    --host 0.0.0.0 \
    --port 8443 \
    --ssl-certfile /etc/letsencrypt/live/DOMAIN/fullchain.pem \
    --ssl-keyfile /etc/letsencrypt/live/DOMAIN/privkey.pem
Restart=always
User=root
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target

EOF

# Reload and Restart
systemctl daemon-reload
systemctl restart vpn-panel

# Show Status
systemctl status vpn-panel



## Make Sure of ocserv.conf

 cat /etc/ocserv/ocserv.conf
auth = "plain[/var/lib/ocserv/ocpasswd]"
tcp-port = 443
udp-port = 443
run-as-user = nobody
run-as-group = nobody

socket-file = /run/ocserv.sock

server-cert = /etc/letsencrypt/live/Your-Domain/fullchain.pem
server-key = /etc/letsencrypt/live/Your-Domain/privkey.pem

max-clients = 100
max-same-clients = 2

try-mtu-discovery = true
dns = 8.8.8.8
dns = 1.1.1.1

ipv4-network = 10.10.10.0
ipv4-netmask = 255.255.255.0

#route = default
route = 0.0.0.0/1
route = 128.0.0.0/1
no-route = Your server ip/32

tunnel-all-dns = false

cisco-client-compat = true

config-per-user = /etc/ocserv/config-per-user/
# config-per-group = /etc/ocserv/config-per-group/

device = vpns
use-occtl = true
occtl-socket-file = /var/run/occtl.socket



## Finally

systemctl restart ocserv
systemctl daemon-reload
systemctl restart vpn-panel
