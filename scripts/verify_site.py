#!/usr/bin/env python3
"""Fail deployment if the site shell or generated news feed is unusable."""
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlsplit

root = Path(__file__).resolve().parents[1]
html = (root / "index.html").read_text(encoding="utf-8")
data = json.loads((root / "data" / "live.json").read_text(encoding="utf-8"))
items = data.get("items", [])
assert 'id="feed"' in html, "News container missing"
assert 'id="briefing-stories"' in html, "Daily briefing container missing"
about=(root/"about.html").read_text(encoding="utf-8")
assert 'href="about.html"' in html, "About page navigation absent"
assert "<h1>Good financial news should make sense.</h1>" in about, "About page content missing"
assert "strict UK calendar-day rule" in about, "Same-day original-source publication standard not documented"
assert "No verified news from today yet." in html, "Empty same-day edition not explained to readers"
assert "automated research and generative AI" in about, "Reporting method must be transparently disclosed"
assert "fetch('data/articles.json'" in html, "AI article loader missing"
assert "fetch('data/live.json'" not in html, "Internal source wire must not be loaded into the public website"
assert '<script type="application/json" id="curated-data">[]</script>' in html, "Legacy hand-written articles remain"
assert 'id="context"' in html and 'id="explainer-list"' in html, "Beginner learning section missing"
assert "const EXPLAINER_GROUPS = " in html and 'Explore all 30 explainers' in html, "Original educational guides are missing"
assert "Math.floor(today.day/2)" in html, "Explainer set does not rotate every two UK calendar days"
assert "const scoreDate=s=>Date.parse(s.dateISO||" in html, "Actual source news date is missing from metadata"
assert "const compareStories=(a,b)=>reportTime(a)-reportTime(b)" in html, "Newest published verified article must appear first"
assert 'id="static-edition"' in html and "THEBRIEF_STATIC_START" in html, "Canonical homepage must display readable published article links without JavaScript"
assert 'date-separator' in html, "Chronological date headings are absent"
assert "fetch('data/live.json'" not in html, "Internal source feed leaked into public site"
assert "const byId=()=>Object.fromEntries(published.map" in html, "External feed records exposed as article pages"
assert "const allItems=()=>sortItems(published.filter(" in html, "Non-AI source headlines are still in the main news feed"
assert "Edition preview · automated updates not connected" not in html, "Outdated status placeholder"
assert len(items) >= 10, f"Too few live stories: {len(items)}"
assert len(data.get("sources_checked", [])) >= 2, "Not enough working news sources"
ts = dt.datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00"))
age = dt.datetime.now(dt.timezone.utc) - ts
assert dt.timedelta(minutes=-10) < age < dt.timedelta(hours=3), f"News collection is stale: {age}"
seen = set()
for s in items:
    assert s.get("id") and s["id"] not in seen, "Missing or repeated story id"
    seen.add(s["id"])
    assert s.get("title") and s.get("source") and s.get("published_at"), "Story metadata missing"
    assert len(s.get("short") or "") >= 45, f"Unusable story description: {s.get('title')}"
    parsed = urlsplit(s.get("url", ""))
    assert parsed.scheme == "https" and parsed.hostname, "Unsafe or missing story source link"
published = json.loads((root / "data" / "articles.json").read_text(encoding="utf-8"))
assert isinstance(published, list), "Published original articles must be a list"
retired_path=root/"data/retired-source-urls.json"
retired_urls=set(json.loads(retired_path.read_text(encoding="utf-8")).get("urls",[])) if retired_path.exists() else set()
ids = set()
for article in published:
    assert article["id"] not in ids, "Repeated original article"
    ids.add(article["id"])
    assert article.get("kind") == "original", "An original article is mislabelled"
    assert article.get("ai_assisted") is True, "An article was not written by the AI newsroom"
    assert article.get("publication_method") == "autonomous", "Public feed must be written and published by the AI newsroom"
    assert article.get("url") not in retired_urls, "Previously deleted article was republished"
    assert str(article.get("editorial_status", "")).startswith("PUBLISHED:"), "An unapproved AI draft appears in the public feed"
    assert len(article.get("blocks", [])) >= 3, "Original article has insufficient coverage"
    assert urlsplit(article.get("url", "")).scheme == "https", "Article source link is invalid"

print(f"PASS: {len(published)} autonomous AI articles, {len(items)} private discovery leads, no legacy news feed, two-day education rotation, healthy website")
