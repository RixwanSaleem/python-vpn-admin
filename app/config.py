import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # Auth (matches the PHP behavior, but pulled from env for safety)
    admin_user: str = os.getenv("ADMIN_USER", "admin")
    # Default preserves the existing PHP password if env var isn't set.
    admin_pass: str = os.getenv("ADMIN_PASS", "StrongPassword")

    # Session/auth
    # Must be set on production. Used to sign the session cookie.
    session_secret: str = os.getenv("SESSION_SECRET", "dev-change-me")

    # Database
    db_path: str = os.getenv("DB_PATH", "var/www/vpn/vpn.db")

    # ocserv helpers
    ocpasswd_path: str = os.getenv("OCPASSWD_PATH", "/usr/bin/ocpasswd")
    occtl_path: str = os.getenv("OCCTL_PATH", "/usr/bin/occtl")
    occtl_socket_file: str = os.getenv("OCCTL_SOCKET_FILE", "")
    ocpasswd_db_path: str = os.getenv("OC_PASSWD_DB", "/var/lib/ocserv/ocpasswd")
    systemctl_path: str = os.getenv("SYSTEMCTL_PATH", "/bin/systemctl")
    ocserv_service: str = os.getenv("OCSERV_SERVICE", "ocserv")

    # Per-user ocserv config
    user_config_dir: str = os.getenv("USER_CONFIG_DIR", "/etc/ocserv/config-per-user")

    # Main ocserv config (for route table display)
    ocserv_conf_path: str = os.getenv("OCSERV_CONF", "/etc/ocserv/ocserv.conf")

    # Debug command logging (PHP writes to this file)
    debug_log_path: str = os.getenv("DEBUG_LOG_PATH", "/tmp/vpn_debug.log")

    # sudo (PHP uses "sudo " prefix in shell)
    sudo_bin: str = os.getenv("SUDO_BIN", "sudo")

    # Firewall
    iptables_bin: str = os.getenv("IPTABLES_BIN", "iptables")
    vpn_chain_name: str = os.getenv("VPN_CHAIN_NAME", "VPN_USERS")


settings = Settings()

