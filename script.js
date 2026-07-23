/* ============================================
   YY · 视频创作者主页 — 交互脚本
   ============================================ */

/**
 * 复制文本到剪贴板
 * @param {string} text - 要复制的文本
 */
function copyText(text) {
  navigator.clipboard?.writeText(text);
  alert('微信号已复制：' + text);
}
