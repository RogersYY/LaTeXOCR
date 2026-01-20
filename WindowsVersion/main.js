const {
  app,
  BrowserWindow,
  ipcMain,
  globalShortcut,
  Tray,
  Menu,
  dialog,
  powerMonitor
} = require('electron');
const path = require('path');
const fs = require('fs');

const APP_DIR_NAME = 'LaTeXOCR-Windows';
const DEFAULT_SETTINGS = {
  apiBaseURL: '',
  apiKey: '',
  apiModel: 'gpt-5.2',
  apiModelCustom: '',
  copyFormat: 'latex'
};

let mainWindow;
let tray;
let registeredShortcut = '';

const isWindows = process.platform === 'win32';
const SCREENSHOT_ACCELERATORS = isWindows
  ? ['Control+Shift+A', 'CommandOrControl+Shift+A', 'Ctrl+Alt+A']
  : ['CommandOrControl+Shift+A'];

if (!app.requestSingleInstanceLock()) {
  app.quit();
  process.exit(0);
}

const getDataDir = () => {
  const portableDir = process.env.PORTABLE_EXECUTABLE_DIR;
  const base = portableDir ? path.join(portableDir, APP_DIR_NAME) : app.getPath('userData');
  if (!fs.existsSync(base)) {
    fs.mkdirSync(base, { recursive: true });
  }
  return base;
};

const getSettingsPath = () => path.join(getDataDir(), 'settings.json');

const createWindow = () => {
  mainWindow = new BrowserWindow({
    width: 1100,
    height: 720,
    minWidth: 780,
    minHeight: 520,
    backgroundColor: '#0f1014',
    title: 'LaTeXOCR - Windows',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  });

  mainWindow.loadFile(path.join(__dirname, 'index.html'));
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
};

const sendToRenderer = (channel, payload) => {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  const deliver = () => mainWindow.webContents.send(channel, payload);
  if (mainWindow.webContents.isLoading()) {
    mainWindow.webContents.once('did-finish-load', deliver);
  } else {
    deliver();
  }
};

const setupTray = () => {
  const iconPath = path.join(__dirname, 'build', 'icon.png');
  tray = new Tray(iconPath);
  const menu = Menu.buildFromTemplate([
    {
      label: '打开主窗口',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      }
    },
    {
      label: '截图识别 (Ctrl+Shift+A)',
      click: () => {
        if (mainWindow) {
          mainWindow.webContents.send('global-shortcut-screenshot');
          mainWindow.show();
          mainWindow.focus();
        }
      }
    },
    { type: 'separator' },
    {
      label: '退出',
      role: 'quit'
    }
  ]);
  tray.setContextMenu(menu);
  tray.setToolTip('LaTeXOCR - Windows');
};

const registerShortcuts = () => {
  globalShortcut.unregisterAll();
  registeredShortcut = '';

  for (const accelerator of SCREENSHOT_ACCELERATORS) {
    const ok = globalShortcut.register(accelerator, () => {
      if (mainWindow) {
        mainWindow.webContents.send('global-shortcut-screenshot');
        mainWindow.show();
        mainWindow.focus();
      }
    });

    if (ok) {
      registeredShortcut = accelerator;
      break;
    }
  }

  if (!registeredShortcut) {
    console.warn(
      `Global shortcut 注册失败，尝试过: ${SCREENSHOT_ACCELERATORS.join(', ')}，可能被其他应用占用`
    );
    sendToRenderer('shortcut-registration-failed');
    return;
  }

  sendToRenderer('shortcut-registered', registeredShortcut);
};

ipcMain.handle('load-settings', async () => {
  try {
    const raw = await fs.promises.readFile(getSettingsPath(), 'utf8');
    const parsed = JSON.parse(raw);
    return { ...DEFAULT_SETTINGS, ...parsed };
  } catch (err) {
    return { ...DEFAULT_SETTINGS };
  }
});

ipcMain.handle('save-settings', async (_event, payload) => {
  const merged = { ...DEFAULT_SETTINGS, ...(payload || {}) };
  try {
    await fs.promises.mkdir(path.dirname(getSettingsPath()), { recursive: true });
    await fs.promises.writeFile(getSettingsPath(), JSON.stringify(merged, null, 2), 'utf8');
  } catch (err) {
    console.error('Failed to persist settings', err);
  }
  return merged;
});

ipcMain.handle('select-image', async () => {
  const result = await dialog.showOpenDialog(mainWindow ?? null, {
    title: '选择一张包含公式的图片',
    properties: ['openFile'],
    filters: [
      { name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'bmp', 'gif', 'webp'] }
    ]
  });

  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }

  const filePath = result.filePaths[0];
  const ext = path.extname(filePath).replace('.', '') || 'png';
  const buffer = await fs.promises.readFile(filePath);
  return `data:image/${ext};base64,${buffer.toString('base64')}`;
});

app.whenReady().then(() => {
  app.setAppUserModelId('com.latexoocr.windows');
  createWindow();
  setupTray();
  registerShortcuts();

  powerMonitor.on('resume', () => {
    registerShortcuts();
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('second-instance', () => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) {
      mainWindow.restore();
    }
    mainWindow.show();
    mainWindow.focus();
    registerShortcuts();
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});
