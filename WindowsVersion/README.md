# LaTeXOCR Windows (Electron)

一个基于 Electron 的 Windows 便携版，实现与 macOS 版相同的「截图/图片 → LaTeX/MathML」流程。

## 功能
- 全局快捷键 `Ctrl+Shift+A` 截图，应用内裁剪后自动识别并复制。
- 手动导入图片，点击“转换公式”触发 OCR。
- KaTeX 预览、MathML 提取，支持一键复制 LaTeX 或 MathML（Word 友好）。
- API 地址/Key/模型与 macOS 版兼容，设置自动保存；托盘菜单可快速唤起窗口或截图。
- 便携构建：`electron-builder` 目标为 `portable`，生成免安装 `.exe`。

## 开发运行
```bash
cd WindowsVersion
npm install
npm start  # 启动 Electron 开发模式
```

## 打包（便携版）
```bash
npm run build  # 生成 dist/LaTeXOCR-Windows-<version>.exe
```
> 打包 Windows 产物建议在 Windows 环境执行；若在 macOS 交叉打包，需要相应的 Wine/VC 运行时支持。

## 使用步骤
1) 右侧填入 API 地址、Key、模型（与 macOS 版一致，形如 `https://host/v1/chat/completions`）。
2) 选择图片或按 `Ctrl+Shift+A` 截屏并裁剪，程序会调用接口识别并自动复制（默认 LaTeX，可在设置里切换 MathML）。
3) 可手动点击“复制 LaTeX”或“复制 MathML (Word)”再次复制输出。

## 数据存储
- 设置文件：`%APPDATA%/LaTeXOCR-Windows/settings.json`（便携版放在可执行文件同层的 `LaTeXOCR-Windows` 目录下）。

## 请求体格式（与原版一致）
```json
{
  "model": "<模型名称>",
  "messages": [
    {
      "role": "user",
      "content": [
        { "type": "text", "text": "Please transcribe it into LaTeX format. please only return LaTeX formula without any other unuseful symbol, so I can patse it to my doc directly." },
        { "type": "image_url", "image_url": { "url": "data:image/jpeg;base64,<base64>" } }
      ]
    }
  ]
}
```
