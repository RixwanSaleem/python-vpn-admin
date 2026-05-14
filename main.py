import os
import shlex
import shutil
import subprocess
import json
import gzip
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from translations import LANGUAGES, get_translation, get_all_translations

app = FastAPI()
# Set max_age to 600 seconds (10 minutes) for auto-logout
app.add_middleware(SessionMiddleware, secret_key="ALFA_PRO_KEY_99", max_age=600)
templates = Jinja2Templates(directory="templates")

# Translation helpers for all templates
def get_user_language(request):
    return request.session.get("language", "en")

def translate(request, key):
    lang = get_user_language(request)
    return get_translation(lang, key)

templates.env.globals["t"] = translate
templates.env.globals["get_user_language"] = get_user_language


ENV_FILE = "/etc/squid-panel.env"
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "password")
PASSWD_FILE = "/etc/squid/passwd"
OCSERV_PASSWD_FILE = "/var/lib/ocserv/ocpasswd"
BACKUP_DIR = "/var/backups/squid-panel"
INTERFACES_CONFIG_FILE = "/etc/squid-panel/interfaces.json"
NOIP_CONFIG_FILE = "/etc/squid-panel/noip.json"

SERVICE_MAP = {
    "dhcp-server": {
        "label": "DHCP Server",
        "package": "dhcp-server",
        "service": "dhcpd",
        "description": "Manage the DHCP allocation service for local network clients."
    },
    "ethernet": {
        "label": "Ethernet",
        "package": "NetworkManager",
        "service": "NetworkManager",
        "description": "Manage wired Ethernet and network adapter services."
    },
    "ipsec": {
        "label": "IPSec",
        "package": "strongswan",
        "service": "strongswan",
        "description": "Manage IPsec VPN tunnels and encrypted site-to-site connections."
    },
    "ssl": {
        "label": "SSL VPN",
        "package": "stunnel",
        "service": "stunnel",
        "description": "Manage SSL-based VPN tunnels and secure transport channels."
    },
    "ssh": {
        "label": "SSH",
        "package": "openssh-server",
        "service": "sshd",
        "description": "Manage SSH remote access, secure shell connections and tunnels."
    },
    "vpn": {
        "label": "VPN",
        "package": "openvpn",
        "service": "openvpn",
        "description": "Manage generic VPN client/server tunnels for remote access."
    },
    "ocserv": {
        "label": "OCSERV",
        "package": "ocserv",
        "service": "ocserv",
        "description": "Manage OpenConnect VPN server for secure client access."
    }
}

def run_cmd(cmd):
    clean_env = os.environ.copy()
    clean_env.pop("PYTHONPATH", None)
    clean_env.pop("VIRTUAL_ENV", None)
    clean_env["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, env=clean_env)


def run_cmd_input(cmd, input_text: str):
    clean_env = os.environ.copy()
    clean_env.pop("PYTHONPATH", None)
    clean_env.pop("VIRTUAL_ENV", None)
    clean_env["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    if isinstance(cmd, list):
        return subprocess.run(cmd, capture_output=True, text=True, env=clean_env, input=input_text)
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, env=clean_env, input=input_text)


def safe_shell_arg(value: str) -> str:
    return shlex.quote(value or "")


def get_stats():
    is_installed = run_cmd("rpm -q squid").returncode == 0
    return {
        "installed": is_installed,
        "squid_active": run_cmd("systemctl is-active squid").stdout.strip() == "active",
        "fw_active": run_cmd("systemctl is-active firewalld").stdout.strip() == "active",
        "uptime": run_cmd("uptime -p").stdout.strip(),
        "load": run_cmd("uptime | awk -F'load average:' '{ print $2 }'").stdout.strip()
    }


# System Management Functions
def get_system_updates():
    """Get available system updates"""
    result = run_cmd("dnf check-update 2>/dev/null | grep -v '^$' | tail -n +1")
    updates = []
    if result.returncode == 100:  # dnf returns 100 when updates are available
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                parts = line.split()
                if len(parts) >= 3:
                    updates.append({
                        'package': parts[0],
                        'new_version': parts[1],
                        'repo': ' '.join(parts[2:])
                    })
    return updates


def get_last_update_time():
    """Get timestamp of last dnf transaction"""
    result = run_cmd("dnf history info 2>/dev/null | grep 'Begin Time' | head -1")
    if result.returncode == 0:
        return result.stdout.strip()
    return "Never"


def search_packages(query: str):
    """Search for packages"""
    safe_query = safe_shell_arg(query)
    result = run_cmd(f"dnf search {safe_query} 2>/dev/null | head -50")
    return result.stdout


def get_installed_packages():
    """Get list of installed packages"""
    result = run_cmd("rpm -qa --qf '[%{NAME}\\n]' | sort")
    packages = result.stdout.strip().split('\n') if result.stdout else []
    return packages[:500]  # Return first 500 for UI performance


def get_update_status():
    """Get update system status"""
    updates = get_system_updates()
    return {
        "updates_available": len(updates),
        "updates": updates,
        "last_update": get_last_update_time()
    }


def read_env_file():
    """Read the environment configuration file"""
    if os.path.exists(ENV_FILE):
        config = {}
        with open(ENV_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    config[key] = value
        return config
    return {}


def write_env_file(config: dict):
    """Write the environment configuration file"""
    try:
        os.makedirs(os.path.dirname(ENV_FILE), exist_ok=True)
        with open(ENV_FILE, 'w') as f:
            for key, value in config.items():
                f.write(f"{key}={value}\n")
        os.chmod(ENV_FILE, 0o600)
        return True
    except Exception as e:
        print(f"Error writing env file: {e}")
        return False


def create_backup():
    """Create a backup of important configuration files"""
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"squid-panel_backup_{timestamp}.tar.gz"
        backup_path = os.path.join(BACKUP_DIR, backup_name)
        
        # Files to backup
        files_to_backup = [
            "/etc/squid/squid.conf",
            "/etc/ocserv/ocserv.conf",
            "/etc/squid-panel.env",
            "/var/lib/ocserv/ocpasswd",
            "/etc/squid/passwd"
        ]
        
        # Create tar.gz archive
        cmd = f"tar -czf {safe_shell_arg(backup_path)} " + " ".join(safe_shell_arg(f) for f in files_to_backup if os.path.exists(f))
        result = run_cmd(cmd)
        
        if result.returncode == 0:
            return {"success": True, "backup_file": backup_name, "path": backup_path}
        return {"success": False, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_backups():
    """List available backups"""
    if not os.path.exists(BACKUP_DIR):
        return []
    
    backups = []
    for file in sorted(os.listdir(BACKUP_DIR), reverse=True):
        if file.endswith('.tar.gz'):
            path = os.path.join(BACKUP_DIR, file)
            size = os.path.getsize(path)
            mtime = os.path.getmtime(path)
            backups.append({
                "name": file,
                "size": f"{size / 1024 / 1024:.2f} MB" if size > 1024*1024 else f"{size / 1024:.2f} KB",
                "date": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "path": path
            })
    return backups


# Network Interfaces Management Functions
def read_interfaces_config():
    """Read network interfaces configuration from JSON"""
    if os.path.exists(INTERFACES_CONFIG_FILE):
        try:
            with open(INTERFACES_CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading interfaces config: {e}")
            return {"interfaces": []}
    return {"interfaces": []}


def write_interfaces_config(config: dict) -> bool:
    """Write network interfaces configuration to JSON"""
    try:
        os.makedirs(os.path.dirname(INTERFACES_CONFIG_FILE), exist_ok=True)
        with open(INTERFACES_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        os.chmod(INTERFACES_CONFIG_FILE, 0o600)
        return True
    except Exception as e:
        print(f"Error writing interfaces config: {e}")
        return False


def read_noip_config():
    """Read noip.com client configuration"""
    if os.path.exists(NOIP_CONFIG_FILE):
        try:
            with open(NOIP_CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading noip config: {e}")
            return {"enabled": False, "username": "", "password": "", "hostname": ""}
    return {"enabled": False, "username": "", "password": "", "hostname": ""}


def write_noip_config(config: dict) -> bool:
    """Write noip.com client configuration"""
    try:
        os.makedirs(os.path.dirname(NOIP_CONFIG_FILE), exist_ok=True)
        with open(NOIP_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        os.chmod(NOIP_CONFIG_FILE, 0o600)
        return True
    except Exception as e:
        print(f"Error writing noip config: {e}")
        return False


def get_system_interfaces() -> list:
    """Get list of network interfaces from system"""
    result = run_cmd("ip link show | grep -oP '^\\d+:\\s+\\K[^:]+' | grep -v lo")
    if result.returncode == 0:
        interfaces = [iface.strip() for iface in result.stdout.strip().split('\n') if iface.strip()]
        return sorted(interfaces)
    return []


def validate_ipv4(ip: str) -> bool:
    """Validate IPv4 address"""
    try:
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
        return True
    except:
        return False


def validate_prefix(prefix: str) -> bool:
    """Validate IPv4 prefix (0-32)"""
    try:
        p = int(prefix)
        return 0 <= p <= 32
    except:
        return False


def validate_interface_config(config: dict) -> dict:
    """Validate interface configuration"""
    errors = []
    
    # Check interface name
    if not config.get("name") or config["name"].strip() == "":
        errors.append("Interface name is required")
    
    # Check interface type
    if config.get("type") not in ["wan", "lan"]:
        errors.append("Interface type must be 'wan' or 'lan'")
    
    # Check bootproto
    if config.get("bootproto") not in ["dhcp", "static"]:
        errors.append("Boot protocol must be 'dhcp' or 'static'")
    
    # If static, validate static config
    if config.get("bootproto") == "static":
        if not config.get("ipaddr") or not validate_ipv4(config["ipaddr"]):
            errors.append("Invalid IP address")
        
        if not config.get("prefix") or not validate_prefix(config["prefix"]):
            errors.append("Invalid prefix (must be 0-32)")
        
        if not config.get("gateway") or not validate_ipv4(config["gateway"]):
            errors.append("Invalid gateway IP address")
        
        if config.get("dns1") and not validate_ipv4(config["dns1"]):
            errors.append("Invalid primary DNS")
        
        if config.get("dns2") and not validate_ipv4(config["dns2"]):
            errors.append("Invalid secondary DNS")
    
    return {"valid": len(errors) == 0, "errors": errors}


def generate_network_config_file(interface: dict) -> str:
    """Generate network configuration file content for ifcfg format"""
    config = f"""TYPE=Ethernet
NAME={interface['name']}
DEVICE={interface['name']}
ONBOOT=yes
"""
    
    if interface.get("bootproto") == "dhcp":
        config += "BOOTPROTO=dhcp\n"
    else:
        config += f"""BOOTPROTO=none
IPADDR={interface.get('ipaddr')}
PREFIX={interface.get('prefix')}
GATEWAY={interface.get('gateway')}
"""
        if interface.get("dns1"):
            config += f"DNS1={interface.get('dns1')}\n"
        if interface.get("dns2"):
            config += f"DNS2={interface.get('dns2')}\n"
    
    config += """DEFROUTE=yes
IPV4_FAILURE_FATAL=no
IPV6INIT=no
"""
    
    return config


def apply_interface_config(interface: dict) -> dict:
    """Apply interface configuration to system with backup"""
    config_path = f"/etc/sysconfig/network-scripts/ifcfg-{interface['name']}"
    backup_path = f"{config_path}.backup"
    
    try:
        # Backup existing config if it exists
        if os.path.exists(config_path):
            shutil.copy(config_path, backup_path)
        
        # Write new config
        config_content = generate_network_config_file(interface)
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        Path(config_path).write_text(config_content)
        os.chmod(config_path, 0o644)
        
        # Reload network manager
        run_cmd("nmcli connection reload")
        run_cmd(f"nmcli connection up {safe_shell_arg(interface['name'])}")
        
        return {"success": True, "message": f"Interface {interface['name']} configured successfully"}
    except Exception as e:
        # Restore backup on error
        if os.path.exists(backup_path):
            shutil.copy(backup_path, config_path)
        print(f"Error applying interface config: {e}")
        return {"success": False, "message": str(e)}


# Language Management Functions
def get_user_language(request: Request) -> str:
    """Get user's preferred language from session or environment"""
    language = request.session.get("language", "en")
    if language not in LANGUAGES:
        language = "en"
    return language


def set_user_language(request: Request, language: str):
    """Set user's preferred language in session"""
    if language in LANGUAGES:
        request.session["language"] = language
        # Also save to config file
        config = read_env_file()
        config["DEFAULT_LANGUAGE"] = language
        write_env_file(config)


def create_translation_context(request: Request, base_context: dict) -> dict:
    """
    Add translation strings to template context
    
    Args:
        request: FastAPI request object
        base_context: Base context dictionary
        
    Returns:
        Context with translations included
    """
    language = get_user_language(request)
    translations = get_all_translations(language)
    
    base_context["language"] = language
    base_context["languages"] = LANGUAGES
    base_context.update(translations)
    
    return base_context

@app.get("/login")
async def login_page(request: Request):
    context = create_translation_context(request, {"request": request})
    return templates.TemplateResponse(request=request, name="login.html", context=context)

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USER and password == ADMIN_PASS:
        request.session["logged_in"] = True
        return RedirectResponse(url="/", status_code=303)
    return RedirectResponse(url="/login?error=1", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")

@app.get("/")
async def dashboard(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")
    conns = run_cmd("netstat -an | grep :3128 | wc -l").stdout.strip()
    installed_services = []
    for key, service in SERVICE_MAP.items():
        if is_package_installed(service["package"]):
            installed_services.append({
                "key": key,
                "label": service["label"],
                "active": is_service_active(service["service"])
            })
    context = create_translation_context(request, {"request": request, **get_stats(), "connections": conns, "installed_services": installed_services})
    return templates.TemplateResponse(request=request, name="dashboard.html", context=context)

@app.get("/proxy")
async def proxy_page(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")
    stats = get_stats()
    users = []
    if stats["installed"] and os.path.exists(PASSWD_FILE):
        with open(PASSWD_FILE, "r") as f:
            users = [line.split(":")[0] for line in f if ":" in line]
    config = Path("/etc/squid/squid.conf").read_text() if os.path.exists("/etc/squid/squid.conf") else ""
    context = create_translation_context(request, {"request": request, **stats, "proxy_users": users, "config": config})
    return templates.TemplateResponse(request=request, name="proxy.html", context=context)

@app.get("/firewall")
async def firewall_page(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")
    ports = run_cmd("firewall-cmd --list-ports").stdout.strip()
    context = create_translation_context(request, {"request": request, **get_stats(), "open_ports": ports.split()})
    return templates.TemplateResponse(request=request, name="firewall.html", context=context)

@app.get("/logs")
async def logs_page(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")
    logs = run_cmd("tail -n 100 /var/log/squid/access.log").stdout
    context = create_translation_context(request, {"request": request, **get_stats(), "logs": logs})
    return templates.TemplateResponse(request=request, name="logs.html", context=context)

@app.get("/network")
@app.get("/networks")
async def networks_page(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")
    service_keys = ["dhcp-server", "ethernet"]
    services = []
    for key in service_keys:
        service = lookup_service(key)
        if not service:
            continue
        installed = is_package_installed(service["package"])
        active = is_service_active(service["service"]) if installed else False
        services.append({
            "key": key,
            "label": service["label"],
            "description": service["description"],
            "installed": installed,
            "active": active,
        })
    noip_config = read_noip_config()
    context = create_translation_context(request, {
        "request": request, 
        **get_stats(), 
        "services": services,
        "noip_config": noip_config
    })
    return templates.TemplateResponse(request=request, name="networks.html", context=context)

@app.get("/vpns")
@app.get("/vpn")
async def vpns_page(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")
    service_keys = ["ipsec", "ssl", "ssh", "vpn", "ocserv"]
    services = []
    for key in service_keys:
        service = lookup_service(key)
        if not service:
            continue
        installed = is_package_installed(service["package"])
        active = is_service_active(service["service"]) if installed else False
        services.append({
            "key": key,
            "label": service["label"],
            "description": service["description"],
            "installed": installed,
            "active": active,
        })
    context = create_translation_context(request, {"request": request, **get_stats(), "services": services})
    return templates.TemplateResponse(request=request, name="vpns.html", context=context)


def lookup_service(service_key: str):
    return SERVICE_MAP.get(service_key)


def is_package_installed(package_name: str) -> bool:
    return run_cmd(f"rpm -q {safe_shell_arg(package_name)}").returncode == 0


def is_service_active(service_name: str) -> bool:
    return run_cmd(f"systemctl is-active {safe_shell_arg(service_name)}").stdout.strip() == "active"


def get_ocserv_users() -> list:
    """Get list of OCSERV users from ocpasswd file"""
    users = []
    if os.path.exists(OCSERV_PASSWD_FILE):
        with open(OCSERV_PASSWD_FILE, 'r') as f:
            for line in f:
                if line.strip() and ':' in line:
                    username = line.strip().split(':')[0]
                    users.append(username)
    return users


def get_ocserv_connected_users() -> list:
    """Get connected OCSERV users using occtl"""
    connected = []
    result = run_cmd(f"occtl -s /var/run/occtl.socket show-users")
    if result.returncode != 0:
        return connected
    for line in result.stdout.strip().split('\n'):
        text = line.strip()
        if not text or text.lower().startswith("no active"):
            continue
        connected.append(text)
    return connected


def create_ocserv_user(username: str, password: str) -> bool:
    """Create or update OCSERV user with password"""
    try:
        os.makedirs(os.path.dirname(OCSERV_PASSWD_FILE), exist_ok=True)
        ocpasswd_bin = shutil.which("ocpasswd")
        input_text = f"{password}\n{password}\n"

        if ocpasswd_bin:
            # Always use -c flag with database path
            cmd = [ocpasswd_bin, "-c", OCSERV_PASSWD_FILE, username]
            result = run_cmd_input(cmd, input_text)
            if result.returncode == 0:
                os.chmod(OCSERV_PASSWD_FILE, 0o600)
                return True
            print(f"ocpasswd failed: {result.stderr.strip()}")
            return False

        # Fallback only if ocpasswd is unavailable
        existing_users = {}
        if os.path.exists(OCSERV_PASSWD_FILE):
            with open(OCSERV_PASSWD_FILE, 'r') as f:
                for line in f:
                    if ':' in line:
                        parts = line.strip().split(':', 1)
                        if len(parts) == 2:
                            user, pass_val = parts
                            existing_users[user] = pass_val

        existing_users[username] = password
        with open(OCSERV_PASSWD_FILE, 'w') as f:
            for user, pass_val in existing_users.items():
                f.write(f"{user}:{pass_val}\n")
        os.chmod(OCSERV_PASSWD_FILE, 0o600)
        return True
    except Exception as e:
        print(f"Error creating OCSERV user: {e}")
        return False


def delete_ocserv_user(username: str) -> bool:
    """Delete OCSERV user"""
    try:
        if not os.path.exists(OCSERV_PASSWD_FILE):
            return True
        ocpasswd_bin = shutil.which("ocpasswd")
        if ocpasswd_bin:
            # Correct syntax: ocpasswd -c <db_path> -d <username>
            result = run_cmd(f"{safe_shell_arg(ocpasswd_bin)} -c {safe_shell_arg(OCSERV_PASSWD_FILE)} -d {safe_shell_arg(username)}")
            if result.returncode == 0:
                return True
            print(f"ocpasswd delete failed: {result.stderr.strip()}")
            return False

        existing_users = {}
        with open(OCSERV_PASSWD_FILE, 'r') as f:
            for line in f:
                if ':' in line:
                    user, pass_val = line.strip().split(':', 1)
                    existing_users[user] = pass_val
        if username in existing_users:
            del existing_users[username]
        with open(OCSERV_PASSWD_FILE, 'w') as f:
            for user, pass_val in existing_users.items():
                f.write(f"{user}:{pass_val}\n")
        return True
    except Exception as e:
        print(f"Error deleting OCSERV user: {e}")
        return False


@app.get("/service/{service_key}")
async def service_page(request: Request, service_key: str):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")
    service = lookup_service(service_key)
    if not service:
        return RedirectResponse(url="/", status_code=303)
    installed = is_package_installed(service["package"])
    active = is_service_active(service["service"]) if installed else False
    category = "network" if service_key in {"dhcp-server", "ethernet"} else "vpn"
    base_context = {
        "request": request,
        **get_stats(),
        "service_key": service_key,
        "service_label": service["label"],
        "description": service["description"],
        "package_name": service["package"],
        "service_name": service["service"],
        "installed": installed,
        "active": active,
        "nav_section": category,
        "ocserv_users": get_ocserv_users() if service_key == "ocserv" else [],
        "ocserv_connections": get_ocserv_connected_users() if service_key == "ocserv" else []
    }
    context = create_translation_context(request, base_context)
    return templates.TemplateResponse(request=request, name="service.html", context=context)

@app.post("/service/{service_key}/manage")
async def manage_service(service_key: str, action: str = Form(...)):
    service = lookup_service(service_key)
    if not service:
        return RedirectResponse(url="/", status_code=303)
    pkg = safe_shell_arg(service["package"])
    svc = safe_shell_arg(service["service"])
    if action == "install":
        run_cmd(f"dnf install {pkg} -y")
    elif action == "uninstall":
        run_cmd(f"systemctl stop {svc} && dnf remove {pkg} -y")
    elif action == "enable":
        run_cmd(f"systemctl enable --now {svc}")
    elif action == "disable":
        run_cmd(f"systemctl disable --now {svc}")
    elif action == "restart":
        run_cmd(f"systemctl restart {svc}")
    elif action == "start":
        run_cmd(f"systemctl start {svc}")
    return RedirectResponse(url=f"/service/{service_key}", status_code=303)

@app.post("/manage")
async def manage_squid(action: str = Form(...)):
    if action == "install":
        run_cmd("dnf install squid httpd-tools -y && mkdir -p /etc/squid && touch /etc/squid/passwd && systemctl enable --now squid")
    elif action == "uninstall":
        run_cmd("systemctl stop squid && dnf remove squid -y")
    elif action in {"start", "stop", "restart"}:
        run_cmd(f"systemctl {action} squid")
    return RedirectResponse(url="/proxy", status_code=303)

@app.post("/proxy-user")
async def manage_user(action: str = Form(...), username: str = Form(...), password: str = Form(None)):
    safe_file = safe_shell_arg(PASSWD_FILE)
    safe_user = safe_shell_arg(username)
    if action == "add":
        safe_pass = safe_shell_arg(password or "")
        run_cmd(f"htpasswd -b {safe_file} {safe_user} {safe_pass}")
    else:
        run_cmd(f"htpasswd -D {safe_file} {safe_user}")
    run_cmd("systemctl restart squid")
    return RedirectResponse(url="/proxy", status_code=303)

@app.post("/ocserv-user")
async def manage_ocserv_user(action: str = Form(...), username: str = Form(...), password: str = Form(None)):
    if action == "add" or action == "reset":
        if not password:
            return RedirectResponse(url="/service/ocserv", status_code=303)
        success = create_ocserv_user(username, password)
        if success:
            run_cmd("systemctl restart ocserv")  # Restart service to pick up changes
    elif action == "delete":
        success = delete_ocserv_user(username)
        if success:
            run_cmd("systemctl restart ocserv")
    return RedirectResponse(url="/service/ocserv", status_code=303)


# Example configurations and installation guides for each service
SERVICE_EXAMPLES = {
    "ocserv": {
        "example_config": """# OpenConnect VPN Server Configuration
# Installation: dnf install ocserv
# Start: systemctl start ocserv

# Listen on all interfaces (HTTPS/443)
listen = 0.0.0.0
listen = [::]

# VPN network configuration
server-stats = /tmp/ocserv.stats
use-utmp = true
pid-file = /var/run/ocserv.pid

# Authentication method
auth = "plain[/var/lib/ocserv/ocpasswd]"

# VPN IP pool
ipv4-network = 192.168.99.0
ipv4-netmask = 255.255.255.0
dns = 8.8.8.8
dns = 8.8.4.4

# Session and bandwidth limits
max-same-clients = 2
max-clients = 128
keepalive = 32400

# Security settings
tls-priorities = "NORMAL:%SERVER_PRECEDENCE:%COMPAT:-VERS-SSL3.0"
enable-compression = true
""",
        "install_steps": """# OCSERV Installation Steps

1. Install the package:
   dnf install ocserv

2. Create user database directory:
   mkdir -p /var/lib/ocserv

3. Create user (example: testuser):
   ocpasswd -c /var/lib/ocserv/ocpasswd testuser

4. Set correct permissions:
   chmod 600 /var/lib/ocserv/ocpasswd

5. Enable and start the service:
   systemctl enable ocserv
   systemctl start ocserv

6. Check if service is running:
   systemctl status ocserv

7. Verify listening ports:
   netstat -an | grep 443

8. View statistics:
   occtl show-users (from VPN console)
"""
    },
    "ipsec": {
        "example_config": """# IPSec VPN Configuration (strongSwan)
# Installation: dnf install strongswan

# General settings
charondebug = "generic 2, cfg 2"
uniqueids = yes

conn default
  ikelifetime = 28800s
  lifetime = 3600s
  rekey = no
  reauth = no

conn site-to-site
  left = 192.168.1.1
  leftsubnet = 192.168.1.0/24
  right = 192.168.2.1
  rightsubnet = 192.168.2.0/24
  
  ike = aes256-sha1-modp1024!
  esp = aes256-sha1!
  
  keyexchange = ikev1
  type = tunnel
  auto = start
  mark = 10
""",
        "install_steps": """# IPSec Installation Steps

1. Install strongSwan:
   dnf install strongswan

2. Edit configuration:
   vim /etc/strongswan/strongswan.conf

3. Create connection file:
   vim /etc/strongswan/ipsec.conf

4. Generate certificates (optional for PSK):
   ipsec pki --gen --outform pem > ca.pem
   ipsec pki --self --in ca.pem --dn "C=US, O=AlfaSolutions, CN=CA" --ca --outform pem > ca-cert.pem

5. Enable and start:
   systemctl enable strongswan
   systemctl start strongswan

6. Check status:
   ipsec status

7. Monitor connections:
   watch -n 1 'ipsec status'
"""
    },
    "ssl": {
        "example_config": """# SSL/TLS Tunnel Configuration (stunnel)
# Installation: dnf install stunnel

setuid = nobody
setgid = nobody
pid = /var/run/stunnel.pid

# Logging
log = append
logfile = /var/log/stunnel/stunnel.log
debug = 7

# Server certificate
cert = /etc/stunnel/stunnel.pem
key = /etc/stunnel/stunnel.key

# Service: proxy-in to TCP port 8080
[proxy-tunnel]
accept = 443
connect = 127.0.0.1:8080
TIMEOUTconnect = 10

# Service: remote-access
[remote-access]
accept = 9999
connect = 192.168.1.100:22
TIMEOUTconnect = 10
""",
        "install_steps": """# SSL VPN Installation Steps

1. Install stunnel:
   dnf install stunnel

2. Generate self-signed certificate:
   openssl req -new -x509 -days 365 -nodes \\
     -out /etc/stunnel/stunnel.pem \\
     -keyout /etc/stunnel/stunnel.key

3. Set permissions:
   chmod 600 /etc/stunnel/stunnel.key
   chmod 644 /etc/stunnel/stunnel.pem

4. Edit configuration:
   vim /etc/stunnel/stunnel.conf

5. Enable and start:
   systemctl enable stunnel
   systemctl start stunnel

6. Check service:
   systemctl status stunnel
   netstat -an | grep LISTEN | grep stunnel

7. Test connection:
   openssl s_client -connect localhost:443
"""
    },
    "ssh": {
        "example_config": """# SSH Server Configuration
# Installation: dnf install openssh-server

# Default SSH configuration
Port 22
AddressFamily inet
ListenAddress 0.0.0.0
Protocol 2

# Authentication
PubkeyAuthentication yes
PasswordAuthentication yes
PermitRootLogin prohibit-password
PermitEmptyPasswords no

# Key exchange and ciphers
Ciphers aes256-ctr,aes192-ctr,aes128-ctr
MACs hmac-sha2-256,hmac-sha1
KexAlgorithms diffie-hellman-group-exchange-sha256

# Session limits
MaxAuthTries 3
MaxSessions 10
LoginGraceTime 120

# Logging
SyslogFacility AUTH
LogLevel INFO

# Tunneling and forwarding
AllowTcpForwarding yes
AllowAgentForwarding yes
GatewayPorts no
X11Forwarding yes

# Advanced security
ClientAliveInterval 300
ClientAliveCountMax 3
UsePAM yes
""",
        "install_steps": """# SSH Installation Steps

1. Install OpenSSH:
   dnf install openssh-server openssh-clients

2. (Optional) Generate host keys if missing:
   ssh-keygen -A

3. Review configuration:
   vim /etc/ssh/sshd_config

4. Test configuration syntax:
   sshd -t

5. Enable and start:
   systemctl enable sshd
   systemctl start sshd

6. Check if running:
   systemctl status sshd

7. Test connection:
   ssh -v localhost

8. Add firewall rule:
   firewall-cmd --permanent --add-service=ssh
   firewall-cmd --reload
"""
    },
    "vpn": {
        "example_config": """# OpenVPN Server Configuration
# Installation: dnf install openvpn

# Server mode
mode server
proto tcp
port 1194
ca ca.crt
cert server.crt
key server.key
dh dh.pem

# Network configuration
server 10.8.0.0 255.255.255.0
push "redirect-gateway def1 bypass-dhcp"
push "dhcp-option DNS 8.8.8.8"
push "dhcp-option DNS 8.8.4.4"
ifconfig-pool-persist ipp.txt

# Client connection settings
keepalive 10 120
tls-auth ta.key 0
cipher AES-256-CBC
auth SHA256
compress lz4-v2

# Security
user nobody
group nobody
persist-key
persist-tun

# Logging
log-append /var/log/openvpn/openvpn.log
verb 3
mute 20
""",
        "install_steps": """# OpenVPN Installation Steps

1. Install OpenVPN and Easy-RSA:
   dnf install openvpn easy-rsa

2. Create PKI directory:
   mkdir -p /etc/openvpn/server/pki
   cd /etc/openvpn/server/pki

3. Initialize PKI:
   easyrsa init-pki

4. Build CA certificate:
   easyrsa build-ca

5. Generate server certificate:
   easyrsa gen-req server nopass
   easyrsa sign-req server server

6. Generate DH parameters:
   easyrsa gen-dh

7. Generate TLS key:
   openvpn --genkey --secret ta.key

8. Configure server:
   cp ca.crt /etc/openvpn/server/
   cp server.crt /etc/openvpn/server/
   cp server.key /etc/openvpn/server/
   cp dh.pem /etc/openvpn/server/
   cp ta.key /etc/openvpn/server/

9. Edit configuration:
   vim /etc/openvpn/server/server.conf

10. Enable and start:
    systemctl enable openvpn-server@server
    systemctl start openvpn-server@server

11. Check status:
    systemctl status openvpn-server@server
"""
    },
    "dhcp-server": {
        "example_config": """# DHCP Server Configuration
# Installation: dnf install dhcp-server

# Global settings
default-lease-time 600;
max-lease-time 7200;
authoritative;
log-facility local7;

# Subnet definition
subnet 192.168.1.0 netmask 255.255.255.0 {
  option routers 192.168.1.1;
  option subnet-mask 255.255.255.0;
  option domain-name "example.com";
  option domain-name-servers 8.8.8.8, 8.8.4.4;
  option time-offset 0;
  
  range 192.168.1.100 192.168.1.200;
  
  # DHCP options
  option dhcp-lease-time 600;
  option dhcp-renewal-time 300;
}

# Static IP assignment
host workstation1 {
  hardware ethernet 00:1a:2b:3c:4d:5e;
  fixed-address 192.168.1.50;
}
""",
        "install_steps": """# DHCP Server Installation Steps

1. Install DHCP Server:
   dnf install dhcp-server

2. Edit configuration:
   vim /etc/dhcp/dhcpd.conf

3. Make backup of original:
   cp /etc/dhcp/dhcpd.conf /etc/dhcp/dhcpd.conf.bak

4. Specify network interface (edit /etc/sysconfig/dhcpd):
   DHCPDARGS="eth0"

5. Enable and start:
   systemctl enable dhcpd
   systemctl start dhcpd

6. Check status:
   systemctl status dhcpd

7. View DHCP leases:
   cat /var/lib/dhcpd/dhcpd.leases

8. Monitor DHCP activity:
   tail -f /var/log/messages | grep dhcpd

9. Test with a client:
   nmcli connection modify eth0 ipv4.method auto
   nmcli connection up eth0
"""
    },
    "ethernet": {
        "example_config": """# Ethernet Network Configuration
# Network interface: eth0

TYPE=Ethernet
BOOTPROTO=none
NAME=eth0
DEVICE=eth0
ONBOOT=yes
IPADDR=192.168.1.10
PREFIX=24
GATEWAY=192.168.1.1
DNS1=8.8.8.8
DNS2=8.8.4.4
DNS3=1.1.1.1
DEFROUTE=yes
IPV4_FAILURE_FATAL=no
IPV6INIT=no
""",
        "install_steps": """# Ethernet Configuration Steps

1. List available interfaces:
   ip link show
   nmcli device status

2. Edit network interface:
   vim /etc/sysconfig/network-scripts/ifcfg-eth0

3. For DHCP (Dynamic IP):
   BOOTPROTO=dhcp
   ONBOOT=yes

4. For Static IP:
   BOOTPROTO=none
   IPADDR=192.168.1.10
   PREFIX=24
   GATEWAY=192.168.1.1
   DNS1=8.8.8.8

5. Reload network configuration:
   systemctl restart NetworkManager
   OR
   nmcli connection reload
   nmcli connection up eth0

6. Check IP configuration:
   ip addr show eth0
   nmcli device show eth0

7. Test connectivity:
   ping 8.8.8.8
   ping google.com

8. Verify DNS:
   cat /etc/resolv.conf
   dig google.com
"""
    }
}


@app.get("/service/{service_key}/config")
async def service_config(request: Request, service_key: str):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")

    service = lookup_service(service_key)
    if not service:
        return RedirectResponse(url="/", status_code=303)

    # Define config file paths for each service
    config_files = {
        "ocserv": "/etc/ocserv/ocserv.conf",
        "ipsec": "/etc/strongswan/strongswan.conf",
        "ssl": "/etc/stunnel/stunnel.conf",
        "ssh": "/etc/ssh/sshd_config",
        "vpn": "/etc/openvpn/server.conf",
        "dhcp-server": "/etc/dhcp/dhcpd.conf",
        "ethernet": "/etc/sysconfig/network-scripts/ifcfg-eth0"
    }

    config_path = config_files.get(service_key)
    if not config_path:
        return RedirectResponse(url=f"/service/{service_key}", status_code=303)

    config_content = ""
    if os.path.exists(config_path):
        try:
            config_content = Path(config_path).read_text()
        except:
            config_content = "# Unable to read configuration file"

    # Get example configuration and installation steps
    example_data = SERVICE_EXAMPLES.get(service_key, {})
    example_config = example_data.get("example_config", "# No example configuration available")
    install_steps = example_data.get("install_steps", "# No installation steps available")

    base_context = {
        "request": request,
        **get_stats(),
        "service_key": service_key,
        "service_label": service["label"],
        "config_path": config_path,
        "config_content": config_content,
        "example_config": example_config,
        "install_steps": install_steps
    }
    context = create_translation_context(request, base_context)
    return templates.TemplateResponse(request=request, name="config.html", context=context)

@app.post("/service/{service_key}/config")
async def save_service_config(service_key: str, config_content: str = Form(...)):
    config_files = {
        "ocserv": "/etc/ocserv/ocserv.conf",
        "ipsec": "/etc/strongswan/strongswan.conf",
        "ssl": "/etc/stunnel/stunnel.conf",
        "ssh": "/etc/ssh/sshd_config",
        "vpn": "/etc/openvpn/server.conf",
        "dhcp-server": "/etc/dhcp/dhcpd.conf",
        "ethernet": "/etc/sysconfig/network-scripts/ifcfg-eth0"
    }

    config_path = config_files.get(service_key)
    if config_path and os.path.exists(config_path):
        try:
            Path(config_path).write_text(config_content)
            # Restart service after config change
            service = lookup_service(service_key)
            if service:
                run_cmd(f"systemctl restart {safe_shell_arg(service['service'])}")
        except:
            pass

    return RedirectResponse(url=f"/service/{service_key}/config", status_code=303)

@app.post("/manage-firewall")
async def manage_fw(action: str = Form(...)):
    if action in {"start", "stop", "restart", "status"}:
        run_cmd(f"systemctl {action} firewalld")
    return RedirectResponse(url="/firewall", status_code=303)

@app.post("/firewall-port")
async def manage_port(action: str = Form(...), port: str = Form(None)):
    if port:
        p = port.strip()
        if p:
            p = p if "/" in p else f"{p}/tcp"
            safe_port = safe_shell_arg(p)
            run_cmd(f"firewall-cmd --{action}-port={safe_port} && firewall-cmd --permanent --{action}-port={safe_port} && firewall-cmd --reload")
    return RedirectResponse(url="/firewall", status_code=303)


# Network Interfaces API Routes
@app.get("/network-interfaces/api/list")
async def list_interfaces(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")
    
    config = read_interfaces_config()
    system_interfaces = get_system_interfaces()
    
    return {
        "interfaces": config.get("interfaces", []),
        "available_interfaces": system_interfaces
    }


@app.post("/network-interfaces/api/add")
async def add_interface(request: Request, name: str = Form(...), interface_type: str = Form(...), 
                       bootproto: str = Form(...), ipaddr: str = Form(None), prefix: str = Form(None),
                       gateway: str = Form(None), dns1: str = Form(None), dns2: str = Form(None)):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")
    
    # Create interface config
    interface = {
        "id": f"{interface_type}-{name}-{datetime.now().timestamp()}",
        "name": name.strip(),
        "type": interface_type,
        "bootproto": bootproto,
        "active": False,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Add static config if applicable
    if bootproto == "static":
        interface["ipaddr"] = ipaddr
        interface["prefix"] = prefix
        interface["gateway"] = gateway
        if dns1:
            interface["dns1"] = dns1
        if dns2:
            interface["dns2"] = dns2
    
    # Validate
    validation = validate_interface_config(interface)
    if not validation["valid"]:
        return {
            "success": False,
            "errors": validation["errors"]
        }
    
    # Save to config
    config = read_interfaces_config()
    config["interfaces"].append(interface)
    
    if write_interfaces_config(config):
        return {
            "success": True,
            "interface": interface,
            "message": f"Interface {name} added successfully"
        }
    
    return {"success": False, "message": "Failed to save configuration"}


@app.post("/network-interfaces/api/edit/{interface_id}")
async def edit_interface(request: Request, interface_id: str, name: str = Form(...), 
                        interface_type: str = Form(...), bootproto: str = Form(...),
                        ipaddr: str = Form(None), prefix: str = Form(None),
                        gateway: str = Form(None), dns1: str = Form(None), dns2: str = Form(None)):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")
    
    config = read_interfaces_config()
    
    # Find interface
    interface = None
    for idx, iface in enumerate(config.get("interfaces", [])):
        if iface["id"] == interface_id:
            interface = iface
            break
    
    if not interface:
        return {"success": False, "message": "Interface not found"}
    
    # Update interface
    interface["name"] = name.strip()
    interface["type"] = interface_type
    interface["bootproto"] = bootproto
    
    if bootproto == "static":
        interface["ipaddr"] = ipaddr
        interface["prefix"] = prefix
        interface["gateway"] = gateway
        if dns1:
            interface["dns1"] = dns1
        if dns2:
            interface["dns2"] = dns2
    else:
        # Remove static config
        interface.pop("ipaddr", None)
        interface.pop("prefix", None)
        interface.pop("gateway", None)
        interface.pop("dns1", None)
        interface.pop("dns2", None)
    
    # Validate
    validation = validate_interface_config(interface)
    if not validation["valid"]:
        return {
            "success": False,
            "errors": validation["errors"]
        }
    
    if write_interfaces_config(config):
        return {
            "success": True,
            "interface": interface,
            "message": f"Interface {name} updated successfully"
        }
    
    return {"success": False, "message": "Failed to save configuration"}


@app.post("/network-interfaces/api/delete/{interface_id}")
async def delete_interface(request: Request, interface_id: str):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")
    
    config = read_interfaces_config()
    
    # Find and remove interface
    new_interfaces = [iface for iface in config.get("interfaces", []) if iface["id"] != interface_id]
    
    if len(new_interfaces) == len(config.get("interfaces", [])):
        return {"success": False, "message": "Interface not found"}
    
    config["interfaces"] = new_interfaces
    
    if write_interfaces_config(config):
        return {"success": True, "message": "Interface deleted successfully"}
    
    return {"success": False, "message": "Failed to delete interface"}


@app.post("/network-interfaces/api/apply")
async def apply_all_interfaces(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")
    
    config = read_interfaces_config()
    results = []
    
    for interface in config.get("interfaces", []):
        result = apply_interface_config(interface)
        results.append({
            "interface": interface["name"],
            **result
        })
    
    return {"success": True, "results": results}


# NoIP.com Client Configuration Routes
@app.get("/network-interfaces/noip/config")
async def get_noip_config_page(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")
    
    noip_config = read_noip_config()
    
    context = create_translation_context(request, {
        "request": request,
        **get_stats(),
        "noip_config": noip_config
    })
    
    return templates.TemplateResponse(request=request, name="noip.html", context=context)


@app.post("/network-interfaces/noip/save")
async def save_noip_config(request: Request, enabled: str = Form(None), username: str = Form(None), 
                          password: str = Form(None), hostname: str = Form(None)):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")
    
    noip_config = {
        "enabled": enabled == "on",
        "username": username or "",
        "password": password or "",
        "hostname": hostname or ""
    }
    
    if write_noip_config(noip_config):
        # If enabled, could start noip2 service here if installed
        if noip_config["enabled"]:
            # Try to restart noip2 service if it exists
            result = run_cmd("systemctl is-active noip2")
            if result.returncode == 0:
                run_cmd("systemctl restart noip2")
        
        return RedirectResponse(url="/network-interfaces/noip/config?success=1", status_code=303)
    
    return RedirectResponse(url="/network-interfaces/noip/config?error=1", status_code=303)


# System Settings Routes
@app.get("/system")
async def system_page(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")
    
    status = get_update_status()
    installed_packages = get_installed_packages()
    
    # Handle search query
    search_query = request.query_params.get("search", "").strip()
    search_results = ""
    if search_query:
        search_results = search_packages(search_query)
    
    # Handle success/error messages
    success = request.query_params.get("success")
    error = request.query_params.get("error")
    
    return templates.TemplateResponse(request=request, name="system.html", context={
        "request": request,
        **get_stats(),
        "updates_available": status["updates_available"],
        "updates": status["updates"],
        "last_update": status["last_update"],
        "installed_count": len(installed_packages),
        "installed_packages": installed_packages[:100],  # Show first 100 in UI
        "search_query": search_query,
        "search_results": search_results,
        "success": success,
        "error": error
    })


@app.post("/admin/delete-backup")
async def delete_backup(backup_name: str = Form(...)):
    # Security: only allow alphanumeric, underscore, dash, and dot
    if not all(c.isalnum() or c in '_-.' for c in backup_name):
        return RedirectResponse("/admin", status_code=303)
    
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    
    # Security: ensure file is in backup directory
    if not os.path.abspath(backup_path).startswith(os.path.abspath(BACKUP_DIR)):
        return RedirectResponse("/admin", status_code=303)
    
    try:
        if os.path.exists(backup_path):
            os.remove(backup_path)
            return RedirectResponse(url="/admin?success=backup_deleted", status_code=303)
    except Exception as e:
        print(f"Error deleting backup: {e}")
    
    return RedirectResponse(url="/admin?error=delete_failed", status_code=303)


@app.post("/admin/change-language")
async def change_language(request: Request, language: str = Form(...)):
    if language in LANGUAGES:
        set_user_language(request, language)
        return RedirectResponse(url="/admin?success=language_changed", status_code=303)
    return RedirectResponse(url="/admin?error=invalid_language", status_code=303)


@app.post("/save-config")
async def save_config(config_text: str = Form(...)):
    if os.path.exists("/etc/squid/squid.conf"):
        Path("/etc/squid/squid.conf").write_text(config_text); run_cmd("systemctl restart squid")
    return RedirectResponse(url="/proxy", status_code=303)
async def system_page(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")
    
    status = get_update_status()
    installed_packages = get_installed_packages()
    
    # Handle search query
    search_query = request.query_params.get("search", "").strip()
    search_results = ""
    if search_query:
        search_results = search_packages(search_query)
    
    # Handle success/error messages
    success = request.query_params.get("success")
    error = request.query_params.get("error")
    
    return templates.TemplateResponse(request=request, name="system.html", context={
        "request": request,
        **get_stats(),
        "updates_available": status["updates_available"],
        "updates": status["updates"],
        "last_update": status["last_update"],
        "installed_count": len(installed_packages),
        "installed_packages": installed_packages[:100],  # Show first 100 in UI
        "search_query": search_query,
        "search_results": search_results,
        "success": success,
        "error": error
    })


@app.post("/system/search-packages")
async def search_packages_action(query: str = Form(...)):
    result = search_packages(query)
    return RedirectResponse(url=f"/system?search={query}", status_code=303)


@app.post("/system/install-updates")
async def install_updates():
    run_cmd("dnf update -y")
    return RedirectResponse(url="/system", status_code=303)


@app.post("/system/install-package")
async def install_package(package_name: str = Form(...)):
    if package_name.strip():
        safe_pkg = safe_shell_arg(package_name)
        result = run_cmd(f"dnf install {safe_pkg} -y")
        if result.returncode == 0:
            return RedirectResponse(url="/system?success=package_installed", status_code=303)
        else:
            return RedirectResponse(url="/system?error=install_failed", status_code=303)
    return RedirectResponse(url="/system", status_code=303)


@app.post("/system/remove-package")
async def remove_package(package_name: str = Form(...)):
    if package_name.strip():
        safe_pkg = safe_shell_arg(package_name)
        result = run_cmd(f"dnf remove {safe_pkg} -y")
        if result.returncode == 0:
            return RedirectResponse(url="/system?success=package_removed", status_code=303)
        else:
            return RedirectResponse(url="/system?error=remove_failed", status_code=303)
    return RedirectResponse(url="/system", status_code=303)


# Administration Routes
@app.get("/admin")
async def admin_page(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")
    
    backups = get_backups()
    
    context = create_translation_context(request, {
        "request": request,
        **get_stats(),
        "backups": backups,
        "backup_count": len(backups)
    })
    
    return templates.TemplateResponse(request=request, name="admin.html", context=context)


@app.post("/admin/change-password")
async def change_admin_password(current_password: str = Form(...), new_password: str = Form(...), confirm_password: str = Form(...)):
    global ADMIN_PASS
    
    # Verify current password
    if current_password != ADMIN_PASS:
        return RedirectResponse(url="/admin?error=invalid_password", status_code=303)
    
    # Verify new passwords match
    if new_password != confirm_password:
        return RedirectResponse(url="/admin?error=passwords_not_match", status_code=303)
    
    # Verify password strength (at least 8 chars)
    if len(new_password) < 8:
        return RedirectResponse(url="/admin?error=password_too_short", status_code=303)
    
    # Update .env file
    config = read_env_file()
    config["ADMIN_PASS"] = new_password
    
    if write_env_file(config):
        # Also update the in-memory variable for this session
        ADMIN_PASS = new_password
        return RedirectResponse(url="/admin?success=password_changed", status_code=303)
    
    return RedirectResponse(url="/admin?error=write_failed", status_code=303)


@app.post("/admin/create-backup")
async def create_backup_action():
    result = create_backup()
    if result["success"]:
        return RedirectResponse(url="/admin?success=backup_created", status_code=303)
    return RedirectResponse(url="/admin?error=backup_failed", status_code=303)


@app.get("/admin/download-backup/{backup_name}")
async def download_backup(backup_name: str, request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")
    
    # Security: only allow alphanumeric, underscore, dash, and dot
    if not all(c.isalnum() or c in '_-.' for c in backup_name):
        return RedirectResponse("/admin", status_code=303)
    
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    
    # Security: ensure file is in backup directory
    if not os.path.abspath(backup_path).startswith(os.path.abspath(BACKUP_DIR)):
        return RedirectResponse("/admin", status_code=303)
    
    if os.path.exists(backup_path):
        return FileResponse(backup_path, filename=backup_name, media_type="application/gzip")
    
    return RedirectResponse("/admin", status_code=303)
