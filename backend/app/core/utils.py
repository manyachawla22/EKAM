"""
EKAM Core Utilities

Shared helpers used across the backend. Keep this module pure (no DB / HTTP imports).
"""

import hashlib


_HASH_CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def generate_event_hash(event_id: str) -> str:
    """
    Derive a short, deterministic EF-XXXXXX display hash from an event UUID string.
    The same event_id always produces the same hash, preventing login failures
    caused by mismatched hashes generated at different call sites.
    """
    digest = hashlib.sha256(event_id.encode()).digest()
    suffix = "".join(_HASH_CHARSET[b % 36] for b in digest[:6])
    return f"EF-{suffix}"
