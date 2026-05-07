import ipaddress
import os
import re
import shlex
import subprocess
from typing import Any, Iterable

from .config import settings


class CommandError(RuntimeError):
    pass


def _cmd_with_optional_sudo(cmd: list[str]) -> list[str]:
    sudo_bin = (settings.sudo_bin or "").strip()
    if sudo_bin:
        return [sudo_bin, *cmd]
    return cmd


def _log_debug(cmd_str: str, output: str) -> None:
    path = settings.debug_log_path
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(cmd_str + "\n" + output + "\n")
    except Exception:
        # Debug logging should never crash the API.
        pass


def run(cmd: list[str], input_text: str | None = None) -> str:
    full_cmd = _cmd_with_optional_sudo(cmd)
    cmd_str = " ".join(full_cmd)

    proc = subprocess.run(
        full_cmd,
        input=input_text,
        text=True,
        capture_output=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    _log_debug(cmd_str, out)

    if proc.returncode != 0:
        raise CommandError(out.strip() or f"Command failed: {cmd_str}")
    return out


def _occtl_base_cmd() -> list[str]:
    cmd = [settings.occtl_path, "-n"]
    socket = (settings.occtl_socket_file or "").strip()
    if socket:
        cmd.extend(["--socket-file", socket])
    return cmd


def ocserv_status() -> dict[str, str]:
    full_cmd = _cmd_with_optional_sudo([settings.systemctl_path, "is-active", settings.ocserv_service])
    proc = subprocess.run(full_cmd, text=True, capture_output=True)
    status = (proc.stdout or "").strip().lower()
    _log_debug(" ".join(full_cmd), (proc.stdout or "") + (proc.stderr or ""))
    if status == "active":
        return {"status": "Running", "color": "#16a34a"}
    if status in {"inactive", "failed", "deactivating"} or proc.returncode != 0:
        return {"status": "Stopped", "color": "#dc2626"}
    return {"status": "Unknown", "color": "#f59e0b"}


def ocserv_control(action: str) -> None:
    if action not in {"start", "stop"}:
        raise ValueError("Invalid action")
    run([settings.systemctl_path, action, settings.ocserv_service])


def occtl_show_users() -> str:
    return run([*_occtl_base_cmd(), "show", "users"])


def occtl_disconnect(username: str) -> None:
    # Different occtl versions accept different disconnect forms.
    errors: list[str] = []
    for args in (
        [*_occtl_base_cmd(), "disconnect", "user", username],
        [*_occtl_base_cmd(), "disconnect", username],
    ):
        try:
            run(args)
            return
        except Exception as e:
            errors.append(str(e))
    raise CommandError(" | ".join(errors))


def occtl_disconnect_session(session_id: str) -> None:
    sid = (session_id or "").strip()
    if not sid:
        raise ValueError("Invalid session id")

    errors: list[str] = []
    for args in (
        [*_occtl_base_cmd(), "disconnect", "id", sid],
        [*_occtl_base_cmd(), "disconnect", "session", sid],
        [*_occtl_base_cmd(), "disconnect", sid],
    ):
        try:
            run(args)
            return
        except Exception as e:
            errors.append(str(e))
    raise CommandError(" | ".join(errors))


def ocpasswd_set(username: str, password: str) -> None:
    # Try direct stdin first.
    input_text = f"{password}\n{password}\n"
    errors: list[str] = []
    try:
        run(
            [settings.ocpasswd_path, "-c", settings.ocpasswd_db_path, username],
            input_text=input_text,
        )
        return
    except Exception as e:
        errors.append(str(e))

    # Fallback: shell pipeline (same approach used in original PHP).
    sudo_prefix = f"{settings.sudo_bin} " if (settings.sudo_bin or "").strip() else ""
    shell_cmd = (
        f"printf '%s\\n%s\\n' {shlex.quote(password)} {shlex.quote(password)}"
        f" | {sudo_prefix}{shlex.quote(settings.ocpasswd_path)} -c {shlex.quote(settings.ocpasswd_db_path)} {shlex.quote(username)}"
    )
    proc = subprocess.run(["/bin/sh", "-lc", shell_cmd], text=True, capture_output=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    _log_debug(shell_cmd, out)
    if proc.returncode == 0:
        return
    errors.append(out.strip() or "fallback ocpasswd_set failed")
    raise CommandError(" | ".join(errors))


def ocpasswd_delete(username: str) -> None:
    errors: list[str] = []
    try:
        run([settings.ocpasswd_path, "-c", settings.ocpasswd_db_path, "-d", username])
        return
    except Exception as e:
        errors.append(str(e))

    # Fallback: ignore if user is absent; force success for panel DB cleanup path.
    # ocpasswd has no easy list mode; absence checks are handled by caller.
    raise CommandError(" | ".join(errors))


def write_user_config(username: str, vpn_ip: str | None = None, bandwidth_kbps: int = 0) -> None:
    # ocserv per-user config.
    path = os.path.join(settings.user_config_dir, username)
    lines: list[str] = []
    if (vpn_ip or "").strip():
        # Newer ocserv expects explicit-ipv4 for per-user static assignment.
        # Keep ipv4 line as compatibility fallback for older builds.
        ip_val = vpn_ip.strip()
        lines.append(f"explicit-ipv4 = {ip_val}")
        lines.append(f"ipv4 = {ip_val}")
    if bandwidth_kbps > 0:
        bytes_per_sec = bandwidth_kbps * 1024 // 8
        lines.append(f"rx-data-per-sec = {bytes_per_sec}")
        lines.append(f"tx-data-per-sec = {bytes_per_sec}")
    body = ("\n".join(lines) + "\n") if lines else ""

    if not body:
        return

    try:
        os.makedirs(settings.user_config_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
        return
    except PermissionError:
        # Fallback for deployments where app user cannot write /etc directly.
        pass

    sudo_prefix = f"{settings.sudo_bin} " if (settings.sudo_bin or "").strip() else ""
    shell_cmd = (
        f"{sudo_prefix}mkdir -p {shlex.quote(settings.user_config_dir)}"
        f" && printf %s {shlex.quote(body)}"
        f" | {sudo_prefix}tee {shlex.quote(path)} >/dev/null"
    )
    proc = subprocess.run(["/bin/sh", "-lc", shell_cmd], text=True, capture_output=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    _log_debug(shell_cmd, out)
    if proc.returncode != 0:
        raise CommandError(out.strip() or "failed to write user config")


def delete_user_config(username: str) -> None:
    path = os.path.join(settings.user_config_dir, username)
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def _validate_ipv4_or_cidr(value: str) -> str:
    v = value.strip()
    if not v:
        raise ValueError("Empty target")
    # Accept single IPs and CIDRs, IPv4 only (mirrors likely ocserv usage).
    if "/" in v:
        net = ipaddress.ip_network(v, strict=False)
        if net.version != 4:
            raise ValueError("Only IPv4 is supported")
        return str(net)
    ip = ipaddress.ip_address(v)
    if ip.version != 4:
        raise ValueError("Only IPv4 is supported")
    return str(ip)


def _parse_allowed_ips(allowed_ips_raw: str) -> list[str]:
    parts = [p.strip() for p in (allowed_ips_raw or "").split(",")]
    return [_validate_ipv4_or_cidr(p) for p in parts if p]


def apply_firewall_for_db_users(db_users: Iterable[dict]) -> None:
    # Mirrors PHP firewall.php behavior, but with safer parsing/validation.
    # It flushes a custom chain, rebuilds rules for each vpn_user, and ensures
    # FORWARD jumps to that chain.

    # Flush old rules (ignore failure if chain doesn't exist)
    try:
        subprocess.run(_cmd_with_optional_sudo([settings.iptables_bin, "-F", settings.vpn_chain_name]), capture_output=True)
    except Exception:
        pass

    # Create chain if not exists
    subprocess.run(
        _cmd_with_optional_sudo([settings.iptables_bin, "-N", settings.vpn_chain_name]),
        capture_output=True,
    )

    # Ensure FORWARD -> VPN_USERS
    chk = subprocess.run(
        _cmd_with_optional_sudo([settings.iptables_bin, "-C", "FORWARD", "-j", settings.vpn_chain_name]),
        capture_output=True,
    )
    if chk.returncode != 0:
        subprocess.run(
            _cmd_with_optional_sudo([settings.iptables_bin, "-A", "FORWARD", "-j", settings.vpn_chain_name]),
            capture_output=True,
        )

    for user in db_users:
        ip = (user.get("vpn_ip") or "").strip()
        allowed_raw = (user.get("allowed_ips") or "").strip()
        if not ip or not allowed_raw:
            continue
        src = _validate_ipv4_or_cidr(ip)
        targets = _parse_allowed_ips(allowed_raw)
        for t in targets:
            run(
                [
                    settings.iptables_bin,
                    "-A",
                    settings.vpn_chain_name,
                    "-s",
                    src,
                    "-d",
                    t,
                    "-j",
                    "ACCEPT",
                ]
            )
        run([settings.iptables_bin, "-A", settings.vpn_chain_name, "-s", src, "-j", "DROP"])


def parse_ocserv_routes(conf_path: str | None = None) -> dict[str, Any]:
    """Read route / no-route / dns directives from ocserv.conf for dashboard display."""
    path = (conf_path or settings.ocserv_conf_path).strip()
    routes: list[str] = []
    no_routes: list[str] = []
    dns_servers: list[str] = []
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            for raw in f:
                line = raw.split("#", 1)[0].strip()
                if not line:
                    continue
                m = re.match(r"^\s*route\s*=\s*(.+)$", line, re.I)
                if m:
                    routes.append(m.group(1).strip())
                    continue
                m = re.match(r"^\s*no-route\s*=\s*(.+)$", line, re.I)
                if m:
                    no_routes.append(m.group(1).strip())
                    continue
                m = re.match(r"^\s*dns\s*=\s*(.+)$", line, re.I)
                if m:
                    dns_servers.append(m.group(1).strip())
    except OSError:
        pass
    return {
        "config_path": path,
        "routes": routes,
        "no_routes": no_routes,
        "dns": dns_servers,
    }


def read_ocserv_conf_raw(conf_path: str | None = None) -> str:
    """Read full ocserv.conf text (may require sudo if app user cannot read /etc)."""
    path = (conf_path or settings.ocserv_conf_path).strip()
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except (PermissionError, OSError):
        pass
    try:
        return run(["/bin/cat", path])
    except Exception:
        pass
    sudo_prefix = f"{settings.sudo_bin} " if (settings.sudo_bin or "").strip() else ""
    shell_cmd = f"{sudo_prefix}/bin/cat {shlex.quote(path)}"
    proc = subprocess.run(["/bin/sh", "-lc", shell_cmd], text=True, capture_output=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    _log_debug(shell_cmd, out)
    if proc.returncode == 0:
        return proc.stdout or ""
    raise CommandError(out.strip() or "cannot read ocserv.conf")


def write_ocserv_conf_raw(content: str, conf_path: str | None = None) -> None:
    """Write full ocserv.conf (requires root/sudo on typical installs)."""
    path = (conf_path or settings.ocserv_conf_path).strip()
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return
    except (PermissionError, OSError):
        pass
    full_cmd = _cmd_with_optional_sudo(["tee", path])
    proc = subprocess.run(full_cmd, input=content, text=True, capture_output=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    _log_debug(" ".join(full_cmd), out)
    if proc.returncode != 0:
        raise CommandError(out.strip() or "failed to write ocserv.conf")

