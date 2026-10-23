#!/usr/bin/env python3
"""Build an offline, human-readable review packet from AI draft artifacts."""
from __future__ import annotations

from html import escape
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "generated-drafts"


def render():
    FOLDER.mkdir(exist_ok=True)
    files = sorted([*FOLDER.glob("ai-*.json"), *FOLDER.glob("HOLD-ai-*.json")])
    repo = os.environ.get("GITHUB_REPOSITORY", "yogeshkaransharma-code/the-brief-financial-news")
    run = os.environ.get("GITHUB_RUN_ID", "unknown")
    cards = []
    for file in files:
        bundle = json.loads(file.read_text(encoding="utf-8"))
        article, audit = bundle["draft"], bundle["audit"]
        flags = bundle.get("editorial_flags") or []
        flagged = bool(flags) or file.name.startswith("HOLD-")
        title = escape(article["title"])
        draft_id = escape(article["id"])
        body = "".join(
            "<h2>" + escape(heading) + "</h2>" +
            "".join("<p>" + escape(p) + "</p>" for p in text.split("\n\n"))
            for heading, text in article.get("blocks", [])
        )
        checks = "".join(
            "<li><strong>" + escape(x["claim"]) + "</strong><blockquote>" +
            escape(x["source_excerpt"]) + "</blockquote></li>"
            for x in audit.get("verbatim_source_checks", [])
        )
        captured = bundle.get("captured_source_excerpt", "")
        evidence_snapshot = (
            "<details><summary>View exact extracted source text supplied to AI (not the complete document)</summary>"
            "<pre class=\"source-extract\">" + escape(captured) + "</pre></details>"
            if captured else "<p class=\"warning\">Source snapshot missing. Publication must be held.</p>"
        )
        source_limits = escape(audit.get("source_retrieval_limits", "Human verification of the complete official source remains essential."))
        source = escape(article["url"], quote=True)
        flag_items = "".join("<li>"+escape(str(flag.get("claim_id","")))+" — "+escape(str(flag.get("reason","")))+"</li>" for flag in flags if isinstance(flag,dict))
        flags_html = ("<h2>Unresolved evidence or interpretation</h2><ul>"+(flag_items or "<li>Material evidence gaps</li>")+"</ul>") if flagged else ""
        cards.append(
            f'<article><small>{("HELD — DO NOT PUBLISH" if flagged else "SCREENED — HUMAN REVIEW REQUIRED")} · {escape(article["status"])}</small>'
            f'<h1>{title}</h1><p class="standfirst">{escape(article["short"])}</p>'
            f'<p><b>Draft ID:</b> <code>{draft_id}</code></p>'
            f'<p><b>Primary source:</b> <a href="{source}" rel="noopener noreferrer">{escape(article["source"])}</a></p>'
            f'<div class="copy">{body}</div>{flags_html}'
            f'<h2>Evidence to check against the original</h2><ol>{checks}</ol>'
            f'<p class="warning">{source_limits}</p>{evidence_snapshot}'
            '<p class="warning">Matching quotes does not verify the interpretation or every claim. '
            'Check all deadlines, amounts, regulatory status and possible implications. '
            'Reject or revise the draft if anything is inaccurate.</p></article>'
        )
    stats = {}
    report = FOLDER / "run-report.json"
    if report.exists():
        data = json.loads(report.read_text(encoding="utf-8"))
        stats = data
    held = "".join(
        "<li>" + escape(x.get("title", "")) + " — " + escape(x.get("reason", "held")) + "</li>"
        for x in stats.get("items_checked", []) if x.get("result") != "draft saved"
    )
    template = """<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Brief · Editorial review</title><style>
body{font:16px/1.7 system-ui,-apple-system,sans-serif;margin:0;background:#f8f8f5;color:#162b2c}
main{max-width:860px;margin:auto;padding:40px 22px}h1,h2{font-family:Georgia,serif;line-height:1.2}h1{font-size:clamp(28px,5vw,42px)}
article{background:white;border:1px solid #d8e1db;padding:clamp(22px,5vw,48px);margin:32px 0;border-radius:10px}
article h2{font-size:26px;margin-top:34px}small{font-weight:800;color:#33645d;letter-spacing:1.3px}
.standfirst{font-size:19px;color:#46615f}.warning{background:#fff4e8;padding:17px;border-left:3px solid #ad7048}
blockquote{margin:8px 0 24px;padding:8px 18px;border-left:3px solid #a4bcb5;color:#45615f}
code{overflow-wrap:anywhere;font-size:14px}a{color:#1f625c}.copy p{margin-bottom:19px}
.source-extract{font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere;border:1px solid #e2e2e2;background:#f7f7f5;padding:18px;max-height:450px;overflow:auto}
</style></head><body><main><p>THE BRIEF · INTERNAL EDITORIAL REVIEW</p>
<h1>Review today's AI-assisted news drafts</h1>
<p>Run ID: <code>__RUN__</code>. Drafts in this packet are not on the public website.</p>
<p><strong>Instructions:</strong> Open each linked primary source, read the full draft,
check every factual assertion and regulatory implication, and confirm that dates and
numbers match the document. You may decline to publish any or all drafts.</p>
<p>Once an article has been reviewed, visit
<a href="https://github.com/__REPO__/actions/workflows/publish-reviewed.yml">Publish a reviewed article</a>.
Select <em>Run workflow</em>, enter the Run ID and exact Draft ID, then type the approval phrase.
The workflow checks the draft again and publishes only that specific article.</p>
__ARTICLES__
<h2>Sources that did not pass the draft process</h2><ul>__HELD__</ul>
</main></body></html>"""
    result = (template.replace("__RUN__", escape(run))
              .replace("__REPO__", escape(repo))
              .replace("__ARTICLES__", "\n".join(cards) if cards else "<p>No drafts passed verification in this run.</p>")
              .replace("__HELD__", held or "<li>None</li>"))
    (FOLDER / "EDITORIAL-REVIEW.html").write_text(result, encoding="utf-8")
    print(f"Editorial review packet: {len(files)} candidate article(s), including {sum(x.name.startswith('HOLD-') for x in files)} held after independent review")


if __name__ == "__main__":
    render()
