import eventlet
eventlet.monkey_patch() # Wajib untuk SocketIO di production

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
import pymysql
import pymysql.cursors # Penting untuk DictCursor
from datetime import datetime
import os
import time # Diperlukan jika ingin menguji koneksi DB awal

# --- 1. Konfigurasi Aplikasi ---
app = Flask(__name__)
# CORS diizinkan untuk semua origin ("*")
CORS(app)
# SocketIO diatur menggunakan async_mode="eventlet"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet") 

# --- 2. Konfigurasi MySQL via Environment Variables ---
# Nilai-nilai ini HARUS diatur di panel Render (Environment Variables)
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DB = os.getenv("MYSQL_DB")
# Ambil port, default 3306 jika tidak diatur
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306)) 

# Fungsi untuk membuat koneksi database
def get_db_connection():
    """Mencoba membuat koneksi ke MySQL."""
    try:
        return pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
            port=MYSQL_PORT,
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        print(f"[ERROR DB] Gagal terhubung ke database: {e}")
        # Dalam production, lebih baik log error ini daripada hanya mencetaknya
        raise ConnectionError("Gagal terhubung ke database")


# --- 3. Endpoint Home (Cek Server Hidup) ---
@app.route('/')
def home():
    """Endpoint sederhana untuk memverifikasi server berjalan."""
    return jsonify({
        "status": "Server running",
        "message": "Akses API di /api/data/suhu (POST) atau /api/data/historis (GET)"
    })


# --- 4. Endpoint menerima data IoT (API Inbound) ---
@app.route('/api/data/suhu', methods=['POST'])
def receive_iot_data():
    """Menerima data suhu dari perangkat IoT, menyimpannya, dan mengirim real-time."""
    if not request.is_json:
        return jsonify({"message": "Request harus dalam format JSON"}), 400

    data = request.get_json()
    if 'suhu' not in data:
        return jsonify({"message": "Data 'suhu' tidak ditemukan"}), 400

    suhu_value = data['suhu']
    current_time = datetime.now()

    # Kirim realtime ke frontend via SocketIO
    socketio.emit('suhu_update', {
        'suhu': suhu_value,
        'timestamp': current_time.strftime('%H:%M:%S')
    })

    # Simpan ke MySQL
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "INSERT INTO suhu_log (suhu, timestamp) VALUES (%s, %s)"
            cursor.execute(sql, (suhu_value, current_time))
        conn.commit()
        conn.close()
    except ConnectionError:
        return jsonify({"message": "Server tidak terhubung ke Database"}), 500
    except Exception as e:
        print(f"[ERROR DB] Gagal menyimpan data: {e}")
        return jsonify({"message": "Gagal menyimpan data ke database"}), 500

    return jsonify({"message": "Data diterima dan diproses"}), 200


# --- 5. Endpoint untuk mengambil data historis (API Outbound) ---
@app.route('/api/data/historis', methods=['GET'])
def get_historical_data():
    """Mengambil 50 data suhu historis terbaru dari database."""
    data_historis_formatted = []
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Mengambil 50 data terbaru
            sql = "SELECT suhu, timestamp FROM suhu_log ORDER BY id DESC LIMIT 50"
            cursor.execute(sql)
            data_historis = cursor.fetchall()
        conn.close()

        for item in data_historis:
            ts = item['timestamp']
            if isinstance(ts, datetime):
                # Format timestamp jika berupa objek datetime
                ts = ts.strftime('%Y-%m-%d %H:%M:%S') 
            
            data_historis_formatted.append({
                'suhu': item['suhu'],
                'timestamp': ts
            })
            
    except ConnectionError:
        return jsonify({"message": "Server tidak terhubung ke Database"}), 500
    except Exception as e:
        print(f"[ERROR DB] Gagal mengambil data: {e}")
        return jsonify({"message": "Gagal mengambil data historis"}), 500

    return jsonify(data_historis_formatted), 200


# --- 6. Menjalankan Server ---
if __name__ == '__main__':
    # Render akan menyediakan variabel PORT, jika tidak ada, default ke 5000 (untuk lokal)
    PORT = int(os.getenv("PORT", 5000)) 
    print(f"Server Backend berjalan di port {PORT}")
    # Menjalankan SocketIO dengan eventlet
    socketio.run(app, host='0.0.0.0', port=PORT, debug=True)
