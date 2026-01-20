const state = {
  imageDataUrl: '',
  latex: '',
  mathml: '',
  settings: {
    apiBaseURL: '',
    apiKey: '',
    apiModel: 'gpt-5.2',
    apiModelCustom: '',
    copyFormat: 'latex'
  },
  isLoading: false
};

const els = {};

const removeLatexMarkers = (input) => {
  if (!input) return '';
  const withoutFence = input.replace(/```latex\n?|```/g, '');
  const trimmed = withoutFence.trim();
  if (trimmed.startsWith('\\[') && trimmed.endsWith('\\]')) {
    return trimmed.slice(2, -2).trim();
  }
  if (trimmed.startsWith('$$') && trimmed.endsWith('$$')) {
    return trimmed.slice(2, -2).trim();
  }
  return trimmed;
};

const extractPureMathML = (htmlString) => {
  try {
    const mathMatch = htmlString.match(/<math[^>]*>([\s\S]*?)<\/math>/);
    if (!mathMatch || !mathMatch[0]) return '';
    let mathmlString = mathMatch[0];
    const semanticsStartIndex = mathmlString.indexOf('<semantics>');
    if (semanticsStartIndex !== -1) {
      const beforeSemantics = mathmlString.substring(0, semanticsStartIndex);
      const mrowMatch = mathmlString.match(/<semantics>([\s\S]*?)<annotation/);
      if (mrowMatch && mrowMatch[1]) {
        return `${beforeSemantics}${mrowMatch[1]}</math>`;
      }
    }
    return mathmlString;
  } catch (error) {
    console.error('MathML 提取错误:', error);
    return '';
  }
};

const generateMathML = (latex) => {
  try {
    const html = window.katex.renderToString(latex || '', {
      output: 'mathml',
      throwOnError: false
    });
    return extractPureMathML(html);
  } catch (err) {
    console.error('MathML render error', err);
    return '';
  }
};

const debounce = (fn, delay = 300) => {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
};

const formatCaptureError = (err) => {
  if (!err) return '';
  return err.message || err.name || String(err);
};

const captureWithFallback = async () => {
  // 优先使用 Electron 的 desktopCapturer
  let electronError = null;
  if (window.electronAPI?.captureScreen) {
    try {
      const shot = await window.electronAPI.captureScreen();
      if (shot) return shot;
    } catch (err) {
      console.warn('desktopCapturer 截图失败', err);
      electronError = err;
    }
  }

  // 浏览器备用方案（会弹出选择屏幕的提示）
  if (navigator.mediaDevices?.getDisplayMedia) {
    let stream;
    try {
      stream = await navigator.mediaDevices.getDisplayMedia({
        video: { displaySurface: 'screen' },
        audio: false
      });
      const track = stream.getVideoTracks()[0];
      const settings = track.getSettings();
      const video = document.createElement('video');
      video.srcObject = stream;
      await video.play();
      const width = settings.width || video.videoWidth;
      const height = settings.height || video.videoHeight;
      const canvas = document.createElement('canvas');
      canvas.width = width || 1920;
      canvas.height = height || 1080;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      track.stop();
      return canvas.toDataURL('image/png');
    } catch (err) {
      if (electronError) {
        throw new Error(`桌面捕获失败：${formatCaptureError(electronError)}`);
      }
      throw err;
    } finally {
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
      }
    }
  }

  if (electronError) {
    throw new Error(`桌面捕获失败：${formatCaptureError(electronError)}`);
  }
  throw new Error('无法获取屏幕截图（浏览器接口不支持）');
};

const setStatus = (message, tone = 'muted') => {
  if (!els.statusLine) return;
  els.statusLine.textContent = message;
  els.statusLine.classList.remove('ok', 'warn', 'error');
  if (tone !== 'muted') {
    els.statusLine.classList.add(tone);
  }
};

const setLoading = (value) => {
  state.isLoading = value;
  if (els.loadingMask) {
    els.loadingMask.hidden = !value;
  }
  if (els.convertBtn) {
    els.convertBtn.disabled = value;
  }
};

const updateCopyFormatPill = () => {
  if (!els.copyFormatPill) return;
  const mode = state.settings.copyFormat === 'mathml' ? 'MathML (Word)' : 'LaTeX';
  els.copyFormatPill.textContent = `自动复制：${mode}`;
};

const updateMathMLPreview = () => {
  if (!els.mathmlPreview) return;
  if (!state.mathml) {
    els.mathmlPreview.textContent = '暂无';
    return;
  }
  const text = state.mathml.replace(/\s+/g, ' ').trim();
  els.mathmlPreview.textContent = text.length > 260 ? `${text.slice(0, 260)}…` : text;
};

const renderLatex = (latex) => {
  if (!els.katexOutput) return;
  els.katexOutput.innerHTML = '';
  const content = latex || '等待识别…';
  try {
    window.katex.render(content, els.katexOutput, {
      throwOnError: false,
      displayMode: true
    });
  } catch (err) {
    els.katexOutput.textContent = content;
  }
};

const updateResultViews = () => {
  renderLatex(state.latex);
  els.latexOutput.value = state.latex;
  state.mathml = state.latex ? generateMathML(state.latex) : '';
  updateMathMLPreview();
  els.resultHint.textContent = state.latex ? '已生成公式' : '等待识别…';
};

const setImagePreview = (dataUrl) => {
  state.imageDataUrl = dataUrl || '';
  els.imagePreview.innerHTML = '';
  if (!dataUrl) {
    els.imagePreview.classList.add('empty');
    els.imagePreview.innerHTML = '<div class="placeholder">暂无图片</div>';
    return;
  }
  els.imagePreview.classList.remove('empty');
  const img = document.createElement('img');
  img.src = dataUrl;
  img.alt = '待识别图片';
  els.imagePreview.appendChild(img);
};

const readSettingsFromForm = () => {
  const apiModel = els.apiModel.value;
  const base = {
    apiBaseURL: (els.apiBase.value || '').trim(),
    apiKey: (els.apiKey.value || '').trim(),
    apiModel,
    apiModelCustom: (els.apiModelCustom.value || '').trim(),
    copyFormat: els.copyFormat.value || 'latex'
  };
  return base;
};

const persistSettings = debounce(async () => {
  state.settings = readSettingsFromForm();
  await window.electronAPI.saveSettings(state.settings);
  updateCopyFormatPill();
  toggleCustomModelField();
}, 350);

const applySettingsToForm = () => {
  const { apiBaseURL, apiKey, apiModel, apiModelCustom, copyFormat } = state.settings;
  els.apiBase.value = apiBaseURL || '';
  els.apiKey.value = apiKey || '';
  els.apiModel.value = apiModel || 'gpt-5.2';
  els.apiModelCustom.value = apiModelCustom || '';
  els.copyFormat.value = copyFormat || 'latex';
  toggleCustomModelField();
  updateCopyFormatPill();
};

const toggleCustomModelField = () => {
  const shouldShow = els.apiModel.value === '其他';
  els.customModelField.hidden = !shouldShow;
};

const loadSettings = async () => {
  const loaded = await window.electronAPI.loadSettings();
  state.settings = { ...state.settings, ...loaded };
  applySettingsToForm();
};

const copyLatex = () => {
  if (!state.latex.trim()) {
    setStatus('暂无公式可复制', 'warn');
    return false;
  }
  window.electronAPI.writeClipboard({ text: state.latex });
  setStatus('已复制 LaTeX', 'ok');
  return true;
};

const copyMathML = () => {
  if (!state.mathml.trim()) {
    setStatus('MathML 为空，先生成或检查公式', 'warn');
    return false;
  }
  const html = `<html><body>${state.mathml}</body></html>`;
  window.electronAPI.writeClipboard({ text: state.mathml, html });
  setStatus('已复制 MathML', 'ok');
  return true;
};

const autoCopy = () => {
  if (state.settings.copyFormat === 'mathml') {
    if (!copyMathML()) {
      copyLatex();
    }
  } else {
    copyLatex();
  }
};

const performOCR = async () => {
  if (!state.imageDataUrl) {
    setStatus('请先选择图片或截图。', 'warn');
    return;
  }
  const { apiBaseURL, apiKey, apiModel, apiModelCustom } = state.settings;
  const model = apiModel === '其他' ? apiModelCustom.trim() : apiModel;
  if (!apiBaseURL || !apiKey || !model) {
    setStatus('请在右侧填写完整的 API 设置。', 'warn');
    return;
  }

  setLoading(true);
  setStatus('识别中…', 'muted');

  try {
    const base64 = state.imageDataUrl.includes(',')
      ? state.imageDataUrl.split(',')[1]
      : state.imageDataUrl;
    if (!base64) {
      setStatus('截图数据为空，请重试。', 'warn');
      return;
    }
    const payload = {
      model,
      messages: [
        {
          role: 'user',
          content: [
            {
              type: 'text',
              text: 'Please transcribe it into LaTeX format. please only return LaTeX formula without any other unuseful symbol, so I can patse it to my doc directly.'
            },
            {
              type: 'image_url',
              image_url: {
                url: `data:image/jpeg;base64,${base64}`
              }
            }
          ]
        }
      ]
    };

    const response = await fetch(apiBaseURL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const bodyText = await response.text();
      throw new Error(`API 错误 ${response.status}: ${bodyText}`);
    }

    const data = await response.json();
    const content = data?.choices?.[0]?.message?.content || '';
    state.latex = removeLatexMarkers(content);
    updateResultViews();
    autoCopy();
    setStatus('识别完成并已复制', 'ok');
  } catch (err) {
    console.error(err);
    setStatus(`识别失败：${err.message}`, 'error');
  } finally {
    setLoading(false);
  }
};

const selectImage = async () => {
  const dataUrl = await window.electronAPI.selectImage();
  if (!dataUrl) return;
  setImagePreview(dataUrl);
  setStatus('已载入图片，点击转换或截图继续。', 'ok');
};

const startScreenshotFlow = async () => {
  try {
    if (!window.electronAPI?.captureScreen && !navigator.mediaDevices?.getDisplayMedia) {
      setStatus('截图接口未加载，请重启应用', 'error');
      return;
    }
    setStatus('准备截图…', 'muted');
    const raw = await captureWithFallback();
    const cropped = await openCropOverlay(raw);
    if (!cropped) {
      setStatus('已取消截图', 'warn');
      return;
    }
    setImagePreview(cropped);
    setStatus('截图完成，自动开始识别…', 'ok');
    performOCR();
  } catch (err) {
    console.error(err);
    setStatus(`截图失败：${err.message || err}`, 'error');
  }
};

const openCropOverlay = (imageDataUrl) => {
  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.className = 'crop-overlay';
    overlay.tabIndex = -1;

    const img = document.createElement('img');
    img.src = imageDataUrl;
    let imageReady = false;
    img.onload = () => {
      imageReady = true;
    };

    const selection = document.createElement('div');
    selection.className = 'crop-selection';
    selection.style.display = 'none';

    const hint = document.createElement('div');
    hint.className = 'crop-hint';
    hint.textContent = '拖拽选择区域，Enter 确认，Esc 取消';

    const actions = document.createElement('div');
    actions.className = 'crop-actions';
    const confirmBtn = document.createElement('button');
    confirmBtn.className = 'btn primary';
    confirmBtn.textContent = '确认';
    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'btn ghost';
    cancelBtn.textContent = '取消';
    actions.append(confirmBtn, cancelBtn);

    overlay.append(img, selection, hint, actions);
    document.body.appendChild(overlay);
    overlay.focus();

    let start = null;
    let currentRect = null;

    const updateSelection = () => {
      if (!currentRect) {
        selection.style.display = 'none';
        return;
      }
      selection.style.display = 'block';
      selection.style.left = `${currentRect.x}px`;
      selection.style.top = `${currentRect.y}px`;
      selection.style.width = `${currentRect.width}px`;
      selection.style.height = `${currentRect.height}px`;
    };

    const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

    const crop = () => {
      if (!imageReady) return imageDataUrl;
      const bounds = img.getBoundingClientRect();
      const useFullImage = !currentRect || currentRect.width < 2 || currentRect.height < 2;
      const sx = useFullImage ? 0 : (currentRect.x - bounds.left) * (img.naturalWidth / bounds.width);
      const sy = useFullImage ? 0 : (currentRect.y - bounds.top) * (img.naturalHeight / bounds.height);
      const sWidth = useFullImage ? img.naturalWidth : currentRect.width * (img.naturalWidth / bounds.width);
      const sHeight = useFullImage ? img.naturalHeight : currentRect.height * (img.naturalHeight / bounds.height);

      const canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round(sWidth));
      canvas.height = Math.max(1, Math.round(sHeight));
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, sx, sy, sWidth, sHeight, 0, 0, canvas.width, canvas.height);
      return canvas.toDataURL('image/png');
    };

    const cleanup = (result) => {
      overlay.removeEventListener('pointerdown', onPointerDown);
      overlay.removeEventListener('pointermove', onPointerMove);
      overlay.removeEventListener('pointerup', onPointerUp);
      document.removeEventListener('keydown', onKey);
      confirmBtn.removeEventListener('click', onConfirm);
      cancelBtn.removeEventListener('click', onCancel);
      overlay.remove();
      resolve(result);
    };

    const onPointerDown = (event) => {
      if (!imageReady) return;
      if (event.target !== overlay && event.target !== img) return;
      const bounds = img.getBoundingClientRect();
      if (!event.target || !bounds) return;
      start = { x: event.clientX, y: event.clientY };
      const x = clamp(start.x, bounds.left, bounds.right);
      const y = clamp(start.y, bounds.top, bounds.bottom);
      start = { x, y };
      currentRect = { x, y, width: 0, height: 0 };
      updateSelection();
    };

    const onPointerMove = (event) => {
      if (!start) return;
      if (!imageReady) return;
      const bounds = img.getBoundingClientRect();
      const x1 = clamp(Math.min(event.clientX, start.x), bounds.left, bounds.right);
      const y1 = clamp(Math.min(event.clientY, start.y), bounds.top, bounds.bottom);
      const x2 = clamp(Math.max(event.clientX, start.x), bounds.left, bounds.right);
      const y2 = clamp(Math.max(event.clientY, start.y), bounds.top, bounds.bottom);
      currentRect = { x: x1, y: y1, width: x2 - x1, height: y2 - y1 };
      updateSelection();
    };

    const onPointerUp = () => {
      start = null;
    };

    const onConfirm = (event) => {
      event.stopPropagation();
      if (!imageReady) return;
      cleanup(crop());
    };

    const onCancel = (event) => {
      event.stopPropagation();
      cleanup(null);
    };

    const onKey = (event) => {
      if (event.key === 'Escape') {
        cleanup(null);
      }
      if (event.key === 'Enter') {
        cleanup(crop());
      }
    };

    overlay.addEventListener('pointerdown', onPointerDown);
    overlay.addEventListener('pointermove', onPointerMove);
    overlay.addEventListener('pointerup', onPointerUp);
    document.addEventListener('keydown', onKey);
    confirmBtn.addEventListener('click', onConfirm);
    cancelBtn.addEventListener('click', onCancel);
    confirmBtn.addEventListener('pointerdown', (e) => e.stopPropagation());
    cancelBtn.addEventListener('pointerdown', (e) => e.stopPropagation());
  });
};

const cacheElements = () => {
  els.imagePreview = document.getElementById('image-preview');
  els.katexOutput = document.getElementById('katex-output');
  els.loadingMask = document.getElementById('loading-mask');
  els.latexOutput = document.getElementById('latex-output');
  els.mathmlPreview = document.getElementById('mathml-preview');
  els.resultHint = document.getElementById('result-hint');
  els.statusLine = document.getElementById('status-line');
  els.copyFormatPill = document.getElementById('copy-format-pill');
  els.customModelField = document.getElementById('custom-model-field');

  els.btnSelectImage = document.getElementById('btn-select-image');
  els.btnScreenshot = document.getElementById('btn-screenshot');
  els.convertBtn = document.getElementById('btn-convert');
  els.btnCopyLatex = document.getElementById('btn-copy-latex');
  els.btnCopyMathml = document.getElementById('btn-copy-mathml');

  els.apiBase = document.getElementById('api-base');
  els.apiKey = document.getElementById('api-key');
  els.apiModel = document.getElementById('api-model');
  els.apiModelCustom = document.getElementById('api-model-custom');
  els.copyFormat = document.getElementById('copy-format');
};

const bindEvents = () => {
  els.btnSelectImage.addEventListener('click', selectImage);
  els.btnScreenshot.addEventListener('click', startScreenshotFlow);
  els.convertBtn.addEventListener('click', performOCR);
  els.btnCopyLatex.addEventListener('click', copyLatex);
  els.btnCopyMathml.addEventListener('click', copyMathML);

  [els.apiBase, els.apiKey, els.apiModel, els.apiModelCustom, els.copyFormat].forEach((input) => {
    input.addEventListener('input', persistSettings);
  });
  els.apiModel.addEventListener('change', persistSettings);
};

const init = async () => {
  cacheElements();
  bindEvents();
  await loadSettings();
  updateResultViews();
  setStatus('等待图片或截图…');
  window.electronAPI.onGlobalScreenshot(() => startScreenshotFlow());
  window.electronAPI.onShortcutFailed(() => {
    setStatus('全局快捷键注册失败，使用按钮截图', 'warn');
  });
  window.electronAPI.onShortcutRegistered((acc) => {
    const hint = acc ? `全局快捷键已就绪：${acc}` : '全局快捷键已就绪';
    setStatus(hint, 'ok');
  });
};

document.addEventListener('DOMContentLoaded', init);
