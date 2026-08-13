const git = require('isomorphic-git');
const fs = require('fs');
const path = require('path');
const http = require('isomorphic-git/http/node');

const DIR = __dirname;
const TOKEN = process.env.GH_TOKEN;
const REMOTE = 'origin';
const BRANCH = 'main';
const REMOTE_URL = 'https://github.com/yy1643/yyhome.git';

// 需要排除的目录（正斜杠路径）
const EXCLUDES = ['.git', 'node_modules', '.reasonix'];

async function run() {
  if (!TOKEN) {
    console.error('请设置环境变量 GH_TOKEN');
    process.exit(1);
  }

  // 1. 初始化仓库（若 .git 不存在）
  if (!fs.existsSync(path.join(DIR, '.git'))) {
    console.log('初始化新仓库...');
    await git.init({ fs, dir: DIR, defaultBranch: BRANCH });
    await git.addRemote({ fs, dir: DIR, remote: REMOTE, url: REMOTE_URL });
    console.log('已添加远程:', REMOTE_URL);
  }

  // 2. 列出所有文件（统一正斜杠路径）
  const files = listAllFiles(DIR);
  console.log(`共 ${files.length} 个文件待处理`);

  // 3. 逐个 add（正斜杠路径）
  for (const filepath of files) {
    await git.add({ fs, dir: DIR, filepath });
  }
  console.log('全部文件已加入暂存区');

  // 4. 检查是否有待提交变更；无变化则跳过提交，直接推送
  const statusMatrix = await git.statusMatrix({ fs, dir: DIR });
  const hasChanges = statusMatrix.some(
    ([filepath, head, workdir, stage]) =>
      filepath.startsWith('.git') ? false : head !== workdir || workdir !== stage
  );

  if (hasChanges) {
    const sha = await git.commit({
      fs,
      dir: DIR,
      author: { name: 'yy1643', email: 'yy1643@users.noreply.github.com' },
      message: `sync: ${new Date().toISOString().slice(0, 16).replace('T', ' ')}`,
    });
    console.log('提交成功:', sha);
  } else {
    console.log('无文件变更，跳过提交，直接推送');
  }

  // 5. 强制推送
  console.log('推送到 GitHub...');
  await git.push({
    fs,
    http,
    dir: DIR,
    remote: REMOTE,
    ref: BRANCH,
    force: true,
    onAuth: () => ({ username: TOKEN, password: '' }),
    onMessage: (msg) => console.log('  >', msg),
  });
  console.log('推送成功! https://github.com/yy1643/yyhome');
}

// 递归列出所有文件，路径统一用正斜杠
function listAllFiles(dir, base = '') {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (EXCLUDES.includes(entry.name)) continue;
    const rel = base ? `${base}/${entry.name}` : entry.name;
    if (entry.isDirectory()) {
      out.push(...listAllFiles(path.join(dir, entry.name), rel));
    } else {
      out.push(rel);
    }
  }
  return out;
}

run().catch((err) => {
  console.error('失败:', err.message);
  process.exit(1);
});
