import logging
import mysql.connector
from fastapi import FastAPI,HTTPException
from database import get_connection
from typing import Literal
from pydantic import BaseModel, Field

from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app=FastAPI(title="GameDev Tracker")

BASE_DIR=Path(__file__).resolve().parent #main.py dosyasının bulunduğu klasörü büldü
#.parent dosya adını çıkartıp path verir C:\Development\All Project\GameDev_Tracker

app.mount(
    "/static", #taracıcıdaki url başlangıcı
    StaticFiles(directory=BASE_DIR/"static"),
    name="static" #isteklerin karşılanacağı klasör
    #C:\Development\All Project\GameDev_Tracker\static\index.html
)

logger=logging.getLogger(__name__)

#yeni oluşturmak için
class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    description: str | None = None
    priority: Literal["low", "medium", "high"] = "medium"
    created_by: int = Field(gt=0)
    assigned_to: int | None = Field(default=None, gt=0)

#task aşaçasını güncellemek için
class TaskStatusUpdate(BaseModel):
    status:Literal["todo","in_progress","testing","done"]

@app.get("/")
def home():
    return FileResponse(BASE_DIR/"static"/"index.html")

#“Yanıt olarak belirtilen dosyanın içeriğini gönder.”
#Tarayıcı HTML dosyasını alınca içindeki başlıkları, formu ve düğmeleri ekrana çizer.

#/tasks adresine gelen GET isteğini karşılar. --------------------
@app.get("/tasks") 
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
#görev ekle --------------------------------------------------------
@app.post("/tasks",status_code=201) 
def create_task(task: TaskCreate):
    title=task.title.strip()

    if not title:
        raise HTTPException(status_code=422,detail="görev başlığı eklenmeli.")
    connection =None
    cursor=None

    try:
        connection=get_connection()
        cursor=connection.cursor()

        cursor.execute("""INSERT INTO tasks (
                title,
                description,
                priority,
                created_by,
                assigned_to
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (
            title,
            task.description,
            task.priority,
            task.created_by,
            task.assigned_to
        )
        )

        task_id=cursor.lastrowid
        connection.commit()

        return{
            "message":"görev oluştu",
            "task_id": task_id
        }
    except mysql.connector.Error as e:
        if connection is not None:
            connection.rollback()     

        if e.errno == 1452:
            raise HTTPException(
                status_code=400,
                detail="Oluşturan veya sorumlu kullanıcı bulunamadı."
            ) from e
        
        logger.exception("Görev eklenirken veritabanı hatası oluştu.")

        raise HTTPException(
            status_code=500,
            detail="görev oluşturulmadı"
                    ) from e
    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
#task aşamasını güncelleme --------------------------------------
@app.patch("/tasks/{task_id}/status")
def update_task_status(task_id:int,task:TaskStatusUpdate):
    connection=None
    cursor=None
    try:
        connection=get_connection()
        cursor=connection.cursor(dictionary=True)
        #görevi bulişlem bitene kadar kilitle
        cursor.execute(
            "select task_id from tasks where task_id = %s for update",(task_id,)
        )
        existing_task=cursor.fetchone()

        if existing_task is None:
            raise HTTPException(status_code=404,detail="görev bulunamadı.")

        cursor.execute("""update tasks 
            set status =%s
            where task_id = %s"""
            ,(task.status,task_id))
        
        connection.commit()

        return{
            "message":"görev durumu güncellendi.",
            "task_id":task_id,
            "status":task.status
        }
    except mysql.connector.Error as e:
        if connection is not None:
            connection.rollback()
        logger.exception("görev durumu güncellenirken hata oluştu.")

        raise HTTPException(status_code=500,
            detail="görev durumu güncellenemedi.")from e
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
            