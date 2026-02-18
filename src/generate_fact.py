"""
generate_fact.py
Uses OpenAI GPT-4o-mini to generate a fresh, viral-worthy AI Fail.
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

Bad example: "An AI made a mistake in a recipe once which was quite funny."
Good example: "A Google AI once identified a simple turtle as a loaded rifle — and it was 100% sure about it."
"""


def generate_fact(api_key: str, topic: str = None) -> dict:
    """
    Returns: { "fact": str, "source": str, "topic": str, "title": str, "description": str, "tags": list }
    """
    if topic is None:
        topic = random.choice(TOPICS)

    user_prompt = f"Write one viral AI fail about: {topic}"

    # First call: get the fail/fact
    fact_response = _call_gpt(
        api_key=api_key,
        system=SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=100
    )

    fact_text = fact_response.strip().strip('"')

    # Second call: generate YouTube metadata
    meta_prompt = f"""For this YouTube Shorts AI Fail video, write:
Fail: "{fact_text}"

Return ONLY valid JSON with these exact keys:
{{
  "title": "YouTube title max 60 chars, start with emoji, hook first",
  "description": "2-3 sentences about this AI glitch, end with question to boost comments",
  "tags": ["AI", "Fail", "Tech", "Funny", "Glitches", "Shorts", "Trending", "Algorithm"],
  "source": "Short source credit e.g. 'Source: Reddit' or 'Source: Tech News'"
}}"""

    meta_response = _call_gpt(
        api_key=api_key,
        system="You write YouTube metadata. Return only valid JSON, no markdown.",
        user=meta_prompt,
        max_tokens=300
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
            "source": "Source: AI Archives"
        }

    return {
        "fact": fact_text,
        "topic": topic,
        "title": meta.get("title", "🤖 Epic AI Fail"),
        "description": meta.get("description", fact_text),
        "tags": meta.get("tags", ["AI", "Fail", "Shorts"]),
        "source": meta.get("source", ""),
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
        "temperature": 0.9
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
    print("Set OPENAI_API_KEY env variable to test.")
    print(f"Available topics: {len(TOPICS)}")
    print(f"Sample topic: {random.choice(TOPICS)}")
