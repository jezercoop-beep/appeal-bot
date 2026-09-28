import datetime
import os
import sqlite3
import time

DB = os.path.join(os.path.dirname(__file__), "appeal.db")


def get():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init():
    con = get()
    con.execute("""CREATE TABLE IF NOT EXISTS users(
        tg_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
        kcal REAL DEFAULT 2000, protein REAL DEFAULT 150,
        fat REAL DEFAULT 70, carbs REAL DEFAULT 250)""")
    con.execute("""CREATE TABLE IF NOT EXISTS meals(
        id INTEGER PRIMARY KEY AUTOINCREMENT, tg_id INTEGER, date TEXT,
        dish TEXT, kcal REAL, protein REAL, fat REAL, carbs REAL, ts INTEGER)""")
    con.execute("""CREATE TABLE IF NOT EXISTS chats(
        id INTEGER PRIMARY KEY AUTOINCREMENT, tg_id INTEGER, role TEXT, text TEXT, ts INTEGER)""")
    con.commit()
    con.close()


def upsert_user(tg_id, username="", first_name=""):
    con = get()
    con.execute("INSERT OR IGNORE INTO users(tg_id,username,first_name) VALUES(?,?,?)",
                (tg_id, username, first_name))
    con.commit()
    con.close()


def get_user(tg_id):
    con = get()
    row = con.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,)).fetchone()
    con.close()
    return dict(row) if row else None


def set_goals(tg_id, kcal, protein, fat, carbs):
    con = get()
    con.execute("UPDATE users SET kcal=?,protein=?,fat=?,carbs=? WHERE tg_id=?",
                (kcal, protein, fat, carbs, tg_id))
    con.commit()
    con.close()


def add_meal(tg_id, dish, kcal, protein, fat, carbs):
    con = get()
    cur = con.execute(
        "INSERT INTO meals(tg_id,date,dish,kcal,protein,fat,carbs,ts) VALUES(?,?,?,?,?,?,?,?)",
        (tg_id, datetime.date.today().isoformat(), dish, kcal, protein, fat, carbs, int(time.time())))
    con.commit()
    mid = cur.lastrowid
    con.close()
    return mid


def del_meal(tg_id, meal_id):
    con = get()
    con.execute("DELETE FROM meals WHERE id=? AND tg_id=?", (meal_id, tg_id))
    con.commit()
    con.close()


def meals_on(tg_id, date_iso):
    con = get()
    rows = con.execute("SELECT * FROM meals WHERE tg_id=? AND date=? ORDER BY ts DESC",
                       (tg_id, date_iso)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def totals_on(tg_id, date_iso):
    t = {"kcal": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
    for m in meals_on(tg_id, date_iso):
        for k in t:
            t[k] += m[k]
    return t


def week(tg_id):
    """Итоги за последние 7 дней."""
    days = []
    for i in range(6, -1, -1):
        d = datetime.date.today() - datetime.timedelta(days=i)
        days.append({"date": d.isoformat(), "label": ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"][d.weekday()],
                     **totals_on(tg_id, d.isoformat())})
    return days


def add_chat(tg_id, role, text):
    con = get()
    con.execute("INSERT INTO chats(tg_id,role,text,ts) VALUES(?,?,?,?)",
                (tg_id, role, text, int(time.time())))
    con.commit()
    con.close()


def chat_history(tg_id, limit=16):
    con = get()
    rows = con.execute("SELECT role,text FROM chats WHERE tg_id=? ORDER BY ts DESC LIMIT ?",
                       (tg_id, limit)).fetchall()
    con.close()
    return [dict(r) for r in reversed(rows)]
