#!/usr/bin/env python3
"""Independent publication gate for The Brief.

Draft existence is not publication approval. Publication requires a person to
review the generated article and its linked official evidence.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from financial_consistency import concerns as financial_concerns
from source_retrieval import ALLOWED as OFFICIAL
from publication_scope import source_lane
from numeric_evidence import unsupported as unsupported_quantities

# Share the primary-source host allowlist with the actual document reader.
STATUSES = {"Proposal", "Confirmed announcement", "Published report", "Speech / commentary", "Original reporting"}
RISKY = re.compile(
    r"\b(?:will\s+(?:now\s+)?(?:have to|be required to|need to|be obliged to)|"
    r"must\s+(?:now\s+|immediately\s+)?comply|"
    r"are\s+now\s+required\s+to|" 
    r"(?:now\s+)?in\s+force|effective\s+immediately|"
    r"(?:final|confirmed)\s+rules?\s+(?:now\s+)?apply)\b", re.I
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
    signature = hashlib.sha256(json.dumps(a, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    if audit.get("draft_sha256") != signature:
        raise ValueError("Draft content differs from the version recorded in its evidence audit")
    if not re.fullmatch(r"[0-9a-f]{64}", audit.get("source_sha256", "")):
        raise ValueError("Missing source-text snapshot fingerprint")
    captured = bundle.get("captured_source_excerpt")
    if not isinstance(captured, str) or len(captured.strip()) < 800:
        raise ValueError("Original source excerpt missing from the audit packet")
    if hashlib.sha256(captured.encode("utf-8")).hexdigest() != audit["source_sha256"]:
        raise ValueError("Source excerpt does not match its recorded fingerprint")
    try:
        retrieved = dt.datetime.fromisoformat(audit["retrieved_at"].replace("Z", "+00:00"))
        if retrieved.tzinfo is None or retrieved > dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=10):
            raise ValueError("Invalid retrieval timestamp")
    except (KeyError, AttributeError, ValueError) as exc:
        raise ValueError("Missing or invalid source retrieval timestamp") from exc
    if not re.fullmatch(r"ai-[a-f0-9]{20}", a["id"]):
        raise ValueError("Unrecognised article identity")
    source = urlsplit(a["url"])
    if (source.scheme != "https" or source.hostname not in OFFICIAL or source.username
            or source.password or source_lane(a["url"]) is None):
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
    if not isinstance(blocks, list) or len(blocks) < 3:
        raise ValueError("At least three coherent explanatory sections are required")
    paragraphs = []
    for block in blocks:
        if not isinstance(block, list) or len(block) != 2 or not all(isinstance(x, str) and x.strip() for x in block):
            raise ValueError("Malformed article section")
        paragraphs.append(block[1])
    word_count = sum(len(p.split()) for p in paragraphs)
    if not 120 <= word_count <= 1100:
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
    if any(not isinstance(x, dict) or len(x.get("source_excerpt", "").split()) < 7 or len(x.get("claim", "")) < (3 if audit.get("review_headings") else 15) for x in evidence):
        raise ValueError("Incomplete evidence record")
    # Every cited excerpt must actually be present in exactly the captured text
    # used by the model, not merely be supplied by the model as a quotation.
    import unicodedata
    normalize = lambda v: re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", unicodedata.normalize("NFKC", v).lower())).strip()
    evidence_source = normalize(captured)
    if any(normalize(x["source_excerpt"]) not in evidence_source for x in evidence):
        raise ValueError("An evidence quote does not appear in the captured official source excerpt")
    unique_supports = {re.sub(r"\s+", " ", x["source_excerpt"]).casefold().strip() for x in evidence}
    if len(unique_supports) < 4:
        raise ValueError("Evidence repeats the same source passage; four distinct excerpts are required")
    unique_claims = {re.sub(r"\s+", " ", x["claim"]).casefold().strip() for x in evidence}
    if len(unique_claims) < 4:
        raise ValueError("Four distinct factual checks are required")
    source_numbers = audit.get("source_number_tokens")
    if not isinstance(source_numbers, list) or any(not isinstance(x, str) for x in source_numbers):
        raise ValueError("Original source's numerical token register is missing")
    reported_numbers = {m.group().lower().replace(",", "") for m in NUMBER.finditer(" ".join([a["title"], a["short"]] + ([v for block in blocks for v in block] if audit.get("review_headings") else paragraphs)))}
    reported_text=' '.join([a['title'],a['short']]+([v for block in blocks for v in block] if audit.get('review_headings') else paragraphs))
    if unsupported_quantities(reported_text,captured+' '+audit.get('source_title','')+' '+a['dateISO']):
        raise ValueError("Article introduces figures not found in the recorded official source")
    combined = "\n".join([v for block in blocks for v in block] + [a["title"], a["short"]])
    if a["status"] in ("Proposal", "Speech / commentary") and RISKY.search(combined):
        raise ValueError("Unqualified compulsory-language claim in proposal/speech")
    contextual_issues = financial_concerns(a, captured)
    if contextual_issues:
        raise ValueError("Financial interpretation requires clarification: " + "; ".join(contextual_issues))
    if audit.get("pipeline_version") == 2:
        review = audit.get("sentence_review")
        if not isinstance(review, dict) or review.get("review_schema") != "one-verdict-per-sentence-v2":
            raise ValueError("Separate evidence-review report missing")
        fields = [a["title"], a["short"]] + ([v for block in blocks for v in block] if audit.get("review_headings") else paragraphs)
        sentence_count = sum(
            len([x for x in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9£])|\n+", field) if x.strip()])
            for field in fields
        )
        labels = [f"C{i:02}" for i in range(1, sentence_count + 1)]
        if review.get("reviewed_sentence_ids") != labels or review.get("reviewed") != sentence_count:
            raise ValueError("Not every sentence was independently screened")
        if (review.get("held") or review.get("supported") != sentence_count
                or bundle.get("editorial_flags")):
            raise ValueError("An unsupported, contradicted or ambiguous sentence was found")
        if not isinstance(audit.get("source_document_urls"), list) or not audit["source_document_urls"]:
            raise ValueError("Original source-document URLs missing from evidence packet")
        import hashlib as _hashlib
        # Numeric tokens are checked again against the captured material;
        # the model's self-reported token register is not authoritative.
        expected_tokens = {m.group().lower().replace(",", "") for m in
                           NUMBER.finditer(captured + " " + audit.get("source_title", "") + " " + a["dateISO"])}
        if set(source_numbers) != expected_tokens:
            raise ValueError("Source numerical register differs from captured source")
    elif human_review:
        raise ValueError("Legacy AI draft has no separate full-sentence evidence review; cannot publish")

    if a.get("category") not in ("Regulation", "Insurance", "Banking", "Technology", "Pensions", "Brokers"):
        raise ValueError("Unrecognised section")
    result = {"id": a["id"], "title": a["title"], "word_count": word_count,
              "status": a["status"], "evidence_checks": len(evidence),
              "needs_human_review": True}
    if human_review and not a.get("ai_assisted"):
        raise ValueError("AI-assisted origin metadata missing")
    return result


def self_test():
    from editorial_fixtures import make_bundle, resign
    bundle = make_bundle()
    assert check(bundle)["needs_human_review"]
    bundle["draft"]["status"] = "Confirmed announcement"
    resign(bundle)
    try:
        check(bundle)
        raise AssertionError("Consultation mislabelling was not rejected")
    except ValueError as exc:
        assert "consultation" in str(exc).lower()
    print("PASS: fingerprint, evidence and regulatory classification checks")


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

