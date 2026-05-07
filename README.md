# 🛡️ VPN Admin Panel (FastAPI)

A secure VPN administration system built with **Python (FastAPI)** for managing VPN users, configurations, and system-level access control.  
This project is a modernization of a legacy PHP-based VPN admin panel into a fast, API-driven backend system.

---

## Packages to install
mod_ssl sqlite-libs php-common httpd-filesystem php-pdo httpd-tools php-cli php-mbstring php-fpm php-xml php-opcache httpd-core httpd php php-mysqlnd sqlite ocserv


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



visudo
apache ALL=NOPASSWD: /bin/systemctl start ocserv, /bin/systemctl stop ocserv, /bin/systemctl restart ocserv, /bin/systemctl is-active ocserv
