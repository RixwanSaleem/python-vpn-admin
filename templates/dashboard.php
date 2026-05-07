<!DOCTYPE html>
<html lang="en">
<head>
    <title>Alfa Solution VPN Admin</title>
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
    <meta http-equiv="Cache-Control" content="no-store" />
    <style>
        :root{
            --bg:#080f27;
            --bg2:#0c1433;
            --card:#121c3e;
            --card2:#0f1736;
            --line:rgba(255,255,255,0.12);
            --text:#e8edff;
            --muted:#a0add8;
            --green:#44d96c;
            --red:#ff6262;
            --blue:#4d8dff;
        }
        html.theme-light{
            --bg:#f0f4fc;
            --bg2:#e6ecf9;
            --card:#ffffff;
            --card2:#f5f8ff;
            --line:rgba(15,23,42,0.12);
            --text:#0f172a;
            --muted:#5b6478;
        }
        *{box-sizing:border-box}
        html,body{
            overflow-x:hidden;
            max-width:100%;
        }
        body{
            margin:0;
            font-family:Inter,Segoe UI,Arial,sans-serif;
            color:var(--text);
            background:radial-gradient(circle at 20% 10%, #19275c, var(--bg) 50%) fixed;
        }
        html.theme-light body{
            background:radial-gradient(circle at 20% 10%, #dbeafe, var(--bg) 50%) fixed;
        }
        .app{
            display:block;
            min-height:100vh;
            min-height:100dvh;
            max-width:100%;
            overflow-x:hidden;
        }
        .main{
            padding:18px;
            padding-left:max(18px, env(safe-area-inset-left));
            padding-right:max(18px, env(safe-area-inset-right));
            padding-bottom:max(18px, env(safe-area-inset-bottom));
            max-width:100%;
        }
        .topbar{
            display:grid;
            grid-template-columns:1fr auto;
            grid-template-areas:
                "brand actions"
                "search search";
            gap:12px 16px;
            align-items:center;
            margin-bottom:18px;
            width:100%;
        }
        .topbar .logo{grid-area:brand;min-width:0}
        .topbar .search{grid-area:search;width:100%;min-width:0}
        .topbar .top-actions{grid-area:actions;justify-self:end}
        @media (min-width:1000px){
            .topbar{
                grid-template-columns:auto 1fr auto;
                grid-template-areas:"brand search actions";
            }
            .topbar .search{max-width:380px;justify-self:stretch}
        }
        .logo{font-weight:700;letter-spacing:.3px}
        .logo span{color:#6fe56a}
        .search{
            padding:10px 12px;border-radius:10px;border:1px solid var(--line);
            background:rgba(255,255,255,0.03);color:var(--text);
        }
        html.theme-light .search{background:rgba(15,23,42,0.04)}
        .top-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap;justify-content:flex-end}
        .btn-theme{
            border:none;border-radius:10px;padding:10px 12px;font-weight:600;cursor:pointer;
            min-height:44px;min-width:44px;
            background:rgba(255,255,255,0.08);border:1px solid var(--line);color:var(--text);
            font-size:18px;line-height:1;
        }
        html.theme-light .btn-theme{background:#fff}
        .btn{
            border:none;border-radius:10px;padding:10px 14px;font-weight:600;color:#fff;cursor:pointer;
            min-height:44px;
        }
        .btn-blue{background:linear-gradient(180deg,#5a9dff,#3f7fff)}
        .btn-green{background:linear-gradient(180deg,#62dc83,#34bb5d)}
        .btn-red{background:linear-gradient(180deg,#ff7f7f,#ff5f5f)}
        .grid{
            display:grid;gap:14px;
            grid-template-columns:repeat(auto-fit, minmax(min(100%, min(320px, 100%)), 1fr));
            width:100%;
            min-width:0;
        }
        .card{
            background:linear-gradient(180deg,var(--card),var(--card2));
            border:1px solid var(--line);
            border-radius:16px;padding:16px;
            box-shadow:0 12px 24px rgba(0,0,0,.2);
        }
        .title{font-size:20px;font-weight:700;margin-bottom:10px}
        .card-header-row{
            display:flex;align-items:center;justify-content:space-between;gap:10px;
            margin-bottom:10px;
        }
        .card-header-row .title{margin-bottom:0!important}
        .icon-btn{
            flex-shrink:0;
            border:none;border-radius:10px;
            background:rgba(255,255,255,0.08);border:1px solid var(--line);
            color:var(--text);cursor:pointer;width:40px;height:40px;
            font-size:18px;line-height:1;display:inline-flex;align-items:center;justify-content:center;
        }
        html.theme-light .icon-btn{background:#f1f5f9}
        .muted{color:var(--muted);font-size:13px}
        .status-pill{
            display:inline-block;padding:6px 12px;border-radius:999px;font-size:13px;font-weight:700;margin:6px 0 10px;
        }
        .row2{display:grid;grid-template-columns:1fr 1fr;gap:8px}
        input,select{
            width:100%;padding:10px 11px;border-radius:10px;
            border:1px solid var(--line);background:rgba(255,255,255,0.02);color:var(--text);
        }
        .stats{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px}
        .mini{
            background:rgba(255,255,255,0.03);
            border:1px solid var(--line);
            border-radius:12px;padding:12px;
        }
        .mini-value{font-size:26px;font-weight:800}
        table{width:100%;border-collapse:collapse}
        th,td{padding:10px 8px;border-bottom:1px solid rgba(255,255,255,0.08);text-align:left;font-size:13px}
        th{color:#b7c2e9;font-weight:600}
        .table-wrap{max-height:280px;overflow:auto;-webkit-overflow-scrolling:touch}
        .table-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;width:100%}
        .full{grid-column:1 / -1}
        .actions{display:flex;gap:6px;flex-wrap:wrap}
        .btn-sm{padding:8px 10px;border-radius:8px;font-size:12px;border:none;color:#fff;cursor:pointer;min-height:40px}
        .tag-online{color:#4be06f;font-weight:700}
        .tag-offline{color:#ff7f7f;font-weight:700}
        .logs{
            white-space:pre-wrap;background:rgba(0,0,0,.2);border:1px solid var(--line);
            border-radius:12px;padding:12px;max-height:230px;overflow:auto
        }
        html.theme-light .logs{background:rgba(15,23,42,0.05)}
        .modal{
            display:none;position:fixed;inset:0;z-index:1000;
            align-items:center;justify-content:center;
            padding:max(12px, env(safe-area-inset-top)) max(12px, env(safe-area-inset-right))
                max(12px, env(safe-area-inset-bottom)) max(12px, env(safe-area-inset-left));
        }
        .modal.open{display:flex}
        .modal-backdrop{
            position:absolute;inset:0;background:rgba(0,0,0,.55);
        }
        .modal-panel{
            position:relative;z-index:1;
            width:min(96vw, 900px);
            max-height:min(88vh, 900px);
            display:flex;flex-direction:column;
            background:linear-gradient(180deg,var(--card),var(--card2));
            border:1px solid var(--line);
            border-radius:16px;
            overflow:hidden;
            box-shadow:0 16px 40px rgba(0,0,0,.35);
            min-width:0;
        }
        .modal-head{
            display:flex;align-items:center;justify-content:space-between;gap:12px;
            padding:12px 14px;border-bottom:1px solid var(--line);
            font-weight:700;
        }
        .conf-editor{
            flex:1;min-height:min(200px, 40vh);max-height:min(55vh, 480px);
            width:100%;margin:0;border:none;border-radius:0;
            padding:12px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
            font-size:12px;line-height:1.45;
            background:rgba(0,0,0,.25);color:var(--text);resize:vertical;
        }
        html.theme-light .conf-editor{background:#f8fafc}
        .modal-actions{
            display:flex;justify-content:flex-end;gap:10px;padding:12px 14px;
            border-top:1px solid var(--line);flex-wrap:wrap;
        }
        .compact-tools{
            display:grid;
            grid-template-columns:repeat(auto-fit, minmax(min(100%, 260px), 320px));
            gap:10px;
            margin-bottom:12px;
            align-items:start;
        }
        .card-compact{
            padding:10px 12px!important;
            border-radius:12px!important;
            box-shadow:0 4px 14px rgba(0,0,0,.15)!important;
        }
        .card-compact .title{
            font-size:14px!important;
            font-weight:700;
            margin-bottom:4px!important;
        }
        .card-compact .muted{
            font-size:11px!important;
            line-height:1.35;
            margin-bottom:2px;
        }
        .card-compact .row2{
            gap:6px!important;
            margin-top:6px!important;
        }
        .card-compact .row2:first-of-type{margin-top:4px!important}
        .card-compact input{
            padding:6px 9px!important;
            font-size:14px!important;
            border-radius:8px!important;
        }
        .card-compact .btn-compact{
            min-height:36px!important;
            padding:6px 14px!important;
            font-size:13px!important;
            margin-top:8px!important;
            width:100%;
            max-width:220px;
            border-radius:8px!important;
        }
        .routes-table-box{
            max-height:100px;
            margin-top:6px;
            overflow:auto;
            border:1px solid var(--line);
            border-radius:8px;
            -webkit-overflow-scrolling:touch;
        }
        .bottom-tools{margin-top:10px}
        .routes-table-box table{min-width:0;width:100%}
        .routes-table-box th,.routes-table-box td{
            padding:4px 8px!important;
            font-size:11px!important;
        }
        .routes-table-box th{color:#94a8d4}
        @media (max-width:1024px){
            .grid{grid-template-columns:1fr}
            .full{grid-column:1 / -1}
            .mini-value{font-size:22px}
        }
        @media (max-width:768px){
            .main{padding:12px}
            .title{font-size:18px}
            .row2{grid-template-columns:1fr}
            textarea{min-height:120px;font-size:16px!important}
            input,select{font-size:16px!important}
            .card-compact input{font-size:14px!important}
        }
        @media (max-width:480px){
            .mini-value{font-size:20px}
            .stats{grid-template-columns:1fr}
        }
    </style>
</head>
<body>
<div class="app">
    <main class="main">
        <div class="topbar">
            <div class="logo">Alfa Solution <span>VPN</span></div>
            <input class="search" placeholder="Search user..." />
            <div class="top-actions">
                <button type="button" class="btn-theme" id="theme_btn" onclick="toggleTheme()" title="Switch to light theme" aria-label="Toggle light or dark theme">☀️</button>
                <button class="btn btn-red" onclick="logout()">Logout</button>
            </div>
        </div>

        <section class="grid">
            <div class="card">
                <div class="card-header-row">
                    <div class="title">OCserv Status</div>
                    <button type="button" class="icon-btn" title="Edit ocserv.conf" onclick="openOcservConfEditor()" aria-label="Edit ocserv.conf">⚙</button>
                </div>
                <div id="ocserv_status" class="status-pill">Checking...</div>
                <div class="row2">
                    <button class="btn btn-green" onclick="controlOcserv('start')">Start</button>
                    <button class="btn btn-red" onclick="controlOcserv('stop')">Stop</button>
                </div>
                <div class="stats">
                    <div class="mini">
                        <div class="muted">Total Users</div>
                        <div class="mini-value" id="stat_total">0</div>
                    </div>
                    <div class="mini">
                        <div class="muted">Online</div>
                        <div class="mini-value" id="stat_online">0</div>
                    </div>
                    <div class="mini">
                        <div class="muted">Traffic Today</div>
                        <div class="mini-value" style="font-size:20px" id="stat_traffic">N/A</div>
                    </div>
                    <div class="mini">
                        <div class="muted">Expiring Soon</div>
                        <div class="mini-value" id="stat_expiring">0</div>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="title">Create User</div>
                <div class="row2">
                    <input id="u" placeholder="Username" />
                    <div style="display:flex;gap:8px">
                        <input id="p" placeholder="Password" />
                        <button class="btn btn-blue" type="button" onclick="generatePassword()" style="white-space:nowrap">Generate</button>
                    </div>
                </div>
                <div class="row2">
                    <input id="e" type="date" />
                    <select id="l">
                        <option value="0">Device Limit: Unlimited</option>
                        <option value="1">1 Device</option>
                        <option value="2">2 Devices</option>
                        <option value="3">3 Devices</option>
                        <option value="5">5 Devices</option>
                        <option value="10">10 Devices</option>
                    </select>
                </div>
                <div class="row2">
                    <input id="vpn_ip" placeholder="VPN IP (10.10.10.10)" />
                    <input id="allowed_ips" placeholder="Allowed IPs (8.8.8.8,1.1.1.1)" />
                </div>
                <div class="row2">
                    <select id="bandwidth_kbps">
                        <option value="0">Bandwidth: Unlimited</option>
                        <option value="512">512 Kbps</option>
                        <option value="1024">1 Mbps</option>
                        <option value="2048">2 Mbps</option>
                        <option value="5120">5 Mbps</option>
                        <option value="10240">10 Mbps</option>
                        <option value="20480">20 Mbps</option>
                        <option value="custom">Custom...</option>
                    </select>
                    <input id="bandwidth_custom" placeholder="Custom Kbps" style="display:none" />
                </div>
                <div class="row2" style="margin-top:8px">
                    <button class="btn btn-blue" onclick="createUser()">Create</button>
                    <button class="btn btn-green" onclick="applyFirewall()">Apply Firewall</button>
                </div>
            </div>

            <div class="card">
                <div class="title">Bulk Create Users</div>
                <div class="muted">Format per line: username,password,expiry(YYYY-MM-DD),limit,vpn_ip,allowed_ips,bandwidth_kbps</div>
                <textarea id="bulk_lines" style="width:100%;min-height:130px;margin-top:8px;border-radius:10px;border:1px solid var(--line);background:rgba(255,255,255,0.02);color:var(--text);padding:10px" placeholder="user1,pass123,2026-12-31,2,10.10.10.51,8.8.8.8,2048"></textarea>
                <div class="row2" style="margin-top:8px">
                    <button class="btn btn-blue" onclick="bulkCreateUsers()">Create Bulk</button>
                    <button class="btn btn-green" onclick="triggerCsvUpload()">Upload CSV</button>
                </div>
                <div class="row2" style="margin-top:8px">
                    <button class="btn btn-blue" onclick="downloadCsvTemplate()">Download CSV Template</button>
                    <button class="btn btn-red" onclick="document.getElementById('bulk_lines').value=''">Clear</button>
                </div>
                <input id="bulk_csv_file" type="file" accept=".csv,text/csv" style="display:none" />
            </div>

            <div class="card">
                <div class="title">Live Users</div>
                <div class="table-wrap">
                    <table id="live_tbl">
                        <thead>
                            <tr><th>User</th><th>IP</th><th>Country</th><th>Since</th><th>Data</th><th>Kick</th></tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>

            <div class="card">
                <div class="title">Geo Blocking</div>
                <div class="row2">
                    <select id="geo_mode">
                        <option value="off">Off</option>
                        <option value="allow">Allow only listed countries</option>
                        <option value="block">Block listed countries</option>
                    </select>
                    <label class="muted" style="display:flex;align-items:center;gap:6px">
                        <input type="checkbox" id="geo_auto_enforce" />
                        Auto-enforce
                    </label>
                </div>
                <input id="geo_countries" placeholder="Country codes, e.g. US,CA,IN" style="margin-top:8px" />
                <div class="row2" style="margin-top:8px">
                    <button class="btn btn-blue" onclick="saveGeoPolicy()">Save Policy</button>
                    <button class="btn btn-red" onclick="enforceGeoNow()">Enforce Now</button>
                </div>
            </div>

            <div class="card full">
                <div class="title">All Users</div>
                <div class="actions" style="margin-bottom:8px">
                    <button class="btn-sm" style="background:#ff6262" onclick="deleteSelectedUsers()">Delete Selected</button>
                </div>
                <div class="table-wrap">
                    <table id="users_tbl">
                        <thead>
                            <tr>
                                <th><input type="checkbox" id="select_all_users" /></th><th>User</th><th>Expiry</th><th>Limit</th><th>Bandwidth</th><th>VPN IP</th><th>Allowed IPs</th><th>Status</th><th>Actions</th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>

            <div class="card full">
                <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
                    <div class="title" style="margin:0">Logs</div>
                    <div class="actions">
                        <button class="btn-sm" style="background:#5a9dff" onclick="toggleLogs()">View Logs</button>
                        <button class="btn-sm" style="background:#ff6262" onclick="clearLogs()">Clear Logs</button>
                    </div>
                </div>
                <div class="logs" id="logs" style="display:none">Loading...</div>
            </div>

            <div class="compact-tools bottom-tools full">
                <div class="card card-compact">
                    <div class="title">Admin</div>
                    <div class="muted">Change panel login</div>
                    <div class="row2">
                        <input id="admin_cur" type="password" placeholder="Current" autocomplete="current-password" />
                        <input id="admin_new_user" placeholder="User (optional)" autocomplete="username" />
                    </div>
                    <div class="row2">
                        <input id="admin_new" type="password" placeholder="New password" autocomplete="new-password" />
                        <input id="admin_new2" type="password" placeholder="Confirm" autocomplete="new-password" />
                    </div>
                    <button class="btn btn-blue btn-compact" type="button" onclick="changeAdminPassword()">Save</button>
                </div>
                <div class="card card-compact">
                    <div class="title">VPN routes</div>
                    <div class="muted" id="routes_config_hint">ocserv.conf</div>
                    <div class="routes-table-box table-scroll">
                        <table id="routes_tbl">
                            <thead><tr><th>Type</th><th>Value</th></tr></thead>
                            <tbody></tbody>
                        </table>
                    </div>
                </div>
            </div>
        </section>
    </main>

    <div id="ocserv_modal" class="modal" role="dialog" aria-modal="true" aria-labelledby="ocserv_modal_title">
        <div class="modal-backdrop" onclick="closeOcservConfEditor()"></div>
        <div class="modal-panel">
            <div class="modal-head">
                <span id="ocserv_modal_title">Edit ocserv.conf</span>
                <button type="button" class="icon-btn" onclick="closeOcservConfEditor()" aria-label="Close">&times;</button>
            </div>
            <textarea id="ocserv_conf_text" class="conf-editor" spellcheck="false" autocomplete="off"></textarea>
            <div class="modal-actions">
                <button type="button" class="btn btn-red" onclick="closeOcservConfEditor()">Cancel</button>
                <button type="button" class="btn btn-blue" onclick="saveOcservConf()">Save</button>
            </div>
        </div>
    </div>
</div>

<script>
const CSRF_TOKEN = "{{ csrf_token }}";
const API = {
    users: "/api/users.php",
    live_json: "/api/live_json.php",
    logs: "/api/logs.php",
    status: "/api/ocserv_status.php",
    stats: "/api/stats.php",
    control: "/api/ocserv_control.php",
    create: "/api/create.php",
    firewall: "/api/firewall.php",
    del: "/api/delete.php",
    disconnect: "/api/disconnect.php",
    reset: "/api/reset.php",
    update_user: "/api/update_user.php",
    bulk_create: "/api/bulk_create.php",
    bulk_delete: "/api/bulk_delete.php",
    bulk_template: "/api/bulk_template.csv",
    logs_clear: "/api/logs_clear.php",
    geo_policy: "/api/geo_policy.php",
    geo_enforce: "/api/geo_enforce.php",
    session: "/api/session.php",
    vpn_routes: "/api/vpn_routes.php",
    change_admin: "/api/change_admin_password.php",
    logout: "/api/logout.php",
    ocserv_conf: "/api/ocserv_conf.php"
};

const THEME_KEY = "vpn_panel_theme";

function applyTheme(mode){
    const isLight = mode === "light";
    document.documentElement.classList.toggle("theme-light", isLight);
    const btn = document.getElementById("theme_btn");
    if (btn){
        btn.textContent = isLight ? "🌙" : "☀️";
        btn.title = isLight ? "Switch to dark theme" : "Switch to light theme";
    }
    try{
        localStorage.setItem(THEME_KEY, isLight ? "light" : "dark");
    }catch{}
}

function toggleTheme(){
    applyTheme(document.documentElement.classList.contains("theme-light") ? "dark" : "light");
}

(function initThemeFromStorage(){
    try{
        const s = localStorage.getItem(THEME_KEY);
        if (s === "light" || s === "dark") applyTheme(s);
    }catch{}
})();

(function(){
    const nativeFetch = window.fetch;
    window.fetch = function(...args){
        return nativeFetch.apply(this, args).then(function(res){
            const req = args[0];
            const url = typeof req === "string" ? req : (req && req.url) || "";
            const path = url.replace(/^https?:\/\/[^/]+/i, "");
            if (path.indexOf("/api/") === 0 && (res.status === 401 || res.status === 403)){
                window.location.replace("/index.php");
            }
            return res;
        });
    };
})();

let LAST_USERS = [];
let LAST_SESSIONS = [];
let LAST_ONLINE_USERNAMES = [];
let LOGS_VISIBLE = false;
let IDLE_TIMEOUT_MS = 15 * 60 * 1000;
let REFRESH_INTERVAL_MS = 5000;
let lastActivityAt = Date.now();

async function readError(res){
    const ct = (res.headers.get("content-type") || "").toLowerCase();
    if (ct.includes("application/json")){
        try{
            const j = await res.json();
            return j.detail || JSON.stringify(j);
        }catch{
            return `HTTP ${res.status}`;
        }
    }
    try{
        return (await res.text()) || `HTTP ${res.status}`;
    }catch{
        return `HTTP ${res.status}`;
    }
}

function esc(v){
    return String(v ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");
}

async function getJson(url){
    const res = await fetch(url, { credentials: "same-origin", cache: "no-store" });
    if (res.status === 401 || res.status === 403){
        window.location.replace("/index.php");
        throw new Error("Unauthorized");
    }
    if (!res.ok) throw new Error(await readError(res));
    return res.json();
}

function renderLiveRows(sessions){
    const tbody = document.querySelector("#live_tbl tbody");
    if (!sessions.length){
        tbody.innerHTML = "<tr><td colspan='6' class='muted'>No active sessions</td></tr>";
        return;
    }
    tbody.innerHTML = sessions.map(s => `
        <tr>
            <td>${esc(s.username)}</td>
            <td>${esc(s.ip || "-")}</td>
            <td>${esc(s.country_code || "-")}</td>
            <td>${esc(s.connected_since || "-")}</td>
            <td>${esc(s.data_used || "-")}</td>
            <td><button class="btn-sm" style="background:#ff6262" onclick='disconnectUser(${JSON.stringify(s.username)}, ${JSON.stringify(s.session_id || "")})'>Kick</button></td>
        </tr>
    `).join("");
}

function renderUsersRows(users, sessions, onlineUsernames){
    const onlineUsers = new Set((onlineUsernames || []).map(v => String(v).toLowerCase()));
    if (!onlineUsers.size){
        sessions
            .map(s => (s.username || "").trim().toLowerCase())
            .filter(Boolean)
            .forEach(v => onlineUsers.add(v));
    }
    const tbody = document.querySelector("#users_tbl tbody");
    if (!users.length){
        tbody.innerHTML = "<tr><td colspan='9' class='muted'>No users found</td></tr>";
        return;
    }
    tbody.innerHTML = users.map(u => {
        const online = onlineUsers.has((u.username || "").trim().toLowerCase());
        return `
            <tr>
                <td><input type="checkbox" class="user-select" value="${esc(u.username)}" /></td>
                <td><button class="btn-sm" style="background:#4d8dff" onclick='editUserProfile(${JSON.stringify(u.username)}, ${JSON.stringify(u.expiry || "")}, ${JSON.stringify(String(u.bandwidth_kbps ?? 0))})'>${esc(u.username)}</button></td>
                <td>${esc(u.expiry || "-")}</td>
                <td>${esc(u.device_limit ?? 0)}</td>
                <td>${esc(u.bandwidth_kbps ?? 0)} Kbps</td>
                <td>${esc(u.vpn_ip || "-")}</td>
                <td>${esc(u.allowed_ips || "-")}</td>
                <td>${online ? "<span class='tag-online'>Online</span>" : "<span class='tag-offline'>Offline</span>"}</td>
                <td>
                    <div class="actions">
                        <button class="btn-sm" style="background:#5a9dff" onclick='resetUser(${JSON.stringify(u.username)})'>Reset</button>
                        <button class="btn-sm" style="background:#ff7f7f" onclick='disconnectUser(${JSON.stringify(u.username)})'>Kick</button>
                        <button class="btn-sm" style="background:#ff6262" onclick='deleteUser(${JSON.stringify(u.username)})'>Delete</button>
                    </div>
                </td>
            </tr>
        `;
    }).join("");
}

function applyUserSearch(){
    const q = (document.querySelector(".search")?.value || "").trim().toLowerCase();
    if (!q){
        renderUsersRows(LAST_USERS, LAST_SESSIONS, LAST_ONLINE_USERNAMES);
        return;
    }
    const filtered = LAST_USERS.filter(u => {
        const username = (u.username || "").toLowerCase();
        const vpnIp = (u.vpn_ip || "").toLowerCase();
        const allowedIps = (u.allowed_ips || "").toLowerCase();
        const bandwidth = String(u.bandwidth_kbps ?? 0).toLowerCase();
        return username.includes(q) || vpnIp.includes(q) || allowedIps.includes(q) || bandwidth.includes(q);
    });
    renderUsersRows(filtered, LAST_SESSIONS, LAST_ONLINE_USERNAMES);
}

async function loadStatus(){
    try{
        const data = await getJson(API.status);
        const el = document.getElementById("ocserv_status");
        el.textContent = data.status || "Unknown";
        el.style.background = data.color || "#ff6262";
    }catch{
        const el = document.getElementById("ocserv_status");
        el.textContent = "Unknown";
        el.style.background = "#ff6262";
    }
}

async function loadStats(){
    try{
        const s = await getJson(API.stats);
        document.getElementById("stat_total").textContent = s.total_users ?? 0;
        document.getElementById("stat_online").textContent = s.online ?? 0;
        document.getElementById("stat_expiring").textContent = s.expiring_soon ?? 0;
        document.getElementById("stat_traffic").textContent = s.traffic_today || "N/A";
    }catch{}
}

async function loadLogs(){
    if (!LOGS_VISIBLE) return;
    try{
        const res = await fetch(API.logs, { credentials: "same-origin", cache: "no-store" });
        if (res.status === 401 || res.status === 403){
            window.location.replace("/index.php");
            return;
        }
        if (!res.ok) throw new Error();
        document.getElementById("logs").textContent = await res.text();
    }catch{
        document.getElementById("logs").textContent = "Logs unavailable.";
    }
}

async function loadTables(){
    let sessions = [];
    try{
        const live = await getJson(API.live_json);
        sessions = live.sessions || [];
        LAST_ONLINE_USERNAMES = live.online_usernames || [];
        if (Array.isArray(live.auto_disconnected_sessions) && live.auto_disconnected_sessions.length){
            await loadLogs();
        }
    }catch{}
    LAST_SESSIONS = sessions;
    renderLiveRows(sessions);

    try{
        const users = await getJson(API.users);
        LAST_USERS = users || [];
        applyUserSearch();
    }catch{
        document.querySelector("#users_tbl tbody").innerHTML =
            "<tr><td colspan='9' class='muted'>Unable to load users</td></tr>";
    }
}

async function loadRoutes(){
    try{
        const d = await getJson(API.vpn_routes);
        const hint = document.getElementById("routes_config_hint");
        if (hint){
            const p = (d.config_path || "").trim();
            hint.textContent = p ? p.split("/").filter(Boolean).pop() || p : "(no conf)";
            hint.title = p || "";
        }
        const tbody = document.querySelector("#routes_tbl tbody");
        const rows = [];
        (d.routes || []).forEach(r => rows.push({ type: "route", val: r }));
        (d.no_routes || []).forEach(r => rows.push({ type: "no-route", val: r }));
        (d.dns || []).forEach(r => rows.push({ type: "dns", val: r }));
        if (!rows.length){
            tbody.innerHTML = "<tr><td colspan='2' class='muted'>No routes (unreadable?).</td></tr>";
            return;
        }
        tbody.innerHTML = rows.map(x => `
            <tr><td>${esc(x.type)}</td><td>${esc(x.val)}</td></tr>
        `).join("");
    }catch{
        const tbody = document.querySelector("#routes_tbl tbody");
        if (tbody) tbody.innerHTML = "<tr><td colspan='2' class='muted'>Could not load routes.</td></tr>";
    }
}

async function load(){
    await Promise.all([loadStatus(), loadStats(), loadLogs(), loadTables(), loadRoutes()]);
}

async function loadGeoPolicy(){
    try{
        const p = await getJson(API.geo_policy);
        document.getElementById("geo_mode").value = p.mode || "off";
        document.getElementById("geo_countries").value = (p.countries || []).join(",");
        document.getElementById("geo_auto_enforce").checked = !!p.auto_enforce;
    }catch{}
}

function toggleLogs(){
    LOGS_VISIBLE = !LOGS_VISIBLE;
    const el = document.getElementById("logs");
    el.style.display = LOGS_VISIBLE ? "" : "none";
    if (LOGS_VISIBLE) loadLogs();
}

async function openOcservConfEditor(){
    const r = await fetch(API.ocserv_conf, { credentials: "same-origin" });
    if (!r.ok) return alert("Could not load ocserv.conf: " + await readError(r));
    const ta = document.getElementById("ocserv_conf_text");
    const modal = document.getElementById("ocserv_modal");
    if (ta) ta.value = await r.text();
    if (modal) modal.classList.add("open");
}

function closeOcservConfEditor(){
    document.getElementById("ocserv_modal")?.classList.remove("open");
}

async function saveOcservConf(){
    const content = document.getElementById("ocserv_conf_text")?.value ?? "";
    const res = await fetch(API.ocserv_conf, {
        method: "POST",
        headers: {
            "X-CSRF-Token": CSRF_TOKEN,
            "Content-Type": "text/plain; charset=utf-8"
        },
        body: content,
        credentials: "same-origin"
    });
    if (!res.ok) return alert("Save failed: " + await readError(res));
    closeOcservConfEditor();
    alert("Saved. Restart ocserv if you changed server settings.");
    await load();
    await loadRoutes();
}

async function controlOcserv(action){
    const res = await fetch(API.control,{
        method:"POST",
        headers:{ "X-CSRF-Token": CSRF_TOKEN },
        credentials:"same-origin",
        body:new URLSearchParams({ action })
    });
    if(!res.ok) return alert("OCSERV control failed: " + await readError(res));
    await load();
}

async function createUser(){
    const user = document.getElementById("u").value.trim();
    const pass = document.getElementById("p").value;
    const expiry = document.getElementById("e").value.trim();
    const limit = document.getElementById("l").value.trim();
    const vpn_ip = document.getElementById("vpn_ip").value.trim();
    const allowed_ips = document.getElementById("allowed_ips").value.trim();
    const bandwidthSelect = document.getElementById("bandwidth_kbps").value.trim();
    const bandwidthCustom = document.getElementById("bandwidth_custom").value.trim();
    const bandwidth_kbps = bandwidthSelect === "custom" ? bandwidthCustom : bandwidthSelect;
    const expiryForApi = expiry ? expiry.split("-").reverse().join("-") : "";

    const res = await fetch(API.create,{
        method:"POST",
        headers:{ "X-CSRF-Token": CSRF_TOKEN },
        credentials:"same-origin",
        body:new URLSearchParams({ user, pass, expiry: expiryForApi, limit, vpn_ip, allowed_ips, bandwidth_kbps })
    });
    if(!res.ok) return alert("Create failed: " + await readError(res));

    document.getElementById("u").value = "";
    document.getElementById("p").value = "";
    document.getElementById("e").value = "";
    document.getElementById("l").value = "0";
    document.getElementById("bandwidth_kbps").value = "0";
    document.getElementById("bandwidth_custom").value = "";
    document.getElementById("bandwidth_custom").style.display = "none";
    await load();
}

async function bulkCreateUsers(){
    const lines = document.getElementById("bulk_lines").value;
    const res = await fetch(API.bulk_create,{
        method:"POST",
        headers:{ "X-CSRF-Token": CSRF_TOKEN },
        credentials:"same-origin",
        body:new URLSearchParams({ lines })
    });
    if(!res.ok) return alert("Bulk create failed: " + await readError(res));
    const out = await res.json();
    const createdCount = (out.created || []).length;
    const failedCount = (out.failed || []).length;
    if (failedCount){
        const top = out.failed.slice(0, 5).map(x => `Line ${x.line}: ${x.error}`).join("\n");
        alert(`Created: ${createdCount}, Failed: ${failedCount}\n${top}`);
    } else {
        alert(`Created ${createdCount} users successfully.`);
    }
    await load();
}

function triggerCsvUpload(){
    document.getElementById("bulk_csv_file").click();
}

async function uploadCsv(file){
    if (!file) return;
    const text = await file.text();
    const normalized = text
        .replace(/\r\n/g, "\n")
        .split("\n")
        .filter(Boolean)
        .map(line => line.trim())
        .join("\n");
    document.getElementById("bulk_lines").value = normalized;
    await bulkCreateUsers();
}

function downloadCsvTemplate(){
    window.location.href = API.bulk_template;
}

async function applyFirewall(){
    const res = await fetch(API.firewall, { credentials:"same-origin" });
    if(!res.ok) return alert("Firewall apply failed: " + await readError(res));
    alert("Firewall applied.");
    await load();
}

async function deleteUser(username){
    if(!confirm(`Delete user "${username}"?`)) return;
    const res = await fetch(API.del,{
        method:"POST",
        headers:{ "X-CSRF-Token": CSRF_TOKEN },
        credentials:"same-origin",
        body:new URLSearchParams({ user:username })
    });
    if(!res.ok) return alert("Delete failed: " + await readError(res));
    await load();
}

async function deleteSelectedUsers(){
    const selected = Array.from(document.querySelectorAll(".user-select:checked")).map(el => el.value);
    if (!selected.length) return alert("Please select users first.");
    if(!confirm(`Delete ${selected.length} selected user(s)?`)) return;
    const res = await fetch(API.bulk_delete,{
        method:"POST",
        headers:{ "X-CSRF-Token": CSRF_TOKEN },
        credentials:"same-origin",
        body:new URLSearchParams({ users: selected.join(",") })
    });
    if(!res.ok) return alert("Bulk delete failed: " + await readError(res));
    const out = await res.json();
    const failed = out.failed || [];
    if (failed.length){
        alert(`Deleted ${ (out.deleted || []).length }, failed ${failed.length}`);
    }
    await load();
}

async function disconnectUser(username, sessionId=""){
    const res = await fetch(API.disconnect,{
        method:"POST",
        headers:{ "X-CSRF-Token": CSRF_TOKEN },
        credentials:"same-origin",
        body:new URLSearchParams({ user:username, session_id:sessionId })
    });
    if(!res.ok) return alert("Kick failed: " + await readError(res));
    await load();
}

async function resetUser(username){
    const p = prompt(`Enter new password for "${username}":`);
    if(!p) return;
    const res = await fetch(API.reset,{
        method:"POST",
        headers:{ "X-CSRF-Token": CSRF_TOKEN },
        credentials:"same-origin",
        body:new URLSearchParams({ user:username, pass:p })
    });
    if(!res.ok) return alert("Reset failed: " + await readError(res));
    await load();
}

async function editUserProfile(username, currentExpiry, currentBandwidth){
    const expiryInput = prompt(
        `Update expiry for ${username} (DD-MM-YYYY or YYYY-MM-DD, empty to clear):`,
        currentExpiry || ""
    );
    if (expiryInput === null) return;
    const bwInput = prompt(
        `Update bandwidth Kbps for ${username} (0 = unlimited):`,
        String(currentBandwidth || "0")
    );
    if (bwInput === null) return;

    const res = await fetch(API.update_user,{
        method:"POST",
        headers:{ "X-CSRF-Token": CSRF_TOKEN },
        credentials:"same-origin",
        body:new URLSearchParams({
            user: username,
            expiry: (expiryInput || "").trim(),
            bandwidth_kbps: (bwInput || "0").trim()
        })
    });
    if(!res.ok) return alert("Update failed: " + await readError(res));
    await load();
}

async function clearLogs(){
    if(!confirm("Delete all logs?")) return;
    const res = await fetch(API.logs_clear,{
        method:"POST",
        headers:{ "X-CSRF-Token": CSRF_TOKEN },
        credentials:"same-origin"
    });
    if(!res.ok) return alert("Clear logs failed: " + await readError(res));
    if (LOGS_VISIBLE) await loadLogs();
    await load();
}

async function saveGeoPolicy(){
    const mode = document.getElementById("geo_mode").value;
    const countries = document.getElementById("geo_countries").value.trim();
    const auto_enforce = document.getElementById("geo_auto_enforce").checked ? "1" : "0";
    const res = await fetch(API.geo_policy,{
        method:"POST",
        headers:{ "X-CSRF-Token": CSRF_TOKEN },
        credentials:"same-origin",
        body:new URLSearchParams({ mode, countries, auto_enforce })
    });
    if(!res.ok) return alert("Save geo policy failed: " + await readError(res));
    alert("Geo policy saved.");
    await load();
}

async function changeAdminPassword(){
    const current_pass = document.getElementById("admin_cur").value;
    const new_user = document.getElementById("admin_new_user").value.trim();
    const new_pass = document.getElementById("admin_new").value;
    const new_pass_confirm = document.getElementById("admin_new2").value;
    const res = await fetch(API.change_admin,{
        method:"POST",
        headers:{ "X-CSRF-Token": CSRF_TOKEN },
        credentials:"same-origin",
        body:new URLSearchParams({ current_pass, new_pass, new_pass_confirm, new_user })
    });
    if(!res.ok) return alert("Update failed: " + await readError(res));
    document.getElementById("admin_cur").value = "";
    document.getElementById("admin_new").value = "";
    document.getElementById("admin_new2").value = "";
    alert("Admin login updated. Use the new password next time.");
    await load();
}

async function enforceGeoNow(){
    const res = await fetch(API.geo_enforce,{
        method:"POST",
        headers:{ "X-CSRF-Token": CSRF_TOKEN },
        credentials:"same-origin"
    });
    if(!res.ok) return alert("Geo enforce failed: " + await readError(res));
    const out = await res.json();
    alert(`Disconnected ${ (out.disconnected || []).length } session(s).`);
    await load();
}

function logout(){
    fetch(API.logout, { credentials:"same-origin" })
        .then(() => window.location.href = "/index.php");
}

function resetIdleTimer(){
    lastActivityAt = Date.now();
}

async function checkIdleLogout(){
    if ((Date.now() - lastActivityAt) < IDLE_TIMEOUT_MS) return;
    try{
        await fetch(API.logout, { credentials:"same-origin" });
    } finally {
        window.location.href = "/index.php";
    }
}

function generatePassword(){
    const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%";
    let out = "";
    const length = 14;
    if (window.crypto?.getRandomValues){
        const buf = new Uint32Array(length);
        window.crypto.getRandomValues(buf);
        for (const n of buf) out += chars[n % chars.length];
    } else {
        for (let i = 0; i < length; i++) out += chars[Math.floor(Math.random() * chars.length)];
    }
    const input = document.getElementById("p");
    input.value = out;
    input.focus();
}

document.getElementById("bandwidth_kbps")?.addEventListener("change", (e) => {
    const input = document.getElementById("bandwidth_custom");
    if (e.target.value === "custom"){
        input.style.display = "";
        input.focus();
    } else {
        input.style.display = "none";
        input.value = "";
    }
});

document.querySelector(".search")?.addEventListener("input", applyUserSearch);
document.getElementById("select_all_users")?.addEventListener("change", (e) => {
    const checked = !!e.target.checked;
    document.querySelectorAll(".user-select").forEach(cb => cb.checked = checked);
});
document.getElementById("bulk_csv_file")?.addEventListener("change", async (e) => {
    const file = e.target.files && e.target.files[0];
    await uploadCsv(file);
    e.target.value = "";
});

async function bootstrap(){
    const r = await fetch(API.session, { credentials: "same-origin", cache: "no-store" });
    if (!r.ok){
        window.location.replace("/index.php");
        return;
    }
    window.addEventListener("pageshow", (ev) => {
        if (ev.persisted){
            fetch(API.session, { credentials: "same-origin", cache: "no-store" }).then(x => {
                if (!x.ok) window.location.replace("/index.php");
            });
        }
    });
    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") resetIdleTimer();
    });
    ["click","touchstart","keydown","mousemove","scroll"].forEach(evt =>
        document.addEventListener(evt, resetIdleTimer, { passive: true })
    );
    resetIdleTimer();
    loadGeoPolicy();
    setInterval(load, REFRESH_INTERVAL_MS);
    setInterval(checkIdleLogout, 10000);
    document.addEventListener("keydown", (ev) => {
        if (ev.key === "Escape") closeOcservConfEditor();
    });
    load();
}
bootstrap();
</script>
</body>
</html>

