# 🛡️ VPN Admin Panel (FastAPI)

A secure VPN administration system built with **Python (FastAPI)** for managing VPN users, configurations, and system-level access control.  
This project is a modernization of a legacy PHP-based VPN admin panel into a fast, API-driven backend system.

---

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


http://localhost:8000


