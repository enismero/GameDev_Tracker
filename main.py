import logging
import mysql.connector
from fastapi import FastAPI,HTTPException
from database import get_connection

app=FastAPI(title="GameDev Tracker")
logger=logging.getLogger(__name__)

@app.get("/")
def home():
    return{"message":"GameDev TRacker api çalışıyo."}

@app.get("/tasks") #/tasks adresine gelen GET isteğini karşılar.
def get_tasks():
    connection=None
    cursor=None

    try:
        connection=get_connection()
        cursor=connection.cursor(dictionary=True)

        cursor.execute("""
             SELECT
                tasks.task_id,
                tasks.title,
                tasks.description,
                tasks.status,
                tasks.priority,
                users.display_name AS assigned_person
            FROM tasks
            LEFT JOIN users
                ON tasks.assigned_to = users.user_id
            ORDER BY tasks.task_id
        """)

        tasks=cursor.fetchall()
        return tasks
    except mysql.connector.Error:
        logger.exception("görev okunurken database hatası oluştu")

        raise HTTPException(
            status_code=500,
            detail="görevler alınamadı"
        )
    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()