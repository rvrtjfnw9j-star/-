 /**
  * 操作台 - 学习模块
  * 管理学习会话、卡片翻转和 FSRS 复习评级。
  */
 
 const study = {
   sessionCards: [],
   currentIndex: 0,
   isCardFlipped: false,
   isSessionActive: false,
   reviewedCount: 0,
   newCount: 0,
   currentWord: null,
   currentMode: 'normal',
 
   setMode(mode) {
     if (this.isSessionActive) this.endSession();
     this.currentMode = mode;
     document.querySelectorAll('.mode-btn').forEach(b => b.classList.toggle('active', b.dataset.mode === mode));
     const msgs = {
       normal: '每日学习模式：随机抽取N个单词学习，答错的自动加入错题本',
       wrong: '错题本模式：复习答错的单词，连续答对3次自动移出错题本',
       all: '全部单词模式：从词库随机抽取单词复习',
       learn: '学习单词模式：点击卡片翻转学习释义'
     };
     document.getElementById('placeholder-text').textContent = msgs[mode] || msgs.normal;
   },
 
   async startSession() {
     const btn = document.getElementById('btn-start-study');
     btn.disabled = true;
     btn.textContent = '加载中...';
     try {
       let data, count = 20;
       if (this.currentMode === 'normal' || this.currentMode === 'learn') {
         try { const s = await api('/settings'); count = s.daily_new || 20; } catch(e) { count = 20; }
       }
       if (this.currentMode === 'normal') {
         data = await api('/study/all-session?count=' + count);
         this.sessionCards = data.words || [];
       } else if (this.currentMode === 'wrong') {
         data = await api('/study/wrong-session');
         this.sessionCards = shuffleArray(data.words || []);
       } else if (this.currentMode === 'all') {
         data = await api('/study/all-session?count=20');
         this.sessionCards = data.words || [];
       } else {
         data = await api('/study/session?new_count=' + count);
         this.sessionCards = [...(data.review || []), ...(data.new || [])];
       }
       if (this.sessionCards.length === 0) {
         showToast('词库为空，请先添加词条', 'error');
         btn.disabled = false; btn.textContent = '开始学习';
         return;
       }
       this.currentIndex = 0;
       this.isSessionActive = true;
       this.isCardFlipped = false;
       this.reviewedCount = 0;
       this.newCount = 0;
       document.getElementById('card-placeholder').style.display = 'none';
       document.getElementById('flashcard').style.display = 'block';
       document.getElementById('session-info').style.display = 'block';
       document.getElementById('btn-leave-session').style.display = 'inline-block';
       this.showCurrentCard();
       btn.textContent = '继续学习';
     } catch (e) { showToast('获取学习词条失败: ' + e.message, 'error'); }
     finally { btn.disabled = false; }
   },
 
   showCurrentCard() {
     if (this.currentIndex >= this.sessionCards.length) { this.endSession(); return; }
     const word = this.sessionCards[this.currentIndex];
     this.currentWord = word;
     this.isCardFlipped = false;
     document.getElementById('flashcard').classList.remove('flipped');
     document.getElementById('card-lang').textContent = word.language === 'en' ? 'EN' : 'JP';
     document.getElementById('card-word').textContent = word.word;
    document.getElementById('card-word').onclick = function(e) { e.stopPropagation(); speakWord(word.word); };
    document.getElementById('card-word').style.cursor = 'pointer';
     document.getElementById('card-word-small').textContent = word.word;
    document.getElementById('card-word-small').onclick = function(e) { e.stopPropagation(); speakWord(word.word); };
    document.getElementById('card-word-small').style.cursor = 'pointer';
     document.getElementById('card-definition').textContent = word.definition;
     document.getElementById('card-pos').textContent = word.pos || '';
     document.getElementById('card-notes').textContent = word.notes || '';
     // 显示日语汉字
     const kanjiEl = document.getElementById('card-kanji');
     if (word.kanji) { kanjiEl.textContent = word.kanji; kanjiEl.style.display = 'inline-block'; }
     else { kanjiEl.style.display = 'none'; }
     // 模式徽章
     const modeBadge = document.getElementById('card-mode-badge');
     const modeNames = { normal: '每日', wrong: '错题', all: '全词', learn: '学习' };
     modeBadge.textContent = modeNames[this.currentMode] || '';
     const reps = word.reps || 0;
     const infoParts = [];
     if (reps > 0) { infoParts.push(`复习次数: ${reps}`); infoParts.push(`难度: ${(word.difficulty || 5).toFixed(1)}`); }
     else { infoParts.push('新词'); }
     document.getElementById('card-info').textContent = infoParts.join(' | ');
     this.updateSessionStatus();
     this.updateProgress();
   },
 
   flipCard() {
     if (this.isCardFlipped || !this.currentWord) return;
     document.getElementById('flashcard').classList.add('flipped');
     this.isCardFlipped = true;
     const reps = this.currentWord.reps || 0;
     if (reps === 0) this.newCount++;
     else this.reviewedCount++;
   },
 
   async submitRating(rating) {
     if (!this.isCardFlipped || !this.currentWord) return;
     const wordId = this.currentWord.id;
     try {
       const endpoint = this.currentMode === 'wrong' ? '/study/wrong-review' : '/study/review';
       await api(endpoint, { method: 'POST', body: JSON.stringify({ word_id: wordId, rating }) });
       this.currentIndex++;
       this.isCardFlipped = false;
       this.showCurrentCard();
       refreshStats();
       updateDueBadge();
     } catch (e) { showToast('提交复习失败: ' + e.message, 'error'); }
   },
 
   endSession() {
     this.isSessionActive = false;
     this.isCardFlipped = false;
     this.currentWord = null;
     document.getElementById('flashcard').style.display = 'none';
     document.getElementById('session-info').style.display = 'none';
     document.getElementById('card-placeholder').style.display = 'block';
     const totalDone = this.reviewedCount + this.newCount;
     document.getElementById('placeholder-text').textContent = totalDone > 0
       ? `学习完成！本次学习了 ${totalDone} 个词（复习 ${this.reviewedCount}，新学 ${this.newCount}）`
       : '学习已结束';
     document.getElementById('btn-start-study').textContent = '开始学习';
     if (totalDone > 0) showToast(`学习完成！共 ${totalDone} 个词`, 'success');
   },
 
   updateSessionStatus() {
     const total = this.sessionCards.length;
     const remaining = total - this.currentIndex;
     document.getElementById('session-status').textContent = `学习中... (新词: ${this.newCount} | 复习: ${this.reviewedCount} | 剩余: ${remaining})`;
   },
 
   updateProgress() {
     const total = this.sessionCards.length;
     const done = this.currentIndex;
     document.getElementById('progress-fill').style.width = total > 0 ? `${done / total * 100}%` : '0%';
   },
 
   async saveSettings() {
     const val = document.getElementById('daily-new-input').value;
     try {
       await api('/settings', { method: 'PUT', body: JSON.stringify({ daily_new: parseInt(val) || 20 }) });
       showToast('设置已保存');
     } catch (e) { showToast('保存设置失败: ' + e.message, 'error'); }
   },
 };
 
 function shuffleArray(arr) {
   for (let i = arr.length - 1; i > 0; i--) {
     const j = Math.floor(Math.random() * (i + 1));
     [arr[i], arr[j]] = [arr[j], arr[i]];
   }
   return arr;
 }
 

// Card events handled in app.js
window.study = study;
 window.shuffleArray = shuffleArray;
