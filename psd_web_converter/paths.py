from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = PROJECT_ROOT / "photoshop-scripts"


def resolve_input_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def prepare_output_dir(output_dir: Path, force: bool) -> Path:
    if output_dir.exists():
        if not force:
            raise FileExistsError(f"输出目录已存在：{output_dir}。如需覆盖，请加 --force。")
        import shutil

        shutil.rmtree(output_dir)

    (output_dir / "assets").mkdir(parents=True, exist_ok=True)
    return output_dir
