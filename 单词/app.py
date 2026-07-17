"""
操作台 - Flask 后端应用
提供 RESTful API 接口，支持词库管理、学习复习、统计分析以及批量删除。
"""

import math
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from datetime import date
from flask import Flask, request, jsonify, render_template

from database.db import (
  add_word, edit_word, delete_word, batch_delete_words,
  get_word, get_all_words, get_all_words_flat, batch_import_words,
  get_due_words, get_new_words, update_fsrs_state, log_review,
  get_stats, get_review_history, get_setting, set_setting,
  get_connection, init_db,
)
from database.extras import (
  add_to_wrong_words, remove_from_wrong_words,
  update_wrong_word_streak, get_wrong_words, get_wrong_word_count,
  get_random_words,
  get_forgetting_curve_data, get_review_pressure_data,
  get_memory_durability_data,
)
from algorithms.fsrs import FSRS


app = Flask(__name__)
fsrs = FSRS()
DEFAULT_DAILY_NEW = 20




def fetch_definition_en(word):
    # Try multiple sources for Chinese translation
    chinese = None
    # Source 1: Youdao translate
    try:
        tu = "https://fanyi.youdao.com/translate?doctype=json&type=EN2ZH_CN&i=" + urllib.parse.quote(word)
        req = urllib.request.Request(tu, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            td = json.loads(resp.read().decode())
        if td.get("errorCode") == 0 and td.get("translation"):
            chinese = td["translation"][0]
    except:
        pass
    # Source 2: dict.youdao suggest backup
    if not chinese:
        try:
            tu = "https://dict.youdao.com/suggest?num=1&ver=3.0&doctype=json&cache=false&le=en&q=" + urllib.parse.quote(word)
            req = urllib.request.Request(tu, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                td = json.loads(resp.read().decode())
            entries = td.get("data", {}).get("entries", [])
            if entries and entries[0].get("explain"):
                chinese = entries[0]["explain"]
        except:
            pass
    return {"definitions": [chinese]} if chinese else None

def fetch_definition_ja(word):
    url = "https://jisho.org/api/v1/search/words?keyword=" + urllib.parse.quote(word)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WordBook/2.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        results = data.get("data", [])
        if not results:
            return None
        entry = results[0]
        senses = entry.get("senses", [])
        definitions = []
        for s in senses[:3]:
            parts = s.get("parts_of_speech", [])
            pos_str = parts[0] if parts else ""
            eng_defs = s.get("english_definitions", [])
            if eng_defs:
                def_text = "\u3001".join(eng_defs[:3])
                definitions.append((pos_str + " " + def_text).strip() if pos_str else def_text)
        japanese = entry.get("japanese", [{}])
        reading = japanese[0].get("reading", "") if japanese else ""
        kanji = japanese[0].get("word", "") if japanese else ""
        return {"definitions": definitions[:3], "examples": [], "phonetic": reading, "word": kanji or word, "kanji": kanji, "reading": reading}
    except Exception:
        return None


@app.route("/api/fetch-definition", methods=["GET"])
def api_fetch_definition():
    word = request.args.get("word", "").strip()
    language = request.args.get("language", "en").strip()
    if not word:
        return jsonify({"error": "\u5355\u8bcd\u4e0d\u80fd\u4e3a\u7a7a"}), 400
    try:
        if language == "ja":
            result = fetch_definition_ja(word)
        else:
            result = fetch_definition_en(word)
        if not result:
            return jsonify({"error": "\u672a\u627e\u5230\u91ca\u4e49", "definitions": [], "examples": []})
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "\u83b7\u53d6\u91ca\u4e49\u5931\u8d25: " + str(e), "definitions": [], "examples": []})


@app.route("/")
def index():
  return render_template("index.html")


@app.route("/api/words", methods=["POST"])
def api_add_word():
  try:
    data = request.get_json(force=True)
    word = data.get("word", "").strip()
    definition = data.get("definition", "").strip()
    if not word or (not definition and not data.get("auto_fetched")):
      return jsonify({"error": "单词和释义不能为空"}), 400
    word_id = add_word(
      word=word, definition=definition,
      language=data.get("language", "en"),
      pos=data.get("pos", ""),
      notes=data.get("notes", ""),
      kanji=data.get("kanji", ""),
    )
    return jsonify({"id": word_id, "message": "添加成功"}), 201
  except Exception as e:
    return jsonify({"error": f"添加词条失败: {str(e)}"}), 500


@app.route("/api/words/<int:word_id>", methods=["PUT"])
def api_edit_word(word_id: int):
  try:
    data = request.get_json(force=True)
    success = edit_word(
      word_id=word_id,
      word=data.get("word", ""),
      definition=data.get("definition", ""),
      language=data.get("language", "en"),
      pos=data.get("pos", ""),
      notes=data.get("notes", ""),
      kanji=data.get("kanji", ""),
    )
    if not success:
      return jsonify({"error": "词条不存在"}), 404
    return jsonify({"message": "更新成功"})
  except Exception as e:
    return jsonify({"error": f"更新失败: {str(e)}"}), 500


@app.route("/api/words/<int:word_id>", methods=["DELETE"])
def api_delete_word(word_id: int):
  try:
    success = delete_word(word_id)
    if not success:
      return jsonify({"error": "词条不存在"}), 404
    return jsonify({"message": "删除成功"})
  except Exception as e:
    return jsonify({"error": f"删除失败: {str(e)}"}), 500


@app.route("/api/words/batch-delete", methods=["POST"])
def api_batch_delete_words():
  try:
    data = request.get_json(force=True)
    ids = data.get("ids", [])
    if not ids or not isinstance(ids, list):
      return jsonify({"error": "请提供要删除的词条ID列表"}), 400
    ids = [int(i) for i in ids if isinstance(i, (int, float)) or (isinstance(i, str) and i.strip().isdigit())]
    if not ids:
      return jsonify({"error": "无效的ID列表"}), 400
    deleted = batch_delete_words(ids)
    return jsonify({"deleted": deleted, "message": f"成功删除 {deleted} 个词条"})
  except Exception as e:
    return jsonify({"error": f"批量删除失败: {str(e)}"}), 500


@app.route("/api/words/<int:word_id>", methods=["GET"])
def api_get_word(word_id: int):
  try:
    word = get_word(word_id)
    if not word:
      return jsonify({"error": "词条不存在"}), 404
    return jsonify(word)
  except Exception as e:
    return jsonify({"error": str(e)}), 500


@app.route("/api/words", methods=["GET"])
def api_list_words():
  try:
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    language = request.args.get("language", "", type=str)
    search = request.args.get("search", "", type=str)
    result = get_all_words(page=page, per_page=per_page,
                language=language, search=search)
    return jsonify(result)
  except Exception as e:
    return jsonify({"error": str(e)}), 500


@app.route("/api/words/batch", methods=["POST"])
def api_batch_import():
  try:
    data = request.get_json(force=True)
    words_data = data.get("words", [])
    if not words_data:
      return jsonify({"error": "词条列表不能为空"}), 400
    result = batch_import_words(words_data)
    return jsonify(result), 201
  except Exception as e:
    return jsonify({"error": f"批量导入失败: {str(e)}"}), 500


@app.route("/api/words/export", methods=["GET"])
def api_export_words():
  try:
    words = get_all_words_flat()
    return jsonify(words)
  except Exception as e:
    return jsonify({"error": str(e)}), 500


@app.route("/api/study/session", methods=["GET"])
def api_study_session():
  try:
    new_count = request.args.get("new_count", DEFAULT_DAILY_NEW, type=int)
    new_count = max(1, min(new_count, 100))
    due_words = get_due_words(limit=100)
    new_words = get_new_words(limit=new_count)
    return jsonify({"review": due_words, "new": new_words})
  except Exception as e:
    return jsonify({"error": f"获取学习会话失败: {str(e)}"}), 500


@app.route("/api/study/review", methods=["POST"])
def api_review_card():
  try:
    data = request.get_json(force=True)
    word_id = data.get("word_id")
    rating = data.get("rating")
    if not word_id or rating not in [1, 2, 3, 4]:
      return jsonify({"error": "参数无效"}), 400
    word = get_word(word_id)
    if not word:
      return jsonify({"error": "词条不存在"}), 404
    stability = word["stability"]
    difficulty = word["difficulty"]
    reps = word["reps"]
    lapses = word["lapses"]
    last_review = word.get("last_review")
    if last_review:
      try:
        last_dt = datetime.strptime(last_review, "%Y-%m-%d %H:%M:%S")
      except ValueError:
        last_dt = datetime.strptime(last_review, "%Y-%m-%d")
      elapsed_days = (datetime.now() - last_dt).total_seconds() / 86400.0
      elapsed_days = max(elapsed_days, 0.01)
    else:
      elapsed_days = 0.0
    pre_ret = fsrs.retrievability(stability, elapsed_days)
    result = fsrs.schedule(rating, stability, difficulty, elapsed_days, reps)
    new_stability = result["stability"]
    new_difficulty = result["difficulty"]
    new_interval = result["interval"]
    new_ret = result["retrievability"]
    new_reps = reps + 1
    new_lapses = lapses + (1 if rating == 1 else 0)
    update_fsrs_state(word_id, new_stability, new_difficulty,
               new_interval, rating, new_reps, new_lapses)
    log_review(word_id, rating, new_stability, new_difficulty,
           pre_ret, elapsed_days)
    if rating <= 2:
      add_to_wrong_words(word_id)
    elif rating >= 3:
      update_wrong_word_streak(word_id, True)
    next_review_date = datetime.now() + timedelta(days=new_interval)
    return jsonify({
      "message": "复习记录成功",
      "stability": new_stability,
      "difficulty": new_difficulty,
      "interval_days": new_interval,
      "next_review": next_review_date.strftime("%Y-%m-%d"),
      "retrievability": round(new_ret, 4),
      "reps": new_reps,
      "lapses": new_lapses,
    })
  except Exception as e:
    return jsonify({"error": f"复习失败: {str(e)}"}), 500


@app.route("/api/study/wrong-session", methods=["GET"])
def api_wrong_session():
  try:
    words = get_wrong_words(limit=50)
    return jsonify({"words": words})
  except Exception as e:
    return jsonify({"error": f"获取错题本失败: {str(e)}"}), 500


@app.route("/api/study/wrong-review", methods=["POST"])
def api_wrong_review():
  try:
    data = request.get_json(force=True)
    word_id = data.get("word_id")
    rating = data.get("rating")
    if not word_id or rating not in [1, 2, 3, 4]:
      return jsonify({"error": "参数无效"}), 400
    is_correct = rating >= 3
    removed = update_wrong_word_streak(word_id, is_correct)
    if not is_correct:
      add_to_wrong_words(word_id)
    return jsonify({
      "message": "提交成功",
      "removed_from_wrong": removed,
      "correct_streak_reset": not is_correct,
    })
  except Exception as e:
    return jsonify({"error": f"错题本复习失败: {str(e)}"}), 500


@app.route("/api/study/all-session", methods=["GET"])
def api_all_session():
  try:
    count = request.args.get("count", 20, type=int)
    count = max(1, min(count, 100))
    words = get_random_words(limit=count)
    return jsonify({"words": words})
  except Exception as e:
    return jsonify({"error": f"获取全词复习失败: {str(e)}"}), 500


@app.route("/api/stats", methods=["GET"])
def api_stats():
  try:
    stats = get_stats()
    return jsonify(stats)
  except Exception as e:
    return jsonify({"error": str(e)}), 500


@app.route("/api/stats/history", methods=["GET"])
def api_stats_history():
  try:
    days = request.args.get("days", 30, type=int)
    history = get_review_history(days=days)
    return jsonify(history)
  except Exception as e:
    return jsonify({"error": str(e)}), 500


@app.route("/api/stats/forgetting-curve", methods=["GET"])
def api_forgetting_curve():
  try:
    data = get_forgetting_curve_data(days=30)
    return jsonify({"data": data})
  except Exception as e:
    return jsonify({"error": str(e)}), 500


@app.route("/api/stats/review-pressure", methods=["GET"])
def api_review_pressure():
  try:
    data = get_review_pressure_data()
    return jsonify(data)
  except Exception as e:
    return jsonify({"error": str(e)}), 500


@app.route("/api/stats/memory-durability", methods=["GET"])
def api_memory_durability():
  try:
    data = get_memory_durability_data()
    return jsonify({"data": data})
  except Exception as e:
    return jsonify({"error": str(e)}), 500


@app.route("/api/stats/enhanced", methods=["GET"])
def api_stats_enhanced():
  try:
    conn = get_connection()
    try:
      c = conn.cursor()
      tr = c.execute("SELECT COUNT(*) FROM review_logs").fetchone()[0]
      wr = c.execute("SELECT COUNT(*) FROM review_logs WHERE rating<=2").fetchone()[0]
      er = round(wr / tr, 4) if tr > 0 else 0
      today = str(date.today())
      tt = c.execute("SELECT COUNT(*) FROM review_logs WHERE review_time>=?", (today,)).fetchone()[0]
      tc = c.execute("SELECT COUNT(*) FROM review_logs WHERE review_time>=? AND rating>=3", (today,)).fetchone()[0]
      ta = round(tc / tt, 4) if tt > 0 else 0
      wc = c.execute("SELECT COUNT(*) FROM wrong_words").fetchone()[0]
      tw = c.execute("SELECT COUNT(*) FROM words").fetchone()[0]
      mw = c.execute("SELECT COUNT(*) FROM fsrs_state WHERE reps>=3 AND stability>=30").fetchone()[0]
      avs = c.execute("SELECT AVG(stability) FROM fsrs_state").fetchone()[0] or 0
    finally:
      conn.close()
    base = get_stats()
    return jsonify({
      "total_reviews": tr, "error_rate": er,
      "today_reviews": tt, "today_accuracy": ta,
      "wrong_count": wc, "total_words": tw,
      "mastered_words": mw, "avg_stability": round(avs, 1),
      "base_stats": base,
    })
  except Exception as e:
    return jsonify({"error": str(e)}), 500


@app.route("/api/settings", methods=["GET"])
def api_get_settings():
  try:
    daily_new = get_setting("daily_new", str(DEFAULT_DAILY_NEW))
    return jsonify({"daily_new": int(daily_new)})
  except Exception as e:
    return jsonify({"error": str(e)}), 500


@app.route("/api/settings", methods=["PUT"])
def api_update_settings():
  try:
    data = request.get_json(force=True)
    if "daily_new" in data:
      val = max(1, min(100, int(data["daily_new"])))
      set_setting("daily_new", str(val))
    return jsonify({"message": "设置已更新"})
  except Exception as e:
    return jsonify({"error": f"更新设置失败: {str(e)}"}), 500


@app.errorhandler(404)
def not_found(e):
  return jsonify({"error": "接口不存在"}), 404


@app.errorhandler(500)
def server_error(e):
  return jsonify({"error": "服务器内部错误"}), 500


if __name__ == "__main__":
  init_db()
  import sys
  app.run(host="127.0.0.1", port=5004, debug=False, use_reloader=False)
