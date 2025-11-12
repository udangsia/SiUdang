import os, random, ssl, datetime
from flask import Flask, render_template_string, request, redirect, session
from supabase import create_client, Client
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from email.message import EmailMessage
import smtplib, ssl, random, os, json, datetime


# ---------------------------
# KONFIGURASI DASAR
# ---------------------------
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ Gagal memuat SUPABASE_URL atau SUPABASE_KEY dari .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------------------
# KONFIGURASI FLASK
# ---------------------------
app = Flask(__name__)
app.secret_key = os.urandom(24)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ---------------------------
# TEMPLATE HALAMAN
# ---------------------------

register_html = """
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daftar Akun - SiUdang</title>
<style>
    body {margin:0; font-family:Poppins,sans-serif; background:linear-gradient(135deg, #ff9a8b, #ff6a00); display:flex; align-items:center; justify-content:center; height:100vh; color:#fff;}
    .container {background:rgba(255,255,255,0.1); backdrop-filter:blur(10px); padding:40px; border-radius:20px; width:350px; text-align:center; box-shadow:0 8px 25px rgba(0,0,0,0.2);}
    h2 {margin-bottom:20px;}
    input {width:85%; padding:10px; margin:8px 0; border:none; border-radius:10px; outline:none;}
    button {width:90%; background:#ff6a00; border:none; color:white; padding:10px; border-radius:10px; cursor:pointer; margin-top:10px; font-weight:bold;}
    button:hover {background:#ff9a8b;}
    a {color:#fff; text-decoration:none; font-size:13px;}
    .message {margin-top:10px; font-size:12px; color:yellow;}
</style>
</head>
<body>
<div class="container">
    <h2>🐠 Buat Akun Baru</h2>
    <form action="{{ url_for('send_otp') }}" method="POST">
        <input type="email" name="email" placeholder="Email Aktif" required><br>
        <input type="password" name="password" placeholder="Password" required><br>
        <button type="submit">Kirim OTP ke Email</button>
    </form>
    <p><a href="/login">Sudah punya akun? Login di sini</a></p>
    {% if message %}<p class="message">{{ message }}</p>{% endif %}
</div>
</body>
</html>
"""

login_html = """
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Login - SiUdang</title>
<style>
    body {margin:0; font-family:Poppins,sans-serif; background:linear-gradient(135deg, #84fab0, #8fd3f4); display:flex; align-items:center; justify-content:center; height:100vh; color:#fff;}
    .container {background:rgba(255,255,255,0.15); backdrop-filter:blur(10px); padding:40px; border-radius:20px; width:350px; text-align:center; box-shadow:0 8px 25px rgba(0,0,0,0.2);}
    h2 {margin-bottom:20px;}
    input {width:85%; padding:10px; margin:8px 0; border:none; border-radius:10px; outline:none;}
    button {width:90%; background:#00a8cc; border:none; color:white; padding:10px; border-radius:10px; cursor:pointer; margin-top:10px; font-weight:bold;}
    button:hover {background:#0096b8;}
    a {color:#fff; text-decoration:none; font-size:13px;}
    .message {margin-top:10px; font-size:12px; color:yellow;}
</style>
</head>
<body>
<div class="container">
    <h2>🔐 Login ke SiUdang</h2>
    <form action="/login_success" method="POST">
        <input type="email" name="email" placeholder="Email Aktif" required><br>
        <input type="password" name="password" placeholder="Password" required><br>
        <button type="submit">Login</button>
    </form>
    <p><a href="/register">Belum punya akun? Daftar di sini</a></p>
    {% if message %}<p class="message">{{ message }}</p>{% endif %}
</div>
</body>
</html>
"""

verify_html = """
<!DOCTYPE html>
<html>
<head>
<title>Verifikasi OTP</title>
<style>
    body {font-family:Poppins,sans-serif; background:linear-gradient(135deg, #f6d365, #fda085); display:flex; align-items:center; justify-content:center; height:100vh; color:#fff;}
    .box {background:rgba(255,255,255,0.15); backdrop-filter:blur(10px); padding:40px; border-radius:20px; text-align:center; width:320px; box-shadow:0 8px 25px rgba(0,0,0,0.2);}
    input {width:80%; padding:10px; border:none; border-radius:10px; margin-top:10px; outline:none;}
    button {width:90%; background:#ff7b54; border:none; color:white; padding:10px; border-radius:10px; cursor:pointer; margin-top:15px; font-weight:bold;}
    button:hover {background:#e76f51;}
    .msg {color:yellow; font-size:12px;}
</style>
</head>
<body>
<div class="box">
    <h2>Masukkan OTP</h2>
    <p>Kode OTP telah dikirim ke email kamu</p>
    <form action="/verify_otp" method="POST">
        <input type="text" name="otp" placeholder="Masukkan 6 digit OTP" required><br>
        <button type="submit">Verifikasi</button>
    </form>
    {% if message %}<p class="msg">{{ message }}</p>{% endif %}
</div>
</body>
</html>
"""

dashboard_html = """
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard SiUdang</title>
<style>
body, html {
    margin:0; padding:0; font-family: 'Poppins', sans-serif; height:100%;
    background: #f0f4f8;
    overflow-x:hidden;
}

/* Sidebar */
.sidebar {
    width: 220px;
    background: linear-gradient(180deg, #b8e3e0 0%, #ffe8de 100%);
    color: #033E3E;
    height:100%;
    position:fixed;
    top:0; left:0;
    padding:20px;
    box-sizing:border-box;
    transition: all 0.3s;
}
.sidebar.collapsed {
    width:60px;
    padding:20px 10px;
}
.sidebar a {
    display:flex; align-items:center; gap:10px;
    text-decoration:none;
    color:#033E3E;
    margin:10px 0;
    padding:10px;
    border-radius:10px;
    transition:0.3s;
    font-weight:500;
}
.sidebar a:hover {
    background: rgba(255,255,255,0.3);
    transform: translateX(5px);
}
.sidebar.collapsed a span.text {
    display:none;
}

/* Toggle Button */
#toggle-btn {
    position:absolute;
    top:20px;
    right:-20px;
    background:#fff;
    color:#0072ff;
    border-radius:50%;
    width:35px; height:35px;
    display:flex;
    align-items:center;
    justify-content:center;
    cursor:pointer;
    box-shadow:0 4px 15px rgba(0,0,0,0.2);
    transition:0.3s;
}
#toggle-btn:hover {
    transform: scale(1.1);
}

/* Content */
.content {
    margin-left:220px;
    padding:30px;
    transition: all 0.3s;
}
.sidebar.collapsed ~ .content {
    margin-left:60px;
}

/* Menu buttons di content */
.menu-btn {
    display:inline-block;
    padding:10px 20px;
    margin:10px 10px 10px 0;
    background: #0072ff;
    color:#fff;
    border:none;
    border-radius:12px;
    cursor:pointer;
    transition:0.3s;
}
.menu-btn:hover {
    background: #00c6ff;
    transform: translateY(-2px);
    box-shadow:0 6px 15px rgba(0,0,0,0.2);
}

/* Content cards */
.card {
    background:#fff;
    padding:20px;
    border-radius:15px;
    box-shadow:0 8px 25px rgba(0,0,0,0.1);
    margin-bottom:20px;
}
.card h3 { color:#0072ff; margin-bottom:10px; }
.card p { color:#555; font-size:14px; }
</style>
</head>
<body>

<div class="sidebar" id="sidebar">
    <h2>SiUdang</h2>
    <a href="/dashboard">🏠 <span class="text">Dashboard</span></a>
    <a href="/coa">📋 <span class="text">COA</span></a>
    <a href="/input_jurnal">✏ <span class="text">Input Jurnal</span></a>
    <a href="/hitung_hpp">💰 <span class="text">Hitung HPP</span></a>
    <a href="/jurnal_umum">📑 <span class="text">Jurnal Umum</span></a>
    <a href="/buku_besar">🗂 <span class="text">Buku Besar</span></a>
    <a href="/neraca_saldo">⚖ <span class="text">Neraca Saldo</span></a>
    <a href="/laporan_keuangan">📊 <span class="text">Laporan Keuangan</span></a>
    <a href="/jurnal_penyesuaian">📝 <span class="text">Jurnal Penyesuaian</span></a>
    <a href="/logout">🚪 <span class="text">Keluar</span></a>
    <div id="toggle-btn">&#9776;</div>
</div>

<div class="content">
    <h1>Selamat datang, {{ email }} 👋</h1>
    <p>Pilih menu di sidebar untuk memulai.</p>

    <!-- Contoh tombol menu -->
    <button class="menu-btn" onclick="location.href='/input_jurnal'">Input Jurnal</button>
    <button class="menu-btn" onclick="location.href='/hitung_hpp'">Hitung HPP</button>
    <button class="menu-btn" onclick="location.href='/laporan_keuangan'">Laporan Keuangan</button>

    <!-- Contoh konten menu -->
    <div class="card">
        <h3>Dashboard Info</h3>
        <p>Ini adalah contoh konten dashboard. Nanti diganti sesuai menu yang dipilih.</p>
    </div>
</div>

<script>
// Toggle sidebar
const sidebar = document.getElementById('sidebar');
const toggleBtn = document.getElementById('toggle-btn');

toggleBtn.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
});
</script>

</body>
</html>
"""

# ---------------------------
# ROUTES
# ---------------------------

@app.route("/")
def index():
    return redirect("/login")

@app.route("/register")
def register():
    return render_template_string(register_html)

@app.route("/login")
def login():
    return render_template_string(login_html)

@app.route("/login_success", methods=["POST"])
def login_success():
    email = request.form["email"]
    password = request.form["password"]
    user = supabase.table("users").select("*").eq("email", email).execute()
    if user.data and check_password_hash(user.data[0]["password"], password):
        session["email"] = email
        return redirect("/dashboard")
    else:
        return render_template_string(login_html, message="❌ Email atau password salah")

@app.route("/send_otp", methods=["POST"])
def send_otp():
    email = request.form["email"]
    password = request.form["password"]
    otp = random.randint(100000, 999999)
    session["otp"] = otp
    session["email"] = email
    session["password"] = password

    try:
        msg = EmailMessage()
        msg.set_content(f"Kode OTP Anda: {otp}")
        msg["Subject"] = "OTP untuk SiUdang"
        msg["From"] = EMAIL_SENDER
        msg["To"] = email

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
            server.send_message(msg)

        return render_template_string(verify_html)
    except Exception as e:
        print(e)
        return render_template_string(register_html, message="❌ Gagal mengirim OTP")

@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    otp_input = request.form["otp"]
    if str(session.get("otp")) == otp_input:
        try:
            hashed_password = generate_password_hash(session["password"])
            supabase.table("users").insert({
                "email": session["email"],
                "password": hashed_password,
                "otp_code": session["otp"],
                "created_at": str(datetime.datetime.now())
            }).execute()
            session.pop("otp", None)
            return redirect("/dashboard")
        except Exception as e:
            print(e)
            return render_template_string(verify_html, message="❌ Gagal menyimpan user ke database.")
    else:
        return render_template_string(verify_html, message="OTP salah. Coba lagi!")

@app.route("/dashboard")
def dashboard():
    if "email" in session:
        return render_template_string(dashboard_html, email=session["email"])
    return redirect("/login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# Dummy menu routes
@app.route("/coa")
@app.route("/input_jurnal")
@app.route("/hitung_hpp")
@app.route("/jurnal_umum")
@app.route("/buku_besar")
@app.route("/neraca_saldo")
@app.route("/laporan_keuangan")
@app.route("/jurnal_penyesuaian")
def dummy_menu():
    return "<h2>Coming Soon! Menu ini sedang dikembangkan.</h2>"

# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True)