#!/usr/bin/env python3
"""AI-assisted editorial draft generator for The Brief.

Reads official UK regulatory source pages and produces original, plain-English
drafts with source excerpts for human editorial review. Does not publish.
Requires GEMINI_API_KEY (GitHub Actions secret); no paid services are selected.
"""
from __future__ import annotations
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from editorial_gate import check as editorial_check

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "generated-drafts"
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
KEY = os.environ.get("GEMINI_API_KEY", "")
MAX_DAILY_DRAFTS = 2
ALLOWED_HOSTS = {"www.fca.org.uk", "fca.org.uk", "www.bankofengland.co.uk", "bankofengland.co.uk"}
AGENT = "TheBrief-EditorialResearch/0.1 (original reporting; linked sources)"


class DocumentParser(HTMLParser):
    """Extract prose from main/article where possible; ignore navigation and scripts."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.skip = 0
        self.active = []
        self.current = []
        self.fragments = []
        self.body_fragments = []
        self.main_fragments = []
        self.main_depth = 0

    def handle_starttag(self, tag, attrs):
        self.depth += 1
        if tag in ("script", "style", "noscript", "nav", "header", "footer", "svg", "aside", "form"):
            self.skip += 1
        if tag in ("main", "article"):
            self.main_depth += 1
        if tag in ("p", "h1", "h2", "h3", "li", "blockquote"):
            self.active.append((tag, self.depth, self.main_depth > 0))
            self.current.append([])

    def handle_data(self, data):
        if self.skip or not self.current:
            return
        self.current[-1].append(data)

    def handle_endtag(self, tag):
        if self.active and self.active[-1][0] == tag:
            _, _, in_main = self.active.pop()
            value = re.sub(r"\s+", " ", " ".join(self.current.pop())).strip()
            if len(value) > 45 and value not in self.body_fragments:
                self.body_fragments.append(value)
                if in_main:
                    self.main_fragments.append(value)
        if tag in ("main", "article"):
            self.main_depth = max(0, self.main_depth - 1)
        if tag in ("script", "style", "noscript", "nav", "header", "footer", "svg", "aside", "form"):
            self.skip = max(0, self.skip - 1)
        self.depth = max(0, self.depth - 1)


def official_url(value: str) -> bool:
    parts = urllib.parse.urlsplit(value)
    return parts.scheme == "https" and (parts.hostname or "").lower() in ALLOWED_HOSTS and not parts.username and not parts.password


def read_official_page(url: str) -> str:
    if not official_url(url):
        raise ValueError("Not a permitted primary-source domain")
    request = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "text/html"})
    with urllib.request.urlopen(request, timeout=18) as response:
        if not official_url(response.geturl()):
            raise ValueError("Official source redirected to a different domain")
        content_type = response.headers.get("Content-Type", "")
        if "html" not in content_type:
            raise ValueError("Page is not HTML; PDFs require a separate parser")
        raw = response.read(800_000)
    parser = DocumentParser()
    parser.feed(raw.decode("utf-8", errors="replace"))
    paragraphs = parser.main_fragments if len(" ".join(parser.main_fragments)) >= 1700 else parser.body_fragments
    document = "\n\n".join(paragraphs)
    if len(document) < 1500:
        raise ValueError("Official page did not contain enough usable evidence")
    return document[:19000]


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", value)).strip()


def fetch_gemini(prompt: str) -> dict:
    if not KEY:
        raise RuntimeError("Missing GEMINI_API_KEY GitHub Actions secret")
    url = "https://generativelanguage.googleapis.com/v1beta/models/" + urllib.parse.quote(MODEL, safe="-._") + ":generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2, "maxOutputTokens": 6000}
    }
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": KEY}
    )
    try:
        with urllib.request.urlopen(request, timeout=70) as response:
            raw = json.loads(response.read(300_000))
    except urllib.error.HTTPError as err:
        detail = err.read(1000).decode("utf-8", errors="replace")
        raise RuntimeError(f"AI API returned HTTP {err.code}: {detail}") from None
    parts = raw.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts)
    if not text:
        raise RuntimeError("AI API returned no article content")
    return json.loads(text)


def make_prompt(item: dict, source: str) -> str:
    return (
        "You are a rigorous British financial-services reporter for The Brief. "
        "Use ONLY the official primary-source text below. Draft a new, original, "
        "easy-to-read article for UK banking and insurance professionals. "
        "Do NOT echo copyrighted secondary publishers, invent dates, numbers, "
        "quoted words, motives, customer impacts or outcomes. Never turn a proposal "
        "into a final rule. Do not repeat source phrasing except short evidence snippets. "
        "Keep the writing like a clear, experienced British reporter talking to a colleague: " 
        "short sentences, natural language, no corporate PR, no exaggerated importance. " 
        "Avoid words like substantial, comprehensive, significantly, stakeholders, " 
        "underpins, pivotal, transformative unless essential and defined. " 
        "Avoid claiming everyone is directly affected or must act unless the evidence says so. " 
        "For a consultation, say proposed and might, never that rules are already changing. " 
        "For a speech, attribute views to the speaker; do not invent binding obligations. " 
        "Each factual assertion and practical consequence must be rooted in this source. " 
        "Use plain British English with useful examples only where the source supports them. " 
        "Return ONLY a JSON object with keys: "
        "headline, standfirst, introduction, what_happened, why_it_matters, "
        "who_is_affected, what_next, context, status, evidence, glossary. "
        "Every body section must be a substantial paragraph (at least 45 words where "
        "the source supports it). All paragraphs together should total 300–550 words. "
        "status must accurately say Proposal, Confirmed announcement, "
        "Published report or Speech / commentary. "
        "evidence must be an array of 4–7 objects with keys claim and support. "
        "Each support must be an EXACT consecutive 7–15 word extract from the "
        "provided primary source, so another programme can verify it. "
        "glossary must be an array of objects with term and explanation (up to 4 items). "
        "Explain what is KNOWN, what isn't, who may need to act and any next steps. "
        "If unknown, say 'The announcement does not specify'. "
        "Do not claim this is independently verified journalism. "
        f"\n\nSOURCE TITLE: {item['title']}\nSOURCE ORGANISATION: {item['source']}"
        f"\nSOURCE DATE: {item['dateISO']}\nSOURCE URL: {item['url']}"
        f"\n\nOFFICIAL TEXT START\n{source}\nOFFICIAL TEXT END"
    )


def validate_draft(generated: dict, source: str, item: dict) -> tuple[dict, dict]:
    keys = ["headline", "standfirst", "introduction", "what_happened",
            "why_it_matters", "who_is_affected", "what_next", "context", "status"]
    if any(not isinstance(generated.get(k), str) or not generated[k].strip() for k in keys):
        raise ValueError("Draft has missing sections")
    evidence = generated.get("evidence", [])
    if not isinstance(evidence, list) or len(evidence) < 4:
        raise ValueError("Draft lacks four source-checkable facts")
    source_norm = norm(source)
    checks = []
    for fact in evidence:
        excerpt = str(fact.get("support", ""))
        claim = str(fact.get("claim", ""))
        if len(excerpt.split()) < 7 or len(excerpt.split()) > 18 or norm(excerpt) not in source_norm or len(claim) < 15:
            raise ValueError("Source claim was not verified against retrieved official document")
        checks.append({"claim": claim[:300], "source_excerpt": excerpt[:220]})
    paras = [generated[x].strip() for x in ["introduction", "what_happened", "why_it_matters",
                                              "who_is_affected", "what_next", "context"]]
    total_words = sum(len(p.split()) for p in paras)
    if total_words < 280 or total_words > 750:
        raise ValueError(f"Article length outside editorial bounds: {total_words} words")
    if len(generated["headline"]) > 170 or len(generated["headline"]) < 25:
        raise ValueError("Unusable headline")
    if len(generated["standfirst"]) < 70 or len(generated["standfirst"]) > 320:
        raise ValueError("Unusable summary")
    if len(generated["what_happened"].split()) < 45 or len(generated["why_it_matters"].split()) < 45:
        raise ValueError("The key explanation sections are too short")
    status = generated["status"].strip()
    if status not in {"Proposal", "Confirmed announcement", "Published report", "Speech / commentary"}:
        raise ValueError("Unknown regulatory publication status")
    glossary = []
    for entry in generated.get("glossary", [])[:4]:
        if isinstance(entry, dict) and entry.get("term") and entry.get("explanation"):
            glossary.append([str(entry["term"])[:55], str(entry["explanation"])[:220]])
    identity = "ai-" + hashlib.sha256(item["url"].encode()).hexdigest()[:20]
    blocks = [
        ["What happened", paras[0] + "\n\n" + paras[1]],
        ["Why it matters at work", paras[2]],
        ["Who is affected", paras[3]],
        ["What happens next", paras[4]],
        ["The background", paras[5]],
    ]
    article = {
        "id": identity, "kind": "original", "category": item.get("category", "Regulation"),
        "dateISO": item["dateISO"], "date": item["dateISO"], "source": item["source"],
        "source_url": item["url"], "url": item["url"], "status": status,
        "title": generated["headline"].strip(), "short": generated["standfirst"].strip(),
        "quick": generated["standfirst"].strip(), "lead": paras[0],
        "blocks": blocks, "glossary": glossary,
        "reading": f"{max(2, round(total_words / 210))} min read",
        "ai_assisted": True,
        "editorial_status": "DRAFT: evidence excerpts checked; not human-reviewed",
    }
    audit = {
        "article_id": identity, "source_url": item["url"], "source_title": item["title"],
        "document_characters": len(source), "word_count": total_words,
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "verbatim_source_checks": checks,
        "limitations": "Excerpt matching is not a complete factual or legal review. Do not publish automatically.",
    }
    return article, audit


def select_candidates(items: list[dict]) -> list[dict]:
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=4)
    choices = []
    for item in items:
        if not official_url(item.get("url", "")):
            continue
        if not (item.get("title") and item.get("dateISO") and item.get("published_at")):
            continue
        try:
            timestamp = dt.datetime.fromisoformat(item["published_at"].replace("Z", "+00:00"))
            if timestamp < cutoff:
                continue
        except ValueError:
            continue
        # Prefer substantive rules, consultations and major official announcements.
        title = item["title"].lower()
        boost = 3 if re.search(r"consultation|regime|rules?|capital|insurance|banking|statement", title) else 0
        choices.append((boost, timestamp.timestamp(), item))
    choices.sort(key=lambda row: (-row[0], -row[1]))
    seen = set()
    selected = []
    for _, _, item in choices:
        if item["url"] in seen:
            continue
        selected.append(item)
        seen.add(item["url"])
        if len(selected) >= 12:
            break
    return selected


def self_test():
    fixture = " ".join(["The regulator proposes to simplify the existing scheme for all qualifying financial institutions."] * 35)
    assert norm("regulator proposes") in norm(fixture)
    assert official_url("https://www.fca.org.uk/news/official-announcement")
    assert not official_url("https://not-fca.org.uk/fake")
    assert not official_url("http://www.fca.org.uk/unsecured")
    assert not official_url("https://www.fca.org.uk.evil.net/")
    assert not official_url("https://www.fca.org.uk@evil.net/")
    data = {"headline": "Regulators propose accountability changes for financial services staff",
            "standfirst": "Regulators have outlined proposed changes to accountability arrangements, with decisions and implementation dates still to be confirmed.",
            "introduction": " ".join(["The regulator has issued an announcement explaining the proposed changes."] * 7),
            "what_happened": " ".join(["The proposal relates to qualifying organisations and their existing responsibilities."] * 7),
            "why_it_matters": " ".join(["Financial services teams need to distinguish proposals from requirements in force."] * 8),
            "who_is_affected": " ".join(["Regulated financial organisations should read the relevant announcement and its scope."] * 7),
            "what_next": " ".join(["Next steps depend on the regulator's published consultation and decision timetable."] * 7),
            "context": " ".join(["Regulatory consultations provide an opportunity to comment before final decisions are made."] * 7),
            "status": "Proposal",
            "evidence": [{"claim": "The regulator proposes changes to the existing scheme", "support": "The regulator proposes to simplify the existing scheme for all qualifying"}] * 4,
            "glossary": [{"term": "Consultation", "explanation": "A proposal on which a regulator seeks feedback."}]}
    item = {"url": "https://www.fca.org.uk/news/official-announcement", "dateISO": "2026-10-22", "source": "FCA", "category": "Regulation", "title": "Draft test"}
    article, audit = validate_draft(data, fixture, item)
    assert article["blocks"] and audit["word_count"] >= 280
    print("PASS: model-response validation and primary-source URL restrictions")


def main():
    if "--self-test" in sys.argv:
        self_test()
        return
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if not KEY:
        print("AI newsroom not activated. Add GEMINI_API_KEY to GitHub Actions secrets.")
        return
    live = json.loads((ROOT / "data" / "live.json").read_text(encoding="utf-8"))
    results = []
    tried = []
    for item in select_candidates(live.get("items", [])):
        if len(results) >= MAX_DAILY_DRAFTS:
            break
        try:
            source = read_official_page(item["url"])
            generated = fetch_gemini(make_prompt(item, source))
            article, audit = validate_draft(generated, source, item)
            editorial_check({"draft": article, "audit": audit})
            results.append(article)
            tried.append({"title": item["title"], "result": "draft saved", "source": item["url"]})
            (OUTPUT / (article["id"] + ".json")).write_text(json.dumps({
                "draft": article, "audit": audit,
                "notice": "Unpublished draft. Evidence quotes are checked, but factual conclusions still need review."
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except Exception as exc:
            tried.append({"title": item["title"], "result": "held back", "reason": str(exc)[:250]})
    (OUTPUT / "run-report.json").write_text(json.dumps({
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "model": MODEL, "drafts": len(results), "items_checked": tried
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"AI newsroom: {len(results)} draft(s), checked {len(tried)} source(s).")
    if not results:
        print("No drafts passed validation; the publication remains unchanged.")


if __name__ == "__main__":
    main()
