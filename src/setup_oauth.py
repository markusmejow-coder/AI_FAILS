"""
setup_oauth.py
Run this ONCE on your local machine to get your YouTube refresh token.
After this, the bot runs forever without needing your browser.

Usage:
  python3 setup_oauth.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from youtube_upload import get_oauth_url, exchange_code_for_tokens


def main():
    print("=" * 60)
    print("  FactDrop Bot — One-Time YouTube OAuth Setup")
    print("=" * 60)
    print()
    print("You need:")
    print("  1. Google Cloud Console project")
    print("  2. YouTube Data API v3 enabled")
    print("  3. OAuth 2.0 credentials (Desktop App)")
    print()

    client_id = input("Paste your OAuth Client ID: ").strip()
    client_secret = input("Paste your OAuth Client Secret: ").strip()

    print()
    print("─" * 60)
    print("Step 1: Open this URL in your browser:")
    print()
    url = get_oauth_url(client_id)
    print(url)
    print()
    print("─" * 60)
    print("Step 2: Sign in with your YouTube account")
    print("Step 3: Click 'Allow'")
    print("Step 4: Copy the authorization code shown")
    print()

    auth_code = input("Paste the authorization code here: ").strip()

    print()
    print("Exchanging code for tokens...")

    try:
        tokens = exchange_code_for_tokens(client_id, client_secret, auth_code)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    if "refresh_token" not in tokens:
        print(f"❌ No refresh token received: {tokens}")
        sys.exit(1)

    refresh_token = tokens["refresh_token"]

    print()
    print("=" * 60)
    print("  ✅ SUCCESS! Save these in your Railway environment variables:")
    print("=" * 60)
    print()
    print(f"  YOUTUBE_CLIENT_ID     = {client_id}")
    print(f"  YOUTUBE_CLIENT_SECRET = {client_secret}")
    print(f"  YOUTUBE_REFRESH_TOKEN = {refresh_token}")
    print()
    print("Add these to Railway → Your Project → Variables")
    print("The bot will use these automatically — forever.")
    print("=" * 60)


if __name__ == "__main__":
    main()
