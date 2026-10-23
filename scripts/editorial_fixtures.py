"""Synthetic editorial fixtures for deterministic CI; no real article is endorsed."""
from __future__ import annotations
import copy
import datetime as dt
import hashlib
import json

PARAGRAPH = " ".join([
    "The regulator has proposed a consultation on possible reporting adjustments.",
    "It has invited feedback from firms before deciding whether to make any rule changes.",
    "The existing framework remains in place while the proposal is assessed."
] * 5)
EXCERPTS = [
    ("C1: Regulator consultation announced", "The regulator has proposed a consultation on possible reporting adjustments"),
    ("C2: Feedback invited from firms", "It has invited feedback from firms before deciding whether to"),
    ("C3: Proposal is not a final rule", "whether to make any rule changes The existing framework"),
    ("C4: Existing obligations remain", "The existing framework remains in place while the proposal is assessed"),
]


def fingerprint(article):
    return hashlib.sha256(json.dumps(article, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def resign(bundle):
    bundle["audit"]["draft_sha256"] = fingerprint(bundle["draft"])
    return bundle


def make_bundle():
    date = dt.datetime.now(dt.timezone.utc).date().isoformat()
    aid = "ai-" + "a" * 20
    article = {
        "id": aid,
        "kind": "original", "ai_assisted": True, "editorial_status": "DRAFT",
        "title": "Regulator begins consultation on changes for financial services firms",
        "short": "The regulator has invited firms to comment on possible reporting changes, with decisions yet to be taken.",
        "source": "FCA",
        "url": "https://www.fca.org.uk/publications/consultation-papers/fictional-test",
        "status": "Proposal", "dateISO": date, "category": "Regulation",
        "blocks": [[f"Section {i}", PARAGRAPH] for i in range(5)],
    }
    audit = {
        "article_id": aid, "source_url": article["url"],
        "source_sha256": hashlib.sha256(PARAGRAPH.encode("utf-8")).hexdigest(),
        "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_number_tokens": [],
        "verbatim_source_checks": [
            {"claim": claim + " according to the primary official source",
             "source_excerpt": excerpt}
            for claim, excerpt in EXCERPTS
        ],
    }
    return resign({"draft": article, "audit": audit, "captured_source_excerpt": PARAGRAPH})


def clone(bundle):
    return copy.deepcopy(bundle)
