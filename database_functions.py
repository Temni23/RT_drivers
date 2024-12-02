"""
Функции для работы с базой данных.
"""
import os
import sqlite3
import time


def init_db(database_folder: str, database_name: str) -> str:
    """
    Инициализирует базу данных.

    Args:
        database_folder (str): Путь к папке, где будет размещена база данных.
        database_name (str): Имя файла базы данных.

    Returns:
        str: Полный путь к базе данных.
    """
    try:
        # Создаём папку для базы данных, если её нет
        os.makedirs(database_folder, exist_ok=True)

        # Формируем полный путь к базе данных
        db_path = os.path.join(database_folder, database_name)

        # Подключаемся к базе и создаём таблицы
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Создание таблицы пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                full_name TEXT,
                phone_number TEXT,
                username TEXT
            )
        ''')

        # Создание таблицы администраторов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY,
                user_id INTEGER
            )
        ''')

        # Создание таблицы отчетов КГМ
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS driver_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER,
                full_name TEXT,
                phone_number TEXT,
                username TEXT,
                user_id INTEGER,
                zone TEXT,
                latitude REAL,
                longitude REAL,
                reason TEXT,
                gos_number TEXT,
                photo_name TEXT,
                full_address TEXT,
                city TEXT,
                county TEXT,
                district TEXT,
                suburb TEXT,
                street TEXT,
                house_number TEXT
            )
        ''')

        # Создание таблицы заблокированных пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ban_list (
                id INTEGER PRIMARY KEY,
                user_id INTEGER
            )
        ''')

        # Сохраняем изменения и закрываем соединение
        conn.commit()
        conn.close()
        return db_path

    except Exception as e:
        print(f"Ошибка при инициализации базы данных: {e}")
        raise


def is_user_registered(db_path: str, user_id: int):
    """
    Проверка пользователя на наличие в базе данных.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def is_admin(db_path: str, user_id: int):
    """
    Проверка пользователя на наличие в базе данных.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM admins WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def is_user_banned(db_path: str, user_id: int):
    """
    Проверка пользователя на наличие в базе данных.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM ban_list WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def register_user(db_path: str, user_id: int, full_name: str,
                  phone_number: str, username: str):
    """
    Сохранение пользователя в базе данных.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (id, full_name, phone_number, username) VALUES (?, ?, ?, ?)",
        (user_id, full_name, phone_number, username))
    conn.commit()
    conn.close()


def save_driver_report(db_path: str, report_data: list) -> bool:
    """
    Сохраняет информацию о заявке в базу данных.

    Args:
        db_path (str): Путь к базе данных SQLite.
        report_data (list): Список данных.

    Returns:
        bool: True, если данные успешно сохранены, иначе False.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        timestamp = int(time.time())  # Текущее время в формате UNIX
        report_data.insert(1, timestamp)
        # SQL-запрос для вставки данных
        cursor.execute('''
            INSERT INTO driver_reports (
                timestamp, full_name, phone_number, username, user_id, zone, latitude, 
                longitude, reason, gos_number, photo_name, full_address, city, 
                county, district, suburb, street, house_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', report_data[1:])

        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Ошибка при сохранении данных: {e}")
        return False

    finally:
        if conn:
            conn.close()


def get_user_by_id(user_id: int, db_path: str) -> dict:
    """
    Получает информацию о пользователе из базы данных по user_id.

    Args:
        user_id (int): Идентификатор пользователя.
        db_path (str): Путь к базе данных SQLite.

    Returns:
        dict: Словарь с информацией о пользователе. Если пользователь не найден, возвращается пустой словарь.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            'SELECT id, full_name, phone_number, username FROM users WHERE id = ?',
            (user_id,))
        row = cursor.fetchone()

        if row:
            user_data = {
                "full_name": row[1],
                "phone_number": row[2],
                "username": row[3],
            }
        else:
            user_data = {}  # Возвращаем пустой словарь, если пользователь не найден

    finally:
        conn.close()

    return user_data


def ban_user(db_path: str, user_id: int) -> bool:
    """
    Находит пользователя в таблице `users`, удаляет его и добавляет в таблицу `ban_list`.

    Args:
        db_path (str): Путь к базе данных SQLite.
        user_id (int): ID пользователя для бана.

    Returns:
        bool: True, если операция выполнена успешно, иначе False.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Проверяем, существует ли пользователь в таблице users
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            return False

        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        cursor.execute("INSERT INTO ban_list (user_id) VALUES (?)", (user_id,))

        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Ошибка при работе с базой данных: {e}")
        return False

    finally:
        if conn:
            conn.close()
