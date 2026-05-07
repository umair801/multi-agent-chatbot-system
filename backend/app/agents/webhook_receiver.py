import os
import logging
import hashlib
import hmac
from typing import Any, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def verify_webhook_signature(
    payload_bytes: bytes,
    signature_header: Optional[str],
    secret: Optional[str],
) -> bool:
    """
    Verify HMAC-SHA256 webhook signature.
    If no secret is configured, skip verification and allow all.
    """
    if not secret:
        logger.warning("No webhook secret configured — skipping signature verification")
        return True

    if not signature_header:
        logger.warning("Webhook received with no signature header")
        return False

    expected = hmac.new(
        secret.encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    # Support both raw hex and 'sha256=<hex>' formats
    incoming = signature_header.replace("sha256=", "").strip()

    verified = hmac.compare_digest(expected, incoming)
    if not verified:
        logger.warning("Webhook signature mismatch")
    return verified


def parse_webhook_payload(raw: dict) -> dict:
    """
    Normalize inbound webhook payload into a standard envelope.
    Handles arbitrary payload shapes from any external system.
    """
    return {
        "received_at": datetime.utcnow().isoformat(),
        "source": raw.get("source", "unknown"),
        "event_type": raw.get("event", raw.get("event_type", raw.get("type", "unknown"))),
        "payload": raw,
    }