"""
bot.py
The main orchestrator — runs the full pipeline:
1. Generate fact via GPT-4o
2. Create 1080x1920 image via Pillow
3. Render high-quality 30s video via FFmpeg (Local Rendering)
4. Upload to YouTube as a Short
5. Log everything & Manage State

Runs as a scheduled job on Railway.
"""

import os
import sys
import json
import time
import random
import traceback
import subprocess
from datetime import datetime
from pathlib import Path

# Add src to path to ensure imports work
sys.path.insert(0, os.path.dirname(__file__))

# Import specialized modules for text and image
from generate_fact import generate_fact
from generate_image import create_fact_image
from youtube_upload import refresh_access_token, upload_short
import archive_manager  # NEU: Archiv-Manager importieren

# ── Configuration & Constants ─────────────────────────────────
LOG_FILE = Path("/app/logs/bot.log")
STATE_FILE = Path("/app/logs/state.json")
ASSETS_DIR = Path("/app/assets")  # Directory for background music

def get_config() -> dict:
    """Validates and returns environment variables."""
    required = [
        "OPENAI_API_KEY",
        "YOUTUBE_CLIENT_ID",
        "YOUTUBE_CLIENT_SECRET",
        "YOUTUBE_REFRESH_TOKEN"
    ]
    config = {}
    missing = []

    for key in required:
        val = os.environ.get(key)
        if not val:
            missing.append(key)
        config[key] = val

    if missing:
        print(f"❌ [CRITICAL] Missing environment variables: {', '.join(missing)}")
        print("   Add them in Railway → Your Project → Variables")
        sys.exit(1)

    return config

# ── Logging System ─────────────────────────────────────────────
def log(message: str, level: str = "INFO"):
    """Writes logs to console and file with timestamps."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}"
    print(line)
    try:
        # FIX: Symlink auflösen, um 'File exists' Fehler zu vermeiden
        real_log_dir = os.path.realpath(LOG_FILE.parent)
        os.makedirs(real_log_dir, exist_ok=True)
        
        real_log_file = os.path.join(real_log_dir, LOG_FILE.name)
        with open(real_log_file, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass  # Fail silently on log write to avoid crashing the bot

# ── State Management (Persistence) ─────────────────────────────
def load_state() -> dict:
    """Loads the last known state from the persistent volume."""
    try:
        # FIX: Symlink sicherheitshalber auflösen
        real_state_file = os.path.realpath(STATE_FILE)
        if os.path.exists(real_state_file):
            with open(real_state_file, 'r') as f:
                return json.load(f)
        return {"last_palette": 0, "total_videos": 0}
    except Exception as e:
        log(f"Could not load state: {e}", "WARN")
        return {"last_palette": 0, "total_videos": 0}

def save_state(state: dict):
    """Saves the current state to the persistent volume."""
    try:
        # FIX: Echten Pfad nutzen, um Ordner zu erstellen
        real_state_dir = os.path.realpath(STATE_FILE.parent)
        os.makedirs(real_state_dir, exist_ok=True)
        
        real_state_file = os.path.join(real_state_dir, STATE_FILE.name)
        with open(real_state_file, "w") as f:
            f.write(json.dumps(state, indent=2))
    except Exception as e:
        log(f"Could not save state: {e}", "WARN")

# ── The "Muscle": FFmpeg Rendering Engine ──────────────────────
def render_robust_video(image_path: str, output_path: str, duration: float = 15.0):
    """
    Renders the video locally using FFmpeg with the 'Anti-Jitter' fix.
    
    Args:
        image_path: Path to the generated PNG.
        output_path: Path where the MP4 should be saved.
        duration: Target duration in seconds.
    """
    
    # 1. Select random background music
    music_file = None
    if ASSETS_DIR.exists():
        mp3s = list(ASSETS_DIR.glob("*.mp3"))
        if mp3s:
            music_file = str(random.choice(mp3s))
            log(f"🎵 Selected background music: {Path(music_file).name}")
    
    # 2. Prepare FFmpeg Command
    # We use a filter complex to ensure smooth zooming without pixel jitter.
    # Key fix: s=1080x1920 in zoompan and exact centering logic.
    
    fps = 30
    total_frames = int(duration * fps)
    
    # Base inputs
    inputs = ["-y", "-loop", "1", "-i", image_path]
    
    # Add audio input if available
    if music_file:
        inputs.extend(["-i", music_file])
    else:
        # Generate silent audio if no music found (prevents upload errors)
        inputs.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"])

    # filter_complex string
    # z='min(zoom+0.0010,1.15)': Very slow, cinematic zoom (ORIGINAL WERT BEIBEHALTEN)
    # x='iw/2-(iw/zoom/2)': Centers X axis perfectly
    # y='ih/2-(ih/zoom/2)': Centers Y axis perfectly
    # s=1080x1920: Forces high internal resolution to prevent aliasing/jitter
    
    vf_filter = (
        f"zoompan=z='min(zoom+0.0010,1.15)':"
        f"x='iw/2-(iw/zoom/2)':"
        f"y='ih/2-(ih/zoom/2)':"
        f"d={total_frames}:"
        f"s=1080x1920,"
        f"fps={fps},"
        f"format=yuv420p"
    )

    cmd = [
        "ffmpeg",
        *inputs,
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-preset", "medium",   # Balance between speed and compression
        "-tune", "stillimage", # Optimization for static images
        "-t", str(duration),   # Exact duration
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",           # Stop when the shortest input (video) ends
        "-pix_fmt", "yuv420p", # Ensure compatibility with all players
        output_path
    ]

    log(f"🎬 Rendering video with FFmpeg ({duration}s)...")
    
    try:
        # Run FFmpeg and capture output for debugging if needed
        result = subprocess.run(
            cmd, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        log(f"✅ FFmpeg rendering complete.")
    except subprocess.CalledProcessError as e:
        log(f"❌ FFmpeg failed with error:\n{e.stderr}", "ERROR")
        raise RuntimeError("FFmpeg rendering failed")

# ── Main Pipeline ──────────────────────────────────────────────
def run(skip_youtube=False):
    log("=" * 50)
    log("🚀 FactDrop Bot starting daily run")
    log("=" * 50)

    config = get_config()
    state  = load_state()

    # Rotate palette for visual variety
    palette_index = (state.get("last_palette", 0) + 1) % 5
    state["last_palette"] = palette_index

    # --- HIER IST DIE NEUE NAMENSGEBUNG ---
    run_date  = datetime.now().strftime("%Y-%m-%d")
    run_time  = datetime.now().strftime("%H%M%S")
    base_name = f"{run_date}_AIFails_{run_time}"

    image_path  = f"/tmp/{base_name}.png"
    video_path  = f"/tmp/{base_name}.mp4"
    # --------------------------------------

    try:
        # ── Step 1: Generate Fact (The Brain) ──────────────────
        log("📝 Step 1/4: Generating fact content...")
        fact_data = generate_fact(config["OPENAI_API_KEY"])
        
        log(f"   Topic: {fact_data.get('topic', 'General')}")
        log(f"   Fact:  {fact_data['fact'][:60]}...")

        # ── Step 2: Create Image (The Design) ──────────────────
        log("🎨 Step 2/4: Rendering static asset...")
        create_fact_image(
            fact_text   = fact_data["fact"],
            source_text = fact_data.get("source", ""),
            output_path = image_path,
            palette_index = palette_index
        )

        # ── Step 3: Create Video (The Muscle) ──────────────────
        # Uses the integrated robust renderer defined above
        render_robust_video(
            image_path  = image_path,
            output_path = video_path,
            duration    = 13.0  # Optimal for Shorts retention
        )

        # ── Step 4: Upload to YouTube (The Distribution) ───────
        if not skip_youtube:
            log("📤 Step 4/4: Uploading to YouTube API...")

            access_token = refresh_access_token(
                client_id     = config["YOUTUBE_CLIENT_ID"],
                client_secret = config["YOUTUBE_CLIENT_SECRET"],
                refresh_token = config["YOUTUBE_REFRESH_TOKEN"]
            )

            # Dynamische Hashtags basierend auf dem Thema (Topic) generieren
            topic_tag = fact_data.get('topic', 'Knowledge').replace(" ", "")
            additional_tags = [topic_tag, "AIFails", "Glitches"]
            
            video_id = upload_short(
                video_path   = video_path,
                title        = fact_data["title"],
                description  = fact_data["description"],
                tags         = fact_data.get("tags", []) + additional_tags,
                access_token = access_token
            )

            # ── Success & State Update ─────────────────────────────
            state["total_videos"]  = state.get("total_videos", 0) + 1
            state["last_run"]      = base_name
            state["last_video_id"] = video_id
            save_state(state)

            log("=" * 50)
            log(f"✅ SUCCESS! Video #{state['total_videos']} published")
            log(f"   URL: https://youtube.com/shorts/{video_id}")
            log(f"   Title: {fact_data['title']}")
            log("=" * 50)
        else:
            log("⏭️ Step 4/4: SKIPPED YouTube Upload (Test Mode)")
            
            # State Update for Test Mode
            state["total_videos"]  = state.get("total_videos", 0) + 1
            state["last_run"]      = base_name
            save_state(state)

            log("=" * 50)
            log(f"✅ SUCCESS! Test-Video #{state['total_videos']} generated (No Upload)")
            log(f"   Title: {fact_data['title']}")
            log("=" * 50)

        # ── Archivierung (Director Move) ──────────────────────
        try:
            # WICHTIG: Wir übergeben jetzt fact_data, damit Titel/Beschreibung 
            # für den Copy-Button in der archive.json landen
            # NEU: image_path wird mit übergeben
            archive_manager.move_to_archive(video_path, fact_data, image_path)
            
            archive_manager.cleanup_old_videos(30)
            log("📦 Video, Bild & Metadaten erfolgreich archiviert")
        except Exception as e:
            log(f"⚠️ Archivierung fehlgeschlagen: {e}", "WARN")

    except Exception as e:
        log(f"❌ Pipeline failed: {e}", "ERROR")
        log(traceback.format_exc(), "ERROR")
        sys.exit(1)

    finally:
        # Cleanup: Always remove temp files to save disk space
        for path in [image_path, video_path]:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    log(f"🧹 Cleaned up temp: {path}")
            except Exception:
                pass

if __name__ == "__main__":
    # Prüft, ob das Argument beim Starten übergeben wurde
    should_skip = "--skip-youtube" in sys.argv
    run(skip_youtube=should_skip)
