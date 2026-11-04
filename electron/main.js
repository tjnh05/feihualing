// Electron 主进程：只是把仓库里那一份 index.html 装进窗口，不含任何玩法代码。
// 判断依据只有一条——这个壳一旦需要写第二份逻辑，它就该被删掉（tkinter 桌面版就是这么归档的）。
const { app, BrowserWindow, Menu, shell } = require('electron');
const path = require('path');

// 开发态（npm start）下 macOS 菜单会显示「Electron」，先把名字改对
app.setName('诗词飞花令');

function createWindow(){
  const win = new BrowserWindow({
    width: 1280,
    height: 850,
    // 800×680 是原来 tkinter 桌面版实测出来的下限：宽度低于 800 会把右侧规则栏的
    // 三个下拉挤出窗外，高度低于 680 时对话区会被压到只剩十几像素
    minWidth: 800,
    minHeight: 680,
    title: '诗词飞花令 · 人机对战',
    icon: path.join(__dirname, '../build/icon.png'),
    backgroundColor: '#f6efe1',        // 页面那张纸的底色，免得开窗时先闪一下白
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  });

  // 非 macOS 隐藏菜单栏：这是个全屏对局窗口，留着 File/Edit 只是让人误点
  //（macOS 保留系统菜单，否则没有 Cmd+Q / Cmd+C 这些标准快捷键）
  if(process.platform !== 'darwin'){
    win.setMenuBarVisibility(false);
    Menu.setApplicationMenu(null);
  }

  // 走 file:// 而不是起本地服务：页面里那段百度统计按 location.protocol 判协议，
  // 这个壳因此天然不发统计请求——桌面使用不该混进网站报表，也守住「本地版零请求」那条底线
  win.loadFile(path.join(__dirname, '../index.html'));

  // 页面里没有任何可点的外链（作者与出处都是文字标注），这两条只是兜底：
  // 真有人从别处塞进来一个 http 链接，交给系统浏览器，不在桌面窗口里开
  win.webContents.setWindowOpenHandler(({ url }) => {
    if(/^https?:/.test(url)) shell.openExternal(url);
    return { action: 'deny' };
  });
  win.webContents.on('will-navigate', (e, url) => {
    if(!url.startsWith('file://')) e.preventDefault();
  });
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    // macOS 点 Dock 图标时窗口已经被关掉了，重建一个
    if(BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if(process.platform !== 'darwin') app.quit();
});
