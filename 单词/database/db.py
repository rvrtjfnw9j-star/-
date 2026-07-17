"""
数据库层 - 使用 SQLite 实现本地持久化存储。
包含表结构定义、数据初始化以及词条和复习记录的 CRUD 操作。
"""

import math
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
import sqlite3


DB_DIR = Path(__file__).resolve().parent.parent
DB_PATH = DB_DIR / "vocab.db"


def get_connection() -> sqlite3.Connection:
  conn = sqlite3.connect(str(DB_PATH))
  conn.row_factory = sqlite3.Row
  conn.execute("PRAGMA journal_mode=WAL")
  conn.execute("PRAGMA foreign_keys=ON")
  return conn


def init_db():
  conn = get_connection()
  try:
    cursor = conn.cursor()
    cursor.execute("""
      CREATE TABLE IF NOT EXISTS words (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        word        TEXT    NOT NULL,
        definition  TEXT    NOT NULL,
        language    TEXT    NOT NULL DEFAULT 'en',
        pos         TEXT    DEFAULT '',
        notes       TEXT    DEFAULT '',
        kanji       TEXT    DEFAULT '',
        created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
        updated_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
      )
    """)
    cursor.execute("""
      CREATE TABLE IF NOT EXISTS fsrs_state (
        word_id     INTEGER PRIMARY KEY,
        stability   REAL    NOT NULL DEFAULT 2.5,
        difficulty  REAL    NOT NULL DEFAULT 5.0,
        due_date    TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
        last_review TEXT,
        reps        INTEGER NOT NULL DEFAULT 0,
        lapses      INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE
      )
    """)
    cursor.execute("""
      CREATE TABLE IF NOT EXISTS review_logs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        word_id     INTEGER NOT NULL,
        review_time TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
        rating      INTEGER NOT NULL,
        stability   REAL,
        difficulty  REAL,
        retrievability REAL,
        elapsed_days REAL,
        FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE
      )
    """)
    cursor.execute("""
      CREATE TABLE IF NOT EXISTS settings (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
      )
    """)
    cursor.execute("""
      CREATE TABLE IF NOT EXISTS wrong_words (
        word_id     INTEGER PRIMARY KEY,
        added_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
        wrong_count INTEGER NOT NULL DEFAULT 1,
        correct_streak INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE
      )
    """)
    conn.commit()
  finally:
    conn.close()


def add_word(word: str, definition: str, language: str = "en",
       pos: str = "", notes: str = "", kanji: str = "") -> int:
  conn = get_connection()
  try:
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
      INSERT INTO words (word, definition, language, pos, notes, kanji, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (word.strip(), definition.strip(), language, pos, notes, kanji, now, now))
    word_id = cursor.lastrowid
    cursor.execute("""
      INSERT INTO fsrs_state (word_id, due_date)
      VALUES (?, ?)
    """, (word_id, now))
    conn.commit()
    return word_id
  finally:
    conn.close()


def edit_word(word_id: int, word: str, definition: str, language: str = "en",
       pos: str = "", notes: str = "", kanji: str = "") -> bool:
  conn = get_connection()
  try:
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
      UPDATE words
      SET word=?, definition=?, language=?, pos=?, notes=?, kanji=?, updated_at=?
      WHERE id=?
    """, (word.strip(), definition.strip(), language, pos, notes, kanji, now, word_id))
    conn.commit()
    return cursor.rowcount > 0
  finally:
    conn.close()


def delete_word(word_id: int) -> bool:
  conn = get_connection()
  try:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM words WHERE id=?", (word_id,))
    conn.commit()
    return cursor.rowcount > 0
  finally:
    conn.close()


def batch_delete_words(word_ids: List[int]) -> int:
  if not word_ids:
    return 0
  conn = get_connection()
  try:
    cursor = conn.cursor()
    placeholders = ",".join("?" * len(word_ids))
    cursor.execute(f"DELETE FROM words WHERE id IN ({placeholders})", word_ids)
    conn.commit()
    return cursor.rowcount
  finally:
    conn.close()


def get_word(word_id: int) -> Optional[Dict[str, Any]]:
  conn = get_connection()
  try:
    cursor = conn.cursor()
    cursor.execute("""
      SELECT w.*, f.stability, f.difficulty, f.due_date,
             f.last_review, f.reps, f.lapses
      FROM words w
      LEFT JOIN fsrs_state f ON w.id = f.word_id
      WHERE w.id=?
    """, (word_id,))
    row = cursor.fetchone()
    return dict(row) if row else None
  finally:
    conn.close()


def get_all_words(page: int = 1, per_page: int = 50,
         language: str = "",
         search: str = "") -> Dict[str, Any]:
  conn = get_connection()
  try:
    cursor = conn.cursor()
    conditions = []
    params = []
    if language:
      conditions.append("w.language=?")
      params.append(language)
    if search:
      conditions.append("(w.word LIKE ? OR w.definition LIKE ?)")
      params.extend([f"%{search}%", f"%{search}%"])
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    cursor.execute(f"SELECT COUNT(*) FROM words w {where}", params)
    total = cursor.fetchone()[0]
    offset = (page - 1) * per_page
    cursor.execute(f"""
      SELECT w.*, f.stability, f.difficulty, f.due_date,
             f.last_review, f.reps, f.lapses
      FROM words w
      LEFT JOIN fsrs_state f ON w.id = f.word_id
      {where}
      ORDER BY w.updated_at DESC
      LIMIT ? OFFSET ?
    """, params + [per_page, offset])
    rows = [dict(r) for r in cursor.fetchall()]
    return {"total": total, "page": page, "per_page": per_page,
       "data": rows}
  finally:
    conn.close()


def get_all_words_flat() -> List[Dict[str, Any]]:
  conn = get_connection()
  try:
    cursor = conn.cursor()
    cursor.execute("""
      SELECT w.*, f.stability, f.difficulty, f.due_date,
             f.last_review, f.reps, f.lapses
      FROM words w
      LEFT JOIN fsrs_state f ON w.id = f.word_id
      ORDER BY w.created_at DESC
    """)
    return [dict(r) for r in cursor.fetchall()]
  finally:
    conn.close()


def batch_import_words(words_data: List[Dict[str, str]]) -> Dict[str, int]:
  succeeded = 0
  failed = 0
  for item in words_data:
    try:
      add_word(
        word=item.get("word", ""),
        definition=item.get("definition", ""),
        language=item.get("language", "en"),
        pos=item.get("pos", ""),
        notes=item.get("notes", ""),
        kanji=item.get("kanji", ""),
      )
      succeeded += 1
    except Exception:
      failed += 1
  return {"total": len(words_data), "succeeded": succeeded, "failed": failed}


def get_due_words(limit: int = 20) -> List[Dict[str, Any]]:
  conn = get_connection()
  try:
    cursor = conn.cursor()
    today = date.today().strftime("%Y-%m-%d")
    cursor.execute("""
      SELECT w.*, f.stability, f.difficulty, f.due_date,
             f.last_review, f.reps, f.lapses
      FROM words w
      JOIN fsrs_state f ON w.id = f.word_id
      WHERE f.due_date <= ?
      ORDER BY f.due_date ASC
      LIMIT ?
    """, (today + " 23:59:59", limit))
    return [dict(r) for r in cursor.fetchall()]
  finally:
    conn.close()


def get_new_words(limit: int = 20) -> List[Dict[str, Any]]:
  conn = get_connection()
  try:
    cursor = conn.cursor()
    cursor.execute("""
      SELECT w.*, f.stability, f.difficulty, f.due_date,
             f.last_review, f.reps, f.lapses
      FROM words w
      JOIN fsrs_state f ON w.id = f.word_id
      WHERE f.reps = 0
      ORDER BY w.created_at ASC
      LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]
  finally:
    conn.close()


def update_fsrs_state(word_id: int, stability: float, difficulty: float,
             interval_days: float, rating: int, reps: int = 0,
             lapses: int = 0):
  conn = get_connection()
  try:
    cursor = conn.cursor()
    now = datetime.now()
    due = now + timedelta(days=interval_days)
    cursor.execute("""
      UPDATE fsrs_state
      SET stability=?, difficulty=?, due_date=?,
        last_review=?, reps=?, lapses=?
      WHERE word_id=?
    """, (stability, difficulty, due.strftime("%Y-%m-%d %H:%M:%S"),
       now.strftime("%Y-%m-%d %H:%M:%S"), reps, lapses, word_id))
    conn.commit()
  finally:
    conn.close()


def log_review(word_id: int, rating: int, stability: float,
        difficulty: float, retrievability: float, elapsed_days: float):
  conn = get_connection()
  try:
    cursor = conn.cursor()
    cursor.execute("""
      INSERT INTO review_logs
        (word_id, review_time, rating, stability, difficulty,
         retrievability, elapsed_days)
      VALUES (?, datetime('now','localtime'), ?, ?, ?, ?, ?)
    """, (word_id, rating, stability, difficulty, retrievability,
       elapsed_days))
    conn.commit()
  finally:
    conn.close()


def get_stats():
  conn = get_connection()
  try:
    cursor = conn.cursor()
    today = date.today().strftime("%Y-%m-%d")
    total = cursor.execute("SELECT COUNT(*) FROM words").fetchone()[0]
    mastered = cursor.execute("""
      SELECT COUNT(*) FROM fsrs_state WHERE reps >= 3 AND stability >= 30
    """).fetchone()[0]
    today_new = cursor.execute("""
      SELECT COUNT(*) FROM review_logs
      WHERE review_time >= ? AND rating >= 3
        AND word_id IN (SELECT word_id FROM fsrs_state WHERE reps = 1)
    """, (today,)).fetchone()[0]
    today_review = cursor.execute("""
      SELECT COUNT(*) FROM review_logs WHERE review_time >= ?
    """, (today,)).fetchone()[0]
    due = cursor.execute("""
      SELECT COUNT(*) FROM fsrs_state
      WHERE due_date <= datetime('now','localtime')
    """).fetchone()[0]
    langs = cursor.execute("""
      SELECT language, COUNT(*) as count FROM words GROUP BY language
    """).fetchall()
    lang_counts = {r["language"]: r["count"] for r in langs}
    wrong_count = cursor.execute("""
      SELECT COUNT(*) FROM wrong_words
    """).fetchone()[0]
    return {
      "total": total, "mastered": mastered,
      "today_new": today_new, "today_review": today_review,
      "due_today": due, "languages": lang_counts,
      "wrong_count": wrong_count,
    }
  finally:
    conn.close()


def get_review_history(days: int = 30) -> List[Dict[str, Any]]:
  conn = get_connection()
  try:
    cursor = conn.cursor()
    cursor.execute("""
      SELECT date(r.review_time) as review_date,
             COUNT(*) as total,
             SUM(CASE WHEN r.rating >= 3 THEN 1 ELSE 0 END) as passed,
             AVG(r.retrievability) as avg_retrievability
      FROM review_logs r
      WHERE r.review_time >= datetime('now', ? || ' days', 'localtime')
      GROUP BY date(r.review_time)
      ORDER BY review_date DESC
    """, (f"-{days}",))
    return [dict(r) for r in cursor.fetchall()]
  finally:
    conn.close()


def get_setting(key: str, default: str = "") -> str:
  conn = get_connection()
  try:
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cursor.fetchone()
    return row["value"] if row else default
  finally:
    conn.close()


def set_setting(key: str, value: str):
  conn = get_connection()
  try:
    cursor = conn.cursor()
    cursor.execute("""
      INSERT INTO settings (key, value) VALUES (?, ?)
      ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (key, value))
    conn.commit()
  finally:
    conn.close()
