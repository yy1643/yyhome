const git = require('isomorphic-git');
const fs = require('fs');
const path = require('path');
const http = require('isomorphic-git/http/node');

const DIR = __dirname;
const TOKEN = process.env.GH_TOKEN;
const REMOTE = 'origin';
const BRANCH = 'main';

async function run() {
  if (!TOKEN) {
    console.error('❌ 请设置环境变量 GH_TOKEN');
    process.exit(1);
  }

  // 1. 检查是否已有远程
  const remotes = await git.listRemotes({ fs, dir: DIR });
  const origin = remotes.find(r => r.remote === REMOTE);
  if (!origin) {
    console.error('❌ 未找到远程仓库 origin');
    process.exit(1);
  }
  console.log(`✅ 远程仓库: ${origin.url}`);

  // 2. 获取仓库状态，列出所有未跟踪/修改的文件
  const statusMatrix = await git.statusMatrix({ fs, dir: DIR });
  const changedFiles = statusMatrix.filter(([filepath, headStatus, workDirStatus, stageStatus]) => {
    // 过滤掉 .git 目录和 node_modules
    if (filepath.startsWith('.git/') || filepath.startsWith('node_modules/')) return false;
    return headStatus !== workDirStatus || workDirStatus !== stageStatus;
  });

  if (changedFiles.length === 0) {
    console.log('ℹ️  没有需要提交的文件');
  } else {
    console.log(`📦 待提交文件数: ${changedFiles.length}`);
    for (const [f] of changedFiles) console.log(`   · ${f}`);
  }

  // 3. 添加所有文件
  console.log('\n📝 添加文件到暂存区...');
  const files = getAllFiles(DIR).filter(f => {
    if (f.startsWith('.git' + path.sep) || f.startsWith('node_modules' + path.sep) || f.startsWith('.reasonix' + path.sep)) return false;
    return true;
  });
  for (const filepath of files) {
    await git.add({ fs, dir: DIR, filepath });
  }
  console.log(`✅ 已添加 ${files.length} 个文件`);

  // 4. 提交
  console.log('\n💾 创建提交...');
  const sha = await git.commit({
    fs,
    dir: DIR,
    author: { name: 'yy1643', email: 'yy1643@users.noreply.github.com' },
    message: 'Initial commit - sync from local workspace'
  });
  console.log(`✅ 提交成功: ${sha}`);

  // 5. 推送
  console.log('\n📤 推送到 GitHub...');
  const remoteUrl = origin.url.replace('https://', `https://${TOKEN}@`);
  
  await git.push({
    fs,
    http,
    dir: DIR,
    remote: REMOTE,
    ref: BRANCH,
    url: remoteUrl,
    force: true,
    onAuth: () => ({ username: TOKEN, password: '' }),
    onMessage: (msg) => console.log(`   > ${msg}`),
  });

  console.log('\n🎉 推送成功！');
  console.log(`🌐 查看: ${origin.url.replace('.git', '')}`);
}

function getAllFiles(dirPath, arrayOfFiles = []) {
  const entries = fs.readdirSync(dirPath, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dirPath, entry.name);
    const relativePath = path.relative(DIR, fullPath);
    if (entry.name === '.git' || entry.name === 'node_modules' || entry.name === '.reasonix') continue;
    if (entry.isDirectory()) {
      getAllFiles(fullPath, arrayOfFiles);
    } else {
      arrayOfFiles.push(relativePath);
    }
  }
  return arrayOfFiles;
}

run().catch(err => {
  console.error('❌ 失败:', err.message);
  process.exit(1);
});
