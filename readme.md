# LaTeXOCR：自动公式识别的 macOS 小工具

## 项目简介

这是一个常驻状态栏的小工具，通过截图 + OCR 将图片中的公式识别为 LaTeX，并支持渲染预览、复制 LaTeX/MathML，方便粘贴到文档或 Word 中。

## 已实现功能

### 功能一：Latex 公式识别

使用快捷键：command + shift + A 调出截图工具
流程：
1. 快捷键：command + shift + A 截图
2. 调用大模型自动识别公式
3. 将识别结果复制到剪切板，并跳动Dock图标通知用户已复制

#### 设置功能

- API 地址与 API Key（不再硬编码）
- 模型选择（支持“其他”自定义模型名）
- 默认复制格式：LaTeX 或 MathML(word)

### 功能二：LaTeX 公式转 MathML (word) 公式

使用: 点击软件界面的 “复制MathML(word)” 按钮即可复制到剪贴板

## 后续功能实现

- [ ] 优化 MathML 在 Word 中的兼容性细节
- [ ] 完成 PPT 的公式插入插件开发
- [ ] 完成配套的PPT插件需要的公式代码转换
