import getpass
import mysql.connector

password=getpass.getpass("MySQL parolan: ")
connection =None

try:
    connection= mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",
        password=password,
        database="gamedev_tracker"
        )

    print("bağlantı başarılı")
    #Sonuçları sütun adlarıyla erişilebilen sözlükler olarak getirir.
    cursor=connection.cursor(dictionary=True)

    try: #sql sorgusunu çalıştırır
        cursor.execute("""
            SELECT
                tasks.task_id,
                tasks.title,
                tasks.status,
                users.display_name AS assigned_person
            FROM tasks
            LEFT JOIN users ON tasks.assigned_to=users.user_id
            ORDER BY tasks.task_id
        """)

        tasks=cursor.fetchall() #sorguda dönen tüm satırları alır

        if not tasks:
            print("henüz görev yok.")
        for task in tasks:
            print(
                f"#{task['task_id']} | "
                f"{task['title']} | "
                f"{task['status']} | "
                f"Sorumlu: {task['assigned_person'] or 'Atanmamış'}"
            )
    finally:
        cursor.close()
except mysql.connector.Error as e:
    print(f"MySQL hatası: {e}")
finally:
    if connection is not None and connection.is_connected():
        connection.close()
        print("bağlantı kapatıldı.")

        