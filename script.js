/* ============================================
   YY · 视频创作者主页 — 交互脚本
   ============================================ */

const THEME_KEY = 'yy-theme';

function getSavedTheme() {
  try {
    return localStorage.getItem(THEME_KEY);
  } catch {
    return null;
  }
}

function saveTheme(theme) {
  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch {
    // Theme persistence is optional when storage is unavailable.
  }
}

function applyTheme(theme) {
  const isNight = theme === 'night';
  document.body.classList.toggle('night', isNight);
  document.documentElement.style.colorScheme = isNight ? 'dark' : 'light';

  const themeColor = document.querySelector('meta[name="theme-color"]');
  if (themeColor) themeColor.setAttribute('content', isNight ? '#172331' : '#dce6ef');

  document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
    button.setAttribute('aria-pressed', String(isNight));
    button.setAttribute('title', isNight ? '切换到浅色模式' : '切换到深色模式');
  });
}

function toggleTheme() {
  const nextTheme = document.body.classList.contains('night') ? 'light' : 'night';
  applyTheme(nextTheme);
  saveTheme(nextTheme);
}

function fallbackCopy(text) {
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand('copy');
  textarea.remove();
  return copied;
}

async function copyText(text, button) {
  const label = button.querySelector('[data-copy-label]');
  const originalLabel = label?.textContent;

  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
    } else if (!fallbackCopy(text)) {
      throw new Error('Clipboard API unavailable');
    }

    if (label) label.textContent = '已复制微信号';
  } catch {
    if (label) label.textContent = '复制失败，请手动复制';
  }

  window.setTimeout(() => {
    if (label && originalLabel) label.textContent = originalLabel;
  }, 2200);
}

document.addEventListener('DOMContentLoaded', () => {
  const savedTheme = getSavedTheme();
  const preferredTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'night'
    : 'light';

  applyTheme(savedTheme || preferredTheme);

  document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
    button.addEventListener('click', toggleTheme);
  });

  document.querySelectorAll('[data-copy-text]').forEach((button) => {
    button.addEventListener('click', () => copyText(button.dataset.copyText, button));
  });
});
