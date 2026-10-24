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
        method=article.get("publication_method","human")
        if method=="autonomous":
            if audit.get("review_mode")!="autonomous_low_risk":
                raise ValueError("Automated article lacks source-limited approval record")
            if audit.get("automation_policy_version") not in {"limited-autonomy-2026-10-23.1","first-party-newsroom-2026-10-23-v1","daily-24-hour-news-2026-10-23-v2","dated-catchup-newsroom-2026-10-24-v3","strict-uk-same-day-original-news-2026-10-24-v4"}:
                raise ValueError("Unknown machine publication policy")
            if article.get("reviewed_by")!="autonomous-evidence-screening" or audit.get("approved_by_github_actor")!="AUTONOMOUS_PIPELINE_NO_HUMAN":
                raise ValueError("Automated article falsely claims a human reviewer")
            if "no human review" not in article["editorial_status"].lower():
                raise ValueError("Autonomous article must disclose no human review")
        elif method=="ai_source_checked":
            # Explicit assistant-led one-off source check; not a human sign-off
            # or a completed unattended publisher run.
            if audit.get("review_mode")!="assistant_source_checked_v1":
                raise ValueError("AI-authored feature lacks the correct source-review record")
            if audit.get("approved_by_github_actor")!="ASSISTANT_NO_HUMAN_EDITOR" or article.get("reviewed_by")!="assistant-ai-source-review":
                raise ValueError("AI-reviewed article misattributes editorial responsibility")
            if audit.get("human_editor_approval") is not False:
                raise ValueError("AI-written feature cannot claim human editorial approval")
            if not article.get("url","").startswith("https://www.fca.org.uk/data/complaints-data-2026-h1"):
                raise ValueError("Initial AI source-review allowance is limited to the checked FCA article")
            if len(audit.get("claims_checked",[]))<8 or not all(
                claim.get("status","").startswith("SUPPORTED") and claim.get("section")
                for claim in audit["claims_checked"]
            ):
                raise ValueError("Claim register is incomplete or has unresolved entries")
            if not audit.get("source_evidence_sha256"):
                raise ValueError("AI source-review evidence fingerprint missing")
        elif method=="human":
            if not audit.get("approved_by_github_actor") or not article.get("reviewed_by"):
                raise ValueError("Accountable human reviewer is not recorded")
            if article["reviewed_by"] != audit["approved_by_github_actor"]:
                raise ValueError("Article reviewer differs from recorded approval")
        else:
            raise ValueError("Unknown approval mode")
        source_hash_key = "source_evidence_sha256" if method=="ai_source_checked" else "source_snapshot_sha256"
        if not audit.get("reviewed_draft_sha256") or not audit.get(source_hash_key):
            raise ValueError("Article/source evidence version hashes are absent")
        if len(str(audit.get("editor_notes", ""))) < 35:
            raise ValueError("Meaningful editorial approval notes are absent")
    print(f"PASS: {len(articles)} approved, version-locked AI article(s)")
    return len(articles)


if __name__ == "__main__":
    validate(Path(__file__).resolve().parents[1])
