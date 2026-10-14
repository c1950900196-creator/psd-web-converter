# PSD Web Converter

本项目是一个本地 PSD 转网页原型工具。第一版只接 Adobe Photoshop，通过 Photoshop JSX 读取图层元数据并导出 flatten 视觉图，不使用 `psd-tools` 兜底。

## 适用场景

- 医学会议 H5
- 活动宣传页
- 专家介绍页
- 会议日程页
- 客户临时改文案的静态页面

## 环境要求

- macOS
- Python 3.10+
- Adobe Photoshop

如果没有 Photoshop，工具会直接报错，不会走其他解析方案。

## 使用方式

启动本地 Web UI：

```bash
python -m psd_web_converter.web --host 127.0.0.1 --port 8787
```

浏览器打开：

```text
http://127.0.0.1:8787
```

Web UI 支持上传 PSD、选择转换模式、查看预览和下载结果。转换仍然在本机完成，不调用大模型。

在项目目录执行：

```bash
python -m psd_web_converter "/path/to/input.psd" "/path/to/output" --mode fidelity --force
```

也可以用可编辑文字模式：

```bash
python -m psd_web_converter "/path/to/input.psd" "/path/to/output" --mode editable --force
```

安装成本地命令后也可以执行：

```bash
psd2web "/path/to/input.psd" "/path/to/output" --mode editable --force
```

批量转换目录内所有 PSD：

```bash
python -m psd_web_converter "/path/to/psd-folder" "/path/to/output-folder" --mode editable --batch --force
```

模式说明：

- `fidelity`：高保真模式，输出 Photoshop flatten 图和结构化数据。
- `editable`：可编辑模式。普通 `textItem` 文字层会先隐藏再导出背景；如果只能通过 `textKey` 兼容读取文字，则默认保留完整 flatten，点击编辑时再显示 HTML 文字层。
- `assets`：只输出 `layout.json`、`text-layers.json`、`assets/flatten.png` 和报告。

## 输出结果

```text
output/
├── index.html
├── layout.json
├── text-layers.json
├── report.md
└── assets/
    └── flatten.png
```

## 设计原则

这个工具把 Photoshop 渲染结果作为视觉基准。复杂效果、蒙版、混合模式、智能对象先由 Photoshop flatten 成图片，避免浏览器逐层复刻导致失真。

`editable` 模式会保留 Photoshop 原始字号到 `rawFontSize`，再按规则生成 HTML 可用的 `fontSize`。常规情况下优先相信 Photoshop 字号；如果字号明显大于文字图层可见高度，就按 bounds 收敛，并在 `fontSizeSource` 和 `fontSizeWarning` 里说明原因。

文字读取按三级兼容：

1. 优先读取 Photoshop DOM 的 `textItem`，可获得文字、字体、字号、颜色等完整信息。
2. 如果 `LayerKind.TEXT` 但 `textItem` 报错，则读取 Action Manager 的 `textKey`，尽量保留文字、字体、字号、行高和颜色。
3. 如果两者都失败，才允许使用图层名兜底，并在 `textWarning` 中标记风险。

当文字来自 `textKey` 或图层名兜底时，工具默认不覆盖 Photoshop 原始视觉，只在用户点击“开启文字编辑”后显示 HTML 文字层，避免字体和颜色信息不足导致预览失真。

已纳入报告的兼容风险：

- 智能对象：不尝试浏览器复刻，交给 Photoshop flatten 烘焙进背景。
- 调整层：不尝试浏览器复刻，交给 Photoshop flatten 烘焙进背景。
- 空图层 / 零尺寸图层：不生成 HTML 元素。
- `textKey` 或图层名兜底文字：可编辑，但默认不覆盖原始视觉。

标准转换流程：

1. Photoshop JSX 导出 `layout.json`。
2. `editable` 模式根据文字读取来源决定是否隐藏 PSD 文字层；只有 `textItem` 信息完整时才隐藏文字导出背景。
3. 提取文字层并生成 `text-layers.json`。
4. 统一计算 HTML 字号，保留原始字号和修正原因。
5. 生成 `index.html`。
6. 校验输出文件和 JSON 格式。
7. 生成 `report.md`，记录校验结果、字号来源统计和风险。

AI 不参与主转换链路。后续可以让 AI 辅助图层语义判断、组件化建议、报告解释，但坐标、字体、颜色和导出结果必须来自确定性程序。

## 开发自查

```bash
python -m psd_web_converter --help
python -m compileall psd_web_converter
```

有 Photoshop 时，可以用 `photoshop-scripts/create-smoke-psd.jsx` 生成一个临时 PSD，再跑完整转换链路。
