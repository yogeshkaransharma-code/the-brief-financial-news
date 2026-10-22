#!/usr/bin/env python3
"""Publish ONE explicitly reviewed draft into The Brief's on-site article feed.

The action must be started by an authorised GitHub user, with a named draft ID.
This script alone cannot attest that the facts were checked by a human.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import os
import json
from pathlib import Path
import re
import sys
from editorial_gate import check

ROOT = Path(__file__).resolve().parents[1]
PUBLISHED = ROOT / "data" / "articles.json"
AUDITS = ROOT / "data" / "editorial-audits"


def publish(bundle_path: Path, draft_id: str) -> dict:
    # This is a second guard behind a manually dispatched GitHub workflow.
    # Attestation is an accountable editor's declaration, NOT machine verification.
    if os.environ.get("EDITORIAL_ATTESTATION") != "ALL_CHECKS_COMPLETED":
        raise ValueError("Explicit editorial verification attestation missing")
    reviewer = os.environ.get("GITHUB_ACTOR", "").strip()
    notes = os.environ.get("EDITORIAL_REVIEW_NOTES", "").strip()
    if not reviewer or reviewer.endswith("[bot]") or len(notes) < 35:
        raise ValueError("A human GitHub reviewer and meaningful approval notes are required")
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
    a["reviewed_by"] = reviewer
    a["published_at"] = a["reviewed_at"]
    a["kind"] = "original"
    a["publication"] = "The Brief"
    existing.insert(0, a)
    PUBLISHED.write_text(json.dumps(existing[:150], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    AUDITS.mkdir(parents=True, exist_ok=True)
    record = {
        "article_id": draft_id,
        "source_url": a["url"],
        "source_snapshot_sha256": bundle["audit"]["source_sha256"],
        "reviewed_draft_sha256": bundle["audit"]["draft_sha256"],
        "published_article_sha256": hashlib.sha256(
            json.dumps(a, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "approved_by_github_actor": reviewer,
        "approved_at_utc": a["reviewed_at"],
        "editor_notes": notes,
        "evidence_passages_screened": audit["evidence_checks"],
        "scope": "Human-declared review of primary evidence. Automated checks are not a certification.",
    }
    (AUDITS / (draft_id + ".json")).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Added approved article {draft_id}: {a['title']} ({audit['word_count']} words)")
    return a


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: publish_reviewed.py PATH_TO_DRAFT_JSON DRAFT_ID")
    publish(Path(sys.argv[1]), sys.argv[2])
