import os
p = "C:\\Users\\28381\\Documents\\Codex\\2026-07-17\\c-users-28381-desktop-2\\wordbook\\app.py"
c = open(p, "r", encoding="utf-8").read()

# 1. Add imports after 'import math'
c = c.replace("import math", "import math\nimport json\nimport urllib.request\nimport urllib.parse")

# 2. Add fetch functions and route before first @app.route
fetch_code = """

def fetch_definition_en(word):
    url = "https://api.dictionaryapi.dev/api/v2/entries/en/" + urllib.parse.quote(word)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WordBook/2.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        if not data or not isinstance(data, list):
            return None
        entry = data[0]
        meanings = entry.get("meanings", [])
        definitions = []
        examples = []
        phonetics = entry.get("phonetics", [])
        phonetic = entry.get("phonetic", phonetics[0].get("text", "") if phonetics else "")
        for m in meanings:
            pos = m.get("partOfSpeech", "")
            for d in m.get("definitions", [])[:2]:
                def_text = d.get("definition", "")
                if def_text:
                    definitions.append((pos + ". " + def_text) if pos else def_text)
                ex = d.get("example", "")
                if ex and len(examples) < 3:
                    examples.append(ex)
        return {"definitions": definitions[:3], "examples": examples[:3], "phonetic": phonetic}
    except Exception:
        return None


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
                def_text = "\\u3001".join(eng_defs[:3])
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
        return jsonify({"error": "\\u5355\\u8bcd\\u4e0d\\u80fd\\u4e3a\\u7a7a"}), 400
    try:
        if language == "ja":
            result = fetch_definition_ja(word)
        else:
            result = fetch_definition_en(word)
        if not result:
            return jsonify({"error": "\\u672a\\u627e\\u5230\\u91ca\\u4e49", "definitions": [], "examples": []})
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "\\u83b7\\u53d6\\u91ca\\u4e49\\u5931\\u8d25: " + str(e), "definitions": [], "examples": []})

"""

c = c.replace("@app.route(\"/\")", fetch_code + "\n@app.route(\"/\")")
open(p, "w", encoding="utf-8").write(c)

compile(c, "app.py", "exec")
print("app.py patched successfully!")
print("Added: urllib imports, fetch_definition_en, fetch_definition_ja, /api/fetch-definition")
