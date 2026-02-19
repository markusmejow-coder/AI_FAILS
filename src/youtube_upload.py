"""
youtube_upload.py
Uploads a video to YouTube as a Short using YouTube Data API v3.
Uses OAuth2 for authentication — one-time setup, then runs forever.
"""

import json
import os
import urllib.request
import urllib.parse
import urllib.error
import mimetypes


YOUTUBE_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
YOUTUBE_TOKEN_URL  = "https://oauth2.googleapis.com/token"


def refresh_access_token(client_id: str, client_secret: str,
                          refresh_token: str) -> str:
    """Get a fresh access token using the refresh token."""
    payload = urllib.parse.urlencode({
        "client_id":     client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type":    "refresh_token"
    }).encode("utf-8")

    req = urllib.request.Request(
        YOUTUBE_TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    if "access_token" not in data:
        raise RuntimeError(f"Token refresh failed: {data}")

    print("  🔑 Access token refreshed")
    return data["access_token"]


def upload_short(video_path: str, title: str, description: str,
                 tags: list, access_token: str) -> str:
    # Metadata
    # Wir fügen themenspezifische Tags hinzu und stellen sicher, dass #Shorts enthalten ist
    snippet = {
        "title":       title[:100], 
        "description": f"{description[:4500]}\n\n#Shorts #MindBlown #Facts #AI",
        "tags":        tags[:15], # YouTube erlaubt max. 500 Zeichen an Tags insgesamt
        "categoryId":  "28"  # Science & Technology
    }
    
    # Hier setzen wir die KI-Kennzeichnung auf True
    status = {
        "privacyStatus":           "public",
        "selfDeclaredMadeForKids": False,
        "selfDeclaredMadeForAIContent": True  # NEU: KI-Kennzeichnung für YouTube 2026
    }

    metadata = json.dumps({
        "snippet": snippet,
        "status":  status
    }).encode("utf-8")

    file_size = os.path.getsize(video_path)

    # Step 1: Initiate resumable upload
    init_url = (
        f"{YOUTUBE_UPLOAD_URL}"
        f"?uploadType=resumable&part=snippet,status"
    )
    init_req = urllib.request.Request(
        init_url,
        data=metadata,
        headers={
            "Authorization":           f"Bearer {access_token}",
            "Content-Type":            "application/json; charset=UTF-8",
            "X-Upload-Content-Type":   "video/mp4",
            "X-Upload-Content-Length": str(file_size)
        },
        method="POST"
    )

    print(f"  📤 Initiating upload for: {os.path.basename(video_path)}")
    with urllib.request.urlopen(init_req, timeout=30) as resp:
        upload_url = resp.headers.get("Location")

    if not upload_url:
        raise RuntimeError("No upload URL received from YouTube")

    # Step 2: Upload the video file
    print(f"  ⬆️  Uploading {file_size / 1024 / 1024:.1f} MB...")
    with open(video_path, "rb") as f:
        video_data = f.read()

    upload_req = urllib.request.Request(
        upload_url,
        data=video_data,
        headers={
            "Authorization":  f"Bearer {access_token}",
            "Content-Type":   "video/mp4",
            "Content-Length": str(file_size)
        },
        method="PUT"
    )

    with urllib.request.urlopen(upload_req, timeout=120) as resp:
        result = json.loads(resp.read().decode())

    video_id = result.get("id")
    if not video_id:
        raise RuntimeError(f"Upload failed: {result}")

    print(f"  ✅ Uploaded! https://youtube.com/shorts/{video_id}")
    return video_id


def get_oauth_url(client_id: str) -> str:
    """
    Step 1 of one-time OAuth setup.
    Open this URL in browser, authorize, copy the code.
    """
    params = urllib.parse.urlencode({
        "client_id":     client_id,
        "redirect_uri":  "urn:ietf:wg:oauth:2.0:oob",
        "response_type": "code",
        "scope":         "https://www.googleapis.com/auth/youtube.upload",
        "access_type":   "offline",
        "prompt":        "consent"
    })
    return f"https://accounts.google.com/o/oauth2/auth?{params}"


def exchange_code_for_tokens(client_id: str, client_secret: str,
                              auth_code: str) -> dict:
    """
    Step 2 of one-time OAuth setup.
    Exchange the auth code for access + refresh tokens.
    Save the refresh_token — you need it forever.
    """
    payload = urllib.parse.urlencode({
        "client_id":     client_id,
        "client_secret": client_secret,
        "code":          auth_code,
        "redirect_uri":  "urn:ietf:wg:oauth:2.0:oob",
        "grant_type":    "authorization_code"
    }).encode("utf-8")

    req = urllib.request.Request(
        YOUTUBE_TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        tokens = json.loads(resp.read().decode())

    return tokens


if __name__ == "__main__":
    print("YouTube uploader ready.")
    print("Run setup.py first to get your OAuth refresh token.")
