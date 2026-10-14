from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .generator import write_html, write_text_layers
from .paths import prepare_output_dir, resolve_input_path
from .photoshop import PhotoshopError, export_flatten, export_layout
from .report import write_report
from .validator import validate_output


VALID_MODES = ("fidelity", "editable", "assets")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="把 PSD 转成 Photoshop 渲染基准的本地 HTML 原型。"
    )
    parser.add_argument("psd", help="输入 PSD 文件路径")
    parser.add_argument("output", help="输出目录")
    parser.add_argument(
        "--mode",
        choices=VALID_MODES,
        default="fidelity",
        help="转换模式：fidelity 高保真、editable 可编辑文字、assets 只导出资产和 JSON",
    )
    parser.add_argument("--force", action="store_true", help="覆盖已存在的输出目录")
    parser.add_argument(
        "--batch",
        action="store_true",
        help="把第一个参数当作 PSD 目录，批量转换其中所有 .psd 文件",
    )
    return parser


def run(args: argparse.Namespace) -> int:
    input_path = resolve_input_path(args.psd)
    output_dir = resolve_input_path(args.output)

    if args.batch:
        return run_batch(input_path, output_dir, args)

    if not input_path.exists():
        print(f"错误：PSD 文件不存在：{input_path}", file=sys.stderr)
        return 2
    if input_path.suffix.lower() != ".psd":
        print(f"错误：输入文件不是 PSD：{input_path}", file=sys.stderr)
        return 2

    return convert_one(input_path, output_dir, args)


def convert_one(psd_path: Path, output_dir: Path, args: argparse.Namespace) -> int:
    layout = None
    text_layers: list[dict] = []
    flatten_path = None

    try:
        prepare_output_dir(output_dir, force=args.force)
        layout = export_layout(psd_path, output_dir / "layout.json")
        text_layers = write_text_layers(output_dir, layout)
        flatten_path = export_flatten(
            psd_path,
            output_dir / "assets" / "flatten.png",
            hide_text=_should_hide_text_for_editable(args.mode, text_layers),
        )
        if args.mode != "assets":
            write_html(output_dir, layout, text_layers, flatten_path, mode=args.mode)
        validation = validate_output(output_dir, args.mode)
        write_report(
            output_dir,
            psd_path,
            layout,
            text_layers,
            flatten_path,
            mode=args.mode,
            validation=validation,
        )
    except FileExistsError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    except PhotoshopError as exc:
        write_report(
            output_dir,
            psd_path,
            layout=None,
            text_layers=[],
            flatten_path=None,
            mode=args.mode,
            error=str(exc),
        )
        print(f"Photoshop 转换失败：{exc}", file=sys.stderr)
        return 1

    doc = layout.get("document", {})
    print(f"PSD 尺寸：{doc.get('widthPx')} x {doc.get('heightPx')}")
    print(f"图层数量：{layout.get('layerCount', 0)}")
    print(f"文字层数量：{len(text_layers)}")
    print(f"输出目录：{output_dir}")
    return 0


def run_batch(input_dir: Path, output_dir: Path, args: argparse.Namespace) -> int:
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"错误：批量模式需要输入 PSD 目录：{input_dir}", file=sys.stderr)
        return 2

    psd_files = sorted(input_dir.glob("*.psd"))
    if not psd_files:
        print(f"错误：目录中没有找到 PSD 文件：{input_dir}", file=sys.stderr)
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)
    failed = 0
    for psd_file in psd_files:
        child_output = output_dir / psd_file.stem
        print(f"开始转换：{psd_file.name}")
        code = convert_one(psd_file, child_output, args)
        if code != 0:
            failed += 1
    print(f"批量转换完成：总数 {len(psd_files)}，失败 {failed}")
    return 1 if failed else 0


def _should_hide_text_for_editable(mode: str, text_layers: list[dict]) -> bool:
    if mode != "editable" or not text_layers:
        return False
    return all(layer.get("textSource") == "textItem" for layer in text_layers)


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    raise SystemExit(run(args))
