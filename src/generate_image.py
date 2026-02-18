"""
generate_image.py
Creates a 1080x1920 (9:16 vertical) AI Fail image for YouTube Shorts.
No external image AI needed — pure Python + Pillow.
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap
import math
import random
import os

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

W, H = 1080, 1920

# Color palettes — KI rotiert automatisch
PALETTES = [
    {"bg": (8, 8, 20),    "accent": (120, 80, 255),  "text": (255, 255, 255), "sub": (180, 160, 255)},
    {"bg": (5, 15, 10),   "accent": (0, 220, 120),   "text": (255, 255, 255), "sub": (150, 255, 200)},
    {"bg": (20, 5, 5),    "accent": (255, 60, 60),    "text": (255, 255, 255), "sub": (255, 160, 160)},
    {"bg": (5, 10, 25),   "accent": (0, 180, 255),   "text": (255, 255, 255), "sub": (140, 210, 255)},
    {"bg": (15, 10, 5),   "accent": (255, 160, 0),   "text": (255, 255, 255), "sub": (255, 210, 120)},
]


def draw_particles(draw, palette, count=60):
    """Draw subtle glowing dots in background."""
    for _ in range(count):
        x = random.randint(0, W)
        y = random.randint(0, H)
        size = random.randint(1, 4)
        alpha = random.randint(40, 140)
        r, g, b = palette["accent"]
        draw.ellipse([x-size, y-size, x+size, y+size],
                     fill=(r, g, b, alpha))


def draw_gradient_bg(img, palette):
    """Draw a vertical gradient background."""
    draw = ImageDraw.Draw(img, "RGBA")
    r1, g1, b1 = palette["bg"]
    # Slightly lighter at center
    for y in range(H):
        factor = 1.0 + 0.3 * math.sin(math.pi * y / H)
        r = min(255, int(r1 * factor))
        g = min(255, int(g1 * factor))
        b = min(255, int(b1 * factor))
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    return draw


def draw_glow_line(draw, palette, y_pos):
    """Draw a glowing horizontal accent line."""
    r, g, b = palette["accent"]
    for thickness in [6, 4, 2]:
        alpha = 60 if thickness == 6 else (120 if thickness == 4 else 255)
        draw.line([(80, y_pos), (W-80, y_pos)],
                  fill=(r, g, b, alpha), width=thickness)


def wrap_text(text, font, max_width, draw):
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def create_fact_image(fact_text: str, source_text: str,
                      output_path: str, palette_index: int = None):
    """
    Creates a 1080x1920 AI Fail image.
    fact_text  : The fail description (auto-wrapped)
    source_text: Small credit line at bottom
    output_path: Where to save the PNG
    palette_index: 0-4, or None for random
    """
    if palette_index is None:
        palette_index = random.randint(0, len(PALETTES) - 1)
    palette = PALETTES[palette_index]

    img = Image.new("RGB", (W, H), palette["bg"])
    draw = draw_gradient_bg(img, palette)

    # Particles layer
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    draw_particles(odraw, palette)
    img.paste(Image.new("RGB", (W, H)), mask=overlay.split()[3])
    img = img.convert("RGBA")
    img.alpha_composite(overlay)
    img = img.convert("RGB")

    draw = ImageDraw.Draw(img)

    # ── TOP BADGE (GEÄNDERT FÜR AI FAILS) ──────────────────────
    badge_font = ImageFont.truetype(FONT_BOLD, 38)
    badge_text = "🤖  AI FAIL ALERT"
    bx, by = 80, 120
    r, g, b = palette["accent"]
    # Badge background
    bbox = draw.textbbox((bx, by), badge_text, font=badge_font)
    pad = 20
    draw.rounded_rectangle(
        [bbox[0]-pad, bbox[1]-pad//2, bbox[2]+pad, bbox[3]+pad//2],
        radius=12,
        fill=(r, g, b, 40)
    )
    draw.text((bx, by), badge_text, font=badge_font, fill=palette["accent"])

    # ── ACCENT LINE ────────────────────────────────────────────
    draw_glow_line(draw, palette, 260)

    # ── MAIN TEXT ──────────────────────────────────────────────
    fact_font_size = 72
    fact_font = ImageFont.truetype(FONT_BOLD, fact_font_size)

    max_text_w = W - 160  # 80px margin each side
    lines = wrap_text(fact_text, fact_font, max_text_w, draw)

    # If too many lines, reduce font size
    while len(lines) > 8 and fact_font_size > 48:
        fact_font_size -= 4
        fact_font = ImageFont.truetype(FONT_BOLD, fact_font_size)
        lines = wrap_text(fact_text, fact_font, max_text_w, draw)

    line_height = fact_font_size + 20
    total_text_h = len(lines) * line_height
    # Center vertically
    text_y_start = 320 + (1380 - total_text_h) // 2

    for i, line in enumerate(lines):
        y = text_y_start + i * line_height
        bbox = draw.textbbox((0, 0), line, font=fact_font)
        x = (W - (bbox[2] - bbox[0])) // 2
        # Shadow
        draw.text((x+3, y+3), line, font=fact_font, fill=(0, 0, 0, 80))
        # Main text
        draw.text((x, y), line, font=fact_font, fill=palette["text"])

    # ── BOTTOM ACCENT LINE ─────────────────────────────────────
    draw_glow_line(draw, palette, 1700)

    # ── CHANNEL TAG (GEÄNDERT FÜR AI FAILS) ────────────────────
    tag_font = ImageFont.truetype(FONT_BOLD, 42)
    tag_text = "AI Fails  •  New glitches every day"
    tbbox = draw.textbbox((0, 0), tag_text, font=tag_font)
    tx = (W - (tbbox[2] - tbbox[0])) // 2
    draw.text((tx, 1740), tag_text, font=tag_font, fill=palette["sub"])

    # ── SOURCE ─────────────────────────────────────────────────
    if source_text:
        src_font = ImageFont.truetype(FONT_REGULAR, 32)
        sbbox = draw.textbbox((0, 0), source_text, font=src_font)
        sx = (W - (sbbox[2] - sbbox[0])) // 2
        draw.text((sx, 1830), source_text, font=src_font,
                  fill=(150, 150, 150))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    print(f"  ✅ Image saved: {output_path}")
    return output_path


if __name__ == "__main__":
    # Test
    create_fact_image(
        "A Google AI once identified a simple turtle as a loaded rifle — and it was 100% sure about it.",
        "Source: AI Research Glitch",
        "output/test_ai_fail.png",
        palette_index=0
    )
