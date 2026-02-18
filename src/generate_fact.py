"""
generate_fact.py
Uses OpenAI GPT-4o-mini to generate a fresh, viral-worthy fact.
Costs ~0.001€ per call.
"""

import json
import urllib.request
import urllib.error
import os
import random
from datetime import datetime


# Topic rotation — KI wählt täglich automatisch
TOPICS = [
    "space and the universe",
    "the human body and brain",
    "animals and nature",
    "history and ancient civilizations",
    "technology and AI",
    "psychology and human behavior",
    "food and chemistry",
    "mathematics and physics",
    "ocean and deep sea creatures",
    "weird laws and world records",
]


SYSTEM_PROMPT = """You are a viral YouTube Shorts fact writer.
Your job: Write ONE mind-blowing, jaw-dropping fact that makes people say "WTF, really?!"

Rules:
- Start with the most shocking part
- Maximum 35 words
- NO emojis in the fact text itself
- Must be 100% accurate and verifiable
- Write ONLY the fact, nothing else
- Make it feel personal: "Your brain...", "Right now...", "Every time you..."

Bad example: "The octopus is an interesting animal with unique features."
Good example: "Your brain generates enough electricity while you sleep to power a small lightbulb — and nobody knows exactly why it does this."
"""


def generate_fact(api_key: str, topic: str = None) -> dict:
    """
    Returns: { "fact": str, "source": str, "topic": str, "title": str, "description": str, "tags": list }
    """
    if topic is None:
        topic = random.choice(TOPICS)

    user_prompt = f"Write one mind-blowing fact about: {topic}"

    # First call: get the fact
    fact_response = _call_gpt(
        api_key=api_key,
        system=SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=100
    )

    fact_text = fact_response.strip().strip('"')

    # Second call: generate YouTube metadata
    meta_prompt = f"""For this YouTube Shorts fact video, write:
Fact: "{fact_text}"

Return ONLY valid JSON with these exact keys:
{{
  "title": "YouTube title max 60 chars, start with emoji, hook first",
  "description": "2-3 sentences, conversational, end with question to boost comments",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8"],
  "source": "Short source credit e.g. 'Source: NASA' or 'Source: Nature Journal'"
}}"""

    meta_response = _call_gpt(
        api_key=api_key,
        system="You write YouTube metadata. Return only valid JSON, no markdown.",
        user=meta_prompt,
        max_tokens=300
    )

    # Parse JSON safely
    try:
        # Strip potential markdown code blocks
        clean = meta_response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        meta = json.loads(clean.strip())
    except json.JSONDecodeError:
        # Fallback metadata
        meta = {
            "title": f"🤯 This fact will blow your mind...",
            "description": f"{fact_text}\n\nDid you know this? Drop a 🤯 below!",
            "tags": ["didyouknow", "facts", "mindblown", "learnontiktok",
                     "shorts", "funfacts", "science", "viral"],
            "source": "Source: Verified Research"
        }

    return {
        "fact": fact_text,
        "topic": topic,
        "title": meta.get("title", "🤯 Mind-blowing fact"),
        "description": meta.get("description", fact_text),
        "tags": meta.get("tags", ["facts", "shorts"]),
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
    # Test with a dummy key placeholder
    print("Fact generator ready.")
    print("Set OPENAI_API_KEY env variable to test.")
    print(f"Available topics: {len(TOPICS)}")
    print(f"Sample topic: {random.choice(TOPICS)}")
