import os
import shutil
import time
import json
import requests
from datetime import datetime

# Wir leihen uns die fertige Token-Funktion aus deinem YouTube-Skript!
from youtube_upload import refresh_access_token

# Pfad zum persistenten Volume & Logs
ARCHIVE_DIR = "/data/archive" 
REAL_ARCHIVE_PATH = os.path.realpath(ARCHIVE_DIR)
DB_FILE = os.path.join(REAL_ARCHIVE_PATH, "archive.json")
LOG_FILE = "/app/logs/bot.log"

def _log_msg(msg):
    """Schreibt Logs in die Konsole (für Railway) UND in die bot.log (fürs Web-Dashboard)"""
    print(msg)
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] [INFO] {msg}\n"
        real_log_file = os.path.realpath(LOG_FILE)
        os.makedirs(os.path.dirname(real_log_file), exist_ok=True)
        with open(real_log_file, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass

def _load_db():
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def _save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def _upload_to_drive(file_path, filename, mime_type="video/mp4"):
    """Lädt eine Datei per REST API in Google Drive hoch mit dedizierten Drive-Credentials."""
    folder_id = os.getenv('DRIVE_FOLDER_ID')
    
    # LOGIK: Nutze DRIVE-spezifische Keys (vom Hauptkonto), 
    # falls nicht vorhanden, Fallback auf YouTube-Keys (vom Brand-Kanal)
    client_id = os.getenv('DRIVE_CLIENT_ID') or os.getenv('YOUTUBE_CLIENT_ID')
    client_secret = os.getenv('DRIVE_CLIENT_SECRET') or os.getenv('YOUTUBE_CLIENT_SECRET')
    refresh_token = os.getenv('DRIVE_REFRESH_TOKEN') or os.getenv('YOUTUBE_REFRESH_TOKEN')

    if not all([folder_id, client_id, client_secret, refresh_token]):
        _log_msg(f"⚠️ Drive Upload übersprungen für {filename}: Fehlende Credentials.")
        return

    try:
        # 1. Frischen Access Token holen (mit den Drive-Keys)
        access_token = refresh_access_token(client_id, client_secret, refresh_token)
        
        # 2. Upload bei Google anmelden (Resumable)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Upload-Content-Type": mime_type
        }
        metadata = {"name": filename, "parents": [folder_id]}
        
        init_res = requests.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable",
            headers=headers,
            json=metadata
        )
        init_res.raise_for_status()
        upload_url = init_res.headers.get("Location")
        
        if not upload_url:
            raise Exception("Keine Upload-URL von Google erhalten.")

        # 3. Datei-Bytes hochschieben
        file_size = os.path.getsize(file_path)
        with open(file_path, "rb") as f:
            upload_res = requests.put(
                upload_url,
                headers={"Content-Length": str(file_size)},
                data=f
            )
            upload_res.raise_for_status()
        
        _log_msg(f"☁️ {filename} erfolgreich in Google Drive gesichert.")
    except Exception as e:
        _log_msg(f"⚠️ Drive Upload fehlgeschlagen für {filename}: {e}")

def move_to_archive(video_path, fact_data, image_path=None):
    """Speichert Video, Bild und Metadaten im Archiv."""
    try:
        real_archive_dir = os.path.realpath(ARCHIVE_DIR)
        os.makedirs(real_archive_dir, exist_ok=True)
        
        # 1. Video kopieren
        video_filename = os.path.basename(video_path)
        dest_video_path = os.path.join(real_archive_dir, video_filename)
        shutil.copy2(video_path, dest_video_path)
        
        # --- GOOGLE DRIVE UPLOAD: VIDEO ---
        _upload_to_drive(dest_video_path, video_filename, "video/mp4")
        
        # 2. Bild kopieren (falls vorhanden) & Hochladen
        new_image_name = None
        if image_path and os.path.exists(image_path):
            image_filename = os.path.basename(image_path)
            new_image_name = image_filename
            dest_image_path = os.path.join(real_archive_dir, new_image_name)
            shutil.copy2(image_path, dest_image_path)
            
            # --- GOOGLE DRIVE UPLOAD: BILD ---
            _upload_to_drive(dest_image_path, new_image_name, "image/png")
            
        # 3. Temporäre Textdatei für Google Drive erstellen & Hochladen
        try:
            base_name_no_ext = os.path.splitext(video_filename)[0]
            txt_filename = f"{base_name_no_ext}_metadata.txt"
            temp_txt_path = os.path.join("/tmp", txt_filename)
            
            with open(temp_txt_path, "w", encoding="utf-8") as f:
                f.write(f"{fact_data.get('title', '')}\n\n")
                f.write(f"{fact_data.get('description', '')}\n\n")
                
                tags = fact_data.get("tags", [])
                if tags:
                    f.write(f"Tags: {', '.join(tags)}\n")
            
            # --- GOOGLE DRIVE UPLOAD: TEXTDATEI ---
            _upload_to_drive(temp_txt_path, txt_filename, "text/plain")
            
            if os.path.exists(temp_txt_path):
                os.remove(temp_txt_path)
        except Exception as txt_err:
            _log_msg(f"⚠️ Fehler beim Erstellen der Drive-Textdatei: {txt_err}")
        
        # 4. Metadaten lokal in JSON speichern
        db = _load_db()
        db.append({
            "timestamp": datetime.now().isoformat(),
            "video_file": video_filename,
            "image_file": new_image_name,
            "title": fact_data.get("title", ""),
            "description": fact_data.get("description", ""),
            "topic": "AI Fails"
        })
        _save_db(db)
        
        return dest_video_path
    except Exception as e:
        _log_msg(f"Fehler beim Archivieren: {e}")
        return None

def cleanup_old_videos(days=30):
    """Löscht Dateien UND Datenbank-Einträge älter als X Tage."""
    try:
        real_archive_dir = os.path.realpath(ARCHIVE_DIR)
        if not os.path.exists(real_archive_dir): return

        now = time.time()
        cutoff = now - (days * 86400)
        
        db = _load_db()
        new_db = []
        
        for f in os.listdir(real_archive_dir):
            if f == "archive.json": continue
            path = os.path.join(real_archive_dir, f)
            if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                os.remove(path)
                _log_msg(f"🧹 Datei gelöscht: {f}")

        for entry in db:
            file_path = os.path.join(real_archive_dir, entry["video_file"])
            if os.path.exists(file_path):
                new_db.append(entry)
        
        _save_db(new_db)
    except Exception as e:
        _log_msg(f"Fehler beim Cleanup: {e}")
