#!/usr/bin/env python3
"""Independent publication gate for The Brief.

Draft existence is not publication approval. Publication requires a person to
review the generated article and its linked official evidence.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

OFFICIAL = {"www.fca.org.uk", "www.bankofengland.co.uk", "fca.org.uk", "bankofengland.co.uk"}
STATUSES = {"Proposal", "Confirmed announcement", "Published report", "Speech / commentary"}
RISKY = re.compile(
    r"\b(?:will\s+(?:now\s+)?(?:have to|be required to|need to|be obliged to)|"
    r"must\s+(?:now\s+|immediately\s+)?comply|"
    r"are\s+now\s+required\s+to)\b", re.I
)
NUMBER = re.compile(r"(?<![\w])(?:£|\$)?\d+(?:[.,]\d+)*(?:%|bn|m|k)?(?![\w])")


def check(bundle: dict, human_review: bool = False) -> dict:
    a = bundle.get("draft")
    audit = bundle.get("audit")
    if not isinstance(a, dict) or not isinstance(audit, dict):
        raise ValueError("Missing article or evidence audit")
    required = ("id", "title", "short", "source", "dateISO", "url", "status", "blocks")
    if any(not a.get(k) for k in required):
        raise ValueError("Missing required article fields")
    if a.get("id") != audit.get("article_id") or a.get("url") != audit.get("source_url"):
        raise ValueError("Article does not match the verified source")
    if not re.fullmatch(r"ai-[a-f0-9]{20}", a["id"]):
        raise ValueError("Unrecognised article identity")
    source = urlsplit(a["url"])
    if source.scheme != "https" or source.hostname not in OFFICIAL or source.username or source.password:
        raise ValueError("Article source is not an approved official site")
    if a["status"] not in STATUSES:
        raise ValueError("Publication status is missing or invalid")
    if "/consultation" in source.path and a["status"] != "Proposal":
        raise ValueError("A consultation cannot be published as a final decision")
    if "/speech" in source.path and a["status"] != "Speech / commentary":
        raise ValueError("A speech cannot be presented as a regulatory decision")
    if a.get("editorial_status", "").startswith("PUBLISHED") and not human_review:
        raise ValueError("Published article was supplied as an unreviewed draft")
    blocks = a["blocks"]
    if not isinstance(blocks, list) or len(blocks) < 5:
        raise ValueError("A full, five-section article is required")
    paragraphs = []
    for block in blocks:
        if not isinstance(block, list) or len(block) != 2 or not all(isinstance(x, str) and x.strip() for x in block):
            raise ValueError("Malformed article section")
        paragraphs.append(block[1])
    word_count = sum(len(p.split()) for p in paragraphs)
    if not 260 <= word_count <= 1150:
        raise ValueError(f"Article length inappropriate: {word_count} words")
    if len(a["title"]) < 22 or len(a["title"]) > 170 or len(a["short"]) < 60:
        raise ValueError("Headline or standfirst fails editorial criteria")
    try:
        published = dt.date.fromisoformat(a["dateISO"])
    except (TypeError, ValueError):
        raise ValueError("Invalid source date") from None
    if published > dt.datetime.now(dt.timezone.utc).date() + dt.timedelta(days=1):
        raise ValueError("Source date is in the future")
    evidence = audit.get("verbatim_source_checks")
    if not isinstance(evidence, list) or len(evidence) < 4:
        raise ValueError("Too few documented source-evidence checks")
    if any(not isinstance(x, dict) or len(x.get("source_excerpt", "").split()) < 7 or len(x.get("claim", "")) < 15 for x in evidence):
        raise ValueError("Incomplete evidence record")
    combined = "\n".join(paragraphs + [a["title"], a["short"]])
    if a["status"] in ("Proposal", "Speech / commentary") and RISKY.search(combined):
        raise ValueError("Unqualified compulsory-language claim in proposal/speech")
    if a.get("category") not in ("Regulation", "Insurance", "Banking", "Technology"):
        raise ValueError("Unrecognised section")
    result = {"id": a["id"], "title": a["title"], "word_count": word_count,
              "status": a["status"], "evidence_checks": len(evidence),
              "needs_human_review": True}
    if human_review and not a.get("ai_assisted"):
        raise ValueError("AI-assisted origin metadata missing")
    return result


def self_test():
    from datetime import timezone
    text = " ".join(["The regulator has described a proposed process for affected firms and invited feedback."] * 12)
    a = {"id": "ai-" + "a" * 20, "title": "Regulator sets out a consultation on accountability rules",
         "short": "The regulator is considering changes, but the proposals are not yet rules that firms have to implement.",
         "source": "FCA", "url": "https://www.fca.org.uk/publications/consultation-papers/example",
         "status": "Proposal", "dateISO": dt.datetime.now(timezone.utc).date().isoformat(),
         "category": "Regulation", "ai_assisted": True, "blocks": [[str(i), text] for i in range(5)]}
    checks = [{"claim": "The regulator has announced a consultation", "source_excerpt": "The regulator has described a proposed process for affected firms"}] * 4
    bundle = {"draft": a, "audit": {"article_id": a["id"], "source_url": a["url"], "verbatim_source_checks": checks}}
    assert check(bundle)["needs_human_review"]
    bundle["draft"]["status"] = "Confirmed announcement"
    try:
        check(bundle)
        raise AssertionError("Consultation should have been rejected")
    except ValueError:
        pass
    print("PASS: full-article editorial gate; consultation mislabelling rejected")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("bundle", nargs="?")
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--reviewed", action="store_true")
    args = p.parse_args()
    if args.self_test:
        self_test()
        return
    if not args.bundle:
        p.error("Specify the editorial draft JSON file")
    bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    print(json.dumps(check(bundle, human_review=args.reviewed), indent=2))


if __name__ == "__main__":
    main()
