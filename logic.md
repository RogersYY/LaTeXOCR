# 项目运行逻辑（学习版）

本文从“启动 → 交互 → 识别 → 渲染 → 复制”的角度，梳理 LaTeXOCR 的核心流程，便于学习 macOS App（SwiftUI + AppKit + WKWebView）开发。

## 1. 启动与窗口/菜单

- 入口：`LaTeXOCR/LaTeXOCRApp.swift`
  - 使用 `@NSApplicationDelegateAdaptor` 挂接 `AppDelegate`。
  - Settings 场景挂载 `SettingsView` 作为设置页。
- 状态栏与窗口：`LaTeXOCR/AppDelegate.swift`
  - 创建状态栏图标与菜单项。
  - 创建主窗口并展示 `MainBoardView`。
  - 注册全局快捷键（目前用于截图）。

## 2. 主界面与状态管理

- 主界面：`LaTeXOCR/MainBoardView.swift`
  - `@StateObject` 持有 `IdentifyProcess`，作为全局可观察状态。
  - 左侧显示截图图片，右侧显示公式预览（KaTeX）。
  - 提供“复制LaTeX”“复制MathML(word)”按钮，并显示复制反馈。

## 3. 截图与识别流程

- 截图逻辑：`IdentifyProcess.startScreenshotProcess()`
  - 使用 `screencapture -i` 生成截图到 Application Support 目录。
  - 截图完成后加载图片，并触发识别流程。
- OCR 识别：`IdentifyProcess.convertImageToLatex()`
  - 将图片转为 Base64。
  - 调用 `ocrFormulaToLatex(...)` 进行网络请求。
  - 识别结果写入 `latexFormula`，并根据设置自动复制到剪贴板。

## 4. API 请求与设置

- API 设置：`LaTeXOCR/SettingsView.swift`
  - `@AppStorage` 保存 API 地址、API Key、模型和默认复制格式。
  - 支持“其他”模型自定义名称。
- 请求构建：`IdentifyProcess.ocrFormulaToLatex(...)`
  - 使用 `URLSession` 发送请求。
  - 解析返回内容并清理多余 LaTeX 包裹符。

## 5. 公式渲染与 MathML 提取

- 公式预览：`LaTeXOCR/KaTexView.swift`
  - `WKWebView` 加载 KaTeX，渲染 LaTeX 到页面。
  - 通过 JS 的 `getMathML()` 提取 MathML。
  - 识别完成后按需请求 MathML，用于 Word 粘贴。

## 6. 复制逻辑

- 自动复制：识别完成后根据设置自动复制 LaTeX 或 MathML。
- 手动复制：
  - “复制LaTeX”：直接复制 `latexFormula`。
  - “复制MathML(word)”：请求/生成 MathML 后复制到剪贴板。
- 剪贴板写入：`IdentifyProcess.copyStringToPasteboard(...)`
  - 以 `public.mathml` + 纯文本写入，便于 Word 识别。

## 7. 你可以从这个项目学到什么

- SwiftUI + AppKit 混合开发（状态栏与主窗口）。
- `@AppStorage` 做设置持久化。
- `WKWebView` 承载 Web 渲染（KaTeX）。
- macOS 剪贴板 API 的使用。
- 通过 `URLSession` 完成 OCR API 请求。

## 8. 建议的学习顺序

1. `LaTeXOCRApp.swift` 与 `AppDelegate.swift`：理解应用启动与菜单窗口。
2. `MainBoardView.swift`：掌握 SwiftUI 布局与状态绑定。
3. `IdentifyProcess.swift`：学习业务流程与异步请求。
4. `KaTexView.swift`：理解 WebView 渲染与 JS 交互。
5. `SettingsView.swift`：学习设置存储与界面交互。
