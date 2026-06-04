"""Shared visual tokens for generated HTML reports/certificates.

These mirror the frontend app theme (frontend_new/src/app/globals.css) so emailed
and stored reports look like the rest of EKAM instead of a generic template.
"""

# App palette (kept in sync with globals.css :root tokens).
BG = "#0a0a0a"
CARD = "#111111"
CARD_ALT = "#1a1a1a"
BORDER = "#222222"
TEXT = "#ffffff"
TEXT_SOFT = "#f5f5f5"
TEXT_MUTED = "#888888"
TEXT_DIM = "#555555"
ACCENT = "#e8503a"
ACCENT_HOVER = "#d4432e"

FONT = "Inter,system-ui,-apple-system,'Segoe UI',Arial,sans-serif"
HEADER_GRADIENT = f"linear-gradient(135deg,{ACCENT},{ACCENT_HOVER})"

# Multi-series chart palette — leads with the brand accent, then distinct hues.
CHART_PALETTE = [
    ACCENT, "#6366f1", "#059669", "#f59e0b", "#3b82f6",
    "#a855f7", "#14b8a6", "#ef4444", "#84cc16", "#ec4899",
]
