import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "user_data.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            created_at TEXT,
            last_accessed TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_skill_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            skill TEXT,
            chosen_in_session INTEGER,
            learned_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    """)
    conn.commit()
    conn.close()


def upsert_user(user_id: str):
    """Create user if new, update last_accessed if returning."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    c.execute("""
        INSERT INTO users (user_id, created_at, last_accessed)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET last_accessed = ?
    """, (user_id, now, now, now))
    conn.commit()
    conn.close()


def save_skills(user_id: str, skills: list[str], chosen: bool = True):
    """
    Save skills to user history.
    chosen=True  → user consciously typed these (used for level calc)
    chosen=False → LLM-generated neighbors (not used for level calc)
    Only saves if skill not already recorded for this user.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    for skill in skills:
        c.execute("""
            SELECT id FROM user_skill_history
            WHERE user_id = ? AND skill = ?
        """, (user_id, skill))
        if not c.fetchone():
            c.execute("""
                INSERT INTO user_skill_history (user_id, skill, chosen_in_session, learned_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, skill, 1 if chosen else 0, now))
    conn.commit()
    conn.close()


def get_user_skills(user_id: str) -> list[str]:
    """
    Return only consciously submitted skills (chosen_in_session=1).
    These are the only ones that count toward level calculation.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT skill FROM user_skill_history
        WHERE user_id = ? AND chosen_in_session = 1
        ORDER BY learned_at
    """, (user_id,))
    skills = [row[0] for row in c.fetchall()]
    conn.close()
    return skills


def get_all_user_data(user_id: str) -> dict:
    """Return full user profile + skill history for export."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, created_at, last_accessed FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    c.execute("""
        SELECT skill, chosen_in_session, learned_at
        FROM user_skill_history
        WHERE user_id = ?
        ORDER BY learned_at
    """, (user_id,))
    skills = [
        {"skill": r[0], "submitted_by_user": bool(r[1]), "learned_at": r[2]}
        for r in c.fetchall()
    ]
    conn.close()
    return {
        "user_id": user_id,
        "created_at": user[1] if user else None,
        "last_accessed": user[2] if user else None,
        "skills": skills
    }


def delete_user_data(user_id: str):
    """Wipe all data for a user. Neo4j graph is unaffected."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM user_skill_history WHERE user_id = ?", (user_id,))
    c.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
