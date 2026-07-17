/**
 * 多语背词 - 词库管理模块
 * 负责词条的增删改查、批量导入导出和搜索。
 */

const wordManager = {
    currentPage: 1,
    perPage: 20,
    searchQuery: "",
    langFilter: "",
    selectedIds: new Set(),
    currentIds: [],
    pendingWords: [],
    parsedWords: [],

    async loadWords(page) {
        if (page) this.currentPage = page;
        const params = {"page": this.currentPage, "per_page": this.perPage};
        try {
            var qs = Object.keys(params).map(k => k + "=" + params[k]).join("&");
            if (this.searchQuery) qs += "&search=" + encodeURIComponent(this.searchQuery);
            if (this.langFilter) qs += "&language=" + encodeURIComponent(this.langFilter);
            const data = await api("/words?" + qs);
            this.renderTable(data.data || []);
            this.renderPagination(data.total || 0);
        } catch (e) {
            document.getElementById("word-table-body").innerHTML =
                '<tr><td colspan="7" class="empty-row">加载失败: ' + this.escapeHtml(e.message) + "</td></tr>";
        }
    },

    renderTable(words) {
        var self = this;
        var tbody = document.getElementById("word-table-body");
        if (words.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-row">词库为空</td></tr>';
            return;
        }
        this.currentIds = words.map(function(w) { return w.id; });
        tbody.innerHTML = words.map(function(w) {
            var esc = function(s) { return self.escapeHtml(s); };
            return "<tr>" +
                '<td><input type="checkbox" class="word-checkbox" onchange="wordManager.toggleSingle(' + w.id + ', this.checked)" ' + (self.selectedIds.has(w.id) ? "checked" : "") + "></td>" +
                '<td><strong class="word-clickable" onclick="speakWord(' + "'" + esc(w.word).replace(/'/g, "'") + "'" + ')" title="点击朗读">' + esc(w.word) + "</strong></td>" +
                "<td>" + esc(w.definition) + "</td>" +
                '<td><span class="lang-tag ' + w.language + '">' + (w.language === "en" ? "英语" : "日语") + "</span></td>" +
                "<td>" + esc(w.pos || "-") + "</td>" +
                "<td>" + (w.reps || 0) + "</td>" +
                '<td><div class="action-btns">' +
                '<button class="btn btn-secondary btn-sm" onclick="wordManager.showEditForm(' + w.id + ')">编辑</button>' +
                '<button class="btn btn-danger btn-sm" onclick="wordManager.confirmDelete(' + w.id + ", '" + esc(w.word).replace(/'/g, "'") + "'" + ')">删除</button>' +
                "</div></td></tr>";
        }).join("");
    },

    renderPagination(total) {
        var container = document.getElementById("pagination");
        var totalPages = Math.ceil(total / this.perPage);
        if (totalPages <= 1) { container.innerHTML = ""; return; }
        var html = '<button class="page-btn" onclick="wordManager.loadWords(1)"' + (this.currentPage <= 1 ? " disabled" : "") + ">首页</button>";
        html += '<button class="page-btn" onclick="wordManager.loadWords(' + (this.currentPage - 1) + ')"' + (this.currentPage <= 1 ? " disabled" : "") + ">上一页</button>";
        var startPage = Math.max(1, this.currentPage - 2);
        var endPage = Math.min(totalPages, this.currentPage + 2);
        for (var i = startPage; i <= endPage; i++) {
            html += '<button class="page-btn' + (i === this.currentPage ? " active" : "") + '" onclick="wordManager.loadWords(' + i + ')">' + i + "</button>";
        }
        html += '<button class="page-btn" onclick="wordManager.loadWords(' + (this.currentPage + 1) + ')"' + (this.currentPage >= totalPages ? " disabled" : "") + ">下一页</button>";
        html += '<button class="page-btn" onclick="wordManager.loadWords(' + totalPages + ')"' + (this.currentPage >= totalPages ? " disabled" : "") + ">末页</button>";
        container.innerHTML = html;
    },

    searchWords() {
        this.searchQuery = document.getElementById("search-input").value.trim();
        this.langFilter = document.getElementById("lang-filter").value;
        this.currentPage = 1;
        this.loadWords();
    },

    showAddForm() {
        var formHtml =
            '<form id="word-form" onsubmit="event.preventDefault(); wordManager.submitAdd()">' +
            '<div class="form-group"><label>单词 * <span class="speak-trigger" onclick="speakWord(document.getElementById(' + "'form-word'" + ').value)" title="朗读">' +
            '<svg class="speak-icon" viewBox="0 0 20 20" width="14" height="14" fill="none">' +
            '<path d="M8.5 4L5 7.5H2v5h3l3.5 3.5V4z" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>' +
            '<path d="M13 7a4 4 0 010 6M14.5 4.5a7 7 0 010 11" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg></span></label>' +
            '<input type="text" id="form-word" required placeholder="输入英语或日语单词"></div>' +
            '<div class="form-group"><label>中文释义 *</label>' +
            '<input type="text" id="form-definition" placeholder="输入中文释义"></div>' +
            '<div class="form-group"><label>语言</label>' +
            '<select id="form-language"><option value="en">英语</option><option value="ja">日语</option></select></div>' +
            '<div class="form-group"><label>日语汉字（可选）</label>' +
            '<input type="text" id="form-kanji" placeholder="如: 無料、勉強"></div>' +
            '<div class="form-group"><label>词性（可选）</label>' +
            '<input type="text" id="form-pos" placeholder="如: noun, verb, 形容詞"></div>' +
            '<div class="form-group"><label>备注（可选）</label>' +
            '<textarea id="form-notes" placeholder="例句、记忆技巧等"></textarea></div>' +
            '<div class="form-group fetch-option">' +
            '<label class="checkbox-label"><input type="checkbox" id="form-auto-fetch"> <span>自动获取释义</span></label></div>' +
            '<div class="form-actions">' +
            '<button type="button" class="btn btn-secondary" onclick="closeModal()">取消</button>' +
            '<button type="submit" class="btn btn-primary">添加</button></div></form>';
        openModal("添加新词条", formHtml);
    },

    async submitAdd() {
        var autoFetch = document.getElementById("form-auto-fetch");
        if (autoFetch && autoFetch.checked) {
            await this.fetchAndFillDefinition(document.getElementById("form-word").value.trim());
        }
        var data = {
            word: document.getElementById("form-word").value.trim(),
            definition: document.getElementById("form-definition").value.trim(),
            language: document.getElementById("form-language").value,
            pos: document.getElementById("form-pos").value.trim(),
            notes: document.getElementById("form-notes").value.trim(),
            kanji: document.getElementById("form-kanji").value.trim(),
        };
        if (!data.word) {
            showToast("请输入单词", "error");
            return;
        }
        if (!data.definition && !(autoFetch && autoFetch.checked)) {
            showToast("请填写释义", "error");
            return;
        }

        if (autoFetch && autoFetch.checked) data.auto_fetched = true;
        try {
            await api("/words", { method: "POST", body: JSON.stringify(data) });
            closeModal();
            showToast("添加成功");
            this.loadWords();
            refreshStats();
        } catch (e) {
            showToast("添加失败: " + e.message, "error");
        }
    },

    async showEditForm(wordId) {
        try {
            var word = await api("/words/" + wordId);
            var esc = function(s) { return (wordManager.escapeHtml(s || "")); };
            var formHtml =
                '<form id="word-form" onsubmit="event.preventDefault(); wordManager.submitEdit(' + wordId + ')">' +
                '<div class="form-group"><label>单词 * <span class="speak-trigger" onclick="speakWord(document.getElementById(' + "'form-word'" + ').value)" title="朗读">' +
                '<svg class="speak-icon" viewBox="0 0 20 20" width="14" height="14" fill="none">' +
                '<path d="M8.5 4L5 7.5H2v5h3l3.5 3.5V4z" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>' +
                '<path d="M13 7a4 4 0 010 6M14.5 4.5a7 7 0 010 11" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg></span></label>' +
                '<input type="text" id="form-word" value="' + esc(word.word) + '" required></div>' +
                '<div class="form-group"><label>中文释义 *</label>' +
                '<input type="text" id="form-definition" value="' + esc(word.definition) + '" required></div>' +
                '<div class="form-group"><label>语言</label>' +
                '<select id="form-language"><option value="en"' + (word.language === "en" ? " selected" : "") + ">英语</option>" +
                '<option value="ja"' + (word.language === "ja" ? " selected" : "") + ">日语</option></select></div>" +
                '<div class="form-group"><label>日语汉字（可选）</label>' +
                '<input type="text" id="form-kanji" value="' + esc(word.kanji) + '"></div>' +
                '<div class="form-group"><label>词性（可选）</label>' +
                '<input type="text" id="form-pos" value="' + esc(word.pos) + '"></div>' +
                '<div class="form-group"><label>备注（可选）</label>' +
                '<textarea id="form-notes">' + esc(word.notes) + "</textarea></div>" +
                '<div class="form-actions">' +
                '<button type="button" class="btn btn-secondary" onclick="closeModal()">取消</button>' +
                '<button type="submit" class="btn btn-primary">保存</button></div></form>';
            openModal("编辑词条", formHtml);
        } catch (e) {
            showToast("获取词条详情失败", "error");
        }
    },

    async submitEdit(wordId) {
        var data = {
            word: document.getElementById("form-word").value.trim(),
            definition: document.getElementById("form-definition").value.trim(),
            language: document.getElementById("form-language").value,
            pos: document.getElementById("form-pos").value.trim(),
            notes: document.getElementById("form-notes").value.trim(),
            kanji: document.getElementById("form-kanji").value.trim(),
        };
        if (!data.word) {
            showToast("请输入单词", "error");
            return;
        }
        if (!data.definition) {
            showToast("请填写释义", "error");
            return;
        }
        try {
            await api("/words/" + wordId, { method: "PUT", body: JSON.stringify(data) });
            closeModal();
            showToast("更新成功");
            this.loadWords();
        } catch (e) {
            showToast("更新失败: " + e.message, "error");
        }
    },

    async confirmDelete(wordId, wordText) {
        if (!confirm('确定要删除词条 "' + wordText + '" 吗？')) return;
        try {
            await api("/words/" + wordId, { method: "DELETE" });
            showToast("删除成功");
            this.loadWords();
            refreshStats();
        } catch (e) {
            showToast("删除失败: " + e.message, "error");
        }
    },

    showImportForm() {
        openModal("批量导入词条",
            '<p class="form-help">每行一个词条，格式：单词 | 释义 | 语言(可选) | 词性(可选) | 备注(可选)</p>' +
            '<p class="form-help" style="margin-bottom:8px">语言：en（英语）或 ja（日语），默认为英语</p>' +
            '<div class="form-group"><label>导入内容</label>' +
            '<textarea id="import-text" rows="10" placeholder="apple | 苹果 | en | noun | 一种水果"></textarea></div>' +
            '<div class="form-actions">' +
            '<button type="button" class="btn btn-secondary" onclick="closeModal()">取消</button>' +
            '<button type="button" class="btn btn-primary" onclick="wordManager.submitImport()">导入</button></div>'
        );
    },

    async submitImport() {
        var text = document.getElementById("import-text").value.trim();
        if (!text) { showToast("请输入词条内容", "error"); return; }
        var words = [];
        var lines = text.split("\n").filter(function(l) { return l.trim(); });
        for (var i = 0; i < lines.length; i++) {
            var parts = lines[i].split("|").map(function(s) { return s.trim(); });
            if (parts.length >= 2) {
                words.push({ word: parts[0], definition: parts[1], language: parts[2] || "en", pos: parts[3] || "", notes: parts[4] || "" });
            }
        }
        if (words.length === 0) { showToast("未解析到有效词条", "error"); return; }
        try {
            var result = await api("/words/batch", { method: "POST", body: JSON.stringify({ words: words }) });
            closeModal();
            showToast("导入完成: 成功 " + result.succeeded + " 条，失败 " + result.failed + " 条");
            this.loadWords();
            refreshStats();
        } catch (e) { showToast("导入失败: " + e.message, "error"); }
    },

    async exportWords() {
        try {
            var words = await api("/words/export");
            var blob = new Blob([JSON.stringify(words, null, 2)], { type: "application/json" });
            var url = URL.createObjectURL(blob);
            var a = document.createElement("a");
            a.href = url;
            a.download = "vocab_export_" + new Date().toISOString().slice(0, 10) + ".json";
            a.click();
            URL.revokeObjectURL(url);
            showToast("已导出 " + words.length + " 个词条");
        } catch (e) { showToast("导出失败: " + e.message, "error"); }
    },

    escapeHtml(str) {
        if (!str) return "";
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    },

    async fetchAndFillDefinition(word) {
        if (!word) return;
        var fd = document.getElementById("form-definition");
        if (!fd) return;
        var fs = document.getElementById("fetch-status");
        if (fs) fs.remove();
        fs = document.createElement("div");
        fs.id = "fetch-status"; fs.className = "fetch-loading";
        fs.innerHTML = "<span class='spinner'></span> 正在获取释义...";
        fd.parentNode.insertBefore(fs, fd.nextSibling);
        try {
            var lang = (document.getElementById("form-language")||{}).value || "en";
            var r = await api("/fetch-definition?word="+encodeURIComponent(word)+"&language="+lang);
            fs.remove();
            if (r.error||!r.definitions||!r.definitions.length) {
                var e = document.createElement("div");
                e.className = "fetch-result error";
                e.textContent = "未找到中文释义";
                fd.parentNode.insertBefore(e, fd.nextSibling);
                setTimeout(function(){e.remove()},4000); return;
            }
            fd.value = r.definitions[0];
            var ok = document.createElement("div");
            ok.className = "fetch-result success";
            ok.textContent = "已填充中文释义";
            fd.parentNode.insertBefore(ok, fd.nextSibling);
            setTimeout(function(){ok.remove()},3000);
            if (typeof speakWord==="function") speakWord(word);
        } catch(e) {
            if (fs) fs.remove();
            var er = document.createElement("div");
            er.className = "fetch-result error";
            er.textContent = "获取失败: "+e.message;
            fd.parentNode.insertBefore(er, fd.nextSibling);
            setTimeout(function(){er.remove()},4000);
        }
    },

    onWordInput() {
        var af = document.getElementById("form-auto-fetch");
        if (!af||!af.checked) return;
        var w = document.getElementById("form-word").value.trim();
        if (w.length>=2) this.fetchAndFillDefinition(w);
    },

    confirmBatchDelete() {
        var count = this.selectedIds.size;
        if (count === 0) return;
        if (!confirm("确定要删除选中的 " + count + " 个词条吗？此操作不可撤销。")) return;
        var ids = Array.from(this.selectedIds);
        var self = this;
        api("/words/batch-delete", { method: "POST", body: JSON.stringify({ ids: ids }) }).then(function(r) {
            showToast("成功删除 " + r.deleted + " 个词条");
            self.selectedIds.clear();
            document.getElementById("select-all").checked = false;
            self.updateBatchToolbar();
            self.loadWords();
            refreshStats();
        }).catch(function(e) { showToast("批量删除失败: " + e.message, "error"); });
    },

    toggleSingle(id, checked) {
        if (checked) this.selectedIds.add(id);
        else this.selectedIds.delete(id);
        this.updateBatchToolbar();
        var sa = document.getElementById("select-all");
        if (sa) {
            sa.checked = this.currentIds.length > 0 && this.currentIds.every(function(i) { return wordManager.selectedIds.has(i); });
        }
    },

    toggleSelectAll(checked) {
        var self = this;
        this.currentIds.forEach(function(id) {
            if (checked) self.selectedIds.add(id);
            else self.selectedIds.delete(id);
        });
        var cbs = document.querySelectorAll(".word-checkbox");
        for (var i = 0; i < cbs.length; i++) { cbs[i].checked = checked; }
        this.updateBatchToolbar();
    },

    clearSelection() {
        this.selectedIds.clear();
        var cbs = document.querySelectorAll(".word-checkbox");
        for (var i = 0; i < cbs.length; i++) { cbs[i].checked = false; }
        document.getElementById("select-all").checked = false;
        this.updateBatchToolbar();
    },

    updateBatchToolbar() {
        var tb = document.getElementById("batch-toolbar");
        var ce = document.getElementById("selected-count");
        var n = this.selectedIds.size;
        if (n > 0) { tb.style.display = "flex"; ce.textContent = n; }
        else { tb.style.display = "none"; }
    },

    showSentenceImport() {
        var area = document.getElementById("sentence-import-area");
        if (area) { area.style.display = "block"; area.scrollIntoView({ behavior: "smooth", block: "start" }); }
        this.loadPendingFromStorage();
    },

    hideSentenceImport() {
        var area = document.getElementById("sentence-import-area");
        if (area) area.style.display = "none";
    },

    parseSentence() {
        var text = document.getElementById("sentence-input").value.trim();
        if (!text) { showToast("请输入文本", "error"); return; }
        var raw = text.split(/[\s,.;:!?"'()\[\]{}<>@#$%^&*+=\/\\|~`\d]+/).filter(function(w) {
            return /^[a-zA-Z\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+$/.test(w);
        });
        var seen = new Set();
        this.parsedWords = [];
        for (var i = 0; i < raw.length; i++) {
            var l = raw[i].toLowerCase();
            if (!seen.has(l) && raw[i].length > 0) { seen.add(l); this.parsedWords.push(raw[i]); }
        }
        if (this.parsedWords.length === 0) { showToast("未解析到有效单词", "error"); return; }
        var ps = new Set(this.pendingWords.map(function(x) { return x.toLowerCase(); }));
        this.parsedWords = this.parsedWords.filter(function(w) { return !ps.has(w.toLowerCase()); });
        if (this.parsedWords.length === 0) { showToast("所有单词已在待处理词库中", "info"); }
        this.renderParsedWords();
    },

    renderParsedWords() {
        var c = document.getElementById("parsed-words-container");
        var s = document.getElementById("parse-result-section");
        if (this.parsedWords.length === 0) { s.style.display = "none"; return; }
        s.style.display = "block";
        document.getElementById("parse-word-count").textContent = this.parsedWords.length + " 个单词";
        var self = this;
        c.innerHTML = this.parsedWords.map(function(word, i) {
            return '<span class="word-block" draggable="true" ondragstart="wordManager.onDragStart(event, ' + "'" + self.escapeHtml(word) + "'" + ", " + i + ')" ondragend="wordManager.onDragEnd(event)">' + self.escapeHtml(word) + "</span>";
        }).join("");
    },

    onDragStart(e, word, idx) {
        e.dataTransfer.setData("text/plain", JSON.stringify({ word: word, index: idx }));
        e.dataTransfer.effectAllowed = "move";
        e.target.classList.add("dragging");
    },

    onDragEnd(e) {
        e.target.classList.remove("dragging");
        var els = document.querySelectorAll(".pending-drop-zone");
        for (var i = 0; i < els.length; i++) { els[i].classList.remove("drag-over"); }
    },

    onDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
        e.currentTarget.classList.add("drag-over");
    },

    onDrop(e) {
        e.preventDefault();
        e.currentTarget.classList.remove("drag-over");
        var data = JSON.parse(e.dataTransfer.getData("text/plain"));
        var word = data.word;
        if (!word) return;
        this.parsedWords = this.parsedWords.filter(function(w) { return w !== word; });
        this.renderParsedWords();
        if (!this.pendingWords.some(function(w) { return w.toLowerCase() === word.toLowerCase(); })) {
            this.pendingWords.push(word);
        }
        this.renderPendingWords();
        this.savePendingToStorage();
        this.updatePendingBar();
        showToast('已添加 "' + word + '" 到待处理词库', "success");
    },

    renderPendingWords() {
        var c = document.getElementById("pending-words-container");
        document.getElementById("pending-word-count").textContent = this.pendingWords.length;
        if (this.pendingWords.length === 0) {
            c.innerHTML = '<div class="pending-empty-hint" id="pending-empty-hint">拖拽单词块到这里，点击即可添加到词库</div>';
            if (document.getElementById("save-pending-btn")) document.getElementById("save-pending-btn").style.display = "none";
            if (document.getElementById("clear-pending-btn")) document.getElementById("clear-pending-btn").style.display = "none";
            return;
        }
        if (document.getElementById("save-pending-btn")) document.getElementById("save-pending-btn").style.display = "none";
        if (document.getElementById("clear-pending-btn")) document.getElementById("clear-pending-btn").style.display = "inline-flex";
        var self = this;
        c.innerHTML = this.pendingWords.map(function(word, i) {
            return '<span class="word-block pending" style="animation-delay:' + (i * 0.06) + 's">' + self.escapeHtml(word) +
                '<span class="speak-trigger" onclick="event.stopPropagation();speakWord(' + "'" + self.escapeHtml(word) + "'" + ')" title="朗读">' +
                '<svg class="speak-icon" viewBox="0 0 20 20" width="12" height="12" fill="none">' +
                '<path d="M8.5 4L5 7.5H2v5h3l3.5 3.5V4z" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>' +
                '<path d="M13 7a4 4 0 010 6M14.5 4.5a7 7 0 010 11" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg></span>' +
                '<span class="pending-click-hint" onclick="wordManager.addPendingWord(' + "'" + self.escapeHtml(word) + "', " + i + ')" title="点击添加到词库">+</span>' +
                '<span class="pending-remove" onclick="event.stopPropagation();wordManager.removePendingWord(' + i + ')">&times;</span></span>';
        }).join("");
    },

    addPendingWord(word, idx) {
        var esc = this.escapeHtml(word);
        var formHtml =
            '<form id="word-form" onsubmit="event.preventDefault(); wordManager.submitAddFromPending(' + "'" + esc + "', " + idx + ')">' +
            '<div class="form-group"><label>单词 * <span class="speak-trigger" onclick="speakWord(document.getElementById(' + "'form-word'" + ').value)" title="朗读">' +
            '<svg class="speak-icon" viewBox="0 0 20 20" width="14" height="14" fill="none">' +
            '<path d="M8.5 4L5 7.5H2v5h3l3.5 3.5V4z" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>' +
            '<path d="M13 7a4 4 0 010 6M14.5 4.5a7 7 0 010 11" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg></span></label>' +
            '<input type="text" id="form-word" value="' + esc + '" required></div>' +
            '<div class="form-group"><label>中文释义 *</label><input type="text" id="form-definition" placeholder="输入中文释义"></div>' +
            '<div class="form-group"><label>语言</label><select id="form-language"><option value="en">英语</option><option value="ja">日语</option></select></div>' +
            '<div class="form-group"><label>日语汉字（可选）</label><input type="text" id="form-kanji" placeholder="如: 無料、勉強"></div>' +
            '<div class="form-group"><label>词性（可选）</label><input type="text" id="form-pos" placeholder="如: noun, verb"></div>' +
            '<div class="form-group"><label>备注（可选）</label><textarea id="form-notes" placeholder="例句、记忆技巧等"></textarea></div>' +
            '<div class="form-group fetch-option"><label class="checkbox-label"><input type="checkbox" id="form-auto-fetch"> <span>自动获取释义</span></label></div>' +
            '<div class="form-actions"><button type="button" class="btn btn-secondary" onclick="closeModal()">取消</button><button type="submit" class="btn btn-primary">添加</button></div></form>';
        openModal("添加词条：" + word, formHtml);
    },

    async submitAddFromPending(word, idx) {
        var w = document.getElementById("form-word").value.trim();
        if (!w) { showToast("请输入单词", "error"); return; }
        var af = document.getElementById("form-auto-fetch");
        if (af && af.checked) { await this.fetchAndFillDefinition(w); }
        var d = {
            word: w,
            definition: document.getElementById("form-definition").value.trim(),
            language: document.getElementById("form-language").value,
            pos: document.getElementById("form-pos").value.trim(),
            notes: document.getElementById("form-notes").value.trim(),
            kanji: document.getElementById("form-kanji").value.trim(),
        };
        if (!d.definition && !(af && af.checked)) { showToast("请填写释义或取消自动获取", "error"); return; }
        if (af && af.checked) d.auto_fetched = true;
        var self = this;
        try {
            await api("/words", { method: "POST", body: JSON.stringify(d) });
            closeModal();
            showToast('"' + word + '" 已添加成功');
            self.pendingWords.splice(idx, 1);
            self.renderPendingWords();
            self.savePendingToStorage();
            self.updatePendingBar();
            self.loadWords();
            refreshStats();
        } catch (e) { showToast("添加失败: " + e.message, "error"); }
    },

    removePendingWord(idx) {
        this.pendingWords.splice(idx, 1);
        this.renderPendingWords();
        this.savePendingToStorage();
        this.updatePendingBar();
    },

    clearPendingWords() {
        if (this.pendingWords.length === 0) return;
        if (!confirm("清空待处理词库中的所有单词？")) return;
        this.pendingWords = [];
        this.renderPendingWords();
        this.savePendingToStorage();
        this.updatePendingBar();
        showToast("待处理词库已清空");
    },

    clearAllPendingWords() {
        this.clearPendingWords();
        if (typeof closePendingModal === "function") closePendingModal();
    },

    savePendingToStorage() {
        try { localStorage.setItem("vocab_pending_words", JSON.stringify(this.pendingWords)); } catch (e) {}
    },

    loadPendingFromStorage() {
        try {
            var s = localStorage.getItem("vocab_pending_words");
            if (s) { this.pendingWords = JSON.parse(s); this.renderPendingWords(); this.updatePendingBar(); }
        } catch (e) {}
    },

    updatePendingBar() {
        var bar = document.getElementById("pending-bar");
        var ce = document.getElementById("pending-bar-count");
        if (this.pendingWords.length > 0) { bar.style.display = "flex"; ce.textContent = "(" + this.pendingWords.length + ")"; }
        else { bar.style.display = "none"; }
    },

    showPendingLibrary() {
        var c = document.getElementById("pending-modal-words-container");
        var o = document.getElementById("pending-modal-overlay");
        if (this.pendingWords.length === 0) {
            c.innerHTML = '<div style="text-align:center;padding:24px;color:var(--text-secondary)">暂无待处理单词</div>';
        } else {
            var self = this;
            c.innerHTML = this.pendingWords.map(function(word, i) {
                return '<span class="word-block pending" style="animation-delay:' + (i * 0.04) + 's">' + self.escapeHtml(word) +
                    '<span class="speak-trigger" onclick="event.stopPropagation();speakWord(' + "'" + self.escapeHtml(word) + "'" + ')" title="朗读">' +
                    '<svg class="speak-icon" viewBox="0 0 20 20" width="12" height="12" fill="none">' +
                    '<path d="M8.5 4L5 7.5H2v5h3l3.5 3.5V4z" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>' +
                    '<path d="M13 7a4 4 0 010 6M14.5 4.5a7 7 0 010 11" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg></span>' +
                    '<span onclick="wordManager.addPendingWord(' + "'" + self.escapeHtml(word) + "', " + i + ');closePendingModal();" style="cursor:pointer;margin-left:2px;font-size:13px;font-weight:700;opacity:0.5">+</span></span>';
            }).join("");
        }
        o.style.display = "flex";
    },
};

function closePendingModal(event) {
    if (event && event.target !== document.getElementById("pending-modal-overlay")) return;
    document.getElementById("pending-modal-overlay").style.display = "none";
}

window.wordManager = wordManager;
window.closePendingModal = closePendingModal;
