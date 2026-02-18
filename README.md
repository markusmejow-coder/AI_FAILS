# 🤯 FactDrop Bot — Vollautomatischer YouTube Shorts Bot

Postet täglich automatisch einen Mind-Blowing Fact als YouTube Short.
**Kein Eingriff nötig. Läuft 24/7 auf Railway.**

---

## Was der Bot tut (täglich automatisch)

1. **GPT-4o-mini** generiert einen viralen Fakt (~0.001€)
2. **Python/Pillow** erstellt ein 1080x1920 Bild mit dem Fakt
3. **FFmpeg** macht ein 30-Sekunden-Video mit Zoom-Effekt
4. **YouTube API** lädt das Video als Short hoch (öffentlich)
5. Wiederholt sich morgen — für immer

**Kosten: ~10-12€/Monat total**

---

## SCHRITT-FÜR-SCHRITT SETUP (einmalig, ca. 30 Min)

### Schritt 1: Google Cloud Projekt erstellen (10 Min)

1. Geh zu: https://console.cloud.google.com
2. Oben links: **"Neues Projekt"** → Name: `factdrop-bot`
3. Links im Menü: **"APIs & Dienste"** → **"Bibliothek"**
4. Suche: `YouTube Data API v3` → **Aktivieren**
5. Links: **"Anmeldedaten"** → **"Anmeldedaten erstellen"** → **"OAuth-Client-ID"**
6. Anwendungstyp: **"Desktop-App"**
7. Name: `FactDrop Bot`
8. **Client-ID** und **Client-Secret** kopieren und speichern

### Schritt 2: OpenAI API Key (5 Min)

1. Geh zu: https://platform.openai.com
2. Links: **"API Keys"** → **"Create new secret key"**
3. Key kopieren und speichern
4. **"Billing"** → 10€ Guthaben aufladen (reicht für ~3 Monate)

### Schritt 3: YouTube Refresh Token holen (5 Min)

Führe dieses Script **einmal lokal** aus (du brauchst Python 3):

```bash
# Dateien herunterladen oder clonen
python3 src/setup_oauth.py
```

Das Script:
- Gibt dir eine URL → öffne sie im Browser
- Melde dich mit deinem YouTube-Kanal-Account an
- Klicke "Zulassen"
- Kopiere den Code ins Terminal
- Du bekommst deinen **YOUTUBE_REFRESH_TOKEN** — einmalig speichern!

### Schritt 4: GitHub Repository erstellen (3 Min)

1. Geh zu: https://github.com/new
2. Repository Name: `factdrop-bot`
3. **Private** (sicherer)
4. Alle Dateien aus diesem Ordner hochladen (oder `git push`)

### Schritt 5: Railway deployen (5 Min)

1. Geh zu: https://railway.app
2. **"New Project"** → **"Deploy from GitHub repo"**
3. Wähle dein `factdrop-bot` Repository
4. Railway erkennt automatisch das Dockerfile

### Schritt 6: Environment Variables in Railway setzen

Im Railway Dashboard → Dein Projekt → **"Variables"** → folgende eintragen:

```
OPENAI_API_KEY          = sk-...dein-key...
YOUTUBE_CLIENT_ID       = ...deine-client-id...
YOUTUBE_CLIENT_SECRET   = ...dein-client-secret...
YOUTUBE_REFRESH_TOKEN   = ...dein-refresh-token...
POST_HOUR_UTC           = 10
POST_MINUTE_UTC         = 0
```

`POST_HOUR_UTC = 10` bedeutet 10:00 UTC = 11:00 Uhr Deutschland (Winter) / 12:00 Uhr (Sommer)

### Schritt 7: Deploy!

Klicke **"Deploy"** in Railway. Der Bot startet und wartet auf die erste Posting-Zeit.

---

## Testen (manuell einen Post triggern)

Im Railway Dashboard → **"Shell"**:
```bash
python3 /app/src/bot.py
```

Das veröffentlicht sofort einen Test-Short auf deinem Kanal.

---

## Logs checken

Railway Dashboard → Dein Projekt → **"Logs"**

Du siehst jeden Tag:
```
[2026-02-18 10:00:01] 🚀 FactDrop Bot starting daily run
[2026-02-18 10:00:03] 📝 Step 1/4: Generating fact...
[2026-02-18 10:00:05] 🎨 Step 2/4: Creating image...
[2026-02-18 10:00:06] 🎬 Step 3/4: Creating video...
[2026-02-18 10:00:25] 📤 Step 4/4: Uploading to YouTube...
[2026-02-18 10:00:38] ✅ SUCCESS! Video #1 published
[2026-02-18 10:00:38]    URL: https://youtube.com/shorts/abc123xyz
```

---

## Monatliche Kosten

| Service         | Kosten      |
|-----------------|-------------|
| Railway Hobby   | 5€/Monat    |
| OpenAI API      | ~2-5€/Monat |
| YouTube API     | Kostenlos   |
| **GESAMT**      | **~7-10€**  |

---

## Kanal-Wachstum (realistische Erwartung)

| Zeitraum   | Erwartung                                    |
|------------|----------------------------------------------|
| Monat 1    | 0–500 Abonnenten, Algorithmus lernt dich     |
| Monat 2–3  | 1.000–5.000 Abonnenten, erster viraler Short |
| Monat 4–6  | 5.000–25.000 Abonnenten, YouTube Partner möglich |
| Monat 7–12 | 25.000–100.000+ Abonnenten                   |

**Ab 1.000 Abonnenten + 4.000 Watch-Hours:** YouTube Partner Programm = Geld pro View.

---

## Troubleshooting

**"quota exceeded"** → YouTube API hat 10.000 Units/Tag Limit. 1 Upload = ~1.600 Units. Du kannst 6 Videos/Tag uploaden — mehr als genug.

**"invalid_grant"** → Refresh Token abgelaufen. Führe `setup_oauth.py` erneut aus.

**Bot postet nicht** → Prüfe Logs in Railway. Stelle sicher alle 4 ENV Variables sind gesetzt.

---

*Bot gebaut mit Claude — February 2026*
