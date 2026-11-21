import logging
import mysql.connector
from fastapi import FastAPI,HTTPException,Request,Response
from database import get_connection
from typing import Literal
from pydantic import BaseModel, Field, SecretStr

from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from auth import hash_password,verify_password,hash_token
import secrets


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

class UserCreate(BaseModel):
    username:str=Field(
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$"
    )
    display_name:str=Field(
        min_length=3,
        max_length=100
    )
    password:SecretStr=Field(
        min_length=8,
        max_length=128
    )

class UserLogin(BaseModel):
    user_id:int=Field(gt=0)
    password: SecretStr=Field(min_length=3,max_length=128)

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

#kullanıcı listeleme-------------------------
@app.get("/users")
def get_users():
    connection=None
    cursor=None

    try:
        connection=get_connection()
        cursor=connection.cursor(dictionary=True)

        cursor.execute("""
        select user_id,display_name 
        from users 
        order by display_name,user_id
        """)
        return cursor.fetchall()
    except mysql.connector.Error as e:
        logger.exception("kullanıcıları alırken hata oldu")
        raise HTTPException(status_code=500,detail="kullanıcılar alınamadı") from e
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()

#user kayıt--------------------------------
@app.post("/auth/register",status_code=201)
def register_user(user:UserCreate):
    username=user.username.lower()
    display_name=user.display_name.strip()

    if not display_name:
        raise HTTPException(status_code=422,detail="display name boş olamaz")
    password_hash=hash_password(user.password.get_secret_value())

    connection=None
    cursor=None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            insert into users(username,display_name,password_hash)
            values(%s,%s,%s)""",(username,display_name,password_hash))

        user_id = cursor.lastrowid
        connection.commit()

        return {
            "message": "Kullanıcı oluşturuldu.",
            "user_id": user_id,
            "display_name": display_name
        }
    except mysql.connector.Error as e:
        if connection is not None:
            connection.rollback()
        if e.errno==1062: #benzersizlik kuralı ihlali hatası
            raise HTTPException(status_code=409,detail="bu kullanıcı adı zaten mevcut") from e
        logger.exception("kullanıcı oluştururken hata oluştu")

        raise HTTPException(status_code=500,detail="kullanıcı oluşturulamadı") from e
    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()

#login ------------------------
@app.post("/auth/login")
def login_user(
    data:UserLogin,
    request: Request,
    response: Response
):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        #kullanıcı idsi ile 
        cursor.execute("""
            SELECT user_id, username, display_name, password_hash
            FROM users
            WHERE user_id = %s
        """, (data.user_id,))

        user = cursor.fetchone()

        if user is None:
            raise HTTPException(
                status_code=401,
                detail="ID veya şifre hatalı."
            )
        
        #şifreyi hash ile karşılaştır
        password_correct=verify_password(
            data.password.get_secret_value(),
            user["password_hash"]
        )

        if not password_correct:
            raise HTTPException(
                status_code=401,
                detail="ID veya şifre hatalı."
            )

        #tarayıcıdaki önceki oturumu kaldır
        old_token=request.cookies.get("tracker_session")

        if old_token:
            cursor.execute("""
                DELETE FROM user_sessions
                WHERE token_hash = %s
            """, (hash_token(old_token),))

        #düresi dolmuş oturumu temizle
        cursor.execute("""
            DELETE FROM user_sessions
            WHERE expires_at <= UTC_TIMESTAMP()
        """)

        #yeni oturum anahtarı oluştur
        token=secrets.token_urlsafe(32)

        cursor.execute("""
            INSERT INTO user_sessions (
                token_hash,
                user_id,
                expires_at
            )
            VALUES (
                %s,
                %s,
                DATE_ADD(UTC_TIMESTAMP(), INTERVAL 1 DAY)
            )
        """, (
            hash_token(token),
            user["user_id"]
        ))

        connection.commit()

        #oturum anahtarını tarayıcıya çerez olarak gönder
        response.set_cookie(
            key="tracker_session",
            value=token,
            httponly=True,
            samesite="strict",
            secure=False,
            max_age=86400,
            path="/"
        )
        response.headers["Cache-Control"] = "no-store"

        return {
            "message": "Giriş başarılı.",
            "user_id": user["user_id"],
            "display_name": user["display_name"]
        }

    except mysql.connector.Error as error:
            if connection is not None:
                connection.rollback()

            logger.exception("Giriş sırasında veritabanı hatası oluştu.")

            raise HTTPException(
                status_code=500,
                detail="Giriş işlemi tamamlanamadı."
            ) from error

    finally:
            if cursor is not None:
                cursor.close()

            if connection is not None and connection.is_connected():
                connection.close()