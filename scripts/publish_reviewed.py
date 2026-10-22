#!/usr/bin/env python3
"""Publish ONE explicitly reviewed draft into The Brief's on-site article feed.

The action must be started by an authorised GitHub user, with a named draft ID.
This script alone cannot attest that the facts were checked by a human.
"""
from __future__ import annotations
import datetime as dt
import json
from pathlib import Path
import re
import sys
from editorial_gate import check

ROOT = Path(__file__).resolve().parents[1]
PUBLISHED = ROOT / "data" / "articles.json"


def publish(bundle_path: Path, draft_id: str) -> dict:
    if not re.fullmatch(r"ai-[a-f0-9]{20}", draft_id):
        raise ValueError("Invalid draft identifier")
    if bundle_path.resolve().name != draft_id + ".json":
        raise ValueError("Requested draft does not match the artifact filename")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    audit = check(bundle, human_review=True)
    a = bundle["draft"].copy()
    if a["id"] != draft_id:
        raise ValueError("Article ID mismatch")
    existing = json.loads(PUBLISHED.read_text(encoding="utf-8")) if PUBLISHED.exists() else []
    if not isinstance(existing, list):
        raise ValueError("Published article feed must be an array")
    if any(x.get("id") == draft_id or x.get("url") == a.get("url") for x in existing):
        raise ValueError("This primary-source story has already been published")
    a["editorial_status"] = "PUBLISHED: explicitly approved through GitHub workflow"
    a["reviewed_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    a["published_at"] = a["reviewed_at"]
    a["kind"] = "original"
    a["publication"] = "The Brief"
    existing.insert(0, a)
    PUBLISHED.write_text(json.dumps(existing[:150], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Added approved article {draft_id}: {a['title']} ({audit['word_count']} words)")
    return a


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: publish_reviewed.py PATH_TO_DRAFT_JSON DRAFT_ID")
    publish(Path(sys.argv[1]), sys.argv[2])
