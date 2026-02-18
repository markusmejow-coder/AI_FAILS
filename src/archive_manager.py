import os
import shutil
import time
from datetime import datetime

# Pfad zum persistenten Volume
ARCHIVE_DIR = "/app/archive"

def move_to_archive(video_path):
    """Kopiert das Video mit Zeitstempel ins Archiv-Verzeichnis."""
    try:
        if not os.path.exists(ARCHIVE_DIR):
            os.makedirs(ARCHIVE_DIR, exist_ok=True)
        
        filename = os.path.basename(video_path)
        # Zeitstempel für Eindeutigkeit (JahrMonatTag_StundeMinuteSekunde)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = os.path.join(ARCHIVE_DIR, f"{timestamp}_{filename}")
        
        # copy2 erhält auch die Metadaten (Erstellungsdatum)
        shutil.copy2(video_path, dest_path)
        return dest_path
    except Exception as e:
        print(f"Fehler beim Archivieren: {e}")
        return None

def cleanup_old_videos(days=30):
    """Löscht Dateien im Archiv, die älter als 'days' Tage sind."""
    try:
        if not os.path.exists(ARCHIVE_DIR):
            return

        now = time.time()
        # Zeitlimit in Sekunden berechnen
        cutoff = now - (days * 86400)

        for f in os.listdir(ARCHIVE_DIR):
            path = os.path.join(ARCHIVE_DIR, f)
            # Nur Dateien (keine Unterordner) prüfen
            if os.path.isfile(path):
                # Wenn das Alter der Datei über dem Limit liegt
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
                    print(f"🧹 Archiv-Cleanup: {f} gelöscht (älter als {days} Tage)")
    except Exception as e:
        print(f"Fehler beim Cleanup: {e}")
