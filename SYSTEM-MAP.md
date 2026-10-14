# SYSTEM-MAP

## 文件职责

- `README.md`：说明工具定位、环境要求、使用命令和输出结果。
- `pyproject.toml`：定义 Python 项目元数据和 `psd2web` 命令入口。
- `psd_web_converter/__init__.py`：声明 Python 包和版本号。
- `psd_web_converter/__main__.py`：支持 `python -m psd_web_converter` 启动。
- `psd_web_converter/cli.py`：解析命令行参数，串联 Photoshop 导出、HTML 生成和报告生成。
- `psd_web_converter/web.py`：本地 Web UI 服务，提供 PSD 上传、模式选择、转换预览和结果下载。
- `psd_web_converter/paths.py`：处理项目路径、输入路径和输出目录准备。
- `psd_web_converter/photoshop.py`：通过 `osascript` 调用 Photoshop JSX，并把失败转换成中文错误。
- `psd_web_converter/generator.py`：从 `layout.json` 提取文字层，生成 `text-layers.json` 和 `index.html`。
- `psd_web_converter/typography.py`：处理 Photoshop 字号到 HTML 字号的转换，保留原始字号并按 bounds 做异常收敛。
- `psd_web_converter/validator.py`：校验转换输出是否完整，包括 HTML、JSON、flatten 图和图片大小。
- `psd_web_converter/report.py`：生成中文 `report.md`，说明转换结果、字体、文字读取来源、图层兼容风险和输出校验。
- `photoshop-scripts/export-layout.jsx`：在 Photoshop 中打开 PSD，导出图层结构、坐标和文字元数据；文字读取依次兼容 `textItem`、Action Manager `textKey` 和图层名兜底。
- `photoshop-scripts/export-flatten.jsx`：在 Photoshop 中打开 PSD，按模式导出网页优化后的 `assets/flatten.png`；可在 `editable` 模式隐藏文字层后再 flatten。
- `photoshop-scripts/create-smoke-psd.jsx`：生成一个最小测试 PSD，用于验证 Photoshop 调用和转换链路。
- `examples/README.md`：预留示例目录说明。

## 依赖关系

- `cli.py` 依赖 `paths.py`、`photoshop.py`、`generator.py`、`validator.py` 和 `report.py`。
- `web.py` 依赖 `cli.py` 的 `convert_one`，复用同一条 Photoshop 转换链路；上传和结果默认写入用户目录 `~/.psd-web-converter/`。
- `photoshop.py` 依赖 `photoshop-scripts/export-layout.jsx` 和 `photoshop-scripts/export-flatten.jsx`。
- `photoshop-scripts/create-smoke-psd.jsx` 只用于人工烟测，不参与正式转换链路。
- `generator.py` 依赖 Photoshop 导出的 `layout.json` 数据结构，并调用 `typography.py` 生成 HTML 字号。
- `validator.py` 依赖输出目录中的 `index.html`、`layout.json`、`text-layers.json` 和 `assets/flatten.png`。
- `report.py` 依赖 CLI 传入的 PSD 路径、layout 数据、文字层数据、flatten 路径和校验结果。

## 数据流向

1. 用户在 CLI 输入 PSD 路径、输出目录和转换模式，或在 Web UI 上传 PSD 并选择模式。
2. `cli.py` 校验 PSD 文件和输出目录。
3. `photoshop.py` 调用 `export-layout.jsx`，Photoshop 打开 PSD 并生成 `layout.json`。
4. `photoshop.py` 调用 `export-flatten.jsx`，Photoshop 生成网页优化后的 `assets/flatten.png`；当文字层来自完整 `textItem` 元数据时，`editable` 模式会隐藏文字层导出背景，否则保留完整 flatten 并在编辑时显示 HTML 文字。
5. `generator.py` 从 `layout.json` 提取文字层，调用 `typography.py` 计算 `fontSize`、`rawFontSize`、`fontSizeSource` 和 `fontSizeWarning`，写入 `text-layers.json`。
6. `generator.py` 根据转换模式生成或跳过 `index.html`。
7. `validator.py` 检查输出文件完整性、JSON 格式和 flatten 图片大小。
8. `report.py` 写入 `report.md`，记录输出、字体、字号统计、校验结果和风险。

## 当前边界

- 只支持 macOS + Adobe Photoshop。
- 不使用 `psd-tools` 兜底。
- 第一版不做云端上传、不做桌面壳、不做用户系统。
- 第一版不逐层导出复杂图片，优先保证 Photoshop flatten 的视觉结果稳定。


## GitHub 发布材料

- `assets/github-cover.svg`：原创项目封面。
- `docs/`：公开版使用说明与发布验证记录。
- `README.md`：公开项目入口与能力边界。
