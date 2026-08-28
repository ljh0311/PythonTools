import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parent.parent / "data" / "dashboard.db"
c = sqlite3.connect(db)
print("tables:", [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()])
for t in ("topics", "message_topics"):
    try:
        n = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"{t}: {n}")
        if n:
            print(c.execute(f"SELECT * FROM {t} LIMIT 8").fetchall())
    except Exception as e:
        print(t, "err", e)
print("topic_mode:", c.execute("SELECT value FROM settings WHERE key='topic_mode'").fetchone())
