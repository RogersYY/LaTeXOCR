const electron = require('electron');
const { contextBridge, ipcRenderer, desktopCapturer, clipboard } = electron;

const getScreenModule = () => electron.screen;

const DEFAULT_THUMBNAILS = [
  { width: 0, height: 0 },
  { width: 1920, height: 1080 },
  { width: 1280, height: 720 }
];

const getThumbnailSizes = (primary) => {
  if (!primary || !primary.size) {
    return DEFAULT_THUMBNAILS.slice();
  }
  const { width, height } = primary.size;
  const scaleFactor = primary.scaleFactor || 1;
  const scaled = {
    width: Math.max(1, Math.floor(width * scaleFactor)),
    height: Math.max(1, Math.floor(height * scaleFactor))
  };
  const capped = {
    width: Math.min(scaled.width, 1920),
    height: Math.min(scaled.height, 1080)
  };
  const sizes = [scaled, ...DEFAULT_THUMBNAILS, capped];
  const seen = new Set();
  return sizes.filter((size) => {
    const key = `${size.width}x${size.height}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

const pickLargestSource = (sources) => {
  if (!sources?.length) return null;
  return sources.reduce((best, source) => {
    const size = source.thumbnail?.getSize?.() || { width: 0, height: 0 };
    const area = size.width * size.height;
    const bestSize = best?.thumbnail?.getSize?.() || { width: 0, height: 0 };
    const bestArea = bestSize.width * bestSize.height;
    return area > bestArea ? source : best;
  }, sources[0]);
};

const pickPrimarySource = (sources, primary) => {
  if (!sources?.length) return null;
  if (primary?.id != null) {
    return (
      sources.find((source) => source.display_id === String(primary.id)) ||
      sources.find((source) => source.id?.startsWith('screen:')) ||
      pickLargestSource(sources)
    );
  }
  return pickLargestSource(sources);
};

async function captureScreen() {
  try {
    const screenModule = getScreenModule();
    const primary = screenModule?.getPrimaryDisplay?.();
    const sizes = getThumbnailSizes(primary);
    let lastError = null;

    for (const thumbSize of sizes) {
      try {
        const sources = await desktopCapturer.getSources({
          types: ['screen'],
          thumbnailSize: thumbSize
        });

        const primarySource = pickPrimarySource(sources, primary);
        if (!primarySource || !primarySource.thumbnail || primarySource.thumbnail.isEmpty?.()) {
          throw new Error('无法获取屏幕图像');
        }
        return primarySource.thumbnail.toDataURL();
      } catch (error) {
        lastError = error;
      }
    }

    console.error('[captureScreen] 失败:', lastError);
    throw lastError || new Error('无法获取屏幕图像');
  } catch (error) {
    console.error('[captureScreen] 失败:', error);
    throw error;
  }
}

contextBridge.exposeInMainWorld('electronAPI', {
  captureScreen,
  selectImage: () => ipcRenderer.invoke('select-image'),
  loadSettings: () => ipcRenderer.invoke('load-settings'),
  saveSettings: (settings) => ipcRenderer.invoke('save-settings', settings),
  onGlobalScreenshot: (callback) => ipcRenderer.on('global-shortcut-screenshot', callback),
  removeGlobalScreenshot: (callback) => ipcRenderer.removeListener('global-shortcut-screenshot', callback),
  onShortcutRegistered: (callback) => ipcRenderer.on('shortcut-registered', (_e, acc) => callback(acc)),
  onShortcutFailed: (callback) => ipcRenderer.on('shortcut-registration-failed', callback),
  writeClipboard: ({ text, html }) => {
    const payload = {};
    if (text) payload.text = text;
    if (html) payload.html = html;
    clipboard.write(payload);
  }
});
