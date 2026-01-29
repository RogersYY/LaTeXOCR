# PythonVersion 打包为 Windows 可执行程序

下面以 Windows 环境为例，使用 PyInstaller 将 `PythonVersion/app.py` 打包成可执行文件。

## 1. 准备环境

在 Windows 安装 Python 3.10+，并确保 `python`/`pip` 可用。

```bash
python --version
pip --version
```

## 2. 安装依赖

在项目根目录执行：

```bash
pip install -r PythonVersion/requirements.txt
```

## 3. 安装 PyInstaller

```bash
pip install pyinstaller
```

## 4. 打包命令

进入 `PythonVersion` 目录，执行：

```bash
pyinstaller --onefile --windowed app.py --add-data "assets;assets"
```

说明：
- `--onefile`：生成单文件可执行程序（启动会更慢）。
- 不加 `--onefile`：生成 “exe + 依赖文件夹” 的目录结构（启动更快，体积分散）。
- 本项目采用的是第二种方案（多文件目录），见 `LaTeXOCR.spec` 的 `COLLECT` 配置。
- `--windowed`：隐藏控制台窗口（GUI 应用建议使用）。
- `--add-data "assets;assets"`：将 `assets` 目录打包进程序。

打包完成后，可执行文件在 `PythonVersion/dist/app.exe`。

## 4.1 使用已有 spec 文件打包（推荐）

如果已经生成过 `LaTeXOCR.spec`，后续可直接用 spec 打包：

```bash
pyinstaller LaTeXOCR.spec
```

说明（来自 `LaTeXOCR.spec`）：
- 入口文件：`app.py`
- 应用名：`LaTeXOCR`
- 资源：`assets` 目录会被打包（等同于 `--add-data "assets;assets"`）
- 图标：`assets\\icon.ico`
- 依赖收集：使用 `collect_all('PySide6')` 自动收集 Qt 相关依赖
- GUI 模式：`console=False`（无控制台窗口）
- 打包方式：使用 `COLLECT` 输出多文件目录（非单文件）
- 需要在 `PythonVersion` 目录下执行该命令

## 5. 如果要改配置

建议直接修改 `LaTeXOCR.spec` 后再运行：

```bash
pyinstaller LaTeXOCR.spec
```

常见可改项：
- `icon=['assets\\icon.ico']`
- `datas = [('assets', 'assets')]`
- `name='LaTeXOCR'`
- `console=False`

## 6. 常见可选项

如需设置图标：

```bash
pyinstaller --onefile --windowed app.py --icon assets/icon.ico --add-data "assets;assets"
```

## 6. 运行验证

双击 `dist/app.exe` 运行，或命令行：

```bash
PythonVersion\dist\app.exe
```
