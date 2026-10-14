from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .paths import SCRIPT_DIR


class PhotoshopError(RuntimeError):
    """Raised when Photoshop cannot complete the conversion."""


def _quote_applescript(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _run_jsx(script_name: str, *args: Path) -> None:
    script_path = SCRIPT_DIR / script_name
    if not script_path.exists():
        raise PhotoshopError(f"缺少 Photoshop 脚本：{script_path}")

    args_file = script_path.with_suffix(".args.txt")
    args_file.write_text("\n".join(str(arg) for arg in args), encoding="utf-8")

    applescript = (
        'tell application id "com.adobe.Photoshop" '
        f'to do javascript file POSIX file "{_quote_applescript(str(script_path))}"'
    )

    try:
        try:
            result = subprocess.run(
                ["osascript", "-e", applescript],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise PhotoshopError("当前系统无法执行 osascript，暂时只支持 macOS + Photoshop。") from exc
    finally:
        args_file.unlink(missing_ok=True)

    if result.returncode != 0:
        details = (result.stderr or result.stdout or "").strip()
        if "Application isn" in details or "Can't get application" in details:
            raise PhotoshopError("没有找到 Adobe Photoshop，请先安装并打开一次 Photoshop。")
        raise PhotoshopError(details or f"Photoshop 脚本执行失败：{script_name}")


def export_layout(psd_path: Path, output_json: Path) -> dict[str, Any]:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    _run_jsx("export-layout.jsx", psd_path, output_json)

    try:
        return json.loads(output_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PhotoshopError(f"Photoshop 导出的 layout.json 不是有效 JSON：{exc}") from exc
    except FileNotFoundError as exc:
        raise PhotoshopError("Photoshop 没有生成 layout.json。") from exc


def export_flatten(psd_path: Path, output_png: Path, hide_text: bool = False) -> Path:
    output_png.parent.mkdir(parents=True, exist_ok=True)
    _run_jsx("export-flatten.jsx", psd_path, output_png, Path("1" if hide_text else "0"))
    if not output_png.exists():
        raise PhotoshopError("Photoshop 没有生成 flatten.png。")
    return output_png
