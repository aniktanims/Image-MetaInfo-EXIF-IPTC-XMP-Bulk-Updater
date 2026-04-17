from __future__ import annotations

from pathlib import Path

import pillow_avif  # noqa: F401
from PIL import Image, ImageDraw, ImageFilter


def build_icon(source: Path, output: Path) -> None:
    size = 1024
    radius = 224

    output.parent.mkdir(parents=True, exist_ok=True)

    # Rich green gradient background.
    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = base.load()
    for y in range(size):
        t = y / (size - 1)
        top = (21, 143, 80)
        bottom = (8, 95, 50)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        for x in range(size):
            pixels[x, y] = (r, g, b, 255)

    # Soft center spotlight.
    spotlight = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    spotlight_draw = ImageDraw.Draw(spotlight)
    spotlight_draw.ellipse((160, 170, 864, 780), fill=(120, 255, 185, 65))
    spotlight = spotlight.filter(ImageFilter.GaussianBlur(60))
    base = Image.alpha_composite(base, spotlight)

    # Rounded app mask.
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)

    # Center glass panel for logo clarity.
    panel = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    panel_draw = ImageDraw.Draw(panel)
    panel_width, panel_height = 620, 250
    panel_x, panel_y = (size - panel_width) // 2, (size - panel_height) // 2
    panel_draw.rounded_rectangle(
        (panel_x, panel_y, panel_x + panel_width, panel_y + panel_height),
        radius=70,
        fill=(255, 255, 255, 18),
        outline=(255, 255, 255, 55),
        width=3,
    )

    # Load logo with controlled upscale.
    logo = Image.open(source).convert("RGBA")
    logo_width = 360
    logo_height = int(logo.height * (logo_width / logo.width))
    logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
    logo = logo.filter(ImageFilter.UnsharpMask(radius=1.6, percent=180, threshold=2))

    # Logo shadow.
    shadow = Image.new("RGBA", (logo.width + 48, logo.height + 48), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        (10, 14, shadow.width - 10, shadow.height - 10),
        radius=22,
        fill=(0, 0, 0, 80),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))

    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    icon.alpha_composite(panel)
    icon.alpha_composite(
        shadow,
        ((size - shadow.width) // 2, (size - shadow.height) // 2 + 8),
    )
    icon.alpha_composite(logo, ((size - logo.width) // 2, (size - logo.height) // 2))

    # Subtle inner border.
    border = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    border_draw = ImageDraw.Draw(border)
    border_draw.rounded_rectangle(
        (18, 18, size - 19, size - 19),
        radius=radius - 12,
        outline=(255, 255, 255, 62),
        width=4,
    )
    icon = Image.alpha_composite(icon, border)

    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(base, (0, 0), mask)
    result.alpha_composite(icon)
    result.putalpha(mask)
    result.save(output)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    source_path = root / "frontend" / "tracktech-logo-nav-tall.avif"
    output_path = root / "dist" / "app-icon-source.png"
    build_icon(source_path, output_path)
    print(output_path)
