from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .typography import resolve_font_size


def _rgb_to_css(color: dict[str, Any] | None) -> str:
    if not color:
        return "#000000"
    return "rgb({red}, {green}, {blue})".format(
        red=int(color.get("red", 0)),
        green=int(color.get("green", 0)),
        blue=int(color.get("blue", 0)),
    )


def _font_family(font: str | None) -> str:
    if not font:
        return '"PingFang SC", "Microsoft YaHei", sans-serif'
    mappings = {
        "SourceHanSansCN": '"Source Han Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
        "SourceHanSansSC": '"Source Han Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
        "HarmonyOS": '"HarmonyOS Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
        "PingFang": '"PingFang SC", "Microsoft YaHei", sans-serif',
    }
    for key, family in mappings.items():
        if key.lower() in font.lower():
            return family
    return f'"{font}", "PingFang SC", "Microsoft YaHei", sans-serif'


def collect_text_layers(layout: dict[str, Any]) -> list[dict[str, Any]]:
    text_layers: list[dict[str, Any]] = []
    for index, layer in enumerate(layout.get("layers", []), 1):
        text = layer.get("text")
        bounds = layer.get("bounds") or {}
        if not text or not text.get("contents"):
            continue
        if not layer.get("visible", False):
            continue

        content = text.get("contents", "")
        height = max(0, bounds.get("height") or 0)
        width = max(0, bounds.get("width") or 0)
        if width == 0 or height == 0:
            continue
        font_decision = resolve_font_size(
            text.get("sizePx"),
            height,
            content,
            raw_leading=text.get("leadingPx"),
        )
        text_layers.append(
            {
                "index": index,
                "id": layer.get("id"),
                "name": layer.get("name"),
                "path": layer.get("path"),
                "x": bounds.get("left", 0),
                "y": bounds.get("top", 0),
                "width": width,
                "height": height,
                "opacity": layer.get("opacity", 100),
                "blendMode": layer.get("blendMode"),
                "text": content,
                "textSource": text.get("source") or "textItem",
                "textWarning": text.get("warning"),
                "font": text.get("font"),
                "fontFamily": _font_family(text.get("font")),
                "fontSize": font_decision.font_size,
                "rawFontSize": font_decision.raw_font_size,
                "fontSizeSource": font_decision.font_size_source,
                "fontSizeWarning": font_decision.font_size_warning,
                "lineHeight": font_decision.line_height,
                "color": _rgb_to_css(text.get("color")),
                "align": _align_to_css(text.get("justification")),
                "position": text.get("position"),
                "horizontalScale": text.get("horizontalScale"),
            }
        )
    return text_layers


def _align_to_css(value: str | None) -> str:
    if not value:
        return "left"
    value = value.lower()
    if "center" in value:
        return "center"
    if "right" in value:
        return "right"
    return "left"


def write_text_layers(output_dir: Path, layout: dict[str, Any]) -> list[dict[str, Any]]:
    text_layers = collect_text_layers(layout)
    (output_dir / "text-layers.json").write_text(
        json.dumps(text_layers, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return text_layers


def write_html(
    output_dir: Path,
    layout: dict[str, Any],
    text_layers: list[dict[str, Any]],
    flatten_path: Path,
    mode: str,
) -> None:
    document = layout.get("document", {})
    width = int(document.get("widthPx") or 0)
    height = int(document.get("heightPx") or 0)
    editable = mode == "editable" and bool(text_layers)
    preview_text = editable and all(layer.get("textSource") == "textItem" for layer in text_layers)
    text_payload = json.dumps(text_layers if editable else [], ensure_ascii=False, separators=(",", ":"))
    escaped_title = html.escape(document.get("name") or "PSD 网页原型")

    content = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{escaped_title}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; min-height: 100vh; background: #11141b; font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif; }}
    .toolbar {{ position: sticky; top: 0; z-index: 20; display: flex; gap: 12px; align-items: center; justify-content: center; padding: 12px; background: rgba(17, 20, 27, .9); color: #eef2ff; backdrop-filter: blur(10px); }}
    .toolbar button {{ display: {("inline-flex" if editable else "none")}; border: 1px solid rgba(255,255,255,.25); background: rgba(255,255,255,.08); color: #fff; border-radius: 999px; padding: 7px 14px; cursor: pointer; }}
    .stage {{ display: flex; justify-content: center; padding: 24px 12px 48px; }}
    .page-wrap {{ width: min(100%, {width}px); }}
    .page {{ position: relative; width: {width}px; height: {height}px; overflow: hidden; background: #fff; transform-origin: top left; }}
    .flatten {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; }}
    .text-layer {{ position: absolute; z-index: 2; display: {("block" if preview_text else "none")}; white-space: pre-wrap; background: transparent; outline: 1px dashed transparent; }}
    .editable .text-layer {{ display: block; }}
    .editable .text-layer:hover {{ outline-color: rgba(38, 114, 255, .7); }}
  </style>
</head>
<body>
  <div class="toolbar">
    <span>{escaped_title}：{width} x {height}，模式：{mode}</span>
    <button type="button" id="toggle-edit">开启文字编辑</button>
  </div>
  <div class="stage">
    <div class="page-wrap">
      <main class="page" id="page" aria-label="PSD generated page">
        <img class="flatten" src="assets/{flatten_path.name}" alt="Photoshop flatten preview" />
      </main>
    </div>
  </div>
  <script>
    const textLayers = {text_payload};
    const page = document.querySelector("#page");
    const wrap = document.querySelector(".page-wrap");
    const toggleEdit = document.querySelector("#toggle-edit");

    function addTextLayer(layer) {{
      const node = document.createElement("div");
      node.className = "text-layer";
      node.dataset.name = layer.name || "";
      node.textContent = layer.text || "";
      Object.assign(node.style, {{
        left: `${{layer.x}}px`,
        top: `${{layer.y}}px`,
        width: `${{layer.width}}px`,
        height: `${{Math.max(layer.height, layer.lineHeight || layer.fontSize || 16)}}px`,
        opacity: String((layer.opacity ?? 100) / 100),
        color: layer.color || "#000",
        fontFamily: layer.fontFamily,
        fontSize: `${{layer.fontSize || 16}}px`,
        lineHeight: `${{layer.lineHeight || (layer.fontSize || 16) * 1.2}}px`,
        textAlign: layer.align || "left",
        overflow: "visible"
      }});
      node.contentEditable = "false";
      page.appendChild(node);
    }}

    function fitPage() {{
      const scale = Math.min(1, wrap.clientWidth / {width});
      page.style.transform = `scale(${{scale}})`;
      page.style.marginBottom = `${{({height} * scale) - {height}}}px`;
    }}

    textLayers.forEach(addTextLayer);
    fitPage();
    window.addEventListener("resize", fitPage);
    if (toggleEdit) {{
      toggleEdit.addEventListener("click", () => {{
      const active = !page.classList.contains("editable");
        page.classList.toggle("editable", active);
        document.querySelectorAll(".text-layer").forEach(node => node.contentEditable = String(active));
        toggleEdit.textContent = active ? "关闭文字编辑" : "开启文字编辑";
      }});
    }}
  </script>
</body>
</html>
"""
    (output_dir / "index.html").write_text(content, encoding="utf-8")
