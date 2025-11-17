import os
import random
import ssl
import datetime
from flask import Flask, render_template_string, request, redirect, session, send_from_directory
from supabase import create_client, Client
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from email.message import EmailMessage
import smtplib

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
# TEMPLATE HALAMAN - SEMUA DITARUH DI ATAS SEBELUM ROUTES
# ---------------------------

# 1. Halaman Registrasi
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
    img.logo {width: 120px; margin-bottom: 20px;}
</style>
</head>
<body>
<div class="container">
    <img src="{{ url_for('static', filename='logo_siudang.png') }}" alt="Logo SiUdang" class="logo">
    
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

# 2. Halaman Login
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
    img.logo {width: 120px; margin-bottom: 20px;}
</style>
</head>
<body>
<div class="container">
    <img src="{{ url_for('static', filename='logo_siudang.png') }}" alt="Logo SiUdang" class="logo">

    <h2>Login ke SiUdang</h2>
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

# 3. Halaman Verifikasi OTP
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

# 4. Halaman Dashboard
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
.content {
    margin-left:220px;
    padding:30px;
}

img.logo { width: 120px; margin-bottom: 20px; }

.accordion {
    background-color: #f1f1f1;
    color: #444;
    cursor: pointer;
    padding: 18px;
    width: 100%;
    border: none;
    text-align: left;
    outline: none;
    font-size: 15px;
    margin-top: 10px;
}

.accordion.active, .accordion:hover {
    background-color: #ddd;
}

.panel {
    padding: 0 18px;
    display: none;
    background-color: #f9f9f9;
    overflow: hidden;
    border-left: 3px solid #ff6a00;
}
</style>
</head>
<body>
<div class="sidebar">
    <h2>SiUdang</h2>
    <a href="/dashboard">🏠 Dashboard</a>
    <a href="/coa"> 📋 COA</a>
    <a href="/input_jurnal"> ✏ Input Transaksi</a>
    <a href="/hitung_hpp"> 💰 Hitung HPP</a>
    <a href="/jurnal_umum"> 📑 Jurnal Umum</a>
    <a href="/buku_besar"> 🗂 Buku Besar</a>
    <a href="/neraca_saldo"> ⚖ Neraca Saldo</a>
    <a href="/buku_pembantu_penyusutan"> 🛠 Buku Pembantu Penyusutan</a>
    <a href="/jurnal_penyesuaian"> 📝 Jurnal Penyesuaian</a>
    <a href="/nssp"> 📚 NSSP</a>
    <a href="/laporan_keuangan">📊 Laporan Keuangan</a>
    <a href="/logout">🚪 Logout</a>
</div>

<div class="content">
    <img src="{{ url_for('static', filename='logo_siudang.png') }}" alt="Logo SiUdang" class="logo">

    <h1>Selamat Datang di SiUdang</h1>
    <p>Halo, {{ email }}!</p>
    <p>Aplikasi ini membantu kamu mencatat transaksi keuangan usaha tambak udang secara otomatis — dari jurnal umum sampai laporan keuangan.</p>
    <p>Gunakan menu di sidebar untuk mengelola akun, mencatat transaksi, dan melihat laporan keuanganmu 📊</p>

    <button class="accordion">🧭 Cara Penggunaan SiUdang:</button>
    <div class="panel">
        <ol>
            <li>Masuk ke menu <strong>Chart of Accounts (COA)</strong> untuk menambahkan akun-akun yang diperlukan.</li>
            <li>Buka <strong>Input Jurnal Umum</strong> untuk mencatat transaksi harian.</li>
            <li>Gunakan <strong>Buku Besar</strong> untuk melihat saldo tiap akun.</li>
            <li>Lihat keseimbangan debit dan kredit di <strong>Neraca Saldo</strong>.</li>
            <li>Cek <strong>Laporan Keuangan</strong> untuk hasil akhirnya (Laba Rugi, Perubahan Modal, dan Neraca).</li>
            <li>Gunakan <strong>Buku Pembantu Aset Tetap</strong> untuk menghitung penyusutan alat tambakmu.</li>
        </ol>
    </div>
</div>

<script>
var acc = document.getElementsByClassName("accordion");
for (var i = 0; i < acc.length; i++) {
    acc[i].addEventListener("click", function() {
        this.classList.toggle("active");
        var panel = this.nextElementSibling;
        if (panel.style.display === "block") {
            panel.style.display = "none";
        } else {
            panel.style.display = "block";
        }
    });
}
</script>

</body>
</html>
"""

# 5. Halaman COA
coa_html = """
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Chart of Accounts (COA)</title>
<style>
body {
    font-family: Poppins, sans-serif;
    background: #f4f9f9;
    margin: 0;
    padding: 0;
}

.sidebar {
    width: 220px;
    background: linear-gradient(180deg, #b8e3e0 0%, #ffe8de 100%);
    height: 100vh;
    position: fixed;
    top: 0;
    left: 0;
    padding: 20px;
    color: #033E3E;
    transition: all 0.3s ease;
}
.sidebar h2 {
    font-weight: 700;
    margin-bottom: 20px;
}
.sidebar a {
    display: block;
    text-decoration: none;
    color: #033E3E;
    margin: 10px 0;
    padding: 10px 12px;
    border-radius: 8px;
    font-weight: 500;
    transition: all 0.2s ease-in-out;
}
.sidebar a:hover {
    background: rgba(255, 255, 255, 0.4);
    transform: translateX(4px);
}

.container {
    padding: 40px;
    margin-left: 230px;
    transition: all 0.3s ease;
}

h1 {
    color: #033E3E;
    font-weight: 700;
}

form {
    background: white;
    padding: 25px;
    border-radius: 15px;
    box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);
    margin-bottom: 30px;
    transition: all 0.2s ease-in-out;
}
form:hover {
    transform: scale(1.01);
}

form h3 {
    margin-bottom: 15px;
    color: #055555;
}
input, select {
    width: 95%;
    padding: 10px;
    margin: 5px 0 15px 0;
    border: 1px solid #ccc;
    border-radius: 10px;
    font-size: 15px;
}

button {
    background: #3cbcb4;
    color: #fff;
    border: none;
    padding: 10px 20px;
    border-radius: 10px;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.2s ease-in-out;
}
button:hover {
    background: #2a9790;
    transform: scale(1.05);
}

table {
    width: 100%;
    border-collapse: collapse;
    background: #fff;
    box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);
    border-radius: 12px;
    overflow: hidden;
}
th, td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}
th {
    background: #b8e3e0;
    color: #033E3E;
}
tr:hover {
    background: #f1f1f1;
}

.message {
    color: green;
    font-weight: bold;
    margin-bottom: 10px;
}
</style>
</head>
<body>

<div class="sidebar">
    <h2>SiUdang</h2>
    <a href="/dashboard">🏠 Dashboard</a>
    <a href="/coa"> 📋 COA</a>
    <a href="/input_jurnal"> ✏ Input Transaksi</a>
    <a href="/hitung_hpp"> 💰 Hitung HPP</a>
    <a href="/jurnal_umum"> 📑 Jurnal Umum</a>
    <a href="/buku_besar"> 🗂 Buku Besar</a>
    <a href="/neraca_saldo"> ⚖ Neraca Saldo</a>
    <a href="/buku_pembantu_penyusutan"> 🛠 Buku Pembantu Penyusutan</a>
    <a href="/jurnal_penyesuaian"> 📝 Jurnal Penyesuaian</a>
    <a href="/nssp"> 📚 NSSP</a>
    <a href="/laporan_keuangan">📊 Laporan Keuangan</a>
    <a href="/logout">🚪 Logout</a>
</div>

<div class="container">
    <h1>📋 Chart of Accounts (COA)</h1>
    {% if message %}<p class="message">{{ message }}</p>{% endif %}
    
    <form method="POST">
        <h3>Tambah Akun Baru</h3>
        <input type="text" name="kode_akun" placeholder="Kode Akun" required>
        <input type="text" name="nama_akun" placeholder="Nama Akun" required>
        <select name="tipe_akun" required>
            <option value="">-- Pilih Tipe Akun --</option>
            <option value="Aset">Aset</option>
            <option value="Kewajiban">Kewajiban</option>
            <option value="Modal">Modal</option>
            <option value="Pendapatan">Pendapatan</option>
            <option value="Beban">Beban</option>
        </select>
        <button type="submit">Tambah Akun</button>
    </form>

    <h3>Daftar Akun</h3>
    <table>
        <tr>
            <th>ID</th>
            <th>Kode Akun</th>
            <th>Nama Akun</th>
            <th>Tipe Akun</th>
            <th>Tanggal Dibuat</th>
        </tr>
        {% for akun in coa_list %}
        <tr>
            <td>{{ akun.id }}</td>
            <td>{{ akun.kode_akun }}</td>
            <td>{{ akun.nama_akun }}</td>
            <td>{{ akun.tipe_akun }}</td>
            <td>{{ akun.created_at[:10] if akun.created_at else '-' }}</td>
        </tr>
        {% endfor %}
    </table>
</div>

</body>
</html>
"""

# 6. Template Halaman Input Jurnal
input_jurnal_html = """
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Input Transaksi - SiUdang</title>
<style>
body {
    font-family: Poppins, sans-serif;
    background: #f4f9f9;
    margin: 0;
}

.sidebar {
    width: 220px;
    background: linear-gradient(180deg, #b8e3e0 0%, #ffe8de 100%);
    height: 100vh;
    position: fixed;
    top: 0; left: 0;
    padding: 20px;
    color: #033E3E;
}
.sidebar a {
    display: block;
    text-decoration: none;
    color: #033E3E;
    margin: 10px 0;
    padding: 10px 12px;
    border-radius: 8px;
    font-weight: 500;
    transition: 0.2s;
}
.sidebar a:hover {
    background: rgba(255, 255, 255, 0.4);
}
.container {
    margin-left: 250px;
    padding: 40px;
}
h1 {
    color: #033E3E;
}
form {
    background: white;
    padding: 25px;
    border-radius: 15px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    width: 600px;
}
label {
    font-weight: 600;
    color: #055555;
}
input, select, textarea {
    width: 100%;
    padding: 10px;
    margin: 8px 0 15px 0;
    border: 1px solid #ccc;
    border-radius: 8px;
    font-size: 14px;
}
button {
    background: #3cbcb4;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 10px;
    cursor: pointer;
    font-weight: bold;
}
button:hover {
    background: #2a9790;
}
.message {
    font-weight: bold;
    margin-top: 10px;
    color: green;
}
</style>
</head>
<body>

<div class="sidebar">
    <h2>SiUdang</h2>
    <a href="/dashboard">🏠 Dashboard</a>
    <a href="/coa"> 📋 COA</a>
    <a href="/input_jurnal"> ✏ Input Transaksi</a>
    <a href="/hitung_hpp"> 💰 Hitung HPP</a>
    <a href="/jurnal_umum"> 📑 Jurnal Umum</a>
    <a href="/buku_besar"> 🗂 Buku Besar</a>
    <a href="/neraca_saldo"> ⚖ Neraca Saldo</a>
    <a href="/buku_pembantu_penyusutan"> 🛠 Buku Pembantu Penyusutan</a>
    <a href="/jurnal_penyesuaian"> 📝 Jurnal Penyesuaian</a>
    <a href="/nssp"> 📚 NSSP</a>
    <a href="/laporan_keuangan">📊 Laporan Keuangan</a>
    <a href="/logout">🚪 Logout</a>
</div>

<div class="container">
    <h1>Input Transaksi (Jurnal)</h1>

    {% if message %}<p class="message">{{ message }}</p>{% endif %}

    <form method="POST">
        <label for="tanggal">Tanggal</label>
        <input type="date" id="tanggal" name="tanggal" required>

        <label for="keterangan">Keterangan</label>
        <textarea id="keterangan" name="keterangan" rows="2" placeholder="Contoh: Pembelian perlengkapan tambak" required></textarea>

        <!-- Akun Debit dan Kredit -->
        <div id="akun-fields">
            <!-- Placeholder untuk akun debit dan kredit yang akan ditambahkan -->
        </div>

         <button type="button" onclick="tambahAkun()">Tambah Akun</button>
        <br>
        <button type="submit">Simpan Jurnal (Debit = Kredit)</button>
    </form>
</div>

<script>
// Fungsi untuk menambah akun ke form
function tambahAkun() {
    const akunFieldsContainer = document.getElementById("akun-fields");

     // Membuat elemen baru untuk akun debit atau kredit
    const newAccountField = document.createElement("div");
    newAccountField.classList.add("akun-group");

    const akunSelect = document.createElement("select");
    akunSelect.name = "akun";
    akunSelect.required = true;
    akunSelect.innerHTML = `
        <option value="">-- Pilih Akun --</option>
        {% for akun in coa_list %}
            <option value="{{ akun.nama_akun }} ({{ akun.kode_akun }})">{{ akun.nama_akun }} ({{ akun.kode_akun }})</option>
        {% endfor %}
    `;
     const typeSelect = document.createElement("select");
    typeSelect.name = "jenis_akun";
    typeSelect.required = true;
    typeSelect.innerHTML = `
        <option value="">-- Pilih Debit atau Kredit --</option>
        <option value="debit">Debit</option>
        <option value="kredit">Kredit</option>
    `;

    // Menambahkan elemen dropdown dan memilih akun
    newAccountField.appendChild(akunSelect);
    newAccountField.appendChild(typeSelect);

    // Menambahkan elemen baru ke dalam container
    akunFieldsContainer.appendChild(newAccountField);
}
</script>

</body>
</html>
"""

# 7. Template Halaman Jurnal Umum
jurnal_umum_html = """
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jurnal Umum - SiUdang</title>
<style>
body {
    font-family: Poppins, sans-serif;
    background: #f4f9f9;
    margin: 0;
}

.sidebar {
    width: 220px;
    background: linear-gradient(180deg, #b8e3e0 0%, #ffe8de 100%);
    height: 100vh;
    position: fixed;
    top: 0; left: 0;
    padding: 20px;
    color: #033E3E;
}
.sidebar a {
    display: block;
    text-decoration: none;
    color: #033E3E;
    margin: 10px 0;
    padding: 10px 12px;
    border-radius: 8px;
    font-weight: 500;
    transition: 0.2s;
}
.sidebar a:hover {
    background: rgba(255, 255, 255, 0.4);
}
.container {
    margin-left: 250px;
    padding: 40px;
}
h1 {
    color: #033E3E;
    margin-bottom: 20px;
}
table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    border-radius: 10px;
    overflow: hidden;
}
th, td {
    padding: 12px 15px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}
th {
    background: #3cbcb4;
    color: white;
    font-weight: 600;
}
tr:hover {
    background: #f1f1f1;
}
.debit {
    color: #2e7d32;
    font-weight: 600;
    text-align: right;
}
.kredit {
    color: #c62828;
    font-weight: 600;
    text-align: right;
}
.total-row {
    background: #e8f5e9;
    font-weight: bold;
}
.total-row td {
    border-top: 2px solid #3cbcb4;
    text-align: right;
}
.no-data {
    text-align: center;
    padding: 20px;
    color: #666;
}
.tanggal-keterangan {
    background: #f8f9fa;
    font-weight: 600;
}
.akun-debit {
    border-left: 3px solid #2e7d32;
}
.akun-kredit {
    border-left: 3px solid #c62828;
}
.no-akun {
    font-weight: 600;
    color: #555;
}
.spacer-row {
    height: 5px;
    background: #f8f9fa;
}
</style>
</head>
<body>

<div class="sidebar">
    <h2>SiUdang</h2>
    <a href="/dashboard">🏠 Dashboard</a>
    <a href="/coa"> 📋 COA</a>
    <a href="/input_jurnal"> ✏ Input Transaksi</a>
    <a href="/hitung_hpp"> 💰 Hitung HPP</a>
    <a href="/jurnal_umum"> 📑 Jurnal Umum</a>
    <a href="/buku_besar"> 🗂 Buku Besar</a>
    <a href="/neraca_saldo"> ⚖ Neraca Saldo</a>
    <a href="/buku_pembantu_penyusutan"> 🛠 Buku Pembantu Penyusutan</a>
    <a href="/jurnal_penyesuaian"> 📝 Jurnal Penyesuaian</a>
    <a href="/nssp"> 📚 NSSP</a>
    <a href="/laporan_keuangan">📊 Laporan Keuangan</a>
    <a href="/logout">🚪 Logout</a>
</div>

<div class="container">
    <h1>📑 Jurnal Umum</h1>
    
    {% if jurnal_data %}
    <table>
        <thead>
            <tr>
                <th width="100">Tanggal</th>
                <th width="120">No. Akun</th>
                <th>Nama Akun & Keterangan</th>
                <th width="150" style="text-align: right;">Debit (Rp)</th>
                <th width="150" style="text-align: right;">Kredit (Rp)</th>
            </tr>
        </thead>
        <tbody>
            {% for jurnal in jurnal_data %}
            <!-- Baris untuk Tanggal dan Keterangan -->
            <tr class="tanggal-keterangan">
                <td><strong>{{ jurnal.tanggal }}</strong></td>
                <td></td>
                <td colspan="3"><strong>{{ jurnal.keterangan }}</strong></td>
            </tr>
            
            <!-- Baris untuk Akun Debit -->
            <tr class="akun-debit">
                <td></td>
                <td class="no-akun">{{ jurnal.kode_akun_debit }}</td>
                <td>{{ jurnal.akun_debit }}</td>
                <td class="debit">{{ "Rp {:,.0f}".format(jurnal.jumlah) if jurnal.jumlah else "-" }}</td>
                <td></td>
            </tr>
            
            <!-- Baris untuk Akun Kredit -->
            <tr class="akun-kredit">
                <td></td>
                <td class="no-akun">{{ jurnal.kode_akun_kredit }}</td>
                <td>{{ jurnal.akun_kredit }}</td>
                <td></td>
                <td class="kredit">{{ "Rp {:,.0f}".format(jurnal.jumlah) if jurnal.jumlah else "-" }}</td>
            </tr>
            
            <!-- Baris kosong sebagai pemisah -->
            <tr class="spacer-row">
                <td colspan="5"></td>
            </tr>
            {% endfor %}
            
            <!-- Baris Total -->
            <tr class="total-row">
                <td colspan="3"><strong>TOTAL</strong></td>
                <td class="debit"><strong>{{ "Rp {:,.0f}".format(total_debit) if total_debit else "Rp 0" }}</strong></td>
                <td class="kredit"><strong>{{ "Rp {:,.0f}".format(total_kredit) if total_kredit else "Rp 0" }}</strong></td>
            </tr>
        </tbody>
    </table>
    {% else %}
    <div class="no-data">
        <p>Belum ada data transaksi. Silakan input transaksi terlebih dahulu.</p>
        <a href="/input_jurnal"><button style="margin-top: 10px;">Input Transaksi</button></a>
    </div>
    {% endif %}
</div>

</body>
</html>
"""

# 8. Template Halaman Buku Besar
buku_besar_html = """
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Buku Besar - SiUdang</title>
<style>
body {
    font-family: Poppins, sans-serif;
    background: #f4f9f9;
    margin: 0;
}

.sidebar {
    width: 220px;
    background: linear-gradient(180deg, #b8e3e0 0%, #ffe8de 100%);
    height: 100vh;
    position: fixed;
    top: 0; left: 0;
    padding: 20px;
    color: #033E3E;
}
.sidebar a {
    display: block;
    text-decoration: none;
    color: #033E3E;
    margin: 10px 0;
    padding: 10px 12px;
    border-radius: 8px;
    font-weight: 500;
    transition: 0.2s;
}
.sidebar a:hover {
    background: rgba(255, 255, 255, 0.4);
}
.container {
    margin-left: 250px;
    padding: 40px;
}
h1 {
    color: #033E3E;
    margin-bottom: 20px;
}
.akun-selector {
    background: white;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin-bottom: 20px;
}
.akun-selector select {
    width: 100%;
    padding: 10px;
    border: 1px solid #ccc;
    border-radius: 8px;
    font-size: 14px;
}
table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    border-radius: 10px;
    overflow: hidden;
    margin-top: 20px;
}
th, td {
    padding: 12px 15px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}
th {
    background: #3cbcb4;
    color: white;
    font-weight: 600;
}
tr:hover {
    background: #f1f1f1;
}
.debit {
    color: #2e7d32;
    font-weight: 600;
}
.kredit {
    color: #c62828;
    font-weight: 600;
}
.saldo {
    color: #1565c0;
    font-weight: 600;
}
.akun-header {
    background: #e3f2fd;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 15px;
}
.akun-header h3 {
    margin: 0;
    color: #033E3E;
}
.total-row {
    background: #e8f5e9;
    font-weight: bold;
}
.total-row td {
    border-top: 2px solid #3cbcb4;
}
.no-data {
    text-align: center;
    padding: 40px;
    color: #666;
    background: white;
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
</style>
</head>
<body>

<div class="sidebar">
    <h2>SiUdang</h2>
    <a href="/dashboard">🏠 Dashboard</a>
    <a href="/coa"> 📋 COA</a>
    <a href="/input_jurnal"> ✏ Input Transaksi</a>
    <a href="/hitung_hpp"> 💰 Hitung HPP</a>
    <a href="/jurnal_umum"> 📑 Jurnal Umum</a>
    <a href="/buku_besar"> 🗂 Buku Besar</a>
    <a href="/neraca_saldo"> ⚖ Neraca Saldo</a>
    <a href="/buku_pembantu_penyusutan"> 🛠 Buku Pembantu Penyusutan</a>
    <a href="/jurnal_penyesuaian"> 📝 Jurnal Penyesuaian</a>
    <a href="/nssp"> 📚 NSSP</a>
    <a href="/laporan_keuangan">📊 Laporan Keuangan</a>
    <a href="/logout">🚪 Logout</a>
</div>

<div class="container">
    <h1>🗂 Buku Besar</h1>
    
    <div class="akun-selector">
        <label for="akun_filter"><strong>Pilih Akun:</strong></label>
        <select id="akun_filter" onchange="filterBukuBesar()">
            <option value="">-- Semua Akun --</option>
            {% for akun in coa_list %}
                <option value="{{ akun.nama_akun }} ({{ akun.kode_akun }})">{{ akun.nama_akun }} ({{ akun.kode_akun }})</option>
            {% endfor %}
        </select>
    </div>

    {% if selected_akun %}
    <div class="akun-header">
        <h3>Buku Besar: {{ selected_akun }}</h3>
    </div>
    {% endif %}

    {% if buku_besar_data %}
    <table>
        <thead>
            <tr>
                <th>Tanggal</th>
                <th>Keterangan</th>
                <th>Debit (Rp)</th>
                <th>Kredit (Rp)</th>
                <th>Saldo (Rp)</th>
            </tr>
        </thead>
        <tbody>
            {% for transaksi in buku_besar_data %}
            <tr>
                <td>{{ transaksi.tanggal }}</td>
                <td>{{ transaksi.keterangan }}</td>
                <td class="debit">
                    {% if transaksi.tipe == 'debit' %}
                    {{ "Rp {:,.0f}".format(transaksi.jumlah) }}
                    {% else %}
                    -
                    {% endif %}
                </td>
                <td class="kredit">
                    {% if transaksi.tipe == 'kredit' %}
                    {{ "Rp {:,.0f}".format(transaksi.jumlah) }}
                    {% else %}
                    -
                    {% endif %}
                </td>
                <td class="saldo">{{ "Rp {:,.0f}".format(transaksi.saldo_akumulasi) }}</td>
            </tr>
            {% endfor %}
            <tr class="total-row">
                <td colspan="2"><strong>Total</strong></td>
                <td class="debit"><strong>{{ "Rp {:,.0f}".format(total_debit) }}</strong></td>
                <td class="kredit"><strong>{{ "Rp {:,.0f}".format(total_kredit) }}</strong></td>
                <td class="saldo"><strong>{{ "Rp {:,.0f}".format(saldo_akhir) }}</strong></td>
            </tr>
        </tbody>
    </table>
    {% else %}
    <div class="no-data">
        <p>Belum ada data transaksi untuk akun ini.</p>
        <p>Silakan input transaksi terlebih dahulu di menu Input Transaksi.</p>
        <a href="/input_jurnal"><button style="margin-top: 10px;">Input Transaksi</button></a>
    </div>
    {% endif %}
</div>

<script>
function filterBukuBesar() {
    const selectedAkun = document.getElementById('akun_filter').value;
    if (selectedAkun) {
        window.location.href = '/buku_besar?akun=' + encodeURIComponent(selectedAkun);
    } else {
        window.location.href = '/buku_besar';
    }
}

// Set selected value in dropdown
window.onload = function() {
    const urlParams = new URLSearchParams(window.location.search);
    const selectedAkun = urlParams.get('akun');
    if (selectedAkun) {
        document.getElementById('akun_filter').value = selectedAkun;
    }
}
</script>

</body>
</html>
"""

# 9. Template Halaman Neraca Saldo
neraca_saldo_html = """
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Neraca Saldo - SiUdang</title>
<style>
body {
    font-family: Poppins, sans-serif;
    background: #f4f9f9;
    margin: 0;
}
.sidebar {
    width: 220px;
    background: linear-gradient(180deg, #b8e3e0 0%, #ffe8de 100%);
    height: 100vh;
    position: fixed;
    top: 0; left: 0;
    padding: 20px;
    color: #033E3E;
}
.sidebar a {
    display: block;
    text-decoration: none;
    color: #033E3E;
    margin: 10px 0;
    padding: 10px 12px;
    border-radius: 8px;
    font-weight: 500;
    transition: 0.2s;
}
.sidebar a:hover {
    background: rgba(255, 255, 255, 0.4);
}
.container {
    margin-left: 250px;
    padding: 40px;
}
h1 {
    color: #033E3E;
    margin-bottom: 20px;
}
table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    border-radius: 10px;
    overflow: hidden;
}
th, td {
    padding: 12px 15px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}
th {
    background: #3cbcb4;
    color: white;
    font-weight: 600;
}
tr:hover {
    background: #f1f1f1;
}
.debit {
    color: #2e7d32;
    font-weight: 600;
    text-align: right;
}
.kredit {
    color: #c62828;
    font-weight: 600;
    text-align: right;
}
.total-row {
    background: #e8f5e9;
    font-weight: bold;
}
.total-row td {
    border-top: 2px solid #3cbcb4;
    text-align: right;
}
.balance-correct {
    color: #2e7d32;
    font-weight: bold;
    text-align: center;
    padding: 10px;
    background: #e8f5e9;
    border-radius: 5px;
    margin-bottom: 20px;
}
.balance-incorrect {
    color: #c62828;
    font-weight: bold;
    text-align: center;
    padding: 10px;
    background: #ffebee;
    border-radius: 5px;
    margin-bottom: 20px;
}
.no-data {
    text-align: center;
    padding: 40px;
    color: #666;
}
</style>
</head>
<body>

<div class="sidebar">
    <h2>SiUdang</h2>
    <a href="/dashboard">🏠 Dashboard</a>
    <a href="/coa"> 📋 COA</a>
    <a href="/input_jurnal"> ✏ Input Transaksi</a>
    <a href="/hitung_hpp"> 💰 Hitung HPP</a>
    <a href="/jurnal_umum"> 📑 Jurnal Umum</a>
    <a href="/buku_besar"> 🗂 Buku Besar</a>
    <a href="/neraca_saldo"> ⚖ Neraca Saldo</a>
    <a href="/buku_pembantu_penyusutan"> 🛠 Buku Pembantu Penyusutan</a>
    <a href="/jurnal_penyesuaian"> 📝 Jurnal Penyesuaian</a>
    <a href="/nssp"> 📚 NSSP</a>
    <a href="/laporan_keuangan">📊 Laporan Keuangan</a>
    <a href="/logout">🚪 Logout</a>
</div>

<div class="container">
    <h1>⚖ Neraca Saldo</h1>
    
    {% if neraca_saldo %}
    <!-- Status Balance Check -->
    {% if total_debit == total_kredit %}
    <div class="balance-correct">
        ✅ Neraca Saldo Seimbang! Total Debit: {{ "Rp {:,.0f}".format(total_debit) }} = Total Kredit: {{ "Rp {:,.0f}".format(total_kredit) }}
    </div>
    {% else %}
    <div class="balance-incorrect">
        ❌ Neraca Saldo Tidak Seimbang! Total Debit: {{ "Rp {:,.0f}".format(total_debit) }} ≠ Total Kredit: {{ "Rp {:,.0f}".format(total_kredit) }}
    </div>
    {% endif %}

    <table>
        <thead>
            <tr>
                <th>Kode Akun</th>
                <th>Nama Akun</th>
                <th>Tipe Akun</th>
                <th>Debit (Rp)</th>
                <th>Kredit (Rp)</th>
            </tr>
        </thead>
        <tbody>
            {% for akun in neraca_saldo %}
            <tr>
                <td>{{ akun.kode_akun }}</td>
                <td>{{ akun.nama_akun }}</td>
                <td>{{ akun.tipe_akun }}</td>
                <td class="debit">
                    {% if akun.saldo_debit > 0 %}
                    {{ "Rp {:,.0f}".format(akun.saldo_debit) }}
                    {% else %}
                    -
                    {% endif %}
                </td>
                <td class="kredit">
                    {% if akun.saldo_kredit > 0 %}
                    {{ "Rp {:,.0f}".format(akun.saldo_kredit) }}
                    {% else %}
                    -
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
            
            <tr class="total-row">
                <td colspan="3"><strong>TOTAL</strong></td>
                <td class="debit"><strong>{{ "Rp {:,.0f}".format(total_debit) }}</strong></td>
                <td class="kredit"><strong>{{ "Rp {:,.0f}".format(total_kredit) }}</strong></td>
            </tr>
        </tbody>
    </table>
    {% else %}
    <div class="no-data">
        <p>Belum ada data transaksi untuk membuat Neraca Saldo.</p>
        <p>Silakan input transaksi terlebih dahulu di menu Input Transaksi.</p>
        <a href="/input_jurnal"><button style="margin-top: 10px;">Input Transaksi</button></a>
    </div>
    {% endif %}
</div>
</body>
</html>
"""

# 10. Template Halaman HPP
hpp_html = """
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hitung HPP - SiUdang</title>
<style>
body {
    font-family: Poppins, sans-serif;
    background: #f4f9f9;
    margin: 0;
}

.sidebar {
    width: 220px;
    background: linear-gradient(180deg, #b8e3e0 0%, #ffe8de 100%);
    height: 100vh;
    position: fixed;
    top: 0; left: 0;
    padding: 20px;
    color: #033E3E;
}
.sidebar h2 {
    margin-bottom: 20px;
}
.sidebar a {
    display: block;
    padding: 10px 12px;
    margin: 8px 0;
    text-decoration: none;
    color: #033E3E;
    font-weight: 500;
    border-radius: 8px;
    transition: 0.2s;
}
.sidebar a:hover {
    background: rgba(255,255,255,0.4);
}

.container {
    margin-left: 250px;
    padding: 40px;
}
h1 {
    color: #033E3E;
    margin-bottom: 20px;
}

.info-box {
    background: #e3f2fd;
    padding: 20px;
    border-radius: 10px;
    margin-bottom: 20px;
    border-left: 4px solid #2196f3;
}

.hpp-result {
    background: white;
    padding: 25px;
    border-radius: 12px;
    box-shadow: 0 3px 10px rgba(0,0,0,0.1);
    margin-top: 20px;
}

.hpp-card {
    background: #f8f9fa;
    padding: 20px;
    border-radius: 8px;
    margin: 15px 0;
    border-left: 4px solid #4caf50;
}

.calculation-steps {
    background: #fff3e0;
    padding: 15px;
    border-radius: 8px;
    margin: 15px 0;
    border-left: 4px solid #ff9800;
}

.result-line {
    margin: 8px 0;
    padding: 5px 0;
    border-bottom: 1px solid #eee;
}

.total-hpp {
    background: #e8f5e9;
    padding: 15px;
    border-radius: 8px;
    margin-top: 15px;
    font-weight: bold;
    font-size: 1.2em;
    text-align: center;
    border: 2px solid #4caf50;
}

.no-data {
    text-align: center;
    padding: 40px;
    color: #666;
    background: white;
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
</style>
</head>

<body>

<div class="sidebar">
    <h2>SiUdang</h2>
    <a href="/dashboard">🏠 Dashboard</a>
    <a href="/coa">📋 COA</a>
    <a href="/input_jurnal">✏ Input Transaksi</a>
    <a href="/hitung_hpp">💰 Hitung HPP</a>
    <a href="/jurnal_umum">📑 Jurnal Umum</a>
    <a href="/buku_besar">🗂 Buku Besar</a>
    <a href="/neraca_saldo">⚖ Neraca Saldo</a>
    <a href="/buku_pembantu_penyusutan">🛠 Buku Pembantu Penyusutan</a>
    <a href="/jurnal_penyesuaian">📝 Jurnal Penyesuaian</a>
    <a href="/nssp">📚 NSSP</a>
    <a href="/laporan_keuangan">📊 Laporan Keuangan</a>
    <a href="/logout">🚪 Logout</a>
</div>

<div class="container">
    <h1>💰 Harga Pokok Penjualan (HPP) - Otomatis</h1>

    <div class="info-box">
        <h3>📊 Informasi HPP</h3>
        <p><strong>Rumus HPP:</strong> Persediaan Awal + Pembelian - Persediaan Akhir</p>
        <p>Data diambil otomatis dari transaksi yang sudah dicatat dalam sistem.</p>
    </div>

    {% if hpp_data %}
    <div class="hpp-result">
        <h3>📦 Hasil Perhitungan HPP Otomatis</h3>
        
        <div class="hpp-card">
            <h4>Data Persediaan Udang</h4>
            <div class="result-line">
                <strong>Persediaan Awal:</strong> {{ "Rp {:,.0f}".format(hpp_data.persediaan_awal) }}
            </div>
            <div class="result-line">
                <strong>Pembelian:</strong> {{ "Rp {:,.0f}".format(hpp_data.pembelian) }}
            </div>
            <div class="result-line">
                <strong>Persediaan Akhir:</strong> {{ "Rp {:,.0f}".format(hpp_data.persediaan_akhir) }}
            </div>
        </div>

        <div class="calculation-steps">
            <h4>🧮 Proses Perhitungan</h4>
            <div class="result-line">
                Persediaan Awal ({{ "Rp {:,.0f}".format(hpp_data.persediaan_awal) }}) + 
                Pembelian ({{ "Rp {:,.0f}".format(hpp_data.pembelian) }}) = 
                {{ "Rp {:,.0f}".format(hpp_data.persediaan_awal + hpp_data.pembelian) }}
            </div>
            <div class="result-line">
                {{ "Rp {:,.0f}".format(hpp_data.persediaan_awal + hpp_data.pembelian) }} - 
                Persediaan Akhir ({{ "Rp {:,.0f}".format(hpp_data.persediaan_akhir) }}) = 
                <strong>HPP</strong>
            </div>
        </div>

        <div class="total-hpp">
            💰 <strong>Harga Pokok Penjualan (HPP): {{ "Rp {:,.0f}".format(hpp_data.hpp) }}</strong>
        </div>
    </div>
    {% else %}
    <div class="no-data">
        <p>Belum ada data transaksi persediaan untuk menghitung HPP.</p>
        <p>Pastikan Anda sudah mencatat transaksi berikut:</p>
        <ul style="text-align: left; display: inline-block;">
            <li>Pembelian persediaan udang</li>
            <li>Persediaan awal periode</li>
            <li>Persediaan akhir periode</li>
        </ul>
        <br>
        <a href="/input_jurnal"><button style="margin-top: 10px;">Input Transaksi Persediaan</button></a>
    </div>
    {% endif %}

</div>

</body>
</html>
"""

# 11. Template Halaman Buku Pembantu Penyusutan
buku_penyusutan_html = """
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Buku Pembantu Penyusutan - SiUdang</title>
<style>
body {
    font-family: Poppins, sans-serif;
    background: #f4f9f9;
    margin: 0;
}

.sidebar {
    width: 220px;
    background: linear-gradient(180deg, #b8e3e0 0%, #ffe8de 100%);
    height: 100vh;
    position: fixed;
    top: 0; left: 0;
    padding: 20px;
    color: #033E3E;
}
.sidebar a {
    display: block;
    text-decoration: none;
    color: #033E3E;
    margin: 10px 0;
    padding: 10px 12px;
    border-radius: 8px;
    font-weight: 500;
    transition: 0.2s;
}
.sidebar a:hover {
    background: rgba(255, 255, 255, 0.4);
}
.container {
    margin-left: 250px;
    padding: 40px;
}
h1 {
    color: #033E3E;
    margin-bottom: 20px;
}
.aset-info {
    background: #e3f2fd;
    padding: 20px;
    border-radius: 10px;
    margin-bottom: 20px;
    border-left: 4px solid #2196f3;
}
.aset-card {
    background: white;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin-bottom: 20px;
}
.aset-header {
    background: #3cbcb4;
    color: white;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 15px;
}
.penyusutan-table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    border-radius: 8px;
    overflow: hidden;
    margin-top: 15px;
}
.penyusutan-table th, .penyusutan-table td {
    padding: 12px 15px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}
.penyusutan-table th {
    background: #3cbcb4;
    color: white;
    font-weight: 600;
}
.penyusutan-table tr:hover {
    background: #f1f1f1;
}
.nilai {
    text-align: right;
    font-weight: 600;
}
.akumulasi {
    color: #1565c0;
}
.beban {
    color: #c62828;
}
.nilai-buku {
    color: #2e7d32;
}
.total-row {
    background: #e8f5e9;
    font-weight: bold;
}
.total-row td {
    border-top: 2px solid #3cbcb4;
}
.no-data {
    text-align: center;
    padding: 40px;
    color: #666;
    background: white;
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.status-aktif {
    background: #e8f5e9;
    color: #2e7d32;
    padding: 5px 10px;
    border-radius: 15px;
    font-size: 12px;
    font-weight: 600;
}
.status-nonaktif {
    background: #ffebee;
    color: #c62828;
    padding: 5px 10px;
    border-radius: 15px;
    font-size: 12px;
    font-weight: 600;
}
</style>
</head>
<body>

<div class="sidebar">
    <h2>SiUdang</h2>
    <a href="/dashboard">🏠 Dashboard</a>
    <a href="/coa"> 📋 COA</a>
    <a href="/input_jurnal"> ✏ Input Transaksi</a>
    <a href="/hitung_hpp"> 💰 Hitung HPP</a>
    <a href="/jurnal_umum"> 📑 Jurnal Umum</a>
    <a href="/buku_besar"> 🗂 Buku Besar</a>
    <a href="/neraca_saldo"> ⚖ Neraca Saldo</a>
    <a href="/buku_pembantu_penyusutan"> 🛠 Buku Pembantu Penyusutan</a>
    <a href="/jurnal_penyesuaian"> 📝 Jurnal Penyesuaian</a>
    <a href="/nssp"> 📚 NSSP</a>
    <a href="/laporan_keuangan">📊 Laporan Keuangan</a>
    <a href="/logout">🚪 Logout</a>
</div>

<div class="container">
    <h1>🛠 Buku Pembantu Penyusutan Aset Tetap</h1>

    <div class="aset-info">
        <h3>📊 Informasi Penyusutan Aset</h3>
        <p><strong>Metode Penyusutan:</strong> Garis Lurus (Straight Line)</p>
        <p><strong>Rumus:</strong> (Harga Perolehan - Nilai Residu) ÷ Umur Ekonomis</p>
        <p>Data diambil otomatis dari transaksi pembelian aset tetap.</p>
    </div>

    {% if aset_penyusutan %}
        {% for aset in aset_penyusutan %}
        <div class="aset-card">
            <div class="aset-header">
                <h3>{{ aset.nama_aset }}</h3>
                <div class="{{ 'status-aktif' if aset.status == 'Aktif' else 'status-nonaktif' }}">
                    {{ aset.status }}
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                <div>
                    <strong>Kode Aset:</strong> {{ aset.kode_aset }}<br>
                    <strong>Tanggal Perolehan:</strong> {{ aset.tanggal_perolehan }}<br>
                    <strong>Umur Ekonomis:</strong> {{ aset.umur_ekonomis }} tahun
                </div>
                <div>
                    <strong>Harga Perolehan:</strong> {{ "Rp {:,.0f}".format(aset.harga_perolehan) }}<br>
                    <strong>Nilai Residu:</strong> {{ "Rp {:,.0f}".format(aset.nilai_residu) }}<br>
                    <strong>Penyusutan/Tahun:</strong> {{ "Rp {:,.0f}".format(aset.penyusutan_per_tahun) }}
                </div>
            </div>

            <h4>📅 Jadwal Penyusutan</h4>
            <table class="penyusutan-table">
                <thead>
                    <tr>
                        <th>Tahun</th>
                        <th>Beban Penyusutan</th>
                        <th>Akumulasi Penyusutan</th>
                        <th>Nilai Buku</th>
                    </tr>
                </thead>
                <tbody>
                    {% for tahun in aset.jadwal_penyusutan %}
                    <tr>
                        <td>Tahun {{ tahun.tahun_ke }}</td>
                        <td class="nilai beban">{{ "Rp {:,.0f}".format(tahun.beban_penyusutan) }}</td>
                        <td class="nilai akumulasi">{{ "Rp {:,.0f}".format(tahun.akumulasi_penyusutan) }}</td>
                        <td class="nilai nilai-buku">{{ "Rp {:,.0f}".format(tahun.nilai_buku) }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endfor %}
    {% else %}
    <div class="no-data">
        <p>Belum ada data aset tetap untuk dihitung penyusutannya.</p>
        <p>Pastikan Anda sudah mencatat transaksi pembelian aset tetap dengan akun yang sesuai.</p>
        <p><strong>Contoh akun aset tetap:</strong> Peralatan Tambak, Kendaraan, Bangunan, Mesin</p>
        <br>
        <a href="/input_jurnal"><button style="margin-top: 10px;">Input Transaksi Aset Tetap</button></a>
    </div>
    {% endif %}

</div>

</body>
</html>
"""

# 12. Template Halaman Jurnal Penyesuaian
jurnal_penyesuaian_html = """
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jurnal Penyesuaian - SiUdang</title>
<style>
body {
    font-family: Poppins, sans-serif;
    background: #f4f9f9;
    margin: 0;
}

.sidebar {
    width: 220px;
    background: linear-gradient(180deg, #b8e3e0 0%, #ffe8de 100%);
    height: 100vh;
    position: fixed;
    top: 0; left: 0;
    padding: 20px;
    color: #033E3E;
}
.sidebar a {
    display: block;
    text-decoration: none;
    color: #033E3E;
    margin: 10px 0;
    padding: 10px 12px;
    border-radius: 8px;
    font-weight: 500;
    transition: 0.2s;
}
.sidebar a:hover {
    background: rgba(255, 255, 255, 0.4);
}
.container {
    margin-left: 250px;
    padding: 40px;
}
h1 {
    color: #033E3E;
    margin-bottom: 20px;
}
.info-box {
    background: #e3f2fd;
    padding: 20px;
    border-radius: 10px;
    margin-bottom: 20px;
    border-left: 4px solid #2196f3;
}
table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    border-radius: 10px;
    overflow: hidden;
}
th, td {
    padding: 12px 15px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}
th {
    background: #3cbcb4;
    color: white;
    font-weight: 600;
}
tr:hover {
    background: #f1f1f1;
}
.debit {
    color: #2e7d32;
    font-weight: 600;
    text-align: right;
}
.kredit {
    color: #c62828;
    font-weight: 600;
    text-align: right;
}
.total-row {
    background: #e8f5e9;
    font-weight: bold;
}
.total-row td {
    border-top: 2px solid #3cbcb4;
    text-align: right;
}
.tanggal-keterangan {
    background: #f8f9fa;
    font-weight: 600;
}
.akun-debit {
    border-left: 3px solid #2e7d32;
}
.akun-kredit {
    border-left: 3px solid #c62828;
}
.no-akun {
    font-weight: 600;
    color: #555;
}
.spacer-row {
    height: 5px;
    background: #f8f9fa;
}
.no-data {
    text-align: center;
    padding: 40px;
    color: #666;
}
</style>
</head>
<body>

<div class="sidebar">
    <h2>SiUdang</h2>
    <a href="/dashboard">🏠 Dashboard</a>
    <a href="/coa"> 📋 COA</a>
    <a href="/input_jurnal"> ✏ Input Transaksi</a>
    <a href="/hitung_hpp"> 💰 Hitung HPP</a>
    <a href="/jurnal_umum"> 📑 Jurnal Umum</a>
    <a href="/buku_besar"> 🗂 Buku Besar</a>
    <a href="/neraca_saldo"> ⚖ Neraca Saldo</a>
    <a href="/buku_pembantu_penyusutan"> 🛠 Buku Pembantu Penyusutan</a>
    <a href="/jurnal_penyesuaian"> 📝 Jurnal Penyesuaian</a>
    <a href="/nssp"> 📚 NSSP</a>
    <a href="/laporan_keuangan">📊 Laporan Keuangan</a>
    <a href="/logout">🚪 Logout</a>
</div>

<div class="container">
    <h1>📝 Jurnal Penyesuaian</h1>

    <div class="info-box">
        <h3>📊 Jurnal Penyesuaian Otomatis</h3>
        <p>Jurnal penyesuaian dihasilkan otomatis berdasarkan:</p>
        <ul>
            <li>Penyusutan aset tetap</li>
            <li>Beban yang masih harus dibayar</li>
            <li>Pendapatan yang masih harus diterima</li>
            <li>Pemakaian perlengkapan</li>
            <li>Pendapatan diterima di muka</li>
        </ul>
    </div>
    
    {% if jurnal_penyesuaian %}
    <table>
        <thead>
            <tr>
                <th width="100">Tanggal</th>
                <th width="120">No. Akun</th>
                <th>Nama Akun & Keterangan</th>
                <th width="150" style="text-align: right;">Debit (Rp)</th>
                <th width="150" style="text-align: right;">Kredit (Rp)</th>
            </tr>
        </thead>
        <tbody>
            {% for jurnal in jurnal_penyesuaian %}
            <!-- Baris untuk Tanggal dan Keterangan -->
            <tr class="tanggal-keterangan">
                <td><strong>{{ jurnal.tanggal }}</strong></td>
                <td></td>
                <td colspan="3"><strong>{{ jurnal.keterangan }}</strong></td>
            </tr>
            
            <!-- Baris untuk Akun Debit -->
            <tr class="akun-debit">
                <td></td>
                <td class="no-akun">{{ jurnal.kode_akun_debit }}</td>
                <td>{{ jurnal.akun_debit }}</td>
                <td class="debit">{{ "Rp {:,.0f}".format(jurnal.jumlah) if jurnal.jumlah else "-" }}</td>
                <td></td>
            </tr>
            
            <!-- Baris untuk Akun Kredit -->
            <tr class="akun-kredit">
                <td></td>
                <td class="no-akun">{{ jurnal.kode_akun_kredit }}</td>
                <td>{{ jurnal.akun_kredit }}</td>
                <td></td>
                <td class="kredit">{{ "Rp {:,.0f}".format(jurnal.jumlah) if jurnal.jumlah else "-" }}</td>
            </tr>
            
            <!-- Baris kosong sebagai pemisah -->
            <tr class="spacer-row">
                <td colspan="5"></td>
            </tr>
            {% endfor %}
            
            <!-- Baris Total -->
            <tr class="total-row">
                <td colspan="3"><strong>TOTAL</strong></td>
                <td class="debit"><strong>{{ "Rp {:,.0f}".format(total_debit) if total_debit else "Rp 0" }}</strong></td>
                <td class="kredit"><strong>{{ "Rp {:,.0f}".format(total_kredit) if total_kredit else "Rp 0" }}</strong></td>
            </tr>
        </tbody>
    </table>
    {% else %}
    <div class="no-data">
        <p>Belum ada jurnal penyesuaian yang diperlukan.</p>
        <p>Jurnal penyesuaian akan muncul otomatis ketika terdapat transaksi yang memerlukan penyesuaian.</p>
    </div>
    {% endif %}
</div>

</body>
</html>
"""

# 13. Template Halaman NSSP (Neraca Saldo Setelah Penyesuaian)
nssp_html = """
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NSSP - SiUdang</title>
<style>
body {
    font-family: Poppins, sans-serif;
    background: #f4f9f9;
    margin: 0;
}
.sidebar {
    width: 220px;
    background: linear-gradient(180deg, #b8e3e0 0%, #ffe8de 100%);
    height: 100vh;
    position: fixed;
    top: 0; left: 0;
    padding: 20px;
    color: #033E3E;
}
.sidebar a {
    display: block;
    text-decoration: none;
    color: #033E3E;
    margin: 10px 0;
    padding: 10px 12px;
    border-radius: 8px;
    font-weight: 500;
    transition: 0.2s;
}
.sidebar a:hover {
    background: rgba(255, 255, 255, 0.4);
}
.container {
    margin-left: 250px;
    padding: 40px;
}
h1 {
    color: #033E3E;
    margin-bottom: 20px;
}
.info-box {
    background: #e3f2fd;
    padding: 20px;
    border-radius: 10px;
    margin-bottom: 20px;
    border-left: 4px solid #2196f3;
}
table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    border-radius: 10px;
    overflow: hidden;
}
th, td {
    padding: 12px 15px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}
th {
    background: #3cbcb4;
    color: white;
    font-weight: 600;
}
tr:hover {
    background: #f1f1f1;
}
.debit {
    color: #2e7d32;
    font-weight: 600;
    text-align: right;
}
.kredit {
    color: #c62828;
    font-weight: 600;
    text-align: right;
}
.total-row {
    background: #e8f5e9;
    font-weight: bold;
}
.total-row td {
    border-top: 2px solid #3cbcb4;
    text-align: right;
}
.balance-correct {
    color: #2e7d32;
    font-weight: bold;
    text-align: center;
    padding: 10px;
    background: #e8f5e9;
    border-radius: 5px;
    margin-bottom: 20px;
}
.balance-incorrect {
    color: #c62828;
    font-weight: bold;
    text-align: center;
    padding: 10px;
    background: #ffebee;
    border-radius: 5px;
    margin-bottom: 20px;
}
.no-data {
    text-align: center;
    padding: 40px;
    color: #666;
}
.comparison-section {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 30px;
}
.comparison-card {
    background: white;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.comparison-card h3 {
    margin-top: 0;
    color: #033E3E;
    border-bottom: 2px solid #3cbcb4;
    padding-bottom: 10px;
}
</style>
</head>
<body>

<div class="sidebar">
    <h2>SiUdang</h2>
    <a href="/dashboard">🏠 Dashboard</a>
    <a href="/coa"> 📋 COA</a>
    <a href="/input_jurnal"> ✏ Input Transaksi</a>
    <a href="/hitung_hpp"> 💰 Hitung HPP</a>
    <a href="/jurnal_umum"> 📑 Jurnal Umum</a>
    <a href="/buku_besar"> 🗂 Buku Besar</a>
    <a href="/neraca_saldo"> ⚖ Neraca Saldo</a>
    <a href="/buku_pembantu_penyusutan"> 🛠 Buku Pembantu Penyusutan</a>
    <a href="/jurnal_penyesuaian"> 📝 Jurnal Penyesuaian</a>
    <a href="/nssp"> 📚 NSSP</a>
    <a href="/laporan_keuangan">📊 Laporan Keuangan</a>
    <a href="/logout">🚪 Logout</a>
</div>

<div class="container">
    <h1>📚 Neraca Saldo Setelah Penyesuaian (NSSP)</h1>

    <div class="info-box">
        <h3>📊 Informasi NSSP</h3>
        <p><strong>NSSP</strong> adalah neraca saldo yang telah disesuaikan dengan jurnal penyesuaian.</p>
        <p>NSSP digunakan sebagai dasar untuk menyusun laporan keuangan (Laba Rugi, Perubahan Modal, dan Neraca).</p>
    </div>

    {% if nssp_data %}
    <!-- Status Balance Check -->
    {% if total_debit_nssp == total_kredit_nssp %}
    <div class="balance-correct">
        ✅ NSSP Seimbang! Total Debit: {{ "Rp {:,.0f}".format(total_debit_nssp) }} = Total Kredit: {{ "Rp {:,.0f}".format(total_kredit_nssp) }}
    </div>
    {% else %}
    <div class="balance-incorrect">
        ❌ NSSP Tidak Seimbang! Total Debit: {{ "Rp {:,.0f}".format(total_debit_nssp) }} ≠ Total Kredit: {{ "Rp {:,.0f}".format(total_kredit_nssp) }}
    </div>
    {% endif %}

    <!-- Perbandingan Neraca Saldo vs NSSP -->
    <div class="comparison-section">
        <div class="comparison-card">
            <h3>📋 Neraca Saldo (Sebelum Penyesuaian)</h3>
            <p><strong>Total Debit:</strong> {{ "Rp {:,.0f}".format(total_debit_neraca) }}</p>
            <p><strong>Total Kredit:</strong> {{ "Rp {:,.0f}".format(total_kredit_neraca) }}</p>
            <p><strong>Status:</strong> 
                {% if total_debit_neraca == total_kredit_neraca %}
                <span style="color: #2e7d32;">✅ Seimbang</span>
                {% else %}
                <span style="color: #c62828;">❌ Tidak Seimbang</span>
                {% endif %}
            </p>
        </div>
        
        <div class="comparison-card">
            <h3>📝 NSSP (Setelah Penyesuaian)</h3>
            <p><strong>Total Debit:</strong> {{ "Rp {:,.0f}".format(total_debit_nssp) }}</p>
            <p><strong>Total Kredit:</strong> {{ "Rp {:,.0f}".format(total_kredit_nssp) }}</p>
            <p><strong>Status:</strong> 
                {% if total_debit_nssp == total_kredit_nssp %}
                <span style="color: #2e7d32;">✅ Seimbang</span>
                {% else %}
                <span style="color: #c62828;">❌ Tidak Seimbang</span>
                {% endif %}
            </p>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th>Kode Akun</th>
                <th>Nama Akun</th>
                <th>Tipe Akun</th>
                <th>Debit (Rp)</th>
                <th>Kredit (Rp)</th>
            </tr>
        </thead>
        <tbody>
            {% for akun in nssp_data %}
            <tr>
                <td>{{ akun.kode_akun }}</td>
                <td>{{ akun.nama_akun }}</td>
                <td>{{ akun.tipe_akun }}</td>
                <td class="debit">
                    {% if akun.saldo_debit_nssp > 0 %}
                    {{ "Rp {:,.0f}".format(akun.saldo_debit_nssp) }}
                    {% else %}
                    -
                    {% endif %}
                </td>
                <td class="kredit">
                    {% if akun.saldo_kredit_nssp > 0 %}
                    {{ "Rp {:,.0f}".format(akun.saldo_kredit_nssp) }}
                    {% else %}
                    -
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
            
            <tr class="total-row">
                <td colspan="3"><strong>TOTAL NSSP</strong></td>
                <td class="debit"><strong>{{ "Rp {:,.0f}".format(total_debit_nssp) }}</strong></td>
                <td class="kredit"><strong>{{ "Rp {:,.0f}".format(total_kredit_nssp) }}</strong></td>
            </tr>
        </tbody>
    </table>
    {% else %}
    <div class="no-data">
        <p>Belum ada data untuk membuat NSSP.</p>
        <p>Pastikan Anda sudah:</p>
        <ul style="text-align: left; display: inline-block;">
            <li>Mencatat transaksi di Jurnal Umum</li>
            <li>Melakukan penyesuaian di Jurnal Penyesuaian</li>
        </ul>
        <br>
        <div style="margin-top: 20px;">
            <a href="/input_jurnal"><button style="margin-right: 10px;">Input Transaksi</button></a>
            <a href="/jurnal_penyesuaian"><button>Jurnal Penyesuaian</button></a>
        </div>
    </div>
    {% endif %}
</div>
</body>
</html>
"""

# 14. Template Halaman Laporan Keuangan
laporan_keuangan_html = """
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Laporan Keuangan - SiUdang</title>
<style>
body {
    font-family: Poppins, sans-serif;
    background: #f4f9f9;
    margin: 0;
}
.sidebar {
    width: 220px;
    background: linear-gradient(180deg, #b8e3e0 0%, #ffe8de 100%);
    height: 100vh;
    position: fixed;
    top: 0; left: 0;
    padding: 20px;
    color: #033E3E;
}
.sidebar a {
    display: block;
    text-decoration: none;
    color: #033E3E;
    margin: 10px 0;
    padding: 10px 12px;
    border-radius: 8px;
    font-weight: 500;
    transition: 0.2s;
}
.sidebar a:hover {
    background: rgba(255, 255, 255, 0.4);
}
.container {
    margin-left: 250px;
    padding: 40px;
}
h1 {
    color: #033E3E;
    margin-bottom: 20px;
}
.laporan-section {
    background: white;
    padding: 25px;
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin-bottom: 30px;
}
.laporan-section h2 {
    color: #033E3E;
    border-bottom: 2px solid #3cbcb4;
    padding-bottom: 10px;
    margin-top: 0;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
}
th, td {
    padding: 12px 15px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}
th {
    background: #3cbcb4;
    color: white;
    font-weight: 600;
}
.total-row {
    background: #e8f5e9;
    font-weight: bold;
}
.total-row td {
    border-top: 2px solid #3cbcb4;
}
.nilai {
    text-align: right;
    font-weight: 600;
}
.debit {
    color: #2e7d32;
}
.kredit {
    color: #c62828;
}
.laba {
    color: #2e7d32;
}
.rugi {
    color: #c62828;
}
.no-data {
    text-align: center;
    padding: 40px;
    color: #666;
}
.export-buttons {
    margin-bottom: 20px;
    text-align: right;
}
.export-buttons button {
    background: #3cbcb4;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 8px;
    cursor: pointer;
    margin-left: 10px;
    font-weight: bold;
}
.export-buttons button:hover {
    background: #2a9790;
}
</style>
</head>
<body>

<div class="sidebar">
    <h2>SiUdang</h2>
    <a href="/dashboard">🏠 Dashboard</a>
    <a href="/coa"> 📋 COA</a>
    <a href="/input_jurnal"> ✏ Input Transaksi</a>
    <a href="/hitung_hpp"> 💰 Hitung HPP</a>
    <a href="/jurnal_umum"> 📑 Jurnal Umum</a>
    <a href="/buku_besar"> 🗂 Buku Besar</a>
    <a href="/neraca_saldo"> ⚖ Neraca Saldo</a>
    <a href="/buku_pembantu_penyusutan"> 🛠 Buku Pembantu Penyusutan</a>
    <a href="/jurnal_penyesuaian"> 📝 Jurnal Penyesuaian</a>
    <a href="/nssp"> 📚 NSSP</a>
    <a href="/laporan_keuangan">📊 Laporan Keuangan</a>
    <a href="/logout">🚪 Logout</a>
</div>

<div class="container">
    <h1>📊 Laporan Keuangan</h1>

    <div class="export-buttons">
        <button onclick="window.print()">🖨 Cetak Laporan</button>
        <button onclick="exportToPDF()">📄 Export PDF</button>
    </div>

    {% if laporan_data %}
    <!-- Laporan Laba Rugi -->
    <div class="laporan-section">
        <h2>📈 Laporan Laba Rugi</h2>
        <p><strong>Periode:</strong> {{ laporan_data.periode }}</p>
        
        <table>
            <thead>
                <tr>
                    <th>Keterangan</th>
                    <th>Jumlah (Rp)</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>Pendapatan Usaha</strong></td>
                    <td class="nilai">{{ "Rp {:,.0f}".format(laporan_data.pendapatan_usaha) }}</td>
                </tr>
                <tr>
                    <td style="padding-left: 20px;">Pendapatan Penjualan Udang</td>
                    <td class="nilai">{{ "Rp {:,.0f}".format(laporan_data.pendapatan_penjualan) }}</td>
                </tr>
                
                <tr>
                    <td><strong>Harga Pokok Penjualan (HPP)</strong></td>
                    <td class="nilai">{{ "Rp {:,.0f}".format(laporan_data.hpp) }}</td>
                </tr>
                
                <tr class="total-row">
                    <td><strong>LABA KOTOR</strong></td>
                    <td class="nilai laba"><strong>{{ "Rp {:,.0f}".format(laporan_data.laba_kotor) }}</strong></td>
                </tr>
                
                <tr>
                    <td><strong>Beban Operasional</strong></td>
                    <td class="nilai">{{ "Rp {:,.0f}".format(laporan_data.total_beban) }}</td>
                </tr>
                {% for beban in laporan_data.beban_operasional %}
                <tr>
                    <td style="padding-left: 20px;">{{ beban.nama }}</td>
                    <td class="nilai">{{ "Rp {:,.0f}".format(beban.jumlah) }}</td>
                </tr>
                {% endfor %}
                
                <tr class="total-row">
                    <td><strong>LABA BERSIH</strong></td>
                    <td class="nilai {{ 'laba' if laporan_data.laba_bersih >= 0 else 'rugi' }}">
                        <strong>{{ "Rp {:,.0f}".format(laporan_data.laba_bersih) }}</strong>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- Laporan Perubahan Modal -->
    <div class="laporan-section">
        <h2>💰 Laporan Perubahan Modal</h2>
        
        <table>
            <tbody>
                <tr>
                    <td>Modal Awal</td>
                    <td class="nilai">{{ "Rp {:,.0f}".format(laporan_data.modal_awal) }}</td>
                </tr>
                <tr>
                    <td>Laba Bersih</td>
                    <td class="nilai {{ 'laba' if laporan_data.laba_bersih >= 0 else 'rugi' }}">
                        {{ "Rp {:,.0f}".format(laporan_data.laba_bersih) }}
                    </td>
                </tr>
                <tr>
                    <td>Prive/Penarikan</td>
                    <td class="nilai">{{ "Rp {:,.0f}".format(laporan_data.prive) }}</td>
                </tr>
                <tr class="total-row">
                    <td><strong>Modal Akhir</strong></td>
                    <td class="nilai"><strong>{{ "Rp {:,.0f}".format(laporan_data.modal_akhir) }}</strong></td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- Neraca -->
    <div class="laporan-section">
        <h2>⚖ Neraca</h2>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <!-- Aset -->
            <div>
                <h3>ASET</h3>
                <table>
                    <tbody>
                        {% for aset in laporan_data.neraca.aset %}
                        <tr>
                            <td>{{ aset.nama }}</td>
                            <td class="nilai">{{ "Rp {:,.0f}".format(aset.saldo) }}</td>
                        </tr>
                        {% endfor %}
                        <tr class="total-row">
                            <td><strong>TOTAL ASET</strong></td>
                            <td class="nilai"><strong>{{ "Rp {:,.0f}".format(laporan_data.neraca.total_aset) }}</strong></td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <!-- Kewajiban & Modal -->
            <div>
                <h3>KEWAJIBAN & MODAL</h3>
                <table>
                    <tbody>
                        <tr>
                            <td><strong>Kewajiban</strong></td>
                            <td></td>
                        </tr>
                        {% for kewajiban in laporan_data.neraca.kewajiban %}
                        <tr>
                            <td style="padding-left: 20px;">{{ kewajiban.nama }}</td>
                            <td class="nilai">{{ "Rp {:,.0f}".format(kewajiban.saldo) }}</td>
                        </tr>
                        {% endfor %}
                        <tr>
                            <td><strong>Modal</strong></td>
                            <td class="nilai">{{ "Rp {:,.0f}".format(laporan_data.modal_akhir) }}</td>
                        </tr>
                        <tr class="total-row">
                            <td><strong>TOTAL KEWAJIBAN & MODAL</strong></td>
                            <td class="nilai"><strong>{{ "Rp {:,.0f}".format(laporan_data.neraca.total_kewajiban_modal) }}</strong></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Status Balance Check -->
        <div style="text-align: center; margin-top: 20px; padding: 15px; background: {{ '#e8f5e9' if laporan_data.neraca.total_aset == laporan_data.neraca.total_kewajiban_modal else '#ffebee' }}; border-radius: 8px;">
            <strong>
                {% if laporan_data.neraca.total_aset == laporan_data.neraca.total_kewajiban_modal %}
                ✅ Neraca Seimbang! Total Aset = Total Kewajiban & Modal
                {% else %}
                ❌ Neraca Tidak Seimbang! Total Aset ≠ Total Kewajiban & Modal
                {% endif %}
            </strong>
        </div>
    </div>
    
    {% else %}
    <div class="no-data">
        <p>Belum ada data untuk membuat laporan keuangan.</p>
        <p>Pastikan Anda sudah menyelesaikan seluruh proses akuntansi:</p>
        <ol style="text-align: left; display: inline-block;">
            <li>Input transaksi di Jurnal Umum</li>
            <li>Lakukan penyesuaian di Jurnal Penyesuaian</li>
            <li>Buat NSSP (Neraca Saldo Setelah Penyesuaian)</li>
        </ol>
        <br>
        <div style="margin-top: 20px;">
            <a href="/nssp"><button>Buat NSSP Terlebih Dahulu</button></a>
        </div>
    </div>
    {% endif %}
</div>

<script>
function exportToPDF() {
    alert('Fitur export PDF akan segera tersedia!');
    // Implementasi export PDF bisa ditambahkan di sini
}
</script>

</body>
</html>
"""

# ---------------------------
# ROUTES - SEMUA DITARUH DI BAWAH TEMPLATE
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

@app.route("/coa", methods=["GET", "POST"])
def coa():
    if "email" not in session:
        return redirect("/login")

    message = ""

    if request.method == "POST":
        kode_akun = request.form["kode_akun"]
        nama_akun = request.form["nama_akun"]
        tipe_akun = request.form["tipe_akun"]

        try:
            supabase.table("coa").insert({
                "kode_akun": kode_akun,
                "nama_akun": nama_akun,
                "tipe_akun": tipe_akun,
            }).execute()
            message = "✅ Akun berhasil ditambahkan!"
        except Exception as e:
            print(e)
            message = "❌ Gagal menambahkan akun."

    data = supabase.table("coa").select("*").execute()
    coa_list = data.data if data.data else []

    return render_template_string(coa_html, coa_list=coa_list, message=message)

@app.route("/input_jurnal", methods=["GET", "POST"])
def input_jurnal():
    if "email" not in session:
        return redirect("/login")

    message = ""

    # Ambil daftar akun dari tabel COA untuk dropdown
    coa_data = supabase.table("coa").select("*").execute()
    coa_list = coa_data.data if coa_data.data else []

    # Jika form disubmit
    if request.method == "POST":
        tanggal = request.form["tanggal"]
        akun_debit = request.form["akun_debit"]
        akun_kredit = request.form["akun_kredit"]
        keterangan = request.form["keterangan"]
        jumlah_str = request.form["jumlah"].replace("Rp ", "").replace(".", "")
        
        try:
            jumlah = float(jumlah_str)
        except ValueError:
            message = "❌ Format jumlah tidak valid"
            return render_template_string(input_jurnal_html, coa_list=coa_list, message=message)

        try:
            # Simpan ke tabel jurnal di Supabase
            response = supabase.table("jurnal").insert({
                "tanggal": tanggal,
                "akun_debit": akun_debit,
                "akun_kredit": akun_kredit,
                "keterangan": keterangan,
                "jumlah": jumlah,
                "created_at": str(datetime.datetime.now())
            }).execute()
            
            if response.data:
                message = "✅ Jurnal berhasil disimpan!"
            else:
                message = "❌ Gagal menyimpan jurnal."
                
        except Exception as e:
            print("Error:", e)
            message = "❌ Terjadi kesalahan saat menyimpan jurnal."

    return render_template_string(input_jurnal_html, coa_list=coa_list, message=message)

@app.route("/jurnal_umum")
def jurnal_umum():
    if "email" not in session:
        return redirect("/login")

    # Ambil data jurnal dari database
    try:
        jurnal_data = supabase.table("jurnal").select("*").order("tanggal").execute()
        jurnal_list = jurnal_data.data if jurnal_data.data else []
        
        # Proses data untuk format baru
        processed_jurnal = []
        for jurnal in jurnal_list:
            # Ekstrak kode akun dari nama akun (format: "Nama Akun (KODE)")
            akun_debit = jurnal["akun_debit"]
            akun_kredit = jurnal["akun_kredit"]
            
            # Ambil kode akun dari dalam kurung
            kode_akun_debit = akun_debit.split('(')[-1].replace(')', '').strip() if '(' in akun_debit else ''
            kode_akun_kredit = akun_kredit.split('(')[-1].replace(')', '').strip() if '(' in akun_kredit else ''
            
            # Ambil nama akun tanpa kode
            nama_akun_debit = akun_debit.split('(')[0].strip() if '(' in akun_debit else akun_debit
            nama_akun_kredit = akun_kredit.split('(')[0].strip() if '(' in akun_kredit else akun_kredit
            
            processed_jurnal.append({
                "tanggal": jurnal["tanggal"],
                "keterangan": jurnal["keterangan"],
                "akun_debit": nama_akun_debit,
                "akun_kredit": nama_akun_kredit,
                "kode_akun_debit": kode_akun_debit,
                "kode_akun_kredit": kode_akun_kredit,
                "jumlah": jurnal["jumlah"]
            })
        
        # Hitung total debit dan kredit
        total_debit = sum(jurnal["jumlah"] for jurnal in jurnal_list if jurnal["jumlah"])
        total_kredit = total_debit  # Karena sistem double entry, debit = kredit
        
    except Exception as e:
        print("Error:", e)
        processed_jurnal = []
        total_debit = 0
        total_kredit = 0

    return render_template_string(jurnal_umum_html, 
                                 jurnal_data=processed_jurnal, 
                                 total_debit=total_debit, 
                                 total_kredit=total_kredit)

@app.route("/buku_besar")
def buku_besar():
    if "email" not in session:
        return redirect("/login")

    # Ambil parameter filter akun dari URL
    selected_akun = request.args.get('akun', '')
    
    # Ambil daftar akun dari COA untuk dropdown
    coa_data = supabase.table("coa").select("*").execute()
    coa_list = coa_data.data if coa_data.data else []

    # Ambil semua data jurnal
    try:
        jurnal_data = supabase.table("jurnal").select("*").order("tanggal").execute()
        jurnal_list = jurnal_data.data if jurnal_data.data else []
    except Exception as e:
        print("Error:", e)
        jurnal_list = []

    # Proses data untuk buku besar
    buku_besar_data = []
    saldo_akun = {}

    for jurnal in jurnal_list:
        # Proses akun debit
        akun_debit = jurnal["akun_debit"]
        if not selected_akun or akun_debit == selected_akun:
            if akun_debit not in saldo_akun:
                saldo_akun[akun_debit] = 0
            
            saldo_akun[akun_debit] += jurnal["jumlah"]
            
            buku_besar_data.append({
                "tanggal": jurnal["tanggal"],
                "keterangan": jurnal["keterangan"],
                "tipe": "debit",
                "jumlah": jurnal["jumlah"],
                "saldo_akumulasi": saldo_akun[akun_debit],
                "akun": akun_debit
            })

        # Proses akun kredit
        akun_kredit = jurnal["akun_kredit"]
        if not selected_akun or akun_kredit == selected_akun:
            if akun_kredit not in saldo_akun:
                saldo_akun[akun_kredit] = 0
            
            saldo_akun[akun_kredit] -= jurnal["jumlah"]
            
            buku_besar_data.append({
                "tanggal": jurnal["tanggal"],
                "keterangan": jurnal["keterangan"],
                "tipe": "kredit",
                "jumlah": jurnal["jumlah"],
                "saldo_akumulasi": saldo_akun[akun_kredit],
                "akun": akun_kredit
            })

    # Urutkan berdasarkan tanggal
    buku_besar_data.sort(key=lambda x: x["tanggal"])

    # Hitung total debit dan kredit untuk akun yang dipilih
    total_debit = sum(item["jumlah"] for item in buku_besar_data if item["tipe"] == "debit" and (not selected_akun or item["akun"] == selected_akun))
    total_kredit = sum(item["jumlah"] for item in buku_besar_data if item["tipe"] == "kredit" and (not selected_akun or item["akun"] == selected_akun))
    
    # Hitung saldo akhir
    if selected_akun and selected_akun in saldo_akun:
        saldo_akhir = saldo_akun[selected_akun]
    else:
        saldo_akhir = total_debit - total_kredit

    # Filter data berdasarkan akun yang dipilih
    if selected_akun:
        buku_besar_data = [item for item in buku_besar_data if item["akun"] == selected_akun]

    return render_template_string(buku_besar_html, 
                                 coa_list=coa_list,
                                 buku_besar_data=buku_besar_data,
                                 selected_akun=selected_akun,
                                 total_debit=total_debit,
                                 total_kredit=total_kredit,
                                 saldo_akhir=saldo_akhir)

@app.route("/neraca_saldo")
def neraca_saldo():
    if "email" not in session:
        return redirect("/login")

    try:
        # Ambil semua data COA
        coa_data = supabase.table("coa").select("*").execute()
        coa_list = coa_data.data if coa_data.data else []

        # Ambil semua data jurnal
        jurnal_data = supabase.table("jurnal").select("*").execute()
        jurnal_list = jurnal_data.data if jurnal_data.data else []

        # Buat struktur untuk menyimpan saldo setiap akun
        saldo_akun = {}
        
        # Inisialisasi saldo untuk setiap akun di COA
        for akun in coa_list:
            kode_akun = akun["kode_akun"]
            saldo_akun[kode_akun] = {
                "kode_akun": kode_akun,
                "nama_akun": akun["nama_akun"],
                "tipe_akun": akun["tipe_akun"],
                "saldo_debit": 0,
                "saldo_kredit": 0
            }

        # Proses setiap transaksi jurnal
        for jurnal in jurnal_list:
            # Ekstrak kode akun dari nama akun (format: "Nama Akun (KODE)")
            akun_debit_full = jurnal["akun_debit"]
            akun_kredit_full = jurnal["akun_kredit"]
            
            # Ambil kode akun dari string
            kode_debit = akun_debit_full.split('(')[-1].replace(')', '').strip() if '(' in akun_debit_full else ''
            kode_kredit = akun_kredit_full.split('(')[-1].replace(')', '').strip() if '(' in akun_kredit_full else ''
            
            jumlah = jurnal["jumlah"]

            # Update saldo untuk akun debit
            if kode_debit and kode_debit in saldo_akun:
                saldo_akun[kode_debit]["saldo_debit"] += jumlah

            # Update saldo untuk akun kredit
            if kode_kredit and kode_kredit in saldo_akun:
                saldo_akun[kode_kredit]["saldo_kredit"] += jumlah

        # Konversi ke list untuk ditampilkan
        neraca_saldo_list = list(saldo_akun.values())
        
        # Hitung total debit dan kredit
        total_debit = sum(akun["saldo_debit"] for akun in neraca_saldo_list)
        total_kredit = sum(akun["saldo_kredit"] for akun in neraca_saldo_list)

        return render_template_string(
            neraca_saldo_html,
            neraca_saldo=neraca_saldo_list,
            total_debit=total_debit,
            total_kredit=total_kredit
        )

    except Exception as e:
        print("Error:", e)
        return render_template_string(neraca_saldo_html, neraca_saldo=None, total_debit=0, total_kredit=0)

@app.route("/hitung_hpp")
def hitung_hpp():
    if "email" not in session:
        return redirect("/login")

    try:
        # Ambil data jurnal untuk menghitung HPP otomatis
        jurnal_data = supabase.table("jurnal").select("*").execute()
        jurnal_list = jurnal_data.data if jurnal_data.data else []

        # Inisialisasi variabel HPP
        persediaan_awal = 0
        pembelian = 0
        persediaan_akhir = 0

        # Analisis transaksi untuk menghitung komponen HPP
        for jurnal in jurnal_list:
            keterangan = jurnal["keterangan"].lower()
            akun_debit = jurnal["akun_debit"].lower()
            akun_kredit = jurnal["akun_kredit"].lower()
            jumlah = jurnal["jumlah"]

            # Identifikasi transaksi persediaan awal
            if any(keyword in keterangan for keyword in ['persediaan awal', 'saldo awal', 'stok awal']):
                if 'persediaan' in akun_debit:
                    persediaan_awal += jumlah

            # Identifikasi transaksi pembelian
            elif any(keyword in keterangan for keyword in ['pembelian', 'beli udang', 'beli bibit']):
                if 'persediaan' in akun_debit or 'pembelian' in akun_debit:
                    pembelian += jumlah

            # Identifikasi transaksi persediaan akhir (biasanya dari penyesuaian)
            elif any(keyword in keterangan for keyword in ['persediaan akhir', 'stock opname', 'penyesuaian persediaan']):
                if 'persediaan' in akun_debit:
                    persediaan_akhir += jumlah

        # Hitung HPP
        hpp = persediaan_awal + pembelian - persediaan_akhir

        # Siapkan data untuk ditampilkan
        hpp_data = None
        if persediaan_awal > 0 or pembelian > 0:
            hpp_data = {
                "persediaan_awal": persediaan_awal,
                "pembelian": pembelian,
                "persediaan_akhir": persediaan_akhir,
                "hpp": hpp
            }

        return render_template_string(hpp_html, hpp_data=hpp_data)

    except Exception as e:
        print("Error:", e)
        return render_template_string(hpp_html, hpp_data=None)

@app.route("/buku_pembantu_penyusutan")
def buku_pembantu_penyusutan():
    if "email" not in session:
        return redirect("/login")

    try:
        # Ambil data COA untuk identifikasi aset tetap
        coa_data = supabase.table("coa").select("*").execute()
        coa_list = coa_data.data if coa_data.data else []

        # Ambil data jurnal untuk analisis aset tetap
        jurnal_data = supabase.table("jurnal").select("*").execute()
        jurnal_list = jurnal_data.data if jurnal_data.data else []

        # Identifikasi aset tetap dari COA
        aset_tetap_coa = [akun for akun in coa_list if any(keyword in akun["nama_akun"].lower() 
                          for keyword in ['peralatan', 'kendaraan', 'bangunan', 'mesin', 'aset', 'inventaris'])]

        # Analisis transaksi untuk aset tetap
        aset_penyusutan = []

        for aset_coa in aset_tetap_coa:
            # Cari transaksi pembelian aset ini
            transaksi_aset = []
            for jurnal in jurnal_list:
                if (aset_coa["kode_akun"] in jurnal["akun_debit"] or 
                    aset_coa["kode_akun"] in jurnal["akun_kredit"]):
                    # Identifikasi transaksi pembelian
                    if any(keyword in jurnal["keterangan"].lower() 
                           for keyword in ['pembelian', 'beli', 'perolehan']):
                        transaksi_aset.append(jurnal)

            if transaksi_aset:
                # Hitung total nilai aset
                total_nilai = 0
                tanggal_perolehan = None
                
                for transaksi in transaksi_aset:
                    if aset_coa["kode_akun"] in transaksi["akun_debit"]:
                        total_nilai += transaksi["jumlah"]
                    if not tanggal_perolehan:
                        tanggal_perolehan = transaksi["tanggal"]

                if total_nilai > 0:
                    # Tentukan umur ekonomis berdasarkan jenis aset
                    nama_aset = aset_coa["nama_akun"].lower()
                    if 'kendaraan' in nama_aset:
                        umur_ekonomis = 5
                        nilai_residu = total_nilai * 0.1  # 10% dari harga perolehan
                    elif 'peralatan' in nama_aset:
                        umur_ekonomis = 3
                        nilai_residu = total_nilai * 0.05  # 5% dari harga perolehan
                    elif 'bangunan' in nama_aset:
                        umur_ekonomis = 20
                        nilai_residu = total_nilai * 0.2  # 20% dari harga perolehan
                    else:
                        umur_ekonomis = 5
                        nilai_residu = total_nilai * 0.1  # 10% dari harga perolehan

                    # Hitung penyusutan per tahun
                    penyusutan_per_tahun = (total_nilai - nilai_residu) / umur_ekonomis

                    # Buat jadwal penyusutan untuk 5 tahun ke depan
                    jadwal_penyusutan = []
                    akumulasi_penyusutan = 0
                    
                    for tahun in range(1, umur_ekonomis + 1):
                        akumulasi_penyusutan += penyusutan_per_tahun
                        nilai_buku = total_nilai - akumulasi_penyusutan
                        
                        jadwal_penyusutan.append({
                            "tahun_ke": tahun,
                            "beban_penyusutan": penyusutan_per_tahun,
                            "akumulasi_penyusutan": akumulasi_penyusutan,
                            "nilai_buku": nilai_buku
                        })

                    # Tentukan status aset
                    status = "Aktif" if nilai_buku > nilai_residu else "Nonaktif"

                    aset_penyusutan.append({
                        "kode_aset": aset_coa["kode_akun"],
                        "nama_aset": aset_coa["nama_akun"],
                        "tanggal_perolehan": tanggal_perolehan,
                        "harga_perolehan": total_nilai,
                        "nilai_residu": nilai_residu,
                        "umur_ekonomis": umur_ekonomis,
                        "penyusutan_per_tahun": penyusutan_per_tahun,
                        "jadwal_penyusutan": jadwal_penyusutan,
                        "status": status
                    })

        return render_template_string(
            buku_penyusutan_html,
            aset_penyusutan=aset_penyusutan
        )

    except Exception as e:
        print("Error:", e)
        return render_template_string(buku_penyusutan_html, aset_penyusutan=None)

@app.route("/jurnal_penyesuaian")
def jurnal_penyesuaian():
    if "email" not in session:
        return redirect("/login")

    try:
        # Ambil data untuk generate jurnal penyesuaian otomatis
        jurnal_penyesuaian_list = []
        total_debit = 0
        total_kredit = 0

        # 1. Penyesuaian Penyusutan Aset Tetap
        aset_penyusutan_data = []  # Data dari buku penyusutan
        
        # Simulasi data penyusutan (dalam implementasi nyata, ambil dari perhitungan sebelumnya)
        # Contoh: Penyusutan peralatan
        jurnal_penyesuaian_list.append({
            "tanggal": datetime.datetime.now().strftime("%Y-%m-%d"),
            "keterangan": "Penyusutan Peralatan Tambak Bulan Ini",
            "akun_debit": "Beban Penyusutan Peralatan",
            "akun_kredit": "Akumulasi Penyusutan Peralatan",
            "kode_akun_debit": "511",
            "kode_akun_kredit": "114",
            "jumlah": 500000
        })
        total_debit += 500000
        total_kredit += 500000

        # 2. Penyesuaian Beban yang Masih Harus Dibayar
        jurnal_penyesuaian_list.append({
            "tanggal": datetime.datetime.now().strftime("%Y-%m-%d"),
            "keterangan": "Beban Gaji yang Masih Harus Dibayar",
            "akun_debit": "Beban Gaji",
            "akun_kredit": "Utang Gaji",
            "kode_akun_debit": "512",
            "kode_akun_kredit": "211",
            "jumlah": 3000000
        })
        total_debit += 3000000
        total_kredit += 3000000

        # 3. Penyesuaian Pemakaian Perlengkapan
        jurnal_penyesuaian_list.append({
            "tanggal": datetime.datetime.now().strftime("%Y-%m-%d"),
            "keterangan": "Pemakaian Perlengkapan Tambak",
            "akun_debit": "Beban Perlengkapan",
            "akun_kredit": "Perlengkapan",
            "kode_akun_debit": "513",
            "kode_akun_kredit": "113",
            "jumlah": 750000
        })
        total_debit += 750000
        total_kredit += 750000

        return render_template_string(
            jurnal_penyesuaian_html,
            jurnal_penyesuaian=jurnal_penyesuaian_list,
            total_debit=total_debit,
            total_kredit=total_kredit
        )

    except Exception as e:
        print("Error:", e)
        return render_template_string(jurnal_penyesuaian_html, jurnal_penyesuaian=None, total_debit=0, total_kredit=0)

@app.route("/nssp")
def nssp():
    if "email" not in session:
        return redirect("/login")

    try:
        # Ambil data neraca saldo sebelum penyesuaian
        coa_data = supabase.table("coa").select("*").execute()
        coa_list = coa_data.data if coa_data.data else []

        jurnal_data = supabase.table("jurnal").select("*").execute()
        jurnal_list = jurnal_data.data if jurnal_data.data else []

        # Hitung neraca saldo sebelum penyesuaian
        saldo_akun = {}
        for akun in coa_list:
            kode_akun = akun["kode_akun"]
            saldo_akun[kode_akun] = {
                "kode_akun": kode_akun,
                "nama_akun": akun["nama_akun"],
                "tipe_akun": akun["tipe_akun"],
                "saldo_debit": 0,
                "saldo_kredit": 0,
                "saldo_debit_nssp": 0,
                "saldo_kredit_nssp": 0
            }

        # Proses transaksi jurnal umum
        for jurnal in jurnal_list:
            akun_debit_full = jurnal["akun_debit"]
            akun_kredit_full = jurnal["akun_kredit"]
            
            kode_debit = akun_debit_full.split('(')[-1].replace(')', '').strip() if '(' in akun_debit_full else ''
            kode_kredit = akun_kredit_full.split('(')[-1].replace(')', '').strip() if '(' in akun_kredit_full else ''
            
            jumlah = jurnal["jumlah"]

            if kode_debit and kode_debit in saldo_akun:
                saldo_akun[kode_debit]["saldo_debit"] += jumlah
                saldo_akun[kode_debit]["saldo_debit_nssp"] += jumlah

            if kode_kredit and kode_kredit in saldo_akun:
                saldo_akun[kode_kredit]["saldo_kredit"] += jumlah
                saldo_akun[kode_kredit]["saldo_kredit_nssp"] += jumlah

        # Proses penyesuaian (dari jurnal penyesuaian)
        # Contoh penyesuaian - dalam implementasi nyata ambil dari database
        penyesuaian_data = [
            {"akun_debit": "511", "akun_kredit": "114", "jumlah": 500000},
            {"akun_debit": "512", "akun_kredit": "211", "jumlah": 3000000},
            {"akun_debit": "513", "akun_kredit": "113", "jumlah": 750000}
        ]

        for penyesuaian in penyesuaian_data:
            kode_debit = penyesuaian["akun_debit"]
            kode_kredit = penyesuaian["akun_kredit"]
            jumlah = penyesuaian["jumlah"]

            if kode_debit in saldo_akun:
                saldo_akun[kode_debit]["saldo_debit_nssp"] += jumlah

            if kode_kredit in saldo_akun:
                saldo_akun[kode_kredit]["saldo_kredit_nssp"] += jumlah

        # Konversi ke list untuk NSSP
        nssp_list = list(saldo_akun.values())
        
        # Hitung total untuk neraca saldo dan NSSP
        total_debit_neraca = sum(akun["saldo_debit"] for akun in nssp_list)
        total_kredit_neraca = sum(akun["saldo_kredit"] for akun in nssp_list)
        total_debit_nssp = sum(akun["saldo_debit_nssp"] for akun in nssp_list)
        total_kredit_nssp = sum(akun["saldo_kredit_nssp"] for akun in nssp_list)

        return render_template_string(
            nssp_html,
            nssp_data=nssp_list,
            total_debit_neraca=total_debit_neraca,
            total_kredit_neraca=total_kredit_neraca,
            total_debit_nssp=total_debit_nssp,
            total_kredit_nssp=total_kredit_nssp
        )

    except Exception as e:
        print("Error:", e)
        return render_template_string(nssp_html, nssp_data=None, total_debit_neraca=0, total_kredit_neraca=0, total_debit_nssp=0, total_kredit_nssp=0)

@app.route("/laporan_keuangan")
def laporan_keuangan():
    if "email" not in session:
        return redirect("/login")

    try:
        # Data contoh untuk laporan keuangan
        # Dalam implementasi nyata, data ini dihitung dari NSSP
        laporan_data = {
            "periode": datetime.datetime.now().strftime("%B %Y"),
            "pendapatan_usaha": 50000000,
            "pendapatan_penjualan": 50000000,
            "hpp": 25000000,
            "laba_kotor": 25000000,
            "total_beban": 8000000,
            "beban_operasional": [
                {"nama": "Beban Gaji", "jumlah": 3000000},
                {"nama": "Beban Penyusutan", "jumlah": 500000},
                {"nama": "Beban Perlengkapan", "jumlah": 750000},
                {"nama": "Beban Lain-lain", "jumlah": 3750000}
            ],
            "laba_bersih": 17000000,
            "modal_awal": 100000000,
            "prive": 5000000,
            "modal_akhir": 112000000,
            "neraca": {
                "aset": [
                    {"nama": "Kas", "saldo": 25000000},
                    {"nama": "Piutang Usaha", "saldo": 15000000},
                    {"nama": "Persediaan Udang", "saldo": 20000000},
                    {"nama": "Peralatan Tambak", "saldo": 80000000},
                    {"nama": "Akumulasi Penyusutan", "saldo": -500000}
                ],
                "total_aset": 139500000,
                "kewajiban": [
                    {"nama": "Utang Usaha", "saldo": 15000000},
                    {"nama": "Utang Gaji", "saldo": 3000000},
                    {"nama": "Utang Lain-lain", "saldo": 9500000}
                ],
                "total_kewajiban_modal": 139500000
            }
        }

        # Hitung total aset dan kewajiban
        laporan_data["neraca"]["total_aset"] = sum(aset["saldo"] for aset in laporan_data["neraca"]["aset"])
        laporan_data["neraca"]["total_kewajiban"] = sum(kewajiban["saldo"] for kewajiban in laporan_data["neraca"]["kewajiban"])
        laporan_data["neraca"]["total_kewajiban_modal"] = laporan_data["neraca"]["total_kewajiban"] + laporan_data["modal_akhir"]

        return render_template_string(laporan_keuangan_html, laporan_data=laporan_data)

    except Exception as e:
        print("Error:", e)
        return render_template_string(laporan_keuangan_html, laporan_data=None)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)