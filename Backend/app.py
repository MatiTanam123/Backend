from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
import pymysql
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# MySQL via environment
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

@app.route('/api/data/suhu', methods=['POST'])
def receive_iot_data():
    if not request.is_json:
        return jsonify({"message": "Request harus JSON"}), 400
    data = request.get_json()
    if 'suhu' not in data:
        return jsonify({"message": "Data 'suhu' tidak ditemukan"}), 400

    suhu_value = data['suhu']
    current_time = datetime.now()
    socketio.emit('suhu_update', {'suhu': suhu_value, 'timestamp': current_time.strftime('%H:%M:%S')})

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO suhu_log (suhu, timestamp) VALUES (%s, %s)", (suhu_value, current_time))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ERROR DB] {e}")

    return jsonify({"message": "Data diterima dan diproses"}), 200

@app.route('/api/data/historis', methods=['GET'])
def get_historical_data():
    data_historis = []
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT suhu, timestamp FROM suhu_log ORDER BY id DESC LIMIT 50")
            data_historis = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"[ERROR DB] {e}")
        return jsonify([]), 500

    # Format timestamp
    for i in data_historis:
        if isinstance(i['timestamp'], datetime):
            i['timestamp'] = i['timestamp'].strftime('%H:%M:%S')
        else:
            i['timestamp'] = str(i['timestamp'])
    return jsonify(data_historis), 200

if __name__ == '__main__':
    PORT = int(os.getenv("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=PORT)
