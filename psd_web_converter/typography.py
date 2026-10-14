from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class FontSizeDecision:
    font_size: float
    line_height: float
    raw_font_size: float | None
    font_size_source: str
    font_size_warning: str | None = None

    def to_dict(self) -> dict[str, float | str | None]:
        return asdict(self)


def ps_pt_to_css_px(pt: float) -> float:
    return round(pt * 96 / 72, 2)


def resolve_font_size(
    raw_font_size: float | int | None,
    bounds_height: float | int,
    text: str,
    raw_leading: float | int | None = None,
) -> FontSizeDecision:
    line_count = max(1, len(str(text).splitlines()))
    height = max(0.0, float(bounds_height or 0))
    bounds_font_size = round(max(8.0, height / line_count * 0.92), 2)
    raw = float(raw_font_size) if raw_font_size else None

    if raw is None:
        font_size = bounds_font_size
        source = "bounds"
        warning = "Photoshop 未返回字号，已按图层可见高度估算。"
    elif height <= 0:
        font_size = round(raw, 2)
        source = "photoshop"
        warning = None
    elif raw <= height * 1.4:
        font_size = round(raw, 2)
        source = "photoshop"
        warning = None
    elif raw <= height * 1.8:
        font_size = round(min(raw, height * 1.1), 2)
        source = "hybrid"
        warning = "Photoshop 字号略大于图层可见高度，已按 bounds 轻微收敛。"
    else:
        font_size = bounds_font_size
        source = "bounds"
        warning = "Photoshop 字号明显大于图层可见高度，已按 bounds 收敛。"

    line_height = _resolve_line_height(font_size, raw_leading)
    return FontSizeDecision(
        font_size=font_size,
        line_height=line_height,
        raw_font_size=round(raw, 2) if raw is not None else None,
        font_size_source=source,
        font_size_warning=warning,
    )


def _resolve_line_height(font_size: float, raw_leading: float | int | None) -> float:
    if raw_leading:
        leading = float(raw_leading)
        if font_size <= leading <= font_size * 1.6:
            return round(leading, 2)
    return round(font_size * 1.2, 2)
