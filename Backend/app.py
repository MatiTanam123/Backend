

# from flask import Flask, request, jsonify
# from flask_cors import CORS
# from flask_socketio import SocketIO
# import pymysql
# from datetime import datetime
# import json
# import os

# # --- 1. Konfigurasi Aplikasi dan Koneksi ---
# app = Flask(__name__)
# CORS(app)
# socketio = SocketIO(app, cors_allowed_origins="*") # Izinkan koneksi dari semua domain untuk kemudahan testing

# # --- Konfigurasi MySQL ---
# # GANTI DENGAN KREDENSIAL DAN NAMA DATABASE ANDA
# # MYSQL_HOST = 'localhost'
# # MYSQL_USER = 'root'
# # MYSQL_PASSWORD = '12345678' 
# # MYSQL_DB = 'iot_db' 
# MYSQL_HOST = os.getenv("MYSQL_HOST")
# MYSQL_USER = os.getenv("MYSQL_USER")
# MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
# MYSQL_DB = os.getenv("MYSQL_DB")
# MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))

# def get_db_connection():
#     """Membuat dan mengembalikan objek koneksi PyMySQL."""
#     return pymysql.connect(
#         host=MYSQL_HOST,
#         user=MYSQL_USER,
#         password=MYSQL_PASSWORD,
#         database=MYSQL_DB,
#         cursorclass=pymysql.cursors.DictCursor # Mengembalikan data sebagai dictionary
#     )
    
# @app.route('/')
# def home():
#     # Ini hanya untuk menghindari 'Not Found' di browser
#     return jsonify({"status": "Server running", "message": "Access API at /api/data/..."})

# # --- 2. Endpoint untuk Menerima Data dari IoT ---
# @app.route('/api/data/suhu', methods=['POST'])
# def receive_iot_data():
    
#     # Memastikan request body adalah JSON
#     if not request.is_json:
#         return jsonify({"message": "Permintaan harus dalam format JSON"}), 400

#     data = request.get_json()
    
#     # Validasi data yang diterima
#     if 'suhu' not in data:
#         return jsonify({"message": "Data 'suhu' tidak ditemukan"}), 400

#     suhu_value = data['suhu']
#     current_time = datetime.now()
    
#     # ----------------------------------------------------
#     # JALUR A: REAL-TIME KE WEBSITE (Via Socket.IO)
#     # ----------------------------------------------------
#     # Data dikirim ke semua klien web yang terhubung
#     data_to_send = {
#         'suhu': suhu_value,
#         # ❗ PERUBAHAN 1: Kirim string waktu H:M:S mentah untuk menghindari Timezone shift di browser ❗
#         'timestamp': current_time.strftime('%H:%M:%S') 
#     }
    
#     # Kirim event 'suhu_update' ke semua klien web
#     socketio.emit('suhu_update', data_to_send)
#     print(f"[SocketIO] Data suhu {suhu_value} dikirim ke klien.")

#     # ----------------------------------------------------
#     # JALUR B: PENYIMPANAN DATA KE MYSQL (Historis)
#     # ----------------------------------------------------
    
#     try:
#         conn = get_db_connection()
#         with conn.cursor() as cursor:
#             # Tetap simpan waktu penuh ke database
#             sql = "INSERT INTO suhu_log (suhu, timestamp) VALUES (%s, %s)"
#             cursor.execute(sql, (suhu_value, current_time))
#         conn.commit()
#         conn.close()
#         print(f"[MySQL] Data suhu {suhu_value} berhasil disimpan.")
        
#     except Exception as e:
#         print(f"[ERROR DB] Gagal menyimpan data: {e}")
#         # Tetap berikan respons berhasil agar IoT tidak mencoba mengirim ulang
    
#     return jsonify({"message": "Data diterima dan diproses"}), 200

# # --- 3. Endpoint untuk Mengambil Data Historis (Saat Website Dimuat) ---
# @app.route('/api/data/historis', methods=['GET'])
# def get_historical_data():
    
#     data_historis_formatted = []
#     try:
#         conn = get_db_connection()
#         with conn.cursor() as cursor:
#             # Ambil 50 data terbaru
#             sql = "SELECT suhu, timestamp FROM suhu_log ORDER BY id DESC LIMIT 50"
#             cursor.execute(sql)
#             data_historis = cursor.fetchall()
            
#         conn.close()
        
#         # ❗ PERUBAHAN 2: Format ulang data historis sebelum dikirim ke frontend ❗
#         for item in data_historis:
#             # Pastikan item['timestamp'] adalah objek datetime dari MySQL
#             if isinstance(item['timestamp'], datetime):
#                 # Format ke string HH:MM:SS
#                 formatted_time = item['timestamp'].strftime('%H:%M:%S')
#             else:
#                 formatted_time = str(item['timestamp'])

#             data_historis_formatted.append({
#                 'suhu': item['suhu'],
#                 'timestamp': formatted_time # Kirim waktu yang sudah diformat
#             })
        
#     except Exception as e:
#         print(f"[ERROR DB] Gagal mengambil data historis: {e}")
#         return jsonify([]), 500

#     # Mengembalikan data historis yang sudah diformat
#     return jsonify(data_historis_formatted), 200


# # --- 4. Menjalankan Server ---
# if __name__ == '__main__':
#     # Pastikan host='0.0.0.0' agar ESP8266 dapat terhubung
#     print("Server Flask dan SocketIO berjalan di http://0.0.0.0:5000")
#     socketio.run(app, host='0.0.0.0', port=5000, debug=True)    
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
import pymysql
from datetime import datetime
import os
import eventlet

eventlet.monkey_patch()

# --- 1. Konfigurasi Aplikasi dan Koneksi ---
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# --- Konfigurasi MySQL dari Environment Railway ---
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DB = os.getenv("MYSQL_DB")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))


def get_db_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        port=MYSQL_PORT,
        cursorclass=pymysql.cursors.DictCursor
    )


@app.route('/')
def home():
    return jsonify({"status": "Server running", "message": "Access API at /api/data/..."})


# --- 2. Endpoint untuk menerima data IoT ---
@app.route('/api/data/suhu', methods=['POST'])
def receive_iot_data():

    if not request.is_json:
        return jsonify({"message": "Permintaan harus dalam format JSON"}), 400

    data = request.get_json()

    if 'suhu' not in data:
        return jsonify({"message": "Data 'suhu' tidak ditemukan"}), 400

    suhu_value = data['suhu']
    current_time = datetime.now()

    # kirim realtime
    data_to_send = {
        'suhu': suhu_value,
        'timestamp': current_time.strftime('%H:%M:%S')
    }

    socketio.emit('suhu_update', data_to_send)

    # simpan database
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "INSERT INTO suhu_log (suhu, timestamp) VALUES (%s, %s)"
            cursor.execute(sql, (suhu_value, current_time))
        conn.commit()
        conn.close()

    except Exception as e:
        print(f"[ERROR DB] {e}")

    return jsonify({"message": "Data diterima dan diproses"}), 200


# --- 3. Endpoint data historis ---
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
            time = item['timestamp'].strftime('%H:%M:%S')
            data_historis_formatted.append({
                'suhu': item['suhu'],
                'timestamp': time
            })

    except Exception as e:
        print(f"[ERROR DB] {e}")
        return jsonify([]), 500

    return jsonify(data_historis_formatted), 200


# --- 4. Menjalankan Server ---
if __name__ == '__main__':
    PORT = int(os.getenv("PORT", 5000))
    print(f"Server jalan di port {PORT}")
    socketio.run(app, host='0.0.0.0', port=PORT)
