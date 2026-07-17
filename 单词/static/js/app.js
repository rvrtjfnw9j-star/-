const API_BASE = '/api';

async function api(path, options) {
  options = options || {};
  var url = API_BASE + path;
  var headers = { 'Content-Type': 'application/json' };
  if (options.headers) Object.assign(headers, options.headers);
  options.headers = headers;
  var r = await fetch(url, options);
  var d = await r.json();
  if (!r.ok) throw new Error(d.error || 'HTTP ' + r.status);
  return d;
}

function showToast(msg, type) {
  type = type || 'success';
  var c = document.querySelector('.toast-container');
  if (!c) { c = document.createElement('div'); c.className = 'toast-container'; document.body.appendChild(c); }
  var t = document.createElement('div');
  t.className = 'toast toast-' + type;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(function() {
    t.style.opacity = '0';
    t.style.transform = 'translateX(40px)';
    setTimeout(function() { t.remove(); }, 300);
  }, 2500);
}

function openModal(title, html) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = html;
  document.getElementById('modal-overlay').style.display = 'flex';
}

function closeModal(e) {
  if (e && e.target !== document.getElementById('modal-overlay')) return;
  document.getElementById('modal-overlay').style.display = 'none';
}

async function refreshStats() {
  try {
    var data = await api('/stats/enhanced');
    var stats = data.base_stats || {};
    var targets = {
      'stat-total': data.total_words || 0,
      'stat-mastered': data.mastered_words || 0,
      'stat-wrong-count': data.wrong_count || 0,
      'stat-total-reviews': data.total_reviews || 0,
      'stat-today-new': stats.today_new || 0,
      'stat-today-review': stats.today_review || 0,
      'stat-due-today': stats.due_today || 0,
    };
    Object.keys(targets).forEach(function(id) {
      var el = document.getElementById(id);
      if (el && typeof animateNumber === 'function') animateNumber(el, targets[id]);
    });
    var erEl = document.getElementById('stat-error-rate');
    if (erEl) erEl.textContent = ((data.error_rate || 0) * 100).toFixed(1) + '%';
    var taEl = document.getElementById('stat-today-accuracy');
    if (taEl) taEl.textContent = ((data.today_accuracy || 0) * 100).toFixed(1) + '%';
    if (typeof refreshBadge === 'function') refreshBadge(data);
    var dc = document.getElementById('due-count-badge');
    if (dc) dc.textContent = '待复习: ' + (stats.due_today || 0);
    return data;
  } catch(e) {}
}

async function updateDueBadge() {
  try {
    var s = await api('/stats');
    var dc = document.getElementById('due-count-badge');
    if (dc) dc.textContent = '待复习: ' + (s.due_today || 0);
  } catch(e) {}
}

async function loadSettings() {
  try {
    var s = await api('/settings');
    var inp = document.getElementById('daily-new-input');
    if (inp) inp.value = s.daily_new || 20;
  } catch(e) { showToast('加载设置失败', 'error'); }
}

async function loadCharts() {
  try {
    var curve = await api('/stats/forgetting-curve');
    if (typeof renderForgettingChart === 'function') renderForgettingChart(curve.data || []);
  } catch(e) {}
  try {
    var pressure = await api('/stats/review-pressure');
    if (typeof renderPressureChart === 'function') renderPressureChart(pressure || []);
  } catch(e) {}
}

document.addEventListener('DOMContentLoaded', function() {
  if (typeof loadTheme === 'function') loadTheme();
  refreshStats();
  if (typeof wordManager !== 'undefined' && wordManager.loadWords) wordManager.loadWords();
  updateDueBadge();

  document.querySelectorAll('.nav-item').forEach(function(item) {
    item.addEventListener('click', function() {
      document.querySelectorAll('.nav-item').forEach(function(n) { n.classList.remove('active'); });
      document.querySelectorAll('.tab-content').forEach(function(t) { t.classList.remove('active'); });
      item.classList.add('active');
      var tab = item.dataset.tab;
      document.getElementById('tab-' + tab).classList.add('active');
      if (tab === 'stats') { refreshStats(); }
      if (tab === 'library') { if (typeof wordManager !== 'undefined') wordManager.loadWords(); }
      if (tab === 'study') updateDueBadge();
      if (tab === 'settings') loadSettings();
    });
  });

  document.addEventListener('keydown', function(e) {
    var tag = (e.target.tagName || '').toUpperCase();
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
    if (e.key === ' ' || e.key === 'Space') { e.preventDefault(); if (typeof study !== 'undefined') study.flipCard(); }
    if (e.key === '1' && typeof study !== 'undefined') study.submitRating(1);
    if (e.key === '2' && typeof study !== 'undefined') study.submitRating(2);
    if (e.key === '3' && typeof study !== 'undefined') study.submitRating(3);
    if (e.key === '4' && typeof study !== 'undefined') study.submitRating(4);
  });

  var flashcard = document.getElementById('flashcard');
  if (flashcard) {
    flashcard.addEventListener('click', function(e) {
      if (e.target.closest('.card-rating')) return;
      if (typeof study !== 'undefined') study.flipCard();
    });
  }
  document.querySelectorAll('.rating-btn').forEach(function(btn) {
    btn.addEventListener('click', function(e) {
      e.stopPropagation();
      if (typeof study !== 'undefined') study.submitRating(parseInt(btn.dataset.rating));
    });
  });
});

window.api = api;
window.showToast = showToast;
window.openModal = openModal;
window.closeModal = closeModal;
window.refreshStats = refreshStats;
window.updateDueBadge = updateDueBadge;
window.loadSettings = loadSettings;
// Charts disabled