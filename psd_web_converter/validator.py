from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ValidationItem:
    name: str
    ok: bool
    message: str

    def to_dict(self) -> dict[str, bool | str]:
        return asdict(self)


def validate_output(output_dir: Path, mode: str) -> list[dict[str, bool | str]]:
    checks = [
        _check_file(output_dir / "layout.json", "layout.json"),
        _check_file(output_dir / "text-layers.json", "text-layers.json"),
        _check_file(output_dir / "assets" / "flatten.png", "assets/flatten.png"),
    ]
    if mode != "assets":
        checks.append(_check_file(output_dir / "index.html", "index.html"))

    checks.extend(
        [
            _check_json(output_dir / "layout.json", "layout.json JSON"),
            _check_json(output_dir / "text-layers.json", "text-layers.json JSON"),
            _check_flatten_size(output_dir / "assets" / "flatten.png"),
        ]
    )
    return [item.to_dict() for item in checks]


def _check_file(path: Path, label: str) -> ValidationItem:
    if path.exists() and path.is_file():
        return ValidationItem(label, True, "文件存在")
    return ValidationItem(label, False, "文件缺失")


def _check_json(path: Path, label: str) -> ValidationItem:
    if not path.exists():
        return ValidationItem(label, False, "文件缺失，无法解析 JSON")
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return ValidationItem(label, False, f"JSON 格式错误：{exc}")
    return ValidationItem(label, True, "JSON 格式正常")


def _check_flatten_size(path: Path) -> ValidationItem:
    if not path.exists():
        return ValidationItem("flatten 文件大小", False, "flatten.png 缺失")
    size = path.stat().st_size
    if size == 0:
        return ValidationItem("flatten 文件大小", False, "flatten.png 是空文件")
    if size > 10 * 1024 * 1024:
        return ValidationItem("flatten 文件大小", False, f"flatten.png 偏大：{_format_size(size)}")
    return ValidationItem("flatten 文件大小", True, f"大小正常：{_format_size(size)}")


def _format_size(size: int) -> str:
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / 1024 / 1024:.1f} MB"
