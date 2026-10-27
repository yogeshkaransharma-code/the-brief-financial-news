"""Optional Cloudflare Web Analytics in the final GitHub Pages artifact.

Cloudflare token is a public beacon site identifier, NOT a secret. A missing
identifier means genuinely NO tracking, not a fake local visitor total.
No cookies, visitor IDs, personally identifying data, or public counter here.
"""
from __future__ import annotations

import html
import os
import re
from pathlib import Path

TOKEN_NAME = "BRIEF_CF_ANALYTICS_TOKEN"
TOKEN_RE = re.compile(r"^[a-fA-F0-9]{32}$")
BEACON_URL = "https://static.cloudflareinsights.com/beacon.min.js"

def token_from_env():
    token = os.environ.get(TOKEN_NAME, "").strip()
    if token and not TOKEN_RE.fullmatch(token):
        raise ValueError("Cloudflare Web Analytics token must be a 32-character hexadecimal site identifier")
    return token

def beacon(token):
    if not token:return ""
    # Site token is intentionally public and appears in HTML, never as a credential.
    return '<script defer src="' + BEACON_URL + '" data-cf-beacon=\'{"token":"' + html.escape(token, quote=True) + '"}\'></script>'

def install(public_dir, token):
    pages = sorted(Path(public_dir).rglob("*.html"))
    if not pages:raise ValueError("No public pages available for analytics setup")
    if not token:return {"mode":"not_connected", "pages":0}
    snippet = beacon(token)
    for page in pages:
        content = page.read_text(encoding="utf-8")
        if content.count("</head>") != 1 or BEACON_URL in content:
            raise ValueError("Analytics needs exactly one clean head tag: " + str(page))
        page.write_text(content.replace("</head>", snippet + "\n</head>", 1), encoding="utf-8")
    return {"mode":"enabled", "pages":len(pages)}
