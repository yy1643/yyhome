/* ============================================
   YY · 视频创作者主页 — 交互脚本
   ============================================ */

/**
 * 切换页面视图（首页 / 作品 / 想法 / 联系）
 * @param {string} id - 视图标识：'home' | 'works' | 'ideas' | 'contact'
 * @param {HTMLElement} [button] - 触发按钮元素（可选）
 */
function showView(id, button) {
  // 隐藏所有视图
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));

  if (id === 'home') {
    // 首页：显示 hero + 项目 + 动态
    document.querySelector('.shell > .hero').style.display = 'grid';
    document.querySelectorAll('.shell > .section-title, .shell > .grid, .shell > .activity')
      .forEach(e => e.style.display = '');
  } else {
    // 其他页：隐藏首页内容，显示对应视图
    document.querySelector('.shell > .hero').style.display = 'none';
    document.querySelectorAll('.shell > .section-title, .shell > .grid, .shell > .activity')
      .forEach(e => e.style.display = 'none');
    document.getElementById(id).classList.add('active');
  }

  // 更新 Dock 按钮激活状态
  document.querySelectorAll('.dock button').forEach(b => b.classList.remove('active'));
  (button || document.querySelector('[data-view="' + id + '"]'))?.classList.add('active');

  // 滚动到顶部
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/**
 * 复制文本到剪贴板
 * @param {string} text - 要复制的文本
 */
function copyText(text) {
  navigator.clipboard?.writeText(text);
  alert('微信号已复制：' + text);
}
