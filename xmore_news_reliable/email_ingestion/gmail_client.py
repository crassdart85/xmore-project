"""
email_ingestion/gmail_client.py — Xmore Reliable News Acquisition Layer

Gmail API client using OAuth2.  Handles:
  - First-run interactive auth flow (opens browser, saves token.json)
  - Silent token refresh on subsequent runs
  - Fetching unread messages by label
  - Decoding MIME bodies (plain + HTML, multipart-recursive)
  - Marking messages as processed (adds label, removes UNREAD)

Credentials NEVER hardcoded — reads from credentials.json / token.json.
"""

import base64
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import (
    GMAIL_CREDENTIALS_FILE,
    GMAIL_SCOPES,
    GMAIL_TOKEN_FILE,
    GMAIL_USER_EMAIL,
    PROCESSED_LABEL,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _load_or_refresh_credentials() -> Credentials:
    """
    Returns valid Credentials.
    - If token.json exists and is valid → use it.
    - If expired but refreshable → refresh silently.
    - Otherwise → run interactive OAuth2 flow (opens browser once).
    """
    creds: Optional[Credentials] = None

    if GMAIL_TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(GMAIL_TOKEN_FILE), GMAIL_SCOPES)
        except Exception as exc:
            logger.warning("Could not load token.json: %s — will re-authenticate", exc)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            logger.info("Gmail token refreshed successfully")
            _persist_credentials(creds)
            return creds
        except RefreshError as exc:
            logger.warning("Token refresh failed (%s) — re-running OAuth flow", exc)

    # Full interactive flow
    if not GMAIL_CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"Gmail credentials file not found at: {GMAIL_CREDENTIALS_FILE}\n"
            "Download it from Google Cloud Console → APIs & Services → Credentials\n"
            "and save it as 'credentials.json' in the xmore_news_reliable/ directory."
        )

    logger.info("Starting Gmail OAuth flow — a browser window will open")
    flow = InstalledAppFlow.from_client_secrets_file(str(GMAIL_CREDENTIALS_FILE), GMAIL_SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")
    _persist_credentials(creds)
    return creds


def _persist_credentials(creds: Credentials) -> None:
    with open(str(GMAIL_TOKEN_FILE), "w", encoding="utf-8") as fh:
        fh.write(creds.to_json())
    logger.info("Gmail token saved to %s", GMAIL_TOKEN_FILE)


# ---------------------------------------------------------------------------
# Label management
# ---------------------------------------------------------------------------

def _get_or_create_label(service, label_name: str) -> str:
    """Return label ID, creating the label if it doesn't exist."""
    response = service.users().labels().list(userId="me").execute()
    for label in response.get("labels", []):
        if label["name"].lower() == label_name.lower():
            return label["id"]

    created = service.users().labels().create(
        userId="me",
        body={
            "name": label_name,
            "messageListVisibility": "show",
            "labelListVisibility": "labelShow",
        },
    ).execute()
    logger.info("Created Gmail label: '%s' (id=%s)", label_name, created["id"])
    return created["id"]


# ---------------------------------------------------------------------------
# MIME body extraction
# ---------------------------------------------------------------------------

def _decode_b64(data: str) -> str:
    """Decode Gmail's URL-safe base64 body data."""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def _walk_parts(parts: List[Dict], text_acc: List[str], html_acc: List[str]) -> None:
    """Recursively walk MIME parts collecting plain-text and HTML bodies."""
    for part in parts:
        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data", "")

        if mime == "text/plain" and data:
            text_acc.append(_decode_b64(data))
        elif mime == "text/html" and data:
            html_acc.append(_decode_b64(data))
        elif "parts" in part:
            _walk_parts(part["parts"], text_acc, html_acc)


def extract_body(message: Dict) -> Tuple[str, str]:
    """
    Returns (plain_text, html_text) from a full Gmail message payload.
    Handles flat, multipart/alternative, and nested multipart structures.
    """
    payload = message.get("payload", {})
    text_parts: List[str] = []
    html_parts: List[str] = []

    if "parts" in payload:
        _walk_parts(payload["parts"], text_parts, html_parts)
    else:
        data = payload.get("body", {}).get("data", "")
        mime = payload.get("mimeType", "text/plain")
        if data:
            decoded = _decode_b64(data)
            if mime == "text/html":
                html_parts.append(decoded)
            else:
                text_parts.append(decoded)

    return "\n".join(text_parts), "\n".join(html_parts)


# ---------------------------------------------------------------------------
# Public client
# ---------------------------------------------------------------------------

class GmailClient:
    """
    Thread-unsafe (single-threaded use only).
    Initialisation will trigger OAuth if token.json is absent or expired.
    """

    def __init__(self) -> None:
        creds = _load_or_refresh_credentials()
        self._service = build("gmail", "v1", credentials=creds)
        self._label_cache: Dict[str, str] = {}
        logger.info("GmailClient ready for %s", GMAIL_USER_EMAIL)

    def _label_id(self, label_name: str) -> str:
        if label_name not in self._label_cache:
            self._label_cache[label_name] = _get_or_create_label(self._service, label_name)
        return self._label_cache[label_name]

    def fetch_unread_by_label(self, label_name: str, max_results: int = 50) -> List[Dict]:
        """
        Return full message objects for all UNREAD messages in *label_name*.
        Returns empty list on any API error (never raises).
        """
        try:
            label_id = self._label_id(label_name)
            result = self._service.users().messages().list(
                userId="me",
                labelIds=[label_id, "UNREAD"],
                maxResults=max_results,
            ).execute()

            stubs = result.get("messages", [])
            logger.info("Label '%s': %d unread message(s)", label_name, len(stubs))

            messages: List[Dict] = []
            for stub in stubs:
                msg = self._service.users().messages().get(
                    userId="me",
                    id=stub["id"],
                    format="full",
                ).execute()
                messages.append(msg)

            return messages

        except HttpError as exc:
            logger.error("Gmail API error (label=%s): %s", label_name, exc)
            return []
        except Exception as exc:
            logger.error("Unexpected error fetching label '%s': %s", label_name, exc)
            return []

    def mark_as_processed(self, message_id: str) -> bool:
        """
        Add PROCESSED_LABEL and remove UNREAD from a message.
        Returns True on success.
        """
        try:
            processed_id = self._label_id(PROCESSED_LABEL)
            self._service.users().messages().modify(
                userId="me",
                id=message_id,
                body={
                    "addLabelIds": [processed_id],
                    "removeLabelIds": ["UNREAD"],
                },
            ).execute()
            logger.debug("Marked processed: %s", message_id)
            return True
        except HttpError as exc:
            logger.warning("Could not mark message %s: %s", message_id, exc)
            return False

    def get_header(self, message: Dict, name: str) -> str:
        """Extract a single header value (case-insensitive)."""
        for h in message.get("payload", {}).get("headers", []):
            if h["name"].lower() == name.lower():
                return h["value"]
        return ""

    def get_body(self, message: Dict) -> Tuple[str, str]:
        """Convenience wrapper → (plain_text, html_text)."""
        return extract_body(message)
