"""
generate_image.py
Erstellt hochauflösende 1080x1920 Assets für AI Fails.
Diese Pro-Version enthält:
1. Exakte horizontale Zentrierung (bbox-Fix)
2. Höhere vertikale Text-Position (Zentrum y=850) für Progress Bar Platz
3. Den klassischen dicken farbigen Balken oben (statt Text)
4. Vollständige Layer-Unterstützung für Multi-Frame-Rendering
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap
import math
import random
import os

# Pfade zu den System-Schriftarten
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# Standard-Auflösung für YouTube Shorts
W, H = 1080, 1920

# ── ERWEITERTE FARBPALETTEN (PRO) ─────────────────────────────
# Jede Palette enthält Background, Accent (Balken/Linien), Text und Sub-Text Farben
PALETTES = [
    {
        "bg": (15, 15, 5),      # Deep Dark
        "accent": (255, 215, 0), # AI Warning Gold
        "text": (255, 255, 255), 
        "sub": (255, 235, 120)
    },
    {
        "bg": (20, 5, 5),       # Dark Red
        "accent": (255, 75, 75),  # Error Red
        "text": (255, 255, 255), 
        "sub": (255, 150, 150)
    },
    {
        "bg": (5, 5, 25),       # Cyber Blue
        "accent": (255, 0, 255), # Glitch Pink
        "text": (255, 255, 255), 
        "sub": (200, 150, 255)
    },
    {
        "bg": (2, 10, 5),       # Matrix Black
        "accent": (50, 255, 50),  # Terminal Green
        "text": (255, 255, 255), 
        "sub": (150, 255, 150)
    },
    {
        "bg": (10, 0, 20),      # Void Purple
        "accent": (0, 255, 255),  # Neon Cyan
        "text": (255, 255, 255), 
        "sub": (150, 255, 255)
    },
]

# ── HILFSFUNKTIONEN FÜR EFFEKTE ──────────────────────────────

def draw_particles(draw, palette, count=65):
    """Zeichnet subtile glühende Punkte im Hintergrund für mehr Tiefe."""
    for _ in range(count):
        x = random.randint(0, W)
        y = random.randint(0, H)
        size = random.randint(1, 4)
        alpha = random.randint(40, 130)
        r, g, b = palette["accent"]
        draw.ellipse([x-size, y-size, x+size, y+size], fill=(r, g, b, alpha))

def draw_gradient_bg(img, palette):
    """Erstellt einen sauberen vertikalen Verlaufshintergrund."""
    draw = ImageDraw.Draw(img, "RGBA")
    r1, g1, b1 = palette["bg"]
    for y in range(H):
        # Zentrierter Lichteffekt (Sinus-Kurve)
        factor = 1.0 + 0.25 * math.sin(math.pi * y / H)
        r = min(255, int(r1 * factor))
        g = min(255, int(g1 * factor))
        b = min(255, int(b1 * factor))
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    return draw

def draw_glow_line(draw, palette, y_pos):
    """Zeichnet eine glühende horizontale Trennlinie mit Weichzeichnungseffekt."""
    r, g, b = palette["accent"]
    for thickness in [7, 4, 2]:
        alpha = 55 if thickness == 7 else (110 if thickness == 4 else 240)
        draw.line([(90, y_pos), (W-90, y_pos)], fill=(r, g, b, alpha), width=thickness)

def wrap_text(text, font, max_width, draw):
    """Word-wrap Logik um Text innerhalb der Seitenränder zu halten."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= max_width:
            current = test
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)
    return lines

# ── HAUPTFUNKTIONEN ──────────────────────────────────────────

def create_fact_image(fact_text, source_text, output_path, palette_index=None):
    """
    Erstellt das vollständige Asset für den 'Classic' Modus.
    """
    if palette_index is None:
        palette_index = random.randint(0, len(PALETTES) - 1)
    palette = PALETTES[palette_index % len(PALETTES)]

    img = Image.new("RGB", (W, H), palette["bg"])
    draw = draw_gradient_bg(img, palette)

    # FX Layer für Partikel
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    draw_particles(odraw, palette)
    img.paste(Image.new("RGB", (W, H)), mask=overlay.split()[3])
    img = img.convert("RGBA"); img.alpha_composite(overlay); img = img.convert("RGB")
    
    draw = ImageDraw.Draw(img)

    # 1. TOP BAR (Der dicke Balken oben statt Text)
    bar_w, bar_h = 340, 65
    bx = (W - bar_w) // 2
    by = 135
    draw.rounded_rectangle([bx, by, bx+bar_w, by+bar_h], radius=18, fill=palette["accent"])
    
    # Trennlinie unter dem Balken
    draw_glow_line(draw, palette, 280)

    # 2. MAIN TEXT BLOCK
    fact_font_size = 76
    fact_font = ImageFont.truetype(FONT_BOLD, fact_font_size)
    max_text_w = W - 220 # 110px Rand auf jeder Seite
    lines = wrap_text(fact_text, fact_font, max_text_w, draw)

    # Font-Scaling: Falls zu viele Zeilen, verkleinern wir die Schrift
    while len(lines) > 8 and fact_font_size > 50:
        fact_font_size -= 4
        fact_font = ImageFont.truetype(FONT_BOLD, fact_font_size)
        lines = wrap_text(fact_text, fact_font, max_text_w, draw)

    line_height = fact_font_size + 22
    total_text_h = len(lines) * line_height
    
    # VISUAL CENTER FIX: Text deutlich höher setzen (Zentrum bei y=850)
    # Das hält den Text fern vom Fortschrittsbalken am unteren Ende.
    text_y_start = 850 - (total_text_h // 2)

    for i, line in enumerate(lines):
        y = text_y_start + i * line_height
        bbox = draw.textbbox((0, 0), line, font=fact_font)
        # Exakte horizontale Zentrierung (Width - (Rechts - Links)) / 2
        x = (W - (bbox[2] - bbox[0])) // 2
        # Schlagschatten für bessere Lesbarkeit
        draw.text((x+4, y+4), line, font=fact_font, fill=(0, 0, 0, 110))
        draw.text((x, y), line, font=fact_font, fill=palette["text"])

    # Untere Trennlinie
    draw_glow_line(draw, palette, 1680)

    # 3. BRANDING & SOCIAL TAG
    tag_font = ImageFont.truetype(FONT_BOLD, 44)
    tag_text = "AI Fails & Glitches • Join the Chaos"
    tbbox = draw.textbbox((0, 0), tag_text, font=tag_font)
    tx = (W - (tbbox[2] - tbbox[0])) // 2
    draw.text((tx, 1725), tag_text, font=tag_font, fill=palette["sub"])

    if source_text:
        src_font = ImageFont.truetype(FONT_REGULAR, 34)
        sbbox = draw.textbbox((0, 0), source_text, font=src_font)
        sx = (W - (sbbox[2] - sbbox[0])) // 2
        draw.text((sx, 1825), source_text, font=src_font, fill=(140, 140, 140))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def create_base_background(palette_index, source_text, output_path):
    """
    Erstellt den Hintergrund-Layer (Balken & Branding) für Layer-Animationen.
    """
    palette = PALETTES[palette_index % len(PALETTES)]
    img = Image.new("RGB", (W, H), palette["bg"])
    draw = draw_gradient_bg(img, palette)
    
    # Balken oben
    bar_w, bar_h = 340, 65
    draw.rounded_rectangle([(W-bar_w)//2, 135, (W+bar_w)//2, 135+bar_h], radius=18, fill=palette["accent"])
    
    draw_glow_line(draw, palette, 280)
    draw_glow_line(draw, palette, 1680)

    # Branding
    tag_font = ImageFont.truetype(FONT_BOLD, 44)
    tag_text = "AI Fails & Glitches • Join the Chaos"
    tx = (W - draw.textbbox((0, 0), tag_text, font=tag_font)[2]) // 2
    draw.text((tx, 1725), tag_text, font=tag_font, fill=palette["sub"])

    if source_text:
        src_font = ImageFont.truetype(FONT_REGULAR, 34)
        sx = (W - draw.textbbox((0, 0), source_text, font=src_font)[2]) // 2
        draw.text((sx, 1825), source_text, font=src_font, fill=(140, 140, 140))

    img.save(output_path, "PNG")
    return output_path


def create_text_layer(text, palette_index, output_path):
    """
    Erstellt einen transparenten Layer, der NUR den Text enthält (Zentriert bei y=850).
    """
    palette = PALETTES[palette_index % len(PALETTES)]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    fact_font_size = 76
    fact_font = ImageFont.truetype(FONT_BOLD, fact_font_size)
    lines = wrap_text(text, fact_font, W - 220, draw)
    
    line_height = fact_font_size + 22
    text_y_start = 850 - ((len(lines) * line_height) // 2)

    for i, line in enumerate(lines):
        y = text_y_start + i * line_height
        bbox = draw.textbbox((0, 0), line, font=fact_font)
        x = (W - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, font=fact_font, fill=palette["text"])

    img.save(output_path, "PNG")
    return output_path

# ── TEST BLOCK ───────────────────────────────────────────────

if __name__ == "__main__":
    # Testlauf zum Prüfen der Positionierung
    test_text = "An AI once classified a standard yellow school bus as a 'Giant Banana' with 99% confidence."
    create_fact_image(test_text, "Source: AI Research", "output/test_ai_fail.png", palette_index=0)
    print("✅ Pro-Testbild erstellt in output/test_ai_fail.png")
