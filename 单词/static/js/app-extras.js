function toggleDarkMode() {
  var h = document.documentElement;
  var d = h.getAttribute('data-theme') === 'dark';
  h.setAttribute('data-theme', d ? '' : 'dark');
  localStorage.setItem('theme', d ? 'light' : 'dark');
  var el = document.getElementById('dark-toggle-text');
  if (el) el.textContent = d ? '深色模式' : '浅色模式';
}
function loadTheme() {
  var s = localStorage.getItem('theme');
  if (s === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
    var el = document.getElementById('dark-toggle-text');
    if (el) el.textContent = '浅色模式';
  }
}
function speakWord(text) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  var u = new SpeechSynthesisUtterance(text);
  u.lang = 'en-US'; u.rate = 0.9;
  window.speechSynthesis.speak(u);
}
function fireConfetti() {
  var colors = ['#6c5ce7','#00b894','#fdcb6e','#ff6b6b','#74b9ff','#fd79a8'];
  for (var i = 0; i < 40; i++) {
    (function(){
      var el = document.createElement('div');
      el.style.cssText = 'position:fixed;width:8px;height:8px;border-radius:50%;pointer-events:none;z-index:9999;opacity:1;';
      el.style.background = colors[Math.floor(Math.random() * colors.length)];
      el.style.left = Math.random() * window.innerWidth + 'px';
      el.style.top = '-10px';
      document.body.appendChild(el);
      var x = (Math.random() - 0.5) * 300;
      var y = 400 + Math.random() * 300;
      var rot = Math.random() * 720;
      requestAnimationFrame(function(){
        el.style.transition = 'transform 1.2s cubic-bezier(0.25,0.46,0.45,0.94), opacity 1.2s ease';
        el.style.transform = 'translate(' + x + 'px,' + y + 'px) rotate(' + rot + 'deg)';
        el.style.opacity = '0';
      });
      setTimeout(function() { el.remove(); }, 1500);
    })();
  }
}
function animateNumber(el, target, dur) {
  dur = dur || 800;
  var start = parseInt(el.textContent.replace(/[^0-9.]/g, '')) || 0;
  var suffix = el.textContent.replace(/[0-9.]/g, '');
  var diff = target - start;
  if (diff === 0) return;
  var t0 = performance.now();
  function step(now) {
    var p = Math.min((now - t0) / dur, 1);
    var e = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.round(start + diff * e) + suffix;
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}


function refreshBadge(data) {
  var wc = data.wrong_count || 0;
  var wcb = document.getElementById('wrong-count-badge');
  if (wcb) wcb.textContent = '错题: ' + wc;
  var wcs = document.getElementById('wrong-count-small');
  if (wcs) wcs.textContent = wc;
  var pt = document.getElementById('progress-text');
  var stats = data.base_stats || {};
  if (pt) pt.textContent = '今日进度: ' + ((stats.today_new||0)+(stats.today_review||0)) + ' 次';
  var lc = document.getElementById('lang-bars');
  if (stats.languages && lc) {
    var langTotal = 0;
    for (var k in stats.languages) langTotal += stats.languages[k];
    var html = '';
    for (var k in stats.languages) {
      var count = stats.languages[k];
      var pct = langTotal > 0 ? (count / langTotal * 100) : 0;
      var label = k === 'en' ? '英语' : k === 'ja' ? '日语' : k;
      html += '<div class="lang-bar-wrap"><span class="lang-bar-label">' + label + '</span><div class="lang-bar-track"><div class="lang-bar-fill" style="width:' + pct + '%"></div></div><span class="lang-bar-count">' + count + '</span></div>';
    }
    lc.innerHTML = html;
  }
}

window.toggleDarkMode = toggleDarkMode;
window.loadTheme = loadTheme;
window.speakWord = speakWord;
window.fireConfetti = fireConfetti;
window.animateNumber = animateNumber;
// renderForgettingChart;
// renderPressureChart;
window.refreshBadge = refreshBadge;