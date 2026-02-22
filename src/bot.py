"""
bot.py
The main orchestrator — runs the full pipeline:
1. Generate fact via GPT-4o
2. Create 1080x1920 image assets via Pillow
3. Render high-quality video via FFmpeg with Super-Sampling Anti-Jitter
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


from generate_image import create_fact_image, create_base_background, create_text_layer, PALETTES


from youtube_upload import refresh_access_token, upload_short


import archive_manager  # Archiv-Manager für Backup und Drive-Upload


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


    """Loads the last known state including new video settings."""
    try:


        # FIX: Symlink sicherheitshalber auflösen
        real_state_file = os.path.realpath(STATE_FILE)


        if os.path.exists(real_state_file):


            with open(real_state_file, 'r') as f:


                state = json.load(f)


                # Sicherstellen, dass neue Felder existieren (Additions)
                if "video_mode" not in state: state["video_mode"] = "classic"


                if "anim_type" not in state: state["anim_type"] = "zoom"


                if "duration" not in state: state["duration"] = 13.0


                if "drive_enabled" not in state: state["drive_enabled"] = True


                if "video_topic" not in state: state["video_topic"] = "random"


                return state


        return {"last_palette": 0, "total_videos": 0, "video_mode": "classic", "anim_type": "zoom", "duration": 13.0, "drive_enabled": True, "video_topic": "random"}


    except Exception as e:


        log(f"Could not load state: {e}", "WARN")


        return {"last_palette": 0, "total_videos": 0, "video_mode": "classic", "anim_type": "zoom", "duration": 13.0, "drive_enabled": True, "video_topic": "random"}


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


# ── The Upgraded Rendering Engine (Super-Sampling & Progress Bar) ──
def render_advanced_video(background_path: str, layer_paths: list, output_path: str, mode: str, anim_type: str, duration: float, palette_index: int):


    """
    Renders the video with Super-Sampling Anti-Jitter, multiple animation types and a Visible Progress Bar.
    """
    fps = 30


    total_frames = int(duration * fps)


    palette = PALETTES[palette_index]


    accent_hex = '#%02x%02x%02x' % palette["accent"]


    # 1. Background Music
    music_file = None


    if ASSETS_DIR.exists():


        mp3s = list(ASSETS_DIR.glob("*.mp3"))


        if mp3s:


            music_file = str(random.choice(mp3s))


            log(f"🎵 Selected background music: {Path(music_file).name}")


    # 2. Prepare FFmpeg Inputs
    inputs = ["-y", "-loop", "1", "-i", background_path]


    for l_path, _, _ in layer_paths:


        inputs.extend(["-i", l_path])


    if music_file:


        inputs.extend(["-i", music_file])


    else:


        inputs.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"])


    # 3. Build Filter Complex for Background Animation
    if anim_type == "zoom":


        bg_filter = (f"scale=2160:3840,zoompan=z='min(zoom+0.0010,1.15)':"
                     f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                     f"d={total_frames}:s=2160x3840,fps={fps},scale=1080:1920")


    elif anim_type == "pan":


        # FIX: Numerical pi and fixed syntax
        bg_filter = (f"scale=2160:3840,zoompan=z=1.15:"
                     f"x='(iw-iw/zoom)/2*(1+sin(2*3.141592*on/({total_frames*2})))':"
                     f"y='(ih-ih/zoom)/2':"
                     f"d={total_frames}:s=2160x3840,fps={fps},scale=1080:1920")


    else:


        # Static + Breathing Vignette for AI Fail Look
        bg_filter = f"scale=1080:1920,fps={fps},vignette='angle=3.141592/4+0.05*sin(2*3.141592*t/4)'"


    # PROGRESS BAR LOGIK: NUR bei statisch! y=H-430 für maximale Sichtbarkeit
    if anim_type == "static":
        filter_chains = [
            f"[0:v]{bg_filter}[bg_base]",
            f"color=c={accent_hex}@0.9:s=1080x10[bar_src]",
            f"[bg_base][bar_src]overlay=x='-W+(W*t/{duration})':y=H-430:shortest=1[bg_final]"
        ]
        last_v_label = "bg_final"
    else:
        # Kein Balken bei Cinematic Zoom oder Slow Pan
        filter_chains = [
            f"[0:v]{bg_filter}[bg_base]"
        ]
        last_v_label = "bg_base"


    # Overlays (Text-Layer)
    for i, (_, start, end) in enumerate(layer_paths):


        next_label = f"ovl{i}"


        filter_chains.append(
            f"[{last_v_label}][{i+1}:v]overlay=enable='between(t,{start},{end})'[ {next_label}]"
        )


        last_v_label = next_label


    filter_chains.append(f"[{last_v_label}]format=yuv420p[outv]")


    # 4. Execute FFmpeg
    cmd = [
        "ffmpeg", *inputs, "-filter_complex", ";".join(filter_chains),
        "-map", "[outv]", "-map", f"{len(layer_paths)+1}:a",
        "-c:v", "libx264", "-preset", "medium", "-tune", "stillimage",
        "-t", str(duration), "-c:a", "aac", "-b:a", "192k", "-shortest",
        output_path
    ]


    log(f"🎬 Rendering {mode} with {anim_type} animation ({duration}s)...")


    try:


        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


        log(f"✅ Rendering complete.")


    except subprocess.CalledProcessError as e:


        log(f"❌ FFmpeg failed:\n{e.stderr}", "ERROR")


        raise RuntimeError("FFmpeg rendering failed")


# ── Main Pipeline ──────────────────────────────────────────────
def run(skip_youtube=False, topic=None):


    log("=" * 50)


    log("🚀 AI Fails Bot starting run")


    log("=" * 50)


    config = get_config()


    state  = load_state()


    # FIX: Falls kein manuelles Thema übergeben wurde, das gespeicherte Standard-Thema nutzen
    if topic is None:
        topic = state.get("video_topic", "random")
        if topic == "random": topic = None


    mode = state.get("video_mode", "classic")


    anim = state.get("anim_type", "zoom")


    duration = float(state.get("duration", 13.0))


    palette_index = (state.get("last_palette", 0) + 1) % 5


    state["last_palette"] = palette_index


    run_date  = datetime.now().strftime("%Y-%m-%d")


    run_time  = datetime.now().strftime("%H%M%S")


    base_name = f"{run_date}_AIFail_{run_time}"


    temp_assets = []


    video_path  = f"/tmp/{base_name}.mp4"


    try:


        log(f"📝 Step 1/4: Generating content (Mode: {mode}, Anim: {anim}, Topic: {topic or 'Rotation'})...")


        fact_data = generate_fact(config["OPENAI_API_KEY"], topic=topic)


        log(f"   Topic: {fact_data.get('topic', 'AI Fails')}")


        layers = []


        # FIX: Wenn Pan gewählt ist, behandeln wir auch "Classic" als Layer-System
        if mode == "classic" and anim != "pan":


            img_path = f"/tmp/{base_name}_full.png"


            create_fact_image(fact_data["fact"], fact_data.get("source", ""), img_path, palette_index)


            temp_assets.append(img_path)


            render_advanced_video(img_path, [], video_path, "classic", anim, duration, palette_index)


        elif mode == "three_parts" or (mode == "classic" and anim == "pan"):


            bg_path = f"/tmp/{base_name}_bg.png"


            create_base_background(palette_index, fact_data.get("source", ""), bg_path)


            temp_assets.append(bg_path)


            if mode == "classic":


                parts = [fact_data["fact"]]


                timings = [(0, duration)]


            else:


                parts = fact_data.get("parts", ["Hook", fact_data["fact"], "Trigger"])


                timings = [(0, 1.5), (1.5, duration - 2.0), (duration - 2.0, duration)]


            for i, text in enumerate(parts):


                l_path = f"/tmp/{base_name}_p{i}.png"


                create_text_layer(text, palette_index, l_path)


                temp_assets.append(l_path)


                layers.append((l_path, timings[i][0], timings[i][1]))


            render_advanced_video(bg_path, layers, video_path, mode, anim, duration, palette_index)


        elif mode == "word_by_word":


            bg_path = f"/tmp/{base_name}_bg.png"


            create_base_background(palette_index, fact_data.get("source", ""), bg_path)


            temp_assets.append(bg_path)


            words = fact_data.get("words", fact_data["fact"].split())


            chunks = [" ".join(words[i:i+3]) for i in range(0, len(words), 3)]


            chunk_dur = duration / len(chunks)


            for i, chunk in enumerate(chunks):


                l_path = f"/tmp/{base_name}_w{i}.png"


                create_text_layer(chunk, palette_index, l_path)


                temp_assets.append(l_path)


                start = i * chunk_dur
                # FIX: Letzter Chunk bleibt bis zum Ende stehen für bessere Lesbarkeit
                end = duration if i == len(chunks) - 1 else (i + 1) * chunk_dur


                layers.append((l_path, start, end))


            render_advanced_video(bg_path, layers, video_path, "word_by_word", anim, duration, palette_index)


        if not skip_youtube:


            log("📤 Step 4/4: Uploading to YouTube API...")


            access_token = refresh_access_token(config["YOUTUBE_CLIENT_ID"], config["YOUTUBE_CLIENT_SECRET"], config["YOUTUBE_REFRESH_TOKEN"])


            topic_tag = fact_data.get('topic', 'AIFails').replace(" ", "")


            video_id = upload_short(video_path, fact_data["title"], fact_data["description"], fact_data.get("tags", []) + [topic_tag], access_token)


            state["total_videos"]  = state.get("total_videos", 0) + 1


            state["last_run"], state["last_video_id"] = base_name, video_id


            save_state(state)


            log(f"✅ SUCCESS! Published: https://youtube.com/shorts/{video_id}")


        else:


            state["total_videos"]  = state.get("total_videos", 0) + 1


            save_state(state)


        try:


            time.sleep(2) 


            archive_manager.move_to_archive(video_path, fact_data, temp_assets[0])


            archive_manager.cleanup_old_videos(30)


            log("📦 Archiviert.")


        except Exception as e:


            log(f"⚠️ Archiv-Warnung: {e}", "WARN")


    except Exception as e:


        log(f"❌ Pipeline failed: {e}", "ERROR")


        log(traceback.format_exc(), "ERROR")


        sys.exit(1)


    finally:


        for path in temp_assets + [video_path]:


            try:


                if os.path.exists(path):


                    os.remove(path)


                    log(f"🧹 Cleaned up temp: {path}")


            except Exception: pass


if __name__ == "__main__":


    should_skip = "--skip-youtube" in sys.argv
    
    # Lese das Thema aus den Kommandozeilen-Argumenten
    target_topic = None
    for arg in sys.argv:
        if arg.startswith("--topic="):
            target_topic = arg.split("=")[1]
            if target_topic == "random": target_topic = None
            
    run(skip_youtube=should_skip, topic=target_topic)
