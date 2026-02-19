import os
import shutil
import time
import json
from datetime import datetime

# --- NEU: Imports für den Drive-Upload ---
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
# -----------------------------------------

# Pfad zum persistenten Volume
ARCHIVE_DIR = "/data/archive" 
REAL_ARCHIVE_PATH = os.path.realpath(ARCHIVE_DIR)
DB_FILE = os.path.join(REAL_ARCHIVE_PATH, "archive.json")

# --- NEU: Hilfsfunktion für Google Drive ---
def _get_drive_service():
    """Erstellt den Drive-Service aus der Railway-Variable."""
    creds_json = os.getenv('GOOGLE_CREDS_JSON')
    if not creds_json:
        return None
    try:
        info = json.loads(creds_json)
        return service_account.Credentials.from_service_account_info(info)
    except Exception as e:
        print(f"Fehler beim Laden der Google Credentials: {e}")
        return None
# -------------------------------------------

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

def move_to_archive(video_path, fact_data, image_path=None):
    """Speichert Video, Bild und Metadaten im Archiv."""
    try:
        real_archive_dir = os.path.realpath(ARCHIVE_DIR)
        os.makedirs(real_archive_dir, exist_ok=True)
        
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Video kopieren
        video_filename = os.path.basename(video_path)
        new_video_name = f"{timestamp_str}_{video_filename}"
        dest_video_path = os.path.join(real_archive_dir, new_video_name)
        shutil.copy2(video_path, dest_video_path)
        
        # 2. Bild kopieren (falls vorhanden)
        new_image_name = None
        if image_path and os.path.exists(image_path):
            image_filename = os.path.basename(image_path)
            new_image_name = f"{timestamp_str}_{image_filename}"
            dest_image_path = os.path.join(real_archive_dir, new_image_name)
            shutil.copy2(image_path, dest_image_path)
            
        # --- NEU: 2.5 GOOGLE DRIVE UPLOAD ---
        try:
            drive_creds = _get_drive_service()
            folder_id = os.getenv('DRIVE_FOLDER_ID')
            
            if drive_creds and folder_id:
                service = build('drive', 'v3', credentials=drive_creds)
                # Lädt das Video in Drive hoch
                file_metadata = {'name': new_video_name, 'parents': [folder_id]}
                media = MediaFileUpload(dest_video_path, mimetype='video/mp4', resumable=True)
                service.files().create(body=file_metadata, media_body=media).execute()
                print(f"☁️ {new_video_name} erfolgreich in Google Drive gesichert.")
        except Exception as drive_err:
            print(f"⚠️ Drive Upload fehlgeschlagen (lokales Archiv läuft weiter): {drive_err}")
        # ------------------------------------
        
        # 3. Metadaten in JSON speichern
        db = _load_db()
        db.append({
            "timestamp": datetime.now().isoformat(),
            "video_file": new_video_name,
            "image_file": new_image_name,  # NEU: Bild-Referenz
            "title": fact_data.get("title", ""),
            "description": fact_data.get("description", ""),
            "topic": fact_data.get("topic", "General")
        })
        _save_db(db)
        
        return dest_video_path
    except Exception as e:
        print(f"Fehler beim Archivieren: {e}")
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
        
        # 1. Dateien auf Festplatte prüfen
        for f in os.listdir(real_archive_dir):
            if f == "archive.json": continue
            path = os.path.join(real_archive_dir, f)
            if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                os.remove(path)
                print(f"🧹 Datei gelöscht: {f}")

        # 2. Datenbank aufräumen (nur behalten, was noch als Datei existiert)
        for entry in db:
            file_path = os.path.join(real_archive_dir, entry["video_file"])
            if os.path.exists(file_path):
                new_db.append(entry)
        
        _save_db(new_db)
    except Exception as e:
        print(f"Fehler beim Cleanup: {e}")
