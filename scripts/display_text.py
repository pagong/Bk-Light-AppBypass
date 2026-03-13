import argparse
import asyncio
import sys
from dataclasses import replace
from pathlib import Path
from typing import Optional
from PIL import Image

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from bk_light.config import AppConfig, load_config, text_options
from bk_light.fonts import get_font_profile, resolve_font
from bk_light.panel_manager import PanelManager
from bk_light.text import build_text_bitmap


def parse_color(value: Optional[str]) -> Optional[tuple[int, int, int]]:
    if value is None:
        return None
    cleaned = value.replace("#", "").replace(" ", "")
    if "," in cleaned:
        parts = cleaned.split(",")
        return tuple(int(part) for part in parts[:3])
    if len(cleaned) == 6:
        return tuple(int(cleaned[i:i + 2], 16) for i in (0, 2, 4))
    raise ValueError("Invalid color")


def render_static_frame(
    canvas: tuple[int, int],
    text_bitmap: Image.Image,
    background: tuple[int, int, int],
    offset_x: int,
    offset_y: int,
) -> Image.Image:
    frame = Image.new("RGBA", canvas, tuple(background) + (255,))
    x = (canvas[0] - text_bitmap.width) // 2 + offset_x
    y = (canvas[1] - text_bitmap.height) // 2 + offset_y
    frame.paste(text_bitmap, (x, y), text_bitmap)
    return frame.convert("RGB")


def render_scroll_frame(
    canvas: tuple[int, int],
    text_bitmap: Image.Image,
    background: tuple[int, int, int],
    direction: str,
    gap: int,
    offset_x: int,
    offset_y: int,
    position: int,
) -> Image.Image:
    strip_width = max(1, text_bitmap.width + gap)
    strip = Image.new("RGBA", (strip_width, canvas[1]), tuple(background) + (255,))
    y = (canvas[1] - text_bitmap.height) // 2 + offset_y
    strip.paste(text_bitmap, (0, y), text_bitmap)
    shift = position % strip_width
    start = offset_x - shift if direction == "left" else offset_x + shift
    while start > -strip_width:
        start -= strip_width
    frame = Image.new("RGBA", canvas, tuple(background) + (255,))
    x = start
    while x < canvas[0]:
        frame.paste(strip, (int(x), 0), strip)
        x += strip_width
    return frame.convert("RGB")


async def display_text(config: AppConfig, message: str, preset_name: str, overrides: dict[str, Optional[str]]) -> None:
    preset = text_options(config, preset_name, overrides)
    color = parse_color(overrides.get("color")) or parse_color(preset.color)
    background = parse_color(overrides.get("background")) or parse_color(preset.background)
    font_ref = overrides.get("font") or preset.font
    font_path = resolve_font(font_ref)
    profile = get_font_profile(font_ref, font_path)
    if overrides.get("size") is not None:
        size = int(overrides["size"])
    elif profile.recommended_size is not None:
        size = int(profile.recommended_size)
    else:
        size = preset.size
    size = max(1, int(round(size)))
    spacing_override = overrides.get("spacing")
    spacing = int(spacing_override) if spacing_override is not None else preset.spacing
    text_bitmap = build_text_bitmap(
        message,
        font_path,
        size,
        spacing,
        color,
        config.display.antialias_text,
        monospace_digits=True,
    )
    offset_x_base = preset.offset_x + profile.offset_x
    offset_y_base = preset.offset_y + profile.offset_y
    try:
        async with PanelManager(config) as manager:
            canvas = manager.canvas_size
            if preset.mode == "scroll":
                gap_override = overrides.get("gap")
                base_gap = gap_override if gap_override is not None else preset.gap
                gap = int(base_gap) if base_gap is not None else 16
                strip_width = max(1, text_bitmap.width + gap)
                step_override = overrides.get("step")
                base_step = step_override if step_override is not None else preset.step
                step_value = int(base_step) if base_step is not None else 1
                step = max(1, step_value)
                interval_override = overrides.get("interval")
                interval = float(interval_override) if interval_override is not None else float(preset.interval)
                if interval <= 0:
                    interval = 0.02
                position = 0
                while True:
                    frame = render_scroll_frame(
                        canvas,
                        text_bitmap,
                        background,
                        preset.direction,
                        gap,
                        offset_x_base,
                        offset_y_base,
                        position,
                    )
                    await manager.send_image(frame, delay=0.0)
                    await asyncio.sleep(interval)
                    position = (position + step) % strip_width
            else:
                # Auto-fit static text so it doesn't clip on small displays (e.g. 64x16)
                while text_bitmap.width > (canvas[0] - 2) and size > 8:
                    size -= 1
                    text_bitmap = build_text_bitmap(
                        message,
                        font_path,
                        size,
                        spacing,
                        color,
                        config.display.antialias_text,
                        monospace_digits=True,
                    )
                frame = render_static_frame(
                    canvas,
                    text_bitmap,
                    background,
                    offset_x_base,
                    offset_y_base,
                )
                await manager.send_image(frame, delay=0.0)
                await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        raise
    except Exception as error:
        print("ERROR", str(error))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("text")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--address")
    parser.add_argument("--preset")
    parser.add_argument("--color")
    parser.add_argument("--background")
    parser.add_argument("--font", type=Path)
    parser.add_argument("--size", type=int)
    parser.add_argument("--spacing", type=int)
    parser.add_argument("--mode", choices=("static", "scroll"))
    parser.add_argument("--direction", choices=("left", "right"))
    parser.add_argument("--speed", type=float)
    parser.add_argument("--gap", type=int)
    parser.add_argument("--step", type=int)
    parser.add_argument("--offset-x", type=int)
    parser.add_argument("--offset-y", type=int)
    parser.add_argument("--interval", type=float)
    return parser.parse_args()


def build_override_map(args: argparse.Namespace) -> dict[str, Optional[str]]:
    return {
        "color": args.color,
        "background": args.background,
        "font": str(args.font) if args.font else None,
        "size": args.size,
        "spacing": args.spacing,
        "mode": args.mode,
        "direction": args.direction,
        "speed": args.speed,
        "gap": args.gap,
        "step": args.step,
        "offset_x": args.offset_x,
        "offset_y": args.offset_y,
        "interval": args.interval,
    }


if __name__ == "__main__":
    args = parse_args()
    config = load_config(args.config)
    if args.address:
        config.device = replace(config.device, address=args.address)
    preset_name = args.preset or config.runtime.preset or "default"
    overrides = build_override_map(args)
    try:
        asyncio.run(display_text(config, args.text, preset_name, overrides))
    except KeyboardInterrupt:
        pass

