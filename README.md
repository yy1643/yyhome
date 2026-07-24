# YY · 视频创作者个人主页 🎬

> 用镜头记录真实，用剪辑讲好故事。

这是视频创作者 **YY** 的个人品牌网站，包含个人简介、作品集、创作想法、联系方式，以及自主研发的 **YY 音频助手** App 下载页。

## 📄 页面一览

| 页面 | 文件 | 说明 |
|------|------|------|
| 🏠 首页 | `index.html` | 个人资料卡、项目进展、最近动态 |
| 🎨 作品集 | `works.html` | 作品展示，含 App 入口卡片 |
| 📱 **App 下载** | **`app.html`** | **YY 音频助手 — 可直接分享给家人** |
| 💡 想法 | `ideas.html` | 创作心得与笔记 |
| 📬 联系我 | `contact.html` | 微信、邮箱、Bilibili |

## 📱 YY 音频助手

这是我用 AI 开发的第一款 Android 软件，目标人群是中老年朋友。

**功能：** 视频一键转换为音频，自动保存到 U 盘

**特点：**
- 🎬 视频转音频 — 支持常见视频格式，保留原声质量
- 💾 一键存 U 盘 — 插上 U 盘自动识别，转换后直接保存
- 👴 大字大按钮 — 专为中老年人优化，操作步骤简单明了
- 📱 轻量小巧 — 安装包不到 80MB，老手机也能流畅运行

**下载地址：** [`https://download.164355.xyz/yyapp.apk`](https://download.164355.xyz/yyapp.apk)

## 🛠️ 技术栈

- **纯静态 HTML + CSS + JavaScript** — 无框架依赖
- **毛玻璃（Glassmorphism）UI** 设计风格
- **深色/浅色主题切换**
- **响应式布局** — 适配手机、平板、桌面
- **Cloudflare Pages** — 网站托管
- **Cloudflare R2** — APK 文件分发

## 🚀 部署

本站通过 Cloudflare Pages 自动部署，连接 GitHub 仓库后，推送代码即可自动更新。

### 本地预览

直接在浏览器打开各 HTML 文件即可：

```bash
open index.html    # 首页
open app.html      # App 下载页
open works.html    # 作品集
open ideas.html    # 想法
open contact.html  # 联系我
```

### 部署到 Cloudflare Pages

1. 将代码推送到 GitHub 仓库
2. 在 Cloudflare 控制台 → **Workers & Pages** → **Connect to Git**
3. 选择仓库，构建设置保持默认（输出目录 `/`）
4. 绑定自定义域名 `164355.xyz`

## 📁 项目结构

```
├── index.html      # 首页
├── app.html        # YY 音频助手下载页
├── works.html      # 作品集
├── ideas.html      # 一些想法
├── contact.html    # 联系我
├── styles.css      # 全局样式表
├── script.js       # 交互脚本（微信号复制）
├── yyapp.apk       # Android 安装包
└── README.md       # 本文件
```

## 📬 联系

- 微信：`17774548253`
- 邮箱：`yy1643558990@gmail.com`
- Bilibili：[space.bilibili.com/35623313](https://space.bilibili.com/35623313)

---

**让每一帧画面，都有值得被记住的情绪。** — YY
