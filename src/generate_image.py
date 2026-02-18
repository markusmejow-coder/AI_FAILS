"""
generate_image.py
Creates a 1200x2133 (high res) AI Fail image for YouTube Shorts.
This higher resolution prevents jitter during the FFmpeg zoompan.
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap
import math
import random
import os

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# High-Res für Anti-Jitter (Faktor 1.11 zu 1080x1920)
W, H = 1200, 2133

# Color palettes — KI rotiert automatisch
PALETTES = [
    {"bg": (8, 8, 20),    "accent": (120, 80, 255),  "text": (255, 255, 255), "sub": (180, 160, 255)},
    {"bg": (5, 15, 10),   "accent": (0, 220, 120),   "text": (255, 255, 255), "sub": (150, 255, 200)},
    {"bg": (20, 5, 5),    "accent": (255, 60, 60),    "text": (255, 255, 255), "sub": (255, 160, 160)},
    {"bg": (5, 10, 25),   "accent": (0, 180, 255),   "text": (255, 255, 255), "sub": (140, 210, 255)},
    {"bg": (15, 10, 5),   "accent": (255, 160, 0),   "text": (255, 255, 255), "sub": (255, 210, 120)},
]


def draw_particles(draw, palette, count=70):
    """Draw subtle glowing dots in background."""
    for _ in range(count):
        x = random.randint(0, W)
        y = random.randint(0, H)
        size = random.randint(1, 5)
        alpha = random.randint(40, 140)
        r, g, b = palette["accent"]
        draw.ellipse([x-size, y-size, x+size, y+size],
                     fill=(r, g, b, alpha))


def draw_gradient_bg(img, palette):
    """Draw a vertical gradient background."""
    draw = ImageDraw.Draw(img, "RGBA")
    r1, g1, b1 = palette["bg"]
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
    for thickness in [8, 5, 3]:
        alpha = 60 if thickness == 8 else (120 if thickness == 5 else 255)
        draw.line([(90, y_pos), (W-90, y_pos)],
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
    Creates a 1200x2133 high-res AI Fail image.
    """
    if palette_index is None:
        palette_index = random.randint(0, len(PALETTES) - 1)
    palette = PALETTES[palette_index]

    img = Image.new("RGB", (W, H), palette["bg"])
    draw = draw_gradient_bg(img, palette)

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    draw_particles(odraw, palette)
    img.paste(Image.new("RGB", (W, H)), mask=overlay.split()[3])
    img = img.convert("RGBA")
    img.alpha_composite(overlay)
    img = img.convert("RGB")

    draw = ImageDraw.Draw(img)

    # ── TOP BADGE (Scaled to High-Res) ─────────────────────────
    badge_font = ImageFont.truetype(FONT_BOLD, 42)
    badge_text = "🤖  AI FAIL ALERT"
    bx, by = 90, 135
    r, g, b = palette["accent"]
    bbox = draw.textbbox((bx, by), badge_text, font=badge_font)
    pad = 22
    draw.rounded_rectangle(
        [bbox[0]-pad, bbox[1]-pad//2, bbox[2]+pad, bbox[3]+pad//2],
        radius=14, fill=(r, g, b, 40)
    )
    draw.text((bx, by), badge_text, font=badge_font, fill=palette["accent"])

    draw_glow_line(draw, palette, 290)

    # ── MAIN TEXT ──────────────────────────────────────────────
    fact_font_size = 80
    fact_font = ImageFont.truetype(FONT_BOLD, fact_font_size)

    max_text_w = W - 180 
    lines = wrap_text(fact_text, fact_font, max_text_w, draw)

    while len(lines) > 8 and fact_font_size > 54:
        fact_font_size -= 4
        fact_font = ImageFont.truetype(FONT_BOLD, fact_font_size)
        lines = wrap_text(fact_text, fact_font, max_text_w, draw)

    line_height = fact_font_size + 24
    total_text_h = len(lines) * line_height
    text_y_start = 360 + (1530 - total_text_h) // 2

    for i, line in enumerate(lines):
        y = text_y_start + i * line_height
        bbox = draw.textbbox((0, 0), line, font=fact_font)
        x = (W - (bbox[2] - bbox[0])) // 2
        draw.text((x+4, y+4), line, font=fact_font, fill=(0, 0, 0, 80))
        draw.text((x, y), line, font=fact_font, fill=palette["text"])

    draw_glow_line(draw, palette, 1890)

    # ── BRANDING ───────────────────────────────────────────────
    tag_font = ImageFont.truetype(FONT_BOLD, 46)
    tag_text = "AI Fails  •  New glitches every day"
    tbbox = draw.textbbox((0, 0), tag_text, font=tag_font)
    tx = (W - (tbbox[2] - tbbox[0])) // 2
    draw.text((tx, 1935), tag_text, font=tag_font, fill=palette["sub"])

    if source_text:
        src_font = ImageFont.truetype(FONT_REGULAR, 36)
        sbbox = draw.textbbox((0, 0), source_text, font=src_font)
        sx = (W - (sbbox[2] - sbbox[0])) // 2
        draw.text((sx, 2035), source_text, font=src_font, fill=(150, 150, 150))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    print(f"  ✅ High-Res Image saved: {output_path}")
    return output_path

if __name__ == "__main__":
    create_fact_image(
        "A Google AI once identified a simple turtle as a loaded rifle — and it was 100% sure about it.",
        "Source: AI Research Glitch",
        "output/test_jitter_fix.png",
        palette_index=0
    )
