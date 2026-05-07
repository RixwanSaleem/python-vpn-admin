import json
import html
import ipaddress
import re
import secrets
import time
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from .auth import (
    validate_device_limit,
    validate_expiry,
    validate_bandwidth_kbps,
    validate_username,
    verify_panel_login,
    set_panel_admin_credentials,
    effective_panel_admin_username,
    validate_admin_username,
    USERNAME_RE,
)
from .config import settings
from .db import (
    clear_logs,
    create_user,
    delete_user,
    get_user_by_username,
    get_setting,
    insert_log,
    list_users,
    get_recent_logs_text,
    set_setting,
    update_user_profile,
)
from .ocserv import (
    CommandError,
    occtl_disconnect,
    occtl_disconnect_session,
    occtl_show_users,
    ocpasswd_delete,
    ocpasswd_set,
    ocserv_control,
    ocserv_status,
    write_user_config,
    delete_user_config,
    apply_firewall_for_db_users,
    parse_ocserv_routes,
    read_ocserv_conf_raw,
    write_ocserv_conf_raw,
)

_BASE_DIR = __import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
templates = Jinja2Templates(directory=__import__("os").path.join(_BASE_DIR, "templates"))

router = APIRouter()
_GEO_CACHE: dict[str, tuple[str, float]] = {}


def _get_csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def require_auth(request: Request) -> None:
    if not request.session.get("auth"):
        raise HTTPException(status_code=401, detail="Unauthorized")


def require_csrf_header(request: Request) -> None:
    expected = request.session.get("csrf_token")
    got = request.headers.get("X-CSRF-Token")
    if not expected or not got or got != expected:
        raise HTTPException(status_code=403, detail="CSRF token missing/invalid")


def _parse_live_sessions(raw: str) -> list[dict[str, str]]:
    # Dedicated table parser for occtl "show users" output.
    table_sessions: list[dict[str, str]] = []
    for line in (raw or "").splitlines():
        m = re.match(
            r"^\s*(\d+)\s+(\S+)\s+(\S+)\s+(\d{1,3}(?:\.\d{1,3}){3})\s+(\d{1,3}(?:\.\d{1,3}){3})\s+(\S+)\s+(.+?)\s+(connected|disconnected)\s*$",
            line.strip(),
            flags=re.I,
        )
        if m:
            table_sessions.append(
                {
                    "session_id": m.group(1),
                    "username": m.group(2),
                    "ip": m.group(4),
                    "connected_since": m.group(7),
                    "data_used": "",
                }
            )
    if table_sessions:
        return table_sessions

    # First pass: key/value block formats (common in many occtl versions).
    sessions: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in (raw or "").splitlines():
        s = line.strip()
        if not s:
            if current.get("username"):
                sessions.append(
                    {
                        "session_id": current.get("session_id", ""),
                        "username": current.get("username", ""),
                        "ip": current.get("ip", ""),
                        "connected_since": current.get("connected_since", ""),
                        "data_used": current.get("data_used", ""),
                    }
                )
            current = {}
            continue
        low = s.lower()
        m = re.match(r"^\s*([^:]+)\s*:\s*(.+)$", s)
        if not m:
            continue
        key = m.group(1).strip().lower()
        val = m.group(2).strip()
        if key in {"id", "session", "session id"} and val.isdigit():
            current["session_id"] = val
        elif key in {"user", "username"}:
            current["username"] = val.split()[0]
        elif key in {"ip", "ip address", "remote ip", "remote-ip"}:
            current["ip"] = val.split()[0]
        elif "connected" in key and "since" in key:
            current["connected_since"] = val
        elif "data" in key and ("used" in key or "recv" in key or "sent" in key):
            current["data_used"] = val

    if current.get("username"):
        sessions.append(
            {
                "session_id": current.get("session_id", ""),
                "username": current.get("username", ""),
                "ip": current.get("ip", ""),
                "connected_since": current.get("connected_since", ""),
                "data_used": current.get("data_used", ""),
            }
        )
    if sessions:
        return sessions

    # Second pass: table-like formats.
    sessions: list[dict[str, str]] = []
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        low = line.lower()
        if "username" in low and ("ip" in low or "address" in low):
            continue
        if "id" in low and "user" in low and ("ip" in low or "address" in low):
            continue
        if low.startswith("connected users"):
            continue
        if set(line) <= {"-", "="}:
            continue

        parts = re.split(r"\s{2,}", line)
        if len(parts) < 2:
            parts = line.split()
        if len(parts) < 2:
            continue

        session_id = ""
        username = ""
        ip_addr = ""
        connected_since = ""
        data_used = ""

        for p in parts:
            token = p.strip()
            if not token:
                continue
            if not session_id and token.isdigit():
                session_id = token
                continue
            if not ip_addr and re.match(r"^\d{1,3}(?:\.\d{1,3}){3}$", token):
                ip_addr = token
                continue
            if not data_used and re.match(r"^\d+(?:\.\d+)?\s*(?:[KMGTP]?B)$", token, flags=re.I):
                data_used = token
                continue
            if not username and re.match(r"^[a-zA-Z0-9_.@-]+$", token):
                # Prefer first username-like token that is not a numeric session id.
                username = token
                continue
            if not connected_since:
                connected_since = token

        if not username:
            username = parts[1].strip() if len(parts) > 1 else parts[0].strip()

        sessions.append(
            {
                "session_id": session_id,
                "username": username,
                "ip": ip_addr,
                "connected_since": connected_since,
                "data_used": data_used,
            }
        )
    return sessions


def _extract_online_usernames(raw: str) -> list[str]:
    found: set[str] = set()
    for line in (raw or "").splitlines():
        m = re.match(r"^\s*\d+\s+([^\s]+)\s+", line.strip())
        if m:
            found.add(m.group(1).lower())
    for line in (raw or "").splitlines():
        s = line.strip()
        if not s:
            continue
        m = re.search(r"(?i)\busername\s*[:=]\s*([a-zA-Z0-9_.@-]+)", s)
        if m:
            found.add(m.group(1).lower())

    if not found:
        for s in _parse_live_sessions(raw):
            u = (s.get("username") or "").strip().lower()
            if u:
                found.add(u)
    return sorted(found)


def _lookup_country_code(ip_addr: str) -> str:
    ip_clean = (ip_addr or "").strip()
    if not ip_clean:
        return ""
    try:
        ip_obj = ipaddress.ip_address(ip_clean)
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
            return "LOCAL"
    except Exception:
        return ""

    now = time.time()
    cached = _GEO_CACHE.get(ip_clean)
    if cached and cached[1] > now:
        return cached[0]

    try:
        url = f"http://ip-api.com/json/{urllib.parse.quote(ip_clean)}?fields=status,countryCode"
        with urllib.request.urlopen(url, timeout=2.5) as res:
            payload = json.loads(res.read().decode("utf-8", errors="ignore"))
        if payload.get("status") == "success":
            cc = (payload.get("countryCode") or "").upper()
            _GEO_CACHE[ip_clean] = (cc, now + 3600)
            return cc
    except Exception:
        pass
    _GEO_CACHE[ip_clean] = ("", now + 300)
    return ""


def _get_geo_policy() -> dict[str, Any]:
    mode = (get_setting("geo_mode", "off") or "off").strip().lower()
    if mode not in {"off", "allow", "block"}:
        mode = "off"
    countries_raw = get_setting("geo_countries", "")
    countries = sorted(
        {
            c.strip().upper()
            for c in countries_raw.split(",")
            if re.match(r"^[A-Za-z]{2}$", c.strip() or "")
        }
    )
    auto_enforce = get_setting("geo_auto_enforce", "0") == "1"
    return {"mode": mode, "countries": countries, "auto_enforce": auto_enforce}


def _is_country_allowed(country_code: str, policy: dict[str, Any]) -> bool:
    mode = policy.get("mode", "off")
    countries = set(policy.get("countries", []))
    cc = (country_code or "").upper()
    if mode == "off" or not cc or cc == "LOCAL":
        return True
    if mode == "allow":
        return cc in countries
    if mode == "block":
        return cc not in countries
    return True


@router.get("/index.php")
def index_get(request: Request):
    # Keep minimal behavior: render login page and an error (optional)
    return templates.TemplateResponse(
        "index.php",
        {"request": request, "error": request.query_params.get("error"), "year": datetime.now().year},
    )


@router.get("/")
def root():
    return RedirectResponse(url="/index.php", status_code=302)


@router.post("/index.php")
def index_post(
    request: Request,
    user: str = Form(""),
    pass_: str = Form("", alias="pass"),
):
    admin_user = (user or "").strip()
    admin_pass = pass_ or ""

    if verify_panel_login(admin_user, admin_pass):
        request.session["auth"] = True
        # Create CSRF token on successful login
        _get_csrf_token(request)
        return RedirectResponse(url="/dashboard.php", status_code=302)

    return templates.TemplateResponse(
        "index.php",
        {"request": request, "error": "Invalid login", "year": datetime.now().year},
        status_code=401,
    )


@router.get("/dashboard.php")
def dashboard_get(request: Request):
    if not request.session.get("auth"):
        return RedirectResponse(url="/index.php", status_code=302)
    csrf_token = _get_csrf_token(request)
    resp = templates.TemplateResponse("dashboard.php", {"request": request, "csrf_token": csrf_token})
    resp.headers["Cache-Control"] = "private, no-store, max-age=0, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Vary"] = "Cookie"
    return resp


@router.get("/api/logout.php", response_class=PlainTextResponse)
def logout(request: Request):
    request.session.clear()
    return "OK"


@router.get("/api/session.php")
def api_session(request: Request):
    require_auth(request)
    return JSONResponse(content={"ok": True, "user": effective_panel_admin_username()})


@router.get("/api/vpn_routes.php")
def api_vpn_routes(request: Request):
    require_auth(request)
    return JSONResponse(content=parse_ocserv_routes())


@router.post("/api/change_admin_password.php", response_class=PlainTextResponse)
def api_change_admin_password(
    request: Request,
    current_pass: str = Form(""),
    new_pass: str = Form(""),
    new_pass_confirm: str = Form(""),
    new_user: str = Form(""),
):
    require_auth(request)
    require_csrf_header(request)
    user_current = effective_panel_admin_username()
    if not verify_panel_login(user_current, current_pass or ""):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if (new_pass or "") != (new_pass_confirm or ""):
        raise HTTPException(status_code=400, detail="New passwords do not match")
    target_user = (new_user or "").strip() or user_current
    try:
        validate_admin_username(target_user)
        set_panel_admin_credentials(target_user, new_pass or "")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    insert_log("ADMIN_PASSWORD", target_user)
    return "OK"


@router.get("/api/ocserv_status.php")
def api_ocserv_status(request: Request):
    require_auth(request)
    return JSONResponse(content=ocserv_status())


@router.get("/api/ocserv_conf.php", response_class=PlainTextResponse)
def api_ocserv_conf_get(request: Request):
    require_auth(request)
    try:
        return read_ocserv_conf_raw()
    except CommandError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/ocserv_conf.php", response_class=PlainTextResponse)
async def api_ocserv_conf_post(request: Request):
    require_auth(request)
    require_csrf_header(request)
    content = (await request.body()).decode("utf-8", errors="replace")
    try:
        write_ocserv_conf_raw(content)
        insert_log("OCSERV_CONF", "update")
        return "OK"
    except CommandError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/live.php", response_class=PlainTextResponse)
def api_live(request: Request):
    require_auth(request)
    try:
        return occtl_show_users()
    except Exception as e:
        # Keep dashboard usable even if occtl command/socket is temporarily unavailable.
        return f"Live users unavailable: {e}"


@router.get("/api/live_json.php")
def api_live_json(request: Request):
    require_auth(request)
    try:
        raw = occtl_show_users()
        sessions = _parse_live_sessions(raw)
        policy = _get_geo_policy()
        disconnected: list[str] = []
        for s in sessions:
            cc = _lookup_country_code(s.get("ip", ""))
            s["country_code"] = cc or "-"
            allowed = _is_country_allowed(cc, policy)
            s["geo_allowed"] = allowed
            if policy.get("auto_enforce") and not allowed:
                sid = (s.get("session_id") or "").strip()
                try:
                    if sid:
                        occtl_disconnect_session(sid)
                        disconnected.append(sid)
                except Exception:
                    pass
        return JSONResponse(
            content={
                "sessions": sessions,
                "online_usernames": _extract_online_usernames(raw),
                "geo_policy": policy,
                "auto_disconnected_sessions": disconnected,
                "raw": raw,
            }
        )
    except Exception as e:
        return JSONResponse(
            content={
                "sessions": [],
                "online_usernames": [],
                "geo_policy": _get_geo_policy(),
                "auto_disconnected_sessions": [],
                "raw": f"Live users unavailable: {e}",
            }
        )


@router.get("/api/geo_policy.php")
def api_geo_policy_get(request: Request):
    require_auth(request)
    return JSONResponse(content=_get_geo_policy())


@router.post("/api/geo_policy.php", response_class=PlainTextResponse)
def api_geo_policy_set(
    request: Request,
    mode: str = Form("off"),
    countries: str = Form(""),
    auto_enforce: str = Form("0"),
):
    require_auth(request)
    require_csrf_header(request)

    mode_clean = (mode or "off").strip().lower()
    if mode_clean not in {"off", "allow", "block"}:
        raise HTTPException(status_code=400, detail="Invalid mode")
    parsed = sorted(
        {
            c.strip().upper()
            for c in (countries or "").split(",")
            if re.match(r"^[A-Za-z]{2}$", c.strip() or "")
        }
    )
    set_setting("geo_mode", mode_clean)
    set_setting("geo_countries", ",".join(parsed))
    set_setting("geo_auto_enforce", "1" if auto_enforce == "1" else "0")
    insert_log("GEO_POLICY", f"{mode_clean}:{','.join(parsed)}")
    return "OK"


@router.post("/api/geo_enforce.php")
def api_geo_enforce(request: Request):
    require_auth(request)
    require_csrf_header(request)
    policy = _get_geo_policy()
    if policy["mode"] == "off":
        return JSONResponse(content={"disconnected": []})
    disconnected: list[str] = []
    try:
        for s in _parse_live_sessions(occtl_show_users()):
            cc = _lookup_country_code(s.get("ip", ""))
            if not _is_country_allowed(cc, policy):
                sid = (s.get("session_id") or "").strip()
                if sid:
                    try:
                        occtl_disconnect_session(sid)
                        disconnected.append(sid)
                    except Exception:
                        pass
    except Exception:
        pass
    return JSONResponse(content={"disconnected": disconnected})


@router.get("/api/users.php")
def api_users(request: Request):
    require_auth(request)
    rows = list_users()
    return JSONResponse(
        content=[
            {
                "username": r["username"] or "",
                "expiry": r["expiry"] or "",
                "device_limit": r["device_limit"] if r["device_limit"] is not None else 0,
                "vpn_ip": r["vpn_ip"] or "",
                "allowed_ips": r["allowed_ips"] or "",
                "bandwidth_kbps": r["bandwidth_kbps"] if r["bandwidth_kbps"] is not None else 0,
            }
            for r in rows
        ]
    )


@router.get("/api/stats.php")
def api_stats(request: Request):
    require_auth(request)
    users = list_users()
    total_users = len(users)

    expiring_soon = 0
    now = datetime.now()
    for u in users:
        expiry = (u["expiry"] or "").strip()
        if not expiry:
            continue
        try:
            dt = datetime.strptime(expiry, "%d-%m-%Y")
            days = (dt.date() - now.date()).days
            if 0 <= days <= 7:
                expiring_soon += 1
        except Exception:
            continue

    online = 0
    try:
        live = occtl_show_users()
        online = len(_extract_online_usernames(live))
    except Exception:
        online = 0

    return JSONResponse(
        content={
            "total_users": total_users,
            "online": online,
            "expiring_soon": expiring_soon,
            "traffic_today": "N/A",
        }
    )


@router.get("/api/list.php", response_class=HTMLResponse)
def api_list(request: Request):
    require_auth(request)
    rows = list_users()

    out = (
        "<tr>"
        "<th>User</th><th>Expiry</th><th>Limit</th><th>Actions</th>"
        "</tr>"
    )

    for r in rows:
        u = r["username"] or ""
        expiry = r["expiry"] or ""
        limit = r["device_limit"] if r["device_limit"] is not None else ""

        # Use json dumps to safely create JS string literals.
        u_js = json.dumps(u)
        out += (
            "<tr>"
            f"<td>{html.escape(str(u))}</td>"
            f"<td>{html.escape(str(expiry))}</td>"
            f"<td>{html.escape(str(limit))}</td>"
            "<td>"
            f"<button onclick='resetUser({u_js})'>Reset</button>"
            f"<button onclick='disconnectUser({u_js})'>Kick</button>"
            f"<button onclick='deleteUser({u_js})'>Delete</button>"
            "</td>"
            "</tr>"
        )
    return out


@router.get("/api/logs.php", response_class=PlainTextResponse)
def api_logs(request: Request):
    require_auth(request)
    return get_recent_logs_text(50)


@router.post("/api/logs_clear.php", response_class=PlainTextResponse)
def api_logs_clear(request: Request):
    require_auth(request)
    require_csrf_header(request)
    clear_logs()
    insert_log("LOGS_CLEAR", "system")
    return "OK"


@router.post("/api/ocserv_control.php", response_class=PlainTextResponse)
def api_ocserv_control(request: Request, action: str = Form("")):
    require_auth(request)
    require_csrf_header(request)
    try:
        ocserv_control(action)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    insert_log(action.upper(), "system")
    return "OK"


@router.post("/api/create.php", response_class=PlainTextResponse)
def api_create(
    request: Request,
    user: str = Form(""),
    pass_: str = Form("", alias="pass"),
    expiry: str = Form(""),
    limit: str = Form("0"),
    vpn_ip: str = Form(""),
    allowed_ips: str = Form(""),
    bandwidth_kbps: str = Form("0"),
):
    require_auth(request)
    require_csrf_header(request)

    try:
        username = validate_username(user)
        password = pass_ or ""
        if not password:
            raise ValueError("Invalid password")

        expiry_raw = (expiry or "").strip()
        expiry_valid = validate_expiry(expiry_raw) if expiry_raw else ""

        limit_raw = (limit or "").strip()
        device_limit = validate_device_limit(limit_raw) if limit_raw else 0

        vpn_ip_val = (vpn_ip or "").strip()
        if vpn_ip_val:
            ip = ipaddress.ip_address(vpn_ip_val)
            if ip.version != 4:
                raise ValueError("Only IPv4 vpn_ip is supported")
        allowed_raw = (allowed_ips or "").strip()
        bandwidth = validate_bandwidth_kbps(bandwidth_kbps)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        # Create/Update password in ocserv
        ocpasswd_set(username, password)

        if vpn_ip_val or bandwidth > 0:
            write_user_config(username, vpn_ip_val or None, bandwidth)
            # Force reconnect so static IP/bandwidth profile is applied immediately.
            try:
                occtl_disconnect(username)
            except Exception:
                pass

        create_user(
            username=username,
            expiry=expiry_valid,
            device_limit=device_limit,
            vpn_ip=vpn_ip_val or None,
            allowed_ips=allowed_raw or None,
            bandwidth_kbps=bandwidth,
        )
        insert_log("CREATE", username)
        return "OK"
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/bulk_create.php")
def api_bulk_create(request: Request, lines: str = Form("")):
    require_auth(request)
    require_csrf_header(request)
    raw = (lines or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="No users provided")

    created: list[str] = []
    failed: list[dict[str, str]] = []

    for idx, line in enumerate(raw.splitlines(), start=1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = [p.strip() for p in s.split(",")]
        # Allow CSV template/header line.
        if parts and parts[0].strip().lower() == "username":
            continue
        if len(parts) < 2:
            failed.append({"line": str(idx), "error": "Need at least username,password"})
            continue
        user = parts[0]
        password = parts[1]
        expiry = parts[2] if len(parts) > 2 else ""
        limit = parts[3] if len(parts) > 3 else "0"
        vpn_ip = parts[4] if len(parts) > 4 else ""
        allowed_ips = parts[5] if len(parts) > 5 else ""
        bandwidth_raw = parts[6] if len(parts) > 6 else "0"

        try:
            username = validate_username(user)
            if not password:
                raise ValueError("Invalid password")
            expiry_valid = validate_expiry(expiry) if expiry else ""
            device_limit = validate_device_limit(limit) if limit else 0
            bandwidth = validate_bandwidth_kbps(bandwidth_raw)
            vpn_ip_val = (vpn_ip or "").strip()
            if vpn_ip_val:
                ip = ipaddress.ip_address(vpn_ip_val)
                if ip.version != 4:
                    raise ValueError("Only IPv4 vpn_ip is supported")

            ocpasswd_set(username, password)
            if vpn_ip_val or bandwidth > 0:
                write_user_config(username, vpn_ip_val or None, bandwidth)
            create_user(
                username=username,
                expiry=expiry_valid,
                device_limit=device_limit,
                vpn_ip=vpn_ip_val or None,
                allowed_ips=allowed_ips or None,
                bandwidth_kbps=bandwidth,
            )
            insert_log("CREATE", username)
            created.append(username)
        except Exception as e:
            failed.append({"line": str(idx), "user": user, "error": str(e)})

    return JSONResponse(content={"created": created, "failed": failed})


@router.post("/api/update_user.php", response_class=PlainTextResponse)
def api_update_user(
    request: Request,
    user: str = Form(""),
    expiry: str = Form(""),
    bandwidth_kbps: str = Form("0"),
):
    require_auth(request)
    require_csrf_header(request)
    username = validate_username(user)

    row = get_user_by_username(username)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    expiry_raw = (expiry or "").strip()
    expiry_valid = validate_expiry(expiry_raw) if expiry_raw else ""
    bandwidth = validate_bandwidth_kbps(bandwidth_kbps)

    vpn_ip = (row["vpn_ip"] or "").strip()
    try:
        if vpn_ip or bandwidth > 0:
            write_user_config(username, vpn_ip or None, bandwidth)
        update_user_profile(username, expiry_valid, bandwidth)
        insert_log("UPDATE", username)
        return "OK"
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/bulk_template.csv")
def api_bulk_template_csv(request: Request):
    require_auth(request)
    sample = (
        "username,password,expiry,limit,vpn_ip,allowed_ips,bandwidth_kbps\n"
        "user1,pass123,2026-12-31,2,10.10.10.51,\"8.8.8.8,1.1.1.1\",2048\n"
        "user2,pass456,2026-12-31,1,10.10.10.52,,1024\n"
    )
    return Response(
        content=sample,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bulk_users_template.csv"},
    )


@router.post("/api/bulk_delete.php")
def api_bulk_delete(request: Request, users: str = Form("")):
    require_auth(request)
    require_csrf_header(request)
    names = [u.strip() for u in (users or "").split(",") if u.strip()]
    if not names:
        raise HTTPException(status_code=400, detail="No users selected")

    deleted: list[str] = []
    failed: list[dict[str, str]] = []
    for username in names:
        if not USERNAME_RE.match(username):
            failed.append({"user": username, "error": "Invalid username"})
            continue
        try:
            try:
                ocpasswd_delete(username)
            except Exception:
                pass
            delete_user(username)
            delete_user_config(username)
            insert_log("DELETE", username)
            deleted.append(username)
        except Exception as e:
            failed.append({"user": username, "error": str(e)})
    return JSONResponse(content={"deleted": deleted, "failed": failed})


@router.post("/api/delete.php", response_class=PlainTextResponse)
def api_delete(request: Request, user: str = Form("")):
    require_auth(request)
    require_csrf_header(request)

    username = (user or "").strip()
    if not USERNAME_RE.match(username or ""):
        raise HTTPException(status_code=400, detail="Invalid username")

    try:
        ocpasswd_delete(username)
    except Exception:
        # Deleting panel DB entry should still work even if ocpasswd delete fails.
        pass

    # DB + optional per-user config removal
    delete_user(username)
    delete_user_config(username)
    insert_log("DELETE", username)
    return "OK"


@router.post("/api/disconnect.php", response_class=PlainTextResponse)
def api_disconnect(request: Request, user: str = Form(""), session_id: str = Form("")):
    require_auth(request)
    require_csrf_header(request)
    username = (user or "").strip()
    sid = (session_id or "").strip()

    if sid:
        try:
            occtl_disconnect_session(sid)
            insert_log("DISCONNECT", f"session:{sid}")
            return "OK"
        except Exception as e:
            msg = str(e).lower()
            if (
                "not found" not in msg
                and "no such" not in msg
                and "does not exist" not in msg
                and "offline" not in msg
                and "no users matched" not in msg
            ):
                raise HTTPException(status_code=500, detail=str(e))
            return "OK"

    if not USERNAME_RE.match(username or ""):
        raise HTTPException(status_code=400, detail="Invalid username")

    try:
        occtl_disconnect(username)
    except Exception as e:
        msg = str(e).lower()
        # Disconnecting a currently offline/non-existing session should be non-fatal.
        if (
            "not found" not in msg
            and "no such" not in msg
            and "does not exist" not in msg
            and "offline" not in msg
            and "no users matched" not in msg
        ):
            raise HTTPException(status_code=500, detail=str(e))

    insert_log("DISCONNECT", username)
    return "OK"


@router.post("/api/reset.php", response_class=PlainTextResponse)
def api_reset(request: Request, user: str = Form(""), pass_: str = Form("", alias="pass")):
    require_auth(request)
    require_csrf_header(request)
    username = (user or "").strip()
    password = pass_ or ""
    if not USERNAME_RE.match(username or ""):
        raise HTTPException(status_code=400, detail="Invalid username")
    if not password:
        raise HTTPException(status_code=400, detail="Invalid password")

    try:
        # PHP uses ocpasswd -c ... username (with stdin password confirmation)
        ocpasswd_set(username, password)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    insert_log("RESET", username)
    return "OK"


@router.get("/api/firewall.php", response_class=PlainTextResponse)
def api_firewall(request: Request):
    require_auth(request)
    try:
        rows = list_users()
        users = [dict(r) for r in rows]
        apply_firewall_for_db_users(users)
        return "OK"
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

