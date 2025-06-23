
import sqlite3
import hashlib
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "db" / "database.db"

def connect():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = connect()
    with open(Path(__file__).resolve().parents[1] / "db" / "setup.sql", "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, email, password, role):
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
            (username, email, hash_password(password), role)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username, password):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT role FROM users WHERE username=? AND password=?", 
                (username, hash_password(password)))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None
