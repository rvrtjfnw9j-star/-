 /**
  * 操作台 - 统计模块
  * 预留扩展点。
  */
 
 const statsModule = {
   refresh() { if (typeof refreshStats === 'function') refreshStats(); },
   async getDetails() {
     try { return await api('/stats'); }
     catch (e) { showToast('获取统计失败', 'error'); return null; }
   },
 };
 
 window.statsModule = statsModule;
