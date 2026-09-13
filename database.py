import sqlite3
import os
from typing import List, Dict, Any, Optional

DB_DIR = "/Users/stefanoraspa/.gemini/antigravity/scratch/associazioni_aggregator/data"
DB_PATH = os.path.join(DB_DIR, "database.db")

def get_connection() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabella Comunicati (Post Facebook)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        association TEXT NOT NULL,
        author TEXT,
        content TEXT NOT NULL,
        date_str TEXT,
        permalink TEXT UNIQUE NOT NULL,
        reactions_count TEXT,
        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Tabella Eventi Facebook
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        association TEXT NOT NULL,
        title TEXT NOT NULL,
        date_str TEXT,
        location TEXT,
        status TEXT,
        participants TEXT,
        permalink TEXT UNIQUE NOT NULL,
        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Tabella Log di Sincronizzazione
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sync_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT,
        posts_count INTEGER,
        events_count INTEGER,
        message TEXT
    )
    """)
    
    conn.commit()
    conn.close()
    print(f"[DB] Database inizializzato correttamente in {DB_PATH}")

def upsert_post(post: Dict[str, Any]) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO posts (association, author, content, date_str, permalink, reactions_count)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(permalink) DO UPDATE SET
            content = excluded.content,
            date_str = excluded.date_str,
            reactions_count = excluded.reactions_count,
            scraped_at = CURRENT_TIMESTAMP
        """, (
            post.get("association"),
            post.get("author"),
            post.get("content"),
            post.get("date_str"),
            post.get("permalink"),
            post.get("reactions_count")
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB Error] Inserimento post fallito: {e}")
        return False
    finally:
        conn.close()

def upsert_event(event: Dict[str, Any]) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO events (association, title, date_str, location, status, participants, permalink)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(permalink) DO UPDATE SET
            title = excluded.title,
            date_str = excluded.date_str,
            location = excluded.location,
            status = excluded.status,
            participants = excluded.participants,
            scraped_at = CURRENT_TIMESTAMP
        """, (
            event.get("association"),
            event.get("title"),
            event.get("date_str"),
            event.get("location"),
            event.get("status"),
            event.get("participants"),
            event.get("permalink")
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB Error] Inserimento evento fallito: {e}")
        return False
    finally:
        conn.close()

def get_posts(association: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM posts WHERE 1=1"
    params = []
    
    if association and association != "Tutte":
        query += " AND association LIKE ?"
        params.append(f"%{association}%")
        
    if search:
        query += " AND (content LIKE ? OR author LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
        
    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_events(association: Optional[str] = None, status: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM events WHERE 1=1"
    params = []
    
    if association and association != "Tutte":
        query += " AND association LIKE ?"
        params.append(f"%{association}%")
        
    if status and status != "Tutti":
        query += " AND status = ?"
        params.append(status)
        
    if search:
        query += " AND (title LIKE ? OR location LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
        
    query += " ORDER BY CASE WHEN status = 'In programma' THEN 0 ELSE 1 END, id DESC"
    cursor.execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_stats() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as c FROM posts")
    total_posts = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) as c FROM events")
    total_events = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) as c FROM events WHERE status = 'In programma'")
    upcoming_events = cursor.fetchone()["c"]
    cursor.execute("SELECT timestamp, status, posts_count, events_count FROM sync_logs ORDER BY id DESC LIMIT 1")
    last_sync_row = cursor.fetchone()
    last_sync = dict(last_sync_row) if last_sync_row else None
    conn.close()
    return {
        "total_posts": total_posts,
        "total_events": total_events,
        "upcoming_events": upcoming_events,
        "last_sync": last_sync
    }

def log_sync(status: str, posts_count: int, events_count: int, message: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO sync_logs (status, posts_count, events_count, message)
    VALUES (?, ?, ?, ?)
    """, (status, posts_count, events_count, message))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
