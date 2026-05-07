<!DOCTYPE html>
<html>
<head>
    <title>VPN Enterprise</title>
    <style>
        body{
            margin:0;
            font-family:Arial;
            background:#0f172a;
            color:#fff;
        }
        .box{
            width:350px;
            margin:120px auto;
            background:#1e293b;
            padding:30px;
            border-radius:12px;
        }
        input{
            width:100%;
            padding:12px;
            margin:10px 0;
            background:#111;
            border:1px solid #333;
            color:#fff;
        }
        button{
            width:100%;
            padding:12px;
            background:#2563eb;
            border:0;
            color:#fff;
            cursor:pointer;
        }
        footer{
            position:fixed;
            bottom:0;
            width:100%;
            text-align:center;
            padding:10px;
            background:#020617;
            color:#94a3b8;
            font-size:14px;
        }
        .error{
            background:#dc2626;
            padding:10px;
            border-radius:8px;
            margin-bottom:12px;
            color:#fff;
        }
    </style>
</head>
<body>
<div class="box">
    <h2>Alfa VPN Admin Login</h2>

    {% if error %}
        <div class="error">{{ error }}</div>
    {% endif %}

    <form method="post" action="/index.php">
        <input name="user" placeholder="Username">
        <input type="password" name="pass" placeholder="Password">
        <button name="login">Login</button>
    </form>
</div>

<footer>
    © {{ year }} Alfa Solution. All rights reserved.
</footer>
</body>
</html>

