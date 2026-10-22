#!/usr/bin/env python3
"""Check that every on-site AI article has an auditable, human-approved version."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path


def fingerprint(article):
    return hashlib.sha256(json.dumps(article, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def validate(root: Path) -> int:
    base = root / "data"
    articles = json.loads((base / "articles.json").read_text(encoding="utf-8"))
    if not isinstance(articles, list):
        raise ValueError("The original article feed must be a list")
    found = set()
    for article in articles:
        ident = article.get("id")
        if not ident or ident in found:
            raise ValueError("Missing or repeated published article ID")
        found.add(ident)
        if not article.get("ai_assisted"):
            raise ValueError("The original article feed contains an unlabelled, unreviewed item")
        if not str(article.get("editorial_status", "")).startswith("PUBLISHED:"):
            raise ValueError("An unpublished draft entered the public article feed")
        audit_file = base / "editorial-audits" / (ident + ".json")
        if not audit_file.is_file():
            raise ValueError("Missing signed approval record for " + ident)
        audit = json.loads(audit_file.read_text(encoding="utf-8"))
        if audit.get("article_id") != ident or audit.get("source_url") != article.get("url"):
            raise ValueError("Approval record is associated with another source/article")
        if audit.get("published_article_sha256") != fingerprint(article):
            raise ValueError("Published article changed after editorial approval")
        if not audit.get("approved_by_github_actor") or not article.get("reviewed_by"):
            raise ValueError("Accountable human reviewer is not recorded")
        if article["reviewed_by"] != audit["approved_by_github_actor"]:
            raise ValueError("Article reviewer differs from recorded approval")
        if not audit.get("reviewed_draft_sha256") or not audit.get("source_snapshot_sha256"):
            raise ValueError("Approved draft/source version hashes are absent")
        if len(str(audit.get("editor_notes", ""))) < 35:
            raise ValueError("Meaningful editorial approval notes are absent")
    print(f"PASS: {len(articles)} approved, version-locked AI article(s)")
    return len(articles)


if __name__ == "__main__":
    validate(Path(__file__).resolve().parents[1])
