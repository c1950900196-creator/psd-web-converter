from __future__ import annotations

from pathlib import Path
from typing import Any


def write_report(
    output_dir: Path,
    psd_path: Path,
    layout: dict[str, Any] | None,
    text_layers: list[dict[str, Any]],
    flatten_path: Path | None,
    mode: str,
    validation: list[dict[str, Any]] | None = None,
    error: str | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        "# PSD 转网页转换报告",
        "",
        f"- 源文件：`{psd_path}`",
        f"- 转换模式：`{mode}`",
        f"- Photoshop 主链路：是",
        f"- psd-tools 兜底：否",
    ]

    if error:
        lines.extend(
            [
                "",
                "## 转换失败",
                "",
                f"发生了什么：Photoshop 没有完成 PSD 转换。",
                f"为什么：{error}",
                "怎么解决：确认本机已安装 Adobe Photoshop，PSD 文件能在 Photoshop 中打开，然后重新执行命令。",
            ]
        )
        (output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
        return

    document = (layout or {}).get("document", {})
    layers = (layout or {}).get("layers", [])
    visible_layers = [layer for layer in layers if layer.get("visible")]
    hidden_layers = len(layers) - len(visible_layers)
    font_names = sorted({layer.get("font") for layer in text_layers if layer.get("font")})
    font_sources = _count_values(text_layers, "fontSizeSource")
    font_warnings = [layer for layer in text_layers if layer.get("fontSizeWarning")]
    text_sources = _count_values(text_layers, "textSource")
    text_warnings = [layer for layer in text_layers if layer.get("textWarning")]
    has_uncertain_text_style = any(layer.get("textSource") != "textItem" for layer in text_layers)
    layer_kind_counts = _count_values(layers, "kind")
    empty_layers = [layer for layer in layers if _is_empty_layer(layer)]
    compatibility_notes = _compatibility_notes(layers, empty_layers)

    lines.extend(
        [
            f"- PSD 尺寸：{document.get('widthPx')} x {document.get('heightPx')}",
            f"- 图层总数：{(layout or {}).get('layerCount', len(layers))}",
            f"- 可见图层：{len(visible_layers)}",
            f"- 隐藏图层：{hidden_layers}",
            f"- 文字层：{len(text_layers)}",
            f"- Flatten 视觉图：`assets/{flatten_path.name if flatten_path else '未生成'}`",
            f"- Flatten 文件大小：{_format_file_size(flatten_path)}",
            f"- Editable 背景处理：{_editable_background_status(mode, text_layers)}",
            "",
            "## 文字读取",
            "",
            f"- 文字读取来源统计：{_format_counts(text_sources)}",
            f"- 触发文字读取告警：{len(text_warnings)}",
            "",
            "## 字号转换",
            "",
            f"- Photoshop 原始字号保留字段：`rawFontSize`",
            f"- HTML 最终字号字段：`fontSize`",
            f"- 字号来源统计：{_format_counts(font_sources)}",
            f"- 触发字号告警：{len(font_warnings)}",
            "",
            "## 图层兼容",
            "",
            f"- 图层类型统计：{_format_counts(layer_kind_counts)}",
            f"- 空图层 / 零尺寸图层：{len(empty_layers)}",
            *compatibility_notes,
            "",
            "## 输出校验",
            "",
            *_format_validation(validation or []),
            "",
            "## 输出文件",
            "",
            "- `index.html`：可打开预览页，`assets` 模式不会生成。",
            "- `assets/flatten.png`：Photoshop flatten 后的高保真视觉基准。",
            "- `layout.json`：Photoshop 导出的完整图层元数据。",
            "- `text-layers.json`：可结构化处理的文字层。",
            "- `report.md`：本报告。",
            "",
            "## 字体",
            "",
        ]
    )

    if font_names:
        lines.extend(f"- `{font}`" for font in font_names)
    else:
        lines.append("- 没有检测到可见文字层字体。")

    lines.extend(
        [
            "",
            "## 风险说明",
            "",
            "- 第一版以 Photoshop flatten 图作为视觉基准，复杂特效、蒙版、混合模式都以 Photoshop 输出为准。",
            "- `editable` 模式会把文字层叠加为 HTML，可能因为字体缺失、浏览器渲染差异产生轻微偏移。",
            *(
                ["- 本次存在非 `textItem` 读取的文字层，默认保留完整 flatten 视觉；点击编辑时才显示 HTML 文字层。"]
                if has_uncertain_text_style
                else []
            ),
            "- 第一版不逐层导出复杂图片，也不使用 `psd-tools` 兜底；Photoshop 不可用时会直接失败。",
        ]
    )

    (output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _format_file_size(path: Path | None) -> str:
    if not path or not path.exists():
        return "未生成"
    size = path.stat().st_size
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / 1024 / 1024:.1f} MB"


def _count_values(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return counts


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "无"
    return "，".join(f"{key} {value} 个" for key, value in sorted(counts.items()))


def _format_validation(validation: list[dict[str, Any]]) -> list[str]:
    if not validation:
        return ["- 未执行输出校验。"]
    lines = []
    for item in validation:
        status = "通过" if item.get("ok") else "失败"
        lines.append(f"- {status}：{item.get('name')}，{item.get('message')}")
    return lines


def _editable_background_status(mode: str, text_layers: list[dict[str, Any]]) -> str:
    if mode != "editable" or not text_layers:
        return "保留完整 Photoshop flatten"
    if all(layer.get("textSource") == "textItem" for layer in text_layers):
        return "已隐藏文字层后再导出背景"
    return "保留完整 Photoshop flatten，编辑时再显示 HTML 文字层"


def _is_empty_layer(layer: dict[str, Any]) -> bool:
    bounds = layer.get("bounds") or {}
    return not bounds.get("width") or not bounds.get("height")


def _compatibility_notes(layers: list[dict[str, Any]], empty_layers: list[dict[str, Any]]) -> list[str]:
    kinds = [str(layer.get("kind") or "") for layer in layers]
    notes = []
    smart_count = sum("SMARTOBJECT" in kind for kind in kinds)
    adjustment_count = sum(any(key in kind for key in ("HUESATURATION", "CURVES", "LEVELS", "BRIGHTNESSCONTRAST")) for kind in kinds)
    if smart_count:
        notes.append(f"- 智能对象：{smart_count} 个，已由 Photoshop flatten 烘焙进背景图。")
    if adjustment_count:
        notes.append(f"- 调整层：{adjustment_count} 个，已由 Photoshop flatten 烘焙进背景图。")
    if empty_layers:
        notes.append("- 空图层不会生成 HTML 元素。")
    if not notes:
        notes.append("- 未发现需要特殊说明的图层兼容风险。")
    return notes
