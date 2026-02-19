#!/usr/bin/env python3
"""
setup_gmail.py — Xmore Reliable News Acquisition Layer
One-time Gmail OAuth2 setup wizard.

Run this script ONCE to authenticate crassdart@gmail.com and generate
token.json.  After that, the main ingestion system uses token.json silently
(auto-refreshing when needed).

Steps this script handles:
  1. Verify credentials.json exists
  2. Open browser for Google OAuth consent
  3. Save token.json with scopes for read + modify (needed to add labels)
  4. Verify connection by listing Gmail labels
  5. Create required labels if missing: CBE, IMF, EGX, Enterprise, xmore-processed

Usage:
  python setup_gmail.py

Prerequisites:
  1. Go to https://console.cloud.google.com/
  2. Create a project (or use existing)
  3. Enable Gmail API: APIs & Services → Library → Gmail API → Enable
  4. Create OAuth 2.0 credentials:
     APIs & Services → Credentials → + Create Credentials → OAuth client ID
     Application type: Desktop app
     Download the JSON → save as credentials.json in this directory
  5. Add your Gmail account as a test user (if app is in testing mode):
     OAuth consent screen → Test users → Add Users → crassdart@gmail.com
"""

import sys
from pathlib import Path

# Ensure we can import from this directory
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    GMAIL_CREDENTIALS_FILE,
    GMAIL_SCOPES,
    GMAIL_TOKEN_FILE,
    GMAIL_USER_EMAIL,
)

REQUIRED_LABELS = ["CBE", "IMF", "EGX", "Enterprise", "xmore-processed"]


def main() -> None:
    print("\n" + "=" * 60)
    print("  Xmore Gmail OAuth2 Setup")
    print("=" * 60)
    print(f"\nAccount  : {GMAIL_USER_EMAIL}")
    print(f"Creds    : {GMAIL_CREDENTIALS_FILE}")
    print(f"Token    : {GMAIL_TOKEN_FILE}")
    print(f"Scopes   : {len(GMAIL_SCOPES)} scope(s)")
    print()

    # Step 1: Check credentials.json
    if not GMAIL_CREDENTIALS_FILE.exists():
        print("ERROR: credentials.json not found.")
        print()
        print("To get credentials.json:")
        print("  1. Go to https://console.cloud.google.com/")
        print("  2. Enable Gmail API")
        print("  3. Create OAuth 2.0 Desktop App credentials")
        print("  4. Download JSON → save as:", GMAIL_CREDENTIALS_FILE)
        sys.exit(1)

    print(f"[OK] credentials.json found: {GMAIL_CREDENTIALS_FILE}")

    # Step 2: Run OAuth flow
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        print("\nERROR: Google API libraries not installed.")
        print("Run: pip install -r requirements.txt")
        sys.exit(1)

    print("\nOpening browser for OAuth consent...")
    print("(Sign in as:", GMAIL_USER_EMAIL, ")\n")

    flow = InstalledAppFlow.from_client_secrets_file(
        str(GMAIL_CREDENTIALS_FILE), GMAIL_SCOPES
    )
    creds = flow.run_local_server(port=0, prompt="consent")

    with open(str(GMAIL_TOKEN_FILE), "w", encoding="utf-8") as fh:
        fh.write(creds.to_json())

    print(f"\n[OK] token.json saved: {GMAIL_TOKEN_FILE}")

    # Step 3: Verify connection
    print("\nVerifying Gmail API connection...")
    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    actual_email = profile.get("emailAddress", "unknown")
    total_messages = profile.get("messagesTotal", "?")

    print(f"[OK] Connected as: {actual_email}")
    print(f"     Total messages in mailbox: {total_messages}")

    if actual_email.lower() != GMAIL_USER_EMAIL.lower():
        print(f"\nWARNING: Authenticated as '{actual_email}' but expected '{GMAIL_USER_EMAIL}'")
        print("         Update GMAIL_USER_EMAIL in .env if this is intentional.")

    # Step 4: Create required labels
    print(f"\nChecking/creating labels: {REQUIRED_LABELS}")
    existing_labels_resp = service.users().labels().list(userId="me").execute()
    existing_names = {
        lbl["name"].lower(): lbl["id"]
        for lbl in existing_labels_resp.get("labels", [])
    }

    for label_name in REQUIRED_LABELS:
        if label_name.lower() in existing_names:
            print(f"  [EXISTS] {label_name}")
        else:
            created = service.users().labels().create(
                userId="me",
                body={
                    "name": label_name,
                    "messageListVisibility": "show",
                    "labelListVisibility": "labelShow",
                },
            ).execute()
            print(f"  [CREATED] {label_name} (id={created['id']})")

    # Done
    print("\n" + "=" * 60)
    print("  Setup complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. In your Gmail, label newsletters/alerts with the appropriate")
    print("     label (CBE, IMF, EGX, Enterprise) to make them auto-ingested.")
    print()
    print("  2. Test ingestion:")
    print("     python main.py --source CBE")
    print()
    print("  3. Run all sources:")
    print("     python main.py --run-all")
    print()
    print("  4. Check health:")
    print("     python main.py --health-check")
    print()


if __name__ == "__main__":
    main()
