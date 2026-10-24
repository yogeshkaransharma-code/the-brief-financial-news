#!/usr/bin/env python3
"""Publish readable HTML directly, with JavaScript as an enhancement only.

Run after provenance and editorial audit validation. Public Pages contains only
approved original articles, not the private RSS discovery feed or held drafts.
"""
from __future__ import annotations
import html
import json
import re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public"


def esc(value):
    return html.escape(str(value or ""), quote=True)


def insert_once(page, old, replacement):
    if page.count(old) != 1:
        raise ValueError(f"Public build anchor missing or repeated: {old[:65]}")
    return page.replace(old, replacement, 1)


def valid_articles():
    records = json.loads((ROOT / "data/articles.json").read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("Invalid article archive")
    seen = set()
    for a in records:
        ident = a.get("id", "")
        if not re.fullmatch(r"ai-[a-f0-9]{20}", ident) or ident in seen:
            raise ValueError("Invalid or repeated article ID")
        seen.add(ident)
        if not (a.get("publication_method") == "autonomous"
                and a.get("ai_assisted") is True
                and str(a.get("editorial_status", "")).startswith("PUBLISHED:")
                and a.get("url", "").startswith("https://")
                and isinstance(a.get("blocks"), list)
                and len(a["blocks"]) >= 3):
            raise ValueError("Unapproved or incomplete article in public build")
    return sorted(records, key=lambda a: (a.get("dateISO", ""), a.get("published_at", ""), a["id"]), reverse=True)


def story_href(a):
    return "story/" + quote(a["id"], safe="") + ".html"


def article_body(a):
    out = []
    for heading, paragraph in a["blocks"]:
        out.append("<h2>" + esc(heading) + "</h2>")
        for part in re.split(r"\n\s*\n", str(paragraph)):
            if part.strip():
                out.append("<p>" + esc(part.strip()) + "</p>")
    return "\n".join(out)


def standalone_story(a):
    heading = esc(a["title"])
    description = esc(a.get("short", ""))
    body = article_body(a)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{heading} — The Brief</title><meta name="description" content="{description}">
<style>
:root{{--ink:#30282a;--accent:#87404b;--paper:#f8f5ef}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:17px/1.7 Georgia,serif}}
header,main,footer{{max-width:810px;margin:auto;padding:22px 25px}}
header{{border-bottom:1px solid #d7c9c6;font:700 25px Arial,sans-serif}}
a{{color:var(--accent)}}.brand{{text-decoration:none}}.kicker{{font:700 12px Arial,sans-serif;letter-spacing:.1em;color:var(--accent)}}
h1{{font-size:clamp(33px,5vw,54px);line-height:1.1;font-weight:500}}
h2{{font-weight:500;font-size:29px;margin-top:37px;line-height:1.25}}
.intro{{font-size:22px;color:#5f5352}}.meta,.disclosure{{font:13px/1.6 Arial,sans-serif;color:#655959}}
.source{{border-top:1px solid #d7c9c6;padding-top:20px;margin-top:30px;font:14px/1.6 Arial,sans-serif;overflow-wrap:anywhere}}
footer{{border-top:1px solid #d7c9c6;font:13px Arial,sans-serif}}
</style></head><body>
<header><a class="brand" href="../index.html">THE BRIEF.</a></header>
<main><p><a href="../index.html">← All articles</a></p>
<p class="kicker">{esc(a.get("category", ""))} · THE BRIEF REPORT</p>
<h1>{heading}</h1><p class="intro">{description}</p>
<p class="meta">Original news: {esc(a.get("dateISO", ""))} · Published by The Brief: {esc(a.get("published_at", "")[:10])} · {esc(a.get("source", ""))}</p>
<article>{body}</article>
<div class="source"><strong>Original evidence</strong><p><a href="{esc(a['url'])}" rel="noopener noreferrer" target="_blank">{esc(a.get("source", "Primary source"))} — source document ↗</a></p></div>
<p class="disclosure">This article was written and screened by an automated newsroom using a named primary source. It has not been approved by a human editor. Read <a href="../about.html">our editorial and corrections policy</a>.</p>
</main><footer><a href="../index.html">Back to The Brief</a> · Not financial advice</footer>
</body></html>
"""


def build():
    records = valid_articles()
    if not records:
        raise ValueError("There are no published articles to display; refusing blank deploy")
    page = (ROOT / "index.html").read_text(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "data").mkdir(exist_ok=True)
    (OUT / "story").mkdir(exist_ok=True)

    latest = max(records, key=lambda a: (a.get("published_at", ""), a["id"]))
    first = records[0]
    feature = (
        '<div id="latest-published-highlight" style="padding:14px 0;border-bottom:1px solid #ded8d0">'
        '<span class="section-kicker">MOST RECENTLY PUBLISHED</span>'
        '<p style="margin:4px 0;font:500 22px/1.25 Georgia,serif"><a href="' + esc(story_href(latest)) + '">'
        + esc(latest["title"]) + '</a></p><p class="meta">Original announcement: '
        + esc(latest.get("dateISO")) + ' · The Brief published: '
        + esc(latest.get("published_at", "")[:10]) + '</p></div>'
    )
    page = insert_once(page,
        '<div class="issue-heading"><span>THE DAILY EDITION</span><span id="issue-date">TODAY</span></div>',
        '<div class="issue-heading"><span>THE DAILY EDITION</span><span id="issue-date">TODAY</span></div>\n' + feature)
    lead = ('<article id="lead-story" class="lead-story"><span class="story-kicker">'
        + esc(first.get("category")) + ' / THE LEAD STORY</span><h1><a href="'
        + esc(story_href(first)) + '">' + esc(first["title"])
        + '</a></h1><p class="standfirst">' + esc(first.get("short")) + '</p>'
        + '<p class="meta">Original news: ' + esc(first.get("dateISO"))
        + ' · The Brief published: ' + esc(first.get("published_at", "")[:10]) + '</p>'
        + '<p><a class="cta" href="' + esc(story_href(first)) + '">Read the full article ↗</a></p></article>')
    page = insert_once(page, '<article id="lead-story" class="lead-story"></article>', lead)
    briefing = ''.join(
        '<div class="briefing-story"><span class="brief-number">0' + str(i+1)
        + '</span><div><span class="story-kind">FULL ARTICLE</span>'
        + '<a href="' + esc(story_href(a)) + '">' + esc(a["title"]) + '</a>'
        + '<p>' + esc(a.get("short", "")[:190]) + '</p></div></div>'
        for i, a in enumerate(records[:3])
    )
    page = insert_once(page,
        '<div id="briefing-stories" class="briefing-stories"></div>',
        '<div id="briefing-stories" class="briefing-stories">' + briefing + '</div>')
    rows = []
    prior = ""
    for i, a in enumerate(records[:15]):
        date = str(a.get("dateISO", ""))[:10]
        if date != prior:
            rows.append('<h3 class="date-separator">' + esc(date) + '</h3>')
            prior = date
        rows.append(
            '<article class="news-item"><div class="story-ordinal">' + str(i+1).zfill(2)
            + '</div><div><div class="news-cat">' + esc(a.get("category")) + ' · OUR REPORT</div>'
            + '<h3><a href="' + esc(story_href(a)) + '">' + esc(a["title"]) + '</a></h3>'
            + '<p class="summary">' + esc(a.get("short")) + '</p>'
            + '<p class="meta">Original news: ' + esc(date)
            + ' · The Brief published: ' + esc(a.get("published_at", "")[:10]) + '</p></div></article>'
        )
    page = insert_once(page, '<div class="feed" id="feed"></div>',
        '<div class="feed" id="feed">' + '\n'.join(rows) + '</div>')
    page = insert_once(page, '<div class="news-count" id="news-count"></div>',
        '<div class="news-count" id="news-count">' + str(len(records)) + ' articles</div>')
    payload = json.dumps(records, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    page = insert_once(page, '<script type="application/json" id="curated-data">[]</script>',
        '<script type="application/json" id="curated-data">[]</script>\n'
        '<script type="application/json" id="embedded-articles">' + payload + '</script>')
    (OUT / "index.html").write_text(page, encoding="utf-8")
    (OUT / "about.html").write_text((ROOT / "about.html").read_text(encoding="utf-8"), encoding="utf-8")
    (OUT / "data/articles.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for a in records:
        (OUT / story_href(a)).write_text(standalone_story(a), encoding="utf-8")

    # These assertions catch the actual failure the earlier smoke tests missed.
    built = (OUT / "index.html").read_text(encoding="utf-8")
    if not all(x["title"].replace("&", "&amp;") in built for x in records[:5]):
        # Some headlines contain punctuation encoded as entities; check rendered text.
        for a in records[:5]:
            if esc(a["title"]) not in built:
                raise ValueError("Missing pre-rendered headline: " + a["id"])
    if built.count('id="embedded-articles"') != 1:
        raise ValueError("Inline fallback missing")
    for a in records:
        if not (OUT / story_href(a)).is_file():
            raise ValueError("Missing public standalone article: " + a["id"])
    print("PUBLIC_BUILD_OK: " + json.dumps({"articles": len(records),
        "latest": latest["id"], "standalone_pages": len(records),
        "pre_rendered_feed": True, "inline_fallback": True}, sort_keys=True))


if __name__ == "__main__":
    build()
