# VPN Admin Panel (FastAPI)

This is a Python/FastAPI conversion of the existing PHP VPN admin panel:
- `GET /index.php` login page
- `GET /dashboard.php` admin dashboard
- `GET|POST /api/*.php` endpoints used by the dashboard JavaScript

## Run (local)

```bash
cd python_vpn_admin
export SESSION_SECRET="change-me"
export ADMIN_USER="admin"
export ADMIN_PASS="StrongPassword"

./.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/index.php`

## Environment variables (main ones)

- `SESSION_SECRET`: required (signs the session cookie)
- `ADMIN_USER` / `ADMIN_PASS`: defaults match the PHP code
- `DB_PATH`: default `var/www/vpn/vpn.db` (or set to your real `vpn.db`)
- `OCPASSWD_PATH`: default `/usr/bin/ocpasswd`
- `OCCTL_PATH`: default `/usr/bin/occtl`
- `OC_PASSWD_DB`: default `/var/lib/ocserv/ocpasswd`
- `SYSTEMCTL_PATH`: default `/bin/systemctl`
- `USER_CONFIG_DIR`: default `/etc/ocserv/config-per-user`

## Notes

This app shells out to `sudo ocpasswd/occtl` and applies `iptables`.
The process running FastAPI must have the same `sudo` permissions the PHP app had.

