from flask import Flask, request, jsonify
import mysql.connector
import os
from dotenv import load_dotenv

# Memuat variabel lingkungan (misalnya, DB_HOST, DB_NAME, dll.)
load_dotenv()

app = Flask(__name__)

# Konfigurasi koneksi database
db = None
try:
    db = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"), # Misalnya 'defaultdb'
        port=int(os.getenv("DB_PORT", 3306))
    )
    print("Database terhubung dengan sukses!")
except mysql.connector.Error as err:
    print(f"Error connecting to MySQL: {err}")
    # Jika koneksi gagal, db tetap None dan endpoint akan mengembalikan error 500

# 1. Endpoint untuk mengambil SEMUA data suhu dari tabel suhu_log
@app.route('/api/data/historis', methods=['GET'])
def get_historis_suhu():
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = db.cursor(dictionary=True) 
    
    # Mengambil semua data dari tabel suhu_log
    cursor.execute("SELECT * FROM suhu_log") 
    data = cursor.fetchall()
    cursor.close()
    
    return jsonify(data)

# 2. Endpoint untuk mengambil data suhu berdasarkan ID
@app.route('/api/data/historis/<int:id>', methods=['GET'])
def get_suhu_by_id(id):
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = db.cursor(dictionary=True)
    
    # Mengambil satu baris dari suhu_log berdasarkan kolom id
    cursor.execute("SELECT * FROM suhu_log WHERE id=%s", (id,))
    data = cursor.fetchone()
    cursor.close()
    
    # Tambahkan penanganan jika ID tidak ditemukan
    if data:
        return jsonify(data)
    else:
        return jsonify({"message": f"Data dengan ID {id} tidak ditemukan"}), 404

# Blok utama untuk menjalankan aplikasi Flask
if __name__ == "__main__":
    print("Aplikasi Flask sedang berjalan...")
    # Menjalankan aplikasi di port default 5000
    app.run(debug=True)
