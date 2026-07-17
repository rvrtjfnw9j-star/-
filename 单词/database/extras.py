"""
错题本与增强统计模块。
"""

from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any

from .db import get_connection


def add_to_wrong_words(word_id: int) -> bool:
  conn = get_connection()
  try:
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existing = cursor.execute(
      "SELECT wrong_count FROM wrong_words WHERE word_id=?", (word_id,)
    ).fetchone()
    if existing:
      cursor.execute(
        "UPDATE wrong_words SET wrong_count=wrong_count+1, added_at=?, correct_streak=0 WHERE word_id=?",
        (now, word_id)
      )
      conn.commit()
      return False
    else:
      cursor.execute(
        "INSERT INTO wrong_words (word_id, added_at, wrong_count, correct_streak) VALUES (?, ?, 1, 0)",
        (word_id, now)
      )
      conn.commit()
      return True
  finally:
    conn.close()


def remove_from_wrong_words(word_id: int) -> bool:
  conn = get_connection()
  try:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM wrong_words WHERE word_id=?", (word_id,))
    conn.commit()
    return cursor.rowcount > 0
  finally:
    conn.close()


def update_wrong_word_streak(word_id: int, is_correct: bool) -> bool:
  conn = get_connection()
  try:
    cursor = conn.cursor()
    row = cursor.execute(
      "SELECT correct_streak FROM wrong_words WHERE word_id=?", (word_id,)
    ).fetchone()
    if not row:
      return False
    if is_correct:
      new_streak = row["correct_streak"] + 1
      if new_streak >= 3:
        cursor.execute("DELETE FROM wrong_words WHERE word_id=?", (word_id,))
        conn.commit()
        return True
      cursor.execute(
        "UPDATE wrong_words SET correct_streak=? WHERE word_id=?",
        (new_streak, word_id)
      )
    else:
      cursor.execute(
        "UPDATE wrong_words SET correct_streak=0 WHERE word_id=?",
        (word_id,)
      )
    conn.commit()
    return False
  finally:
    conn.close()


def get_wrong_words(limit: int = 20) -> List[Dict[str, Any]]:
  conn = get_connection()
  try:
    cursor = conn.cursor()
    cursor.execute("""
      SELECT w.*, f.stability, f.difficulty, f.due_date,
             f.last_review, f.reps, f.lapses,
             ww.wrong_count, ww.correct_streak, ww.added_at as wrong_added_at
      FROM wrong_words ww
      JOIN words w ON w.id = ww.word_id
      LEFT JOIN fsrs_state f ON w.id = f.word_id
      ORDER BY ww.added_at ASC
      LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]
  finally:
    conn.close()


def get_wrong_word_count() -> int:
  conn = get_connection()
  try:
    return conn.execute("SELECT COUNT(*) FROM wrong_words").fetchone()[0]
  finally:
    conn.close()


def get_random_words(limit: int = 20) -> List[Dict[str, Any]]:
  conn = get_connection()
  try:
    cursor = conn.cursor()
    cursor.execute("""
      SELECT w.*, f.stability, f.difficulty, f.due_date,
             f.last_review, f.reps, f.lapses
      FROM words w
      LEFT JOIN fsrs_state f ON w.id = f.word_id
      ORDER BY RANDOM()
      LIMIT ?
    """, (limit,))
    return [dict(r) for r in cursor.fetchall()]
  finally:
    conn.close()


def get_forgetting_curve_data(days: int = 30) -> List[Dict[str, Any]]:
  conn = get_connection()
  try:
    cursor = conn.cursor()
    cursor.execute("""
      SELECT
        date(r.review_time) as review_date,
        AVG(CASE WHEN r.rating >= 3 THEN 1.0 ELSE 0.0 END) as retention_rate,
        COUNT(*) as total_reviews,
        AVG(r.retrievability) as avg_retrievability,
        AVG(CASE WHEN r.rating >= 3 THEN r.elapsed_days END) as avg_interval
      FROM review_logs r
      WHERE r.review_time >= datetime('now', ? || ' days', 'localtime')
      GROUP BY date(r.review_time)
      ORDER BY review_date ASC
    """, (f"-{days}",))
    return [dict(r) for r in cursor.fetchall()]
  finally:
    conn.close()


def get_review_pressure_data() -> List[Dict[str, Any]]:
  conn = get_connection()
  try:
    cursor = conn.cursor()
    result = []
    for day_offset in range(30):
      day = date.today() + timedelta(days=day_offset)
      day_str = day.strftime("%Y-%m-%d")
      count = cursor.execute("""
        SELECT COUNT(*) FROM fsrs_state
        WHERE due_date >= ? AND due_date < datetime(?, '+1 day')
      """, (day_str, day_str)).fetchone()[0]
      result.append({"date": day_str, "due_count": count})
    return result
  finally:
    conn.close()


def get_memory_durability_data() -> List[Dict[str, Any]]:
  conn = get_connection()
  try:
    cursor = conn.cursor()
    buckets = [
      (0, 1, "\u4e00\u5929\u4ee5\u5185"),
      (1, 7, "1-7\u5929"),
      (7, 30, "1\u5468-1\u6708"),
      (30, 90, "1\u6708-3\u6708"),
      (90, 365, "3\u6708-1\u5e74"),
      (365, 99999, "1\u5e74\u4ee5\u4e0a"),
    ]
    data = []
    for lo, hi, label in buckets:
      count = cursor.execute("""
        SELECT COUNT(*) FROM fsrs_state WHERE stability >= ? AND stability < ?
      """, (lo, hi)).fetchone()[0]
      data.append({"label": label, "count": count, "range": f"{lo}-{hi}"})
    return data
  finally:
    conn.close()
