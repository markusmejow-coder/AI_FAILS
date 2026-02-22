"""
generate_fact.py
Uses OpenAI GPT-4o-mini to generate a fresh, viral-worthy AI Fail.
Includes Archive-Check to prevent repetition of the same content.
Costs ~0.001€ per call.
"""

import json
import urllib.request
import urllib.error
import os
import random
from datetime import datetime


# Topic rotation — Speziell für KI-Fehler und Technik-Glitches
TOPICS = [
    "AI image generation fails (too many fingers)",
    "funny ChatGPT hallucinations",
    "self-driving car glitches",
    "algorithm bias and weird predictions",
    "chatbot customer service disasters",
    "facial recognition mistakes",
    "funny smart home assistant fails",
    "AI translation errors",
    "weird AI-generated recipes or art",
    "social media algorithm glitches",
]


SYSTEM_PROMPT = """You are a viral YouTube Shorts writer specializing in "AI Fails".
Your job: Write ONE hilarious or shocking instance where an Artificial Intelligence completely failed or made a ridiculous mistake.

Rules:
- Start with the most absurd part
- Maximum 35 words
- NO emojis in the text itself
- Must be a real, documented or highly relatable AI glitch
- Write ONLY the fail description, nothing else
- Make it punchy: "Imagine an AI...", "This chatbot...", "A computer once..."
"""


def generate_fact(api_key: str, topic: str = None) -> dict:
    """
    Returns: { "fact": str, "source": str, "topic": str, "title": str, "description": str, "tags": list, "parts": list, "words": list }
    """
    if topic is None or topic == "random":
        topic = random.choice(TOPICS)

    # REPETITION FIX: Lade die letzten Fakten aus dem Archiv
    history_context = ""
    try:
        archive_path = "/data/archive/archive.json"
        if os.path.exists(archive_path):
            with open(archive_path, "r") as f:
                data = json.load(f)
                # Wir nehmen die letzten 10 Fail-Inhalte als Ausschlusskriterium
                recent_fails = [item.get("fact", "") for item in data[-10:]]
                if recent_fails:
                    history_context = "IMPORTANT: Do NOT repeat the content of these recent AI fails: " + " | ".join(recent_fails)
    except:
        pass

    user_prompt = f"{history_context}\n\nWrite one fresh, obscure, and hilarious AI fail about: {topic}. Surprise me!"

    # First call: get the fail
    fact_response = _call_gpt(
        api_key=api_key,
        system=SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=100
    )

    fact_text = fact_response.strip().strip('"')

    # Second call: generate YouTube metadata including parts for retention modes
    meta_prompt = f"""For this YouTube Shorts AI Fail video, write:
Fail: "{fact_text}"
Topic: "{topic}"

Return ONLY valid JSON with these exact keys:
{{
  "title": "YouTube title max 60 chars, start with emoji, hook first",
  "description": "2-3 sentences about this AI glitch, conversational, end with a question. Do NOT include hashtags here.",
  "tags": ["{topic.replace(' ', '').replace('(', '').replace(')', '')}", "AIFail", "Funny", "Glitches", "Shorts"],
  "source": "Short source credit e.g. 'Source: Reddit'",
  "parts": ["Hook (max 4 words)", "The core fail description", "Final punchline/trigger"],
  "words": ["List", "of", "every", "single", "word", "from", "the", "fail", "text"]
}}"""

    meta_response = _call_gpt(
        api_key=api_key,
        system="You write YouTube metadata and segment text for viral retention. Return only valid JSON, no markdown.",
        user=meta_prompt,
        max_tokens=500
    )

    # Parse JSON safely
    try:
        clean = meta_response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        meta = json.loads(clean.strip())
    except json.JSONDecodeError:
        meta = {
            "title": f"🤖 AI Fail: You won't believe this...",
            "description": f"{fact_text}\n\nIs AI taking over or just failing? 😂",
            "tags": ["AI", "Fail", "Funny", "Tech", "Shorts"],
            "source": "Source: AI Archives",
            "parts": ["AI Fails...", fact_text, "Unbelievable."],
            "words": fact_text.split()
        }

    # Ensure keys exist for retention modes
    if "parts" not in meta or not meta["parts"]:
        meta["parts"] = ["AI Fails...", fact_text, "Unbelievable."]
    if "words" not in meta or not meta["words"]:
        meta["words"] = fact_text.split()

    tags_str = " ".join([f"#{t.replace(' ', '')}" for t in meta.get("tags", [])])
    if "#Shorts" not in tags_str:
        tags_str += " #Shorts #AIFails"
    
    full_description = f"{meta.get('description', '')}\n\n{tags_str}"

    # --- PRO-CLEANING: TITEL BEREINIGUNG ---
    # Sicherstellen, dass der Titel ein sauberer String ohne Artefakte ist
    raw_title = meta.get("title", "🤖 Epic AI Fail")
    if isinstance(raw_title, list):
        final_title = str(raw_title[0]) if raw_title else "🤖 Epic AI Fail"
    else:
        final_title = str(raw_title)
    
    # Entferne explizit '[]' falls die KI sie als Text zurückgegeben hat
    final_title = final_title.replace("[]", "").strip()
    # --------------------------------------

    return {
        "fact": fact_text,
        "topic": topic,
        "title": final_title,
        "description": full_description,
        "tags": meta.get("tags", ["AI", "Fail"]),
        "source": meta.get("source", ""),
        "parts": meta.get("parts"),
        "words": meta.get("words"),
        "generated_at": datetime.now().isoformat()
    }


def _call_gpt(api_key: str, system: str, user: str,
              max_tokens: int = 200) -> str:
    """Raw OpenAI API call via urllib (no SDK needed)."""
    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user}
        ],
        "max_tokens": max_tokens,
        "temperature": 1.0 
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        raise RuntimeError(f"OpenAI API error {e.code}: {error_body}")


if __name__ == "__main__":
    print("AI Fail generator ready.")
