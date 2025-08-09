import sqlite3
import os

DB_PATH = os.path.join('database', 'game.db')

os.makedirs('database', exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute('''
CREATE TABLE IF NOT EXISTS rooms (
    id TEXT PRIMARY KEY,
    rounds INTEGER DEFAULT 5
)
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    room_id TEXT,
    score INTEGER DEFAULT 0
)
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS captions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id TEXT,
    round INTEGER,
    username TEXT,
    caption TEXT
)
''')

conn.commit()
conn.close()
print('Database initialized at', DB_PATH)
