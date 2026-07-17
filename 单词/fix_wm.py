import os
p = r"C:\Users\28381\Documents\Codex\2026-07-17\c-users-28381-desktop-2\wordbook\static\js\wordManager.js"
c = open(p, "r", encoding="utf-8").read()

# The empty function
old = "    async fetchAndFillDefinition(word) {\n    },"

# The replacement with full implementation
new = r"""    async fetchAndFillDefinition(word) {
        if (!word) return;
        var fd = document.getElementById("form-definition");
        var fn = document.getElementById("form-notes");
        if (!fd) return;
        var fs = document.getElementById("fetch-status");
        if (fs) fs.remove();
        fs = document.createElement("div");
        fs.id = "fetch-status"; fs.className = "fetch-loading";
        fs.innerHTML = "<span class='spinner'></span> \u6b63\u5728\u83b7\u53d6\u91ca\u4e49...";
        fd.parentNode.insertBefore(fs, fd.nextSibling);
        try {
            var lang = (document.getElementById("form-language")||{}).value || "en";
            var r = await api("/fetch-definition?word="+encodeURIComponent(word)+"&language="+lang);
            fs.remove();
            if (r.error||!r.definitions||!r.definitions.length) {
                var e = document.createElement("div");
                e.className = "fetch-result error";
                e.textContent = "\u672a\u627e\u5230\u91ca\u4e49";
                fd.parentNode.insertBefore(e, fd.nextSibling);
                setTimeout(function(){e.remove()},4000); return;
            }
            var dt = r.definitions.map(function(d){return d.replace(/^[a-z]+\.\s*/,"");}).join("; ");
            fd.value = dt;
            if (r.phonetic && lang==="en") {
                var pe = document.getElementById("form-pos");
                if (pe && !pe.value) pe.value = "/"+r.phonetic+"/";
            }
            if (r.examples && r.examples.length) {
                var exs = r.examples.map(function(ex,i){return (i+1)+". "+ex;}).join("\\n");
                if (fn) fn.value = exs;
            }
            if (r.kanji) {
                var ke = document.getElementById("form-kanji");
                if (ke && !ke.value) ke.value = r.kanji;
            }
            var ok = document.createElement("div");
            ok.className = "fetch-result success";
            ok.textContent = "\u5df2\u83b7\u53d6 "+r.definitions.length+" \u6761\u91ca\u4e49";
            fd.parentNode.insertBefore(ok, fd.nextSibling);
            setTimeout(function(){ok.remove()},5000);
            if (typeof speakWord==="function") speakWord(word);
        } catch(e) {
            if (fs) fs.remove();
            var er = document.createElement("div");
            er.className = "fetch-result error";
            er.textContent = "\u83b7\u53d6\u5931\u8d25: "+e.message;
            fd.parentNode.insertBefore(er, fd.nextSibling);
            setTimeout(function(){er.remove()},4000);
        }
    },

    onWordInput() {
        var af = document.getElementById("form-auto-fetch");
        if (!af||!af.checked) return;
        var w = document.getElementById("form-word").value.trim();
        if (w.length>=2) this.fetchAndFillDefinition(w);
    },"""

if old in c:
    c = c.replace(old, new)
    open(p, "w", encoding="utf-8").write(c)
    print("SUCCESS: fetchAndFillDefinition patched!")
    # Verify
    compile(open(p, "r", encoding="utf-8").read(), "wm.js", "exec")
    print("JS syntax OK")
else:
    print("FAILED: Could not find old function")
    idx = c.find("async fetchAndFillDefinition")
    if idx >= 0:
        print("Found at", idx, repr(c[idx:idx+100]))
