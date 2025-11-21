from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
import pymysql
from datetime import datetime
import os

# --- 1. Konfigurasi Aplikasi ---
# Jika Anda menggunakan file .env, pastikan library dotenv sudah terinstal
# pip install python-dotenv
# from dotenv import load_dotenv
# load_dotenv()

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- 2. Konfigurasi MySQL via Environment Variables ---
# Nilai-nilai ini diambil dari environment atau file .env (lihat file .env)
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DB = os.getenv("MYSQL_DB")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))

# Tambahan untuk Aiven: Path ke CA Certificate yang diunduh dari Aiven Console
MYSQL_CA_PATH = os.getenv("MYSQL_CA_PATH") 


def get_db_connection():
    """Membuka koneksi database baru, termasuk konfigurasi SSL untuk Aiven."""
    
    # Konfigurasi SSL (Wajib untuk Aiven)
    ssl_config = {}
    if MYSQL_CA_PATH and os.path.exists(MYSQL_CA_PATH):
        ssl_config = {'ca': MYSQL_CA_PATH}
    else:
        # Peringatan jika path CA tidak ditemukan, yang dapat menyebabkan koneksi gagal
        print("[WARNING] MYSQL_CA_PATH tidak ditemukan atau kosong. Koneksi mungkin gagal tanpa SSL.")
        
    try:
        return pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
            port=MYSQL_PORT,
            cursorclass=pymysql.cursors.DictCursor,
            # Menggunakan konfigurasi SSL yang sudah disiapkan
            ssl=ssl_config 
        )
    except Exception as e:
        print(f"[ERROR DB CONNECT] Gagal terhubung ke MySQL: {e}")
        # Penting: Jika koneksi gagal, Flask akan berhenti di sini.
        raise Exception("Database Connection Failed")


# --- 3. Endpoint Home (Tidak Berubah) ---
@app.route('/')
def home():
    return jsonify({"status": "Server running", "message": "Aplikasi IoT Logger berjalan"})


# --- 4. Endpoint menerima data IoT (Tidak Berubah) ---
@app.route('/api/data/suhu', methods=['POST'])
def receive_iot_data():
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
    except Exception as e:
        print(f"[ERROR DB] Gagal menyimpan data: {e}")
        return jsonify({"message": "Data diterima, namun gagal disimpan ke DB"}), 500

    return jsonify({"message": "Data diterima dan diproses"}), 200


# --- 5. Endpoint untuk mengambil data historis (Tidak Berubah) ---
@app.route('/api/data/historis', methods=['GET'])
def get_historical_data():
    data_historis_formatted = []
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "SELECT suhu, timestamp FROM suhu_log ORDER BY id DESC LIMIT 50"
            cursor.execute(sql)
            data_historis = cursor.fetchall()
        conn.close()

        for item in data_historis:
            ts = item['timestamp']
            if isinstance(ts, datetime):
                ts = ts.strftime('%H:%M:%S')
            data_historis_formatted.append({
                'suhu': item['suhu'],
                'timestamp': ts
            })
    except Exception as e:
        print(f"[ERROR DB] Gagal mengambil data historis: {e}")
        return jsonify([]), 500

    return jsonify(data_historis_formatted), 200


# --- 6. Menjalankan Server ---
if __name__ == '__main__':
    # Untuk local development, pastikan Anda install python-dotenv 
    # dan gunakan load_dotenv() di awal skrip.
    PORT = int(os.getenv("PORT", 5000))
    print(f"Server berjalan di port {PORT}...")
    socketio.run(app, host='0.0.0.0', port=PORT)
