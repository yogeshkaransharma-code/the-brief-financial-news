#!/usr/bin/env python3
"""Adversarial deterministic editorial gate benchmark.

Tests only faults code can reasonably detect. Explicitly lists semantic/rights
failures that remain HUMAN REVIEW, not claims of automated fact verification.
"""
import copy
import datetime as dt
import json
from editorial_gate import check
from editorial_fixtures import make_bundle, resign


def run_case(name, mutator, expected_part=None, resign_after=True, human=False):
    bundle = copy.deepcopy(make_bundle())
    mutator(bundle)
    if resign_after:
        resign(bundle)
    try:
        check(bundle, human_review=human)
    except (ValueError, KeyError, TypeError) as err:
        if expected_part and expected_part.lower() not in str(err).lower():
            raise AssertionError(f"{name}: wrong failure cause: {err}") from err
        print("HOLD:", name, "->", str(err)[:105])
        return
    raise AssertionError(f"UNSAFE PASS: {name}")


def main():
    valid = make_bundle()
    assert check(valid)["needs_human_review"] is True
    print("PASS: valid synthetic draft is screened but flagged for human review")
    test_cases = [
        ("missing source URL", lambda b: b["draft"].update(url=""), "Missing required"),
        ("source and audit disagree", lambda b: b["draft"].update(url="https://www.fca.org.uk/publications/consultation-papers/other"), "does not match"),
        ("spoofed FCA hostname", lambda b: (b["draft"].update(url="https://fca.org.uk.malicious.test/news"), b["audit"].update(source_url="https://fca.org.uk.malicious.test/news")), "approved official"),
        ("insecure source", lambda b: (b["draft"].update(url="http://www.fca.org.uk/publications/consultation-papers/x"), b["audit"].update(source_url="http://www.fca.org.uk/publications/consultation-papers/x")), "approved official"),
        ("consultation falsely final", lambda b: b["draft"].update(status="Confirmed announcement"), "consultation"),
        ("regulator speech falsely rule", lambda b: (b["draft"].update(url="https://www.fca.org.uk/news/speeches/fictional-speech"), b["audit"].update(source_url="https://www.fca.org.uk/news/speeches/fictional-speech")), "speech"),
        ("proposal presented as effective immediately", lambda b: b["draft"]["blocks"][2].__setitem__(1, b["draft"]["blocks"][2][1]+" These rules are effective immediately."), "compulsory-language"),
        ("unsupported figure in article", lambda b: b["draft"]["blocks"][1].__setitem__(1, b["draft"]["blocks"][1][1]+" The increase is 12.5%."), "figures"),
        ("unsupported amount in headline", lambda b: b["draft"].update(title=b["draft"]["title"]+" costing £90m"), "figures"),
        ("missing number register", lambda b: b["audit"].pop("source_number_tokens"), "numerical token register"),
        ("repeated evidence passage", lambda b: b["audit"].update(verbatim_source_checks=[b["audit"]["verbatim_source_checks"][0]]*4), "repeats"),
        ("repeated factual claim", lambda b: [x.update(claim="The consultation has a common repeated factual claim") for x in b["audit"]["verbatim_source_checks"]], "distinct factual"),
        ("missing source fingerprint", lambda b: b["audit"].pop("source_sha256"), "fingerprint"),
        ("invalid retrieval timestamp", lambda b: b["audit"].update(retrieved_at="not-a-date"), "timestamp"),
        ("future publication date", lambda b: b["draft"].update(dateISO=(dt.datetime.now(dt.timezone.utc).date()+dt.timedelta(days=200)).isoformat()), "future"),
        ("unrecognised category", lambda b: b["draft"].update(category="Crypto"), "section"),
        ("missing full sections", lambda b: b["draft"].update(blocks=b["draft"]["blocks"][:2]), "five-section"),
        ("short summary", lambda b: b["draft"].update(short="Short"), "headline or standfirst"),
        ("tampered after review snapshot", lambda b: b["draft"].update(title="This was quietly changed after drafting"), "Draft content differs", False),
        ("invalid story ID", lambda b: (b["draft"].update(id="ai-invalid"),b["audit"].update(article_id="ai-invalid")), "identity"),
        ("unreviewed but labelled published", lambda b: b["draft"].update(editorial_status="PUBLISHED: forged approval"), "unreviewed"),
        ("AI source provenance missing at approval", lambda b: b["draft"].update(ai_assisted=False), "AI-assisted", True, True),
    ]
    for name, fn, cause, *settings in test_cases:
        run_case(name, fn, cause, *(settings or []))
    # These are deliberate blind spots: no lexical/regex rule can reliably
    # establish semantic entailment or what an article omitted.
    human_only = [
        "incorrect denominator when both numbers occur somewhere in the source",
        "fabricated causal link using otherwise genuine facts",
        "real qualification omitted from an accurate-looking summary",
        "wrong interpretation of a consultation not detectable from the URL",
        "misleading implication despite supporting quotations",
        "source rights, fairness to affected parties, and non-public conflicts",
    ]
    print(f"PASS: {len(test_cases)} known machine-detectable faults blocked.")
    print(f"REVIEW REQUIRED: {len(human_only)} classes of material semantic or legal errors cannot be certified automatically.")
    for item in human_only:
        print("HUMAN-ONLY:", item)
    report = {"expected_holds": len(test_cases), "unexpected_passes": 0,
              "valid_synthetic_screened": 1, "human_only_unresolved": human_only,
              "meaning": "Machine preflight only; no independent fact-check or permission to auto-publish."}
    print("BENCHMARK_SUMMARY:", json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
