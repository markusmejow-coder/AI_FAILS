"""
generate_video.py
Turns a static fact image into a 30-second YouTube Short
with a slow zoom-in effect using FFmpeg.
No external dependencies needed beyond FFmpeg.
"""

import subprocess
import os
import random


def create_short_video(image_path: str, output_path: str,
                       duration: int = 13) -> str:
    """
    Creates a 1080x1920 MP4 Short from a static image.
    Uses a slow Ken Burns zoom effect to keep it dynamic.
    
    image_path : Path to the 1080x1920 PNG
    output_path: Where to save the .mp4
    duration   : Video length in seconds (default 13)
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Ken Burns effect: slow zoom from 1.0x to 1.08x
    zoom_speed = 0.08 / (duration * 25)
    zoom_filter = (
        f"zoompan=z='zoom+{zoom_speed}':x='iw/2-(iw/zoom/2)':"
    f"y='ih/2-(ih/zoom/2)':d={duration*25}:s=1080x1920:fps=25"
    )

    # Add a subtle vignette on top
    vignette = "vignette=PI/4"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-vf", f"{zoom_filter},{vignette}",
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path
    ]

    print(f"  🎬 Generating video: {output_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ❌ FFmpeg error: {result.stderr[-500:]}")
        raise RuntimeError("FFmpeg failed")

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"  ✅ Video saved: {output_path} ({size_mb:.1f} MB)")
    return output_path


if __name__ == "__main__":
    create_short_video(
        "/home/claude/factbot/output/test_frame.png",
        "/home/claude/factbot/output/test_short.mp4",
        duration=10  # short test
    )
