import sqlite3, os, secrets

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'subscribers.db')


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                token TEXT NOT NULL,
                active INTEGER DEFAULT 1,
                lang TEXT DEFAULT 'en',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        # migrate existing rows that lack the lang column
        try:
            conn.execute("ALTER TABLE subscribers ADD COLUMN lang TEXT DEFAULT 'en'")
        except Exception:
            pass


def add_subscriber(email, lang='en'):
    """Returns (True, token) on new subscribe or re-subscribe, (False, None) if already active."""
    token = secrets.token_urlsafe(32)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT active FROM subscribers WHERE email = ?", (email,)
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO subscribers (email, token, lang) VALUES (?, ?, ?)",
                (email, token, lang)
            )
            return True, token
        elif row['active'] == 0:
            conn.execute(
                "UPDATE subscribers SET active = 1, token = ?, lang = ? WHERE email = ?",
                (token, lang, email)
            )
            return True, token
        else:
            return False, None


def get_active_subscribers():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT email FROM subscribers WHERE active = 1"
        ).fetchall()
    return [row['email'] for row in rows]


def get_active_subscribers_with_tokens():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT email, token, lang FROM subscribers WHERE active = 1"
        ).fetchall()
    return [(row['email'], row['token'], row['lang'] or 'en') for row in rows]


def unsubscribe(token):
    with get_conn() as conn:
        conn.execute(
            "UPDATE subscribers SET active = 0 WHERE token = ?", (token,)
        )
