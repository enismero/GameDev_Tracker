import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
#bu dosyayla aynı klasördeki .env dosyasını oku
env_path= Path(__file__).resolve().parent/".env"
load_dotenv(env_path,interpolate=False)
#yeni mysql bağlantısı açılır
#os.environ yüklenen ayarları okur
def get_connection():
    return mysql.connector.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        connection_timeout=5
    )