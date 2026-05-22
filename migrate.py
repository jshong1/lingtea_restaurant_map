import sqlite3

def migrate():
    conn = sqlite3.connect('matzip.db')
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE restaurants ADD COLUMN address TEXT")
        cur.execute("ALTER TABLE restaurants ADD COLUMN lat REAL")
        cur.execute("ALTER TABLE restaurants ADD COLUMN lng REAL")
        print("Migration successful.")
    except Exception as e:
        print("Migration failed or already applied:", e)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
