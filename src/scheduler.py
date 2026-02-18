"""
scheduler.py
Keeps the bot running on Railway 24/7.
Posts videos at scheduled UTC times.

Also runs a web dashboard for manual triggers.
"""

import time
import subprocess
import sys
import os
from datetime import datetime
from http.server import HTTPServer
from threading import Thread

# Import the web interface
sys.path.insert(0, os.path.dirname(__file__))
try:
    from web_interface import DashboardHandler
    WEB_AVAILABLE = True
except Exception as e:
    print(f"⚠️  Web interface import failed: {e}")
    print("   Continuing with basic health check only")
    WEB_AVAILABLE = False
    from http.server import BaseHTTPRequestHandler
    
    class DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"FactDrop Bot Running - Web UI unavailable")
        def log_message(self, format, *args):
            pass

# NEU: Liest eine Liste von Zeiten aus Railway (z.B. "11:15, 19:15")
# Falls die neue Variable nicht da ist, nutzt er die alten Variablen als Backup
POST_TIMES_RAW = os.environ.get("POST_TIMES")

if POST_TIMES_RAW:
    POST_TIMES = [t.strip() for t in POST_TIMES_RAW.split(",")]
else:
    # Backup: Nutzt die alten Variablen, falls POST_TIMES nicht gesetzt ist
    h = int(os.environ.get("POST_HOUR_UTC", "10"))
    m = int(os.environ.get("POST_MINUTE_UTC", "0"))
    POST_TIMES = [f"{h:02d}:{m:02d}"]

def should_run_now() -> bool:
    """Prüft, ob die aktuelle UTC-Zeit in der Liste der geplanten Zeiten steht."""
    now = datetime.utcnow()
    current_time = now.strftime("%H:%M")
    return current_time in POST_TIMES

def run_bot():
    print(f"\n{'='*50}")
    print(f"[{datetime.utcnow().isoformat()}] 🤖 Triggering scheduled bot run...")
    print(f"{'='*50}\n")

    # capture_output=False bleibt, damit die Logs direkt in Railway erscheinen
    result = subprocess.run(
        [sys.executable, "/app/src/bot.py"],
        capture_output=False 
    )

    if result.returncode != 0:
        print(f"⚠️  Bot exited with code {result.returncode}")
    else:
        print(f"✅ Bot run complete")

def main():
    print("\n" + "="*60)
    print("  🚀 FactDrop Bot Initializing...")
    print("="*60)
    
    port = int(os.environ.get("PORT", "8080"))
    
    try:
        server = HTTPServer(("0.0.0.0", port), DashboardHandler)
        web_thread = Thread(target=server.serve_forever, daemon=True)
        web_thread.start()
        
        if WEB_AVAILABLE:
            print(f"  ✅ Web dashboard running on port {port}")
            print(f"  🔐 Login: admin / a763763B!")
        else:
            print(f"  ✅ Health check running on port {port}")
    except Exception as e:
        print(f"  ⚠️  Failed to start web server: {e}")
        print("  Continuing without web interface...")
    
    print(f"\n{'='*60}")
    print(f"  📅 FactDrop Scheduler Started")
    print(f"  ⏰ Geplante Zeiten (UTC): {', '.join(POST_TIMES)}")
    print(f"  ⏱️  Checking every 30 seconds...")
    print(f"{'='*60}\n")

    # Wir tracken jetzt die letzte Minute, um Doppel-Posts in derselben Minute zu verhindern
    last_run_minute = None
    check_count = 0

    while True:
        check_count += 1
        now = datetime.utcnow()
        current_minute = now.strftime("%Y-%m-%d %H:%M")
        
        # Log heartbeat every 10 minutes (alle 20 Checks à 30s)
        if check_count % 20 == 0:
            print(f"💓 Heartbeat [{now.strftime('%H:%M:%S UTC')}] - Aktiv & Geplant: {', '.join(POST_TIMES)}", flush=True)

        if should_run_now():
            if last_run_minute != current_minute:
                last_run_minute = current_minute
                run_bot()

        time.sleep(30)

if __name__ == "__main__":
    main()
