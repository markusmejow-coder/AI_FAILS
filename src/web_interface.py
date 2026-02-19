"""
web_interface.py
Simple web dashboard for AI Fails Bot.
Login: admin / a763763B!
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import json
import subprocess
import sys
import os
from datetime import datetime
import hashlib

# Password hash (sha256 of "a763763B!")
PASSWORD_HASH = hashlib.sha256("a763763B!".encode()).hexdigest()

# Pfade für das Archiv
ARCHIVE_DIR = "/data/archive"
DB_FILE = os.path.join(ARCHIVE_DIR, "archive.json")

# Simple session management
sessions = {}

HTML_LOGIN = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Fails Bot - Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-box {
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            width: 90%;
            max-width: 400px;
        }
        h1 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .subtitle {
            color: #888;
            margin-bottom: 30px;
            font-size: 14px;
        }
        input {
            width: 100%;
            padding: 15px;
            margin-bottom: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: border 0.3s;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
        }
        .error {
            background: #fee;
            color: #c33;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 15px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>🤖 AI Fails Bot</h1>
        <p class="subtitle">Admin Dashboard</p>
        {error}
        <form method="POST" action="/login">
            <input type="text" name="username" placeholder="Username" required autofocus>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        
        <div style="text-align: center; margin-top: 20px; border-top: 1px solid #eee; padding-top: 15px;">
            <a href="/impressum" style="color: #888; text-decoration: none; font-size: 12px; font-family: sans-serif;">Impressum</a>
        </div>
    </div>
</body>
</html>
"""

HTML_DASHBOARD = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Fails Bot - Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f5f5f7;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        h1 {
            color: #667eea;
            margin-bottom: 5px;
        }
        .subtitle {
            color: #888;
            font-size: 14px;
        }
        .card {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .card h2 {
            color: #333;
            margin-bottom: 15px;
            font-size: 20px;
        }
        .btn {
            display: inline-block;
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            text-decoration: none;
            transition: transform 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .status-item {
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .status-label {
            color: #888;
            font-size: 12px;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        .status-value {
            color: #333;
            font-size: 20px;
            font-weight: bold;
        }
        .info {
            background: #e3f2fd;
            color: #1976d2;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        .logout {
            text-align: right;
            margin-top: 20px;
        }
        .logout a {
            color: #888;
            text-decoration: none;
            font-size: 14px;
        }
        #result {
            display: none;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            font-size: 14px;
        }
        #result.success {
            display: block;
            background: #d4edda;
            color: #155724;
        }
        #result.error {
            display: block;
            background: #f8d7da;
            color: #721c24;
        }
        .spinner {
            display: none;
            margin-top: 15px;
        }
        .spinner.active {
            display: block;
        }
        pre {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            border-radius: 10px;
            font-size: 12px;
            overflow-x: auto;
            white-space: pre-wrap;
            line-height: 1.5;
            max-height: 300px;
        }
        .count-setter {
            margin-top: 10px;
            display: flex;
            gap: 5px;
            align-items: center;
        }
        .count-setter input {
            width: 70px;
            padding: 5px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 14px;
        }
        .count-setter button {
            font-size: 12px;
            padding: 5px 10px;
            cursor: pointer;
            border: 1px solid #667eea;
            background: #fff;
            color: #667eea;
            border-radius: 4px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤯 AI Fails Bot</h1>
            <p class="subtitle">Admin Dashboard</p>
        </div>

        <div class="card">
            <h2>📊 Status</h2>
            <div class="status-grid">
                <div class="status-item">
                    <div class="status-label">Bot Status</div>
                    <div class="status-value">✅ Running</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Next Post</div>
                    <div class="status-value">{next_post}</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Total Videos</div>
                    <div class="status-value">
                        {total_videos}
                        <div class="count-setter">
                            <input type="number" id="newCount" placeholder="Nr.">
                            <button onclick="setCustomCount()">Setzen</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>🚀 Manual Post</h2>
            <div class="info">
                ⚠️ This will immediately generate and post a new video to your YouTube channel.
                The bot will continue its normal daily schedule.
            </div>
            <button class="btn" onclick="triggerPost()">Create & Post Video Now</button>
            <div id="spinner" class="spinner">
                <p>⏳ Generating video... This takes ~30 seconds...</p>
            </div>
            <div id="result"></div>
        </div>

        <div class="card">
            <h2>📦 Video Archiv</h2>
            <div class="info" style="background: #e8f5e9; color: #2e7d32;">
                Hier findest du alle generierten Videos der letzten 30 Tage zum Download.
            </div>
            <a href="/archive" class="btn" style="background: linear-gradient(135deg, #43a047 0%, #2e7d32 100%);">Zum Archiv</a>
        </div>
        
        <div class="card">
            <h2>📜 Live Logs (Letzte 15 Zeilen)</h2>
            <pre>{logs}</pre>
        </div>

        <div class="logout">
            <a href="/logout">Logout</a> | <a href="/impressum">Impressum</a>
        </div>
    </div>

    <script>
        function triggerPost() {
            const btn = document.querySelector('.btn');
            const result = document.getElementById('result');
            const spinner = document.getElementById('spinner');
            
            btn.disabled = true;
            btn.textContent = 'Processing...';
            spinner.classList.add('active');
            result.className = '';
            result.style.display = 'none';

            fetch('/trigger', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    spinner.classList.remove('active');
                    btn.disabled = false;
                    btn.textContent = 'Create & Post Video Now';
                    
                    if (data.success) {
                        result.className = 'success';
                        result.innerHTML = '✅ ' + data.message;
                    } else {
                        result.className = 'error';
                        result.innerHTML = '❌ ' + data.message;
                    }
                })
                .catch(err => {
                    spinner.classList.remove('active');
                    btn.disabled = false;
                    btn.textContent = 'Create & Post Video Now';
                    result.className = 'error';
                    result.innerHTML = '❌ Error: ' + err.message;
                });
        }
        
        function setCustomCount() {
            const newCount = document.getElementById('newCount').value;
            if(!newCount || newCount < 0) {
                alert('Bitte eine gültige Zahl eingeben!');
                return;
            }
            if(confirm('Möchtest du den Video-Zähler wirklich auf ' + newCount + ' setzen?')) {
                fetch('/set_count', { 
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'count=' + newCount
                })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        alert(data.message);
                        location.reload();
                    } else {
                        alert('Fehler: ' + data.message);
                    }
                })
                .catch(err => alert('Fehler: ' + err));
            }
        }
    </script>
</body>
</html>
"""

class DashboardHandler(BaseHTTPRequestHandler):
    
    def _get_archive_db(self):
        """Lädt die archive.json Metadaten-Datenbank."""
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r") as f:
                    return json.load(f)
            except:
                return []
        return []

    def do_GET(self):
        session_id = self._get_session()
        
        if self.path == "/":
            if session_id and session_id in sessions:
                self._serve_dashboard()
            else:
                self._serve_login()
        
        elif self.path == "/logout":
            if session_id and session_id in sessions:
                del sessions[session_id]
            self.send_response(302)
            self.send_header("Location", "/")
            self.send_header("Set-Cookie", "session=; Max-Age=0")
            self.end_headers()
        
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")

        elif self.path == "/impressum":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            impressum_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>Impressum - AI Fails Bot</title>
                <style>
                    body { font-family: -apple-system, sans-serif; line-height: 1.6; padding: 40px; color: #333; max-width: 600px; margin: auto; }
                    h1 { color: #667eea; border-bottom: 2px solid #eee; padding-bottom: 10px; }
                    .back-link { display: inline-block; margin-top: 30px; color: #667eea; text-decoration: none; font-weight: bold; }
                    hr { border: 0; border-top: 1px solid #eee; margin: 20px 0; }
                </style>
            </head>
            <body>
                <h1>Impressum</h1>
                <p><strong>Angaben gemäß § 5 DDG:</strong></p>
                <p>Markus Mejow<br>
                Kortenkamp 1<br>
                48291 Telgte</p>
                
                <p><strong>Kontakt:</strong><br>
                E-Mail: markusmejow@gmail.com</p>
                
                <hr>
                <p><i>Technischer Prototyp zur Demonstration von KI-Automatisierung.</i></p>
                
                <a href="/" class="back-link">&larr; Zurück zum Dashboard</a>
            </body>
            </html>
            """
            self.wfile.write(impressum_html.encode('utf-8'))

        elif self.path == "/archive":
            if session_id and session_id in sessions:
                self._serve_archive_list()
            else:
                self.send_response(302)
                self.send_header("Location", "/")
                self.end_headers()

        elif self.path.startswith("/download/"):
            if session_id and session_id in sessions:
                self._serve_archive_file()
            else:
                self.send_response(401)
                self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        session_id = self._get_session()
        
        if self.path == "/login":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode()
            params = urllib.parse.parse_qs(body)
            
            username = params.get('username', [''])[0]
            password = params.get('password', [''])[0]
            
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            if username == "admin" and password_hash == PASSWORD_HASH:
                import secrets
                session_id = secrets.token_hex(16)
                sessions[session_id] = {"username": username, "created": datetime.now()}
                
                self.send_response(302)
                self.send_header("Location", "/")
                self.send_header("Set-Cookie", f"session={session_id}; HttpOnly; Max-Age=86400")
                self.end_headers()
            else:
                self._serve_login(error="Invalid username or password")
        
        elif self.path == "/set_count":
            if not (session_id and session_id in sessions):
                self._send_json({"success": False, "message": "Not authenticated"}, 401)
                return
            
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode()
                params = urllib.parse.parse_qs(body)
                new_count = int(params.get('count', [0])[0])

                state_path = "/app/logs/state.json"
                real_dir = os.path.realpath(os.path.dirname(state_path))
                os.makedirs(real_dir, exist_ok=True)

                state = {"last_palette": (new_count - 1) % 5, "total_videos": new_count}
                with open(state_path, "w") as f:
                    json.dump(state, f)
                
                self._send_json({"success": True, "message": f"Zähler auf {new_count} gesetzt!"})
            except Exception as e:
                self._send_json({"success": False, "message": str(e)})

        elif self.path == "/trigger":
            if not (session_id and session_id in sessions):
                self._send_json({"success": False, "message": "Not authenticated"}, 401)
                return
            
            try:
                result = subprocess.run(
                    [sys.executable, "/app/src/bot.py"],
                    capture_output=False,
                    text=True,
                    timeout=300
                )
                
                if result.returncode == 0:
                    self._send_json({
                        "success": True,
                        "message": "Video posted successfully! Check Logs."
                    })
                else:
                    self._send_json({
                        "success": False,
                        "message": "Bot finished with error code."
                    })
            except subprocess.TimeoutExpired:
                self._send_json({
                    "success": False,
                    "message": "Timeout - bot took too long"
                })
            except Exception as e:
                self._send_json({
                    "success": False,
                    "message": str(e)
                })
        else:
            self.send_response(404)
            self.end_headers()
    
    def _get_session(self):
        cookie_header = self.headers.get('Cookie', '')
        for cookie in cookie_header.split(';'):
            if 'session=' in cookie:
                return cookie.split('session=')[1].strip()
        return None
    
    def _serve_login(self, error=""):
        error_html = f'<div class="error">{error}</div>' if error else ''
        html = HTML_LOGIN.replace('{error}', error_html)
        
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())
    
    def _serve_dashboard(self):
        now_utc = datetime.utcnow()
        current_time_str = now_utc.strftime("%H:%M")
        
        post_times_raw = os.environ.get("POST_TIMES", "11:00,19:00")
        post_times = [t.strip() for t in post_times_raw.split(",")]
        
        future_times = [t for t in post_times if t > current_time_str]
        if future_times:
            next_post_utc = min(future_times)
            day_prefix = "Heute"
        else:
            next_post_utc = min(post_times)
            day_prefix = "Morgen"

        def to_de(utc_str):
            h, m = map(int, utc_str.split(':'))
            return f"{(h + 1) % 24:02d}:{m:02d}"

        next_post_de = to_de(next_post_utc)
        all_times_de = ", ".join([f"<b>{to_de(t)} MEZ</b>" for t in post_times])
        
        try:
            with open("/app/logs/state.json") as f:
                state = json.load(f)
            total_videos = state.get("total_videos", 0)
        except:
            total_videos = 0

        try:
            with open("/app/logs/bot.log", "r") as f:
                logs = "".join(f.readlines()[-15:])
        except:
            logs = "Noch keine Logs vorhanden."
        
        html = HTML_DASHBOARD.replace('<head>', '<head><meta http-equiv="refresh" content="30">')
        
        status_html = f"<b>{day_prefix} {next_post_de} Uhr</b> ({next_post_utc} UTC)<br><small style='font-size:10px; color:#888;'>Intervalle: {all_times_de}</small>"
        html = html.replace('{next_post}', status_html)
        html = html.replace('{total_videos}', str(total_videos))
        html = html.replace('{logs}', logs)
        
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def _serve_archive_list(self):
        """Erweiterte Archiv-Liste mit Metadaten und Copy-Button."""
        items = self._get_archive_db()
        # Sortieren: Neueste zuerst
        items = sorted(items, key=lambda x: x.get('timestamp', ''), reverse=True)
        
        rows = ""
        for item in items:
            # 100% bombensicheres Escaping für JavaScript via URL-Encoding
            raw_text = f"{item.get('title', '')}\n\n{item.get('description', '')}"
            encoded_meta = urllib.parse.quote(raw_text)
            
            # Bild-Button dynamisch einblenden, falls vorhanden
            image_btn = ""
            if item.get("image_file"):
                image_btn = f'<a href="/download/{item["image_file"]}" style="color: #e91e63; text-decoration: none; font-weight: bold; font-size: 14px; margin-left: 15px;">🖼️ Bild</a>'
            
            rows += f"""
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 15px; font-size: 14px;">{item.get('timestamp', '')[:10]}</td>
                <td style="padding: 15px; font-size: 14px;"><b>{item.get('topic', 'General')}</b></td>
                <td style="padding: 15px;">
                    <a href="/download/{item.get('video_file', '')}" style="color: #43a047; text-decoration: none; font-weight: bold; font-size: 14px;">🎬 Video</a>
                    {image_btn}
                </td>
                <td style="padding: 15px;">
                    <button onclick="copyToClipboard('{encoded_meta}')" style="background: #667eea; color: white; border: none; padding: 8px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: bold;">
                        📋 Copy Meta
                    </button>
                </td>
            </tr>
            """
        
        html = f"""
        <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>Video Archiv</title>
                <style>
                    body {{ font-family: -apple-system, sans-serif; padding: 20px; background: #f5f5f7; color: #333; }}
                    .container {{ max-width: 800px; margin: auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                    th {{ text-align: left; color: #888; font-size: 11px; text-transform: uppercase; padding: 10px; border-bottom: 2px solid #f5f5f7; }}
                </style>
                <script>
                function copyToClipboard(encodedText) {{
                    // Text wird hier wieder entschlüsselt, inklusive aller echten Zeilenumbrüche
                    const text = decodeURIComponent(encodedText);
                    navigator.clipboard.writeText(text).then(() => {{
                        alert("Metadaten (Titel & Beschreibung) kopiert!");
                    }}).catch(err => {{
                        alert("Fehler beim Kopieren: " + err);
                    }});
                }}
                </script>
            </head>
            <body>
                <div class="container">
                    <h1 style="color: #667eea;">📦 Video Archiv</h1>
                    <p style="color: #888; font-size: 14px; margin-bottom: 20px;">Alle generierten Videos der letzten 30 Tage mit Metadaten.</p>
                    <table>
                        <thead>
                            <tr><th>Datum</th><th>Thema</th><th>Video</th><th>Aktion</th></tr>
                        </thead>
                        <tbody>
                            {rows if rows else "<tr><td colspan='4' style='padding:20px; text-align:center; color:#888;'>Noch keine Videos archiviert</td></tr>"}
                        </tbody>
                    </table>
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0;">
                    <a href="/" style="color: #667eea; text-decoration: none; font-weight: bold; font-family: sans-serif;">&larr; Zurück zum Dashboard</a>
                </div>
            </body>
        </html>
        """
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def _serve_archive_file(self):
        filename = self.path.replace("/download/", "")
        file_path = os.path.join(ARCHIVE_DIR, filename)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                self.send_response(200)
                self.send_header("Content-type", "video/mp4")
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.end_headers()
                self.wfile.write(f.read())
        else:
            self.send_error(404, "Datei nicht gefunden")
    
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    server.serve_forever()
