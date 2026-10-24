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
from same_day_policy import published_same_day, clock

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
    return sorted(records, key=lambda a: (a.get("published_at", ""), a.get("dateISO", ""), a["id"]), reverse=True)


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
    """One source-attributed reading page styled as part of the publication."""
    from datetime import date

    headline = esc(a["title"])
    description = esc(a.get("short", ""))
    body = article_body(a)
    news_date = date.fromisoformat(a["dateISO"][:10]).strftime("%-d %B %Y")
    release_date = date.fromisoformat(a["published_at"][:10]).strftime("%-d %B %Y")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{headline} — The Brief</title><meta name="description" content="{description}">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&amp;family=Newsreader:wght@400;500;600;700&amp;display=swap" rel="stylesheet">
<style>
:root{{--ink:#272323;--paper:#F8F5EF;--accent:#87404B;--muted:#6B5F5C;--rule:#DED8D0;--serif:'Newsreader',Georgia,serif;--sans:'Inter',Arial,sans-serif}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink);-webkit-font-smoothing:antialiased}}
a{{color:inherit;text-underline-offset:4px;text-decoration-color:#B58B91}}
a:hover{{color:var(--accent)}}
.utility{{background:#30282A;color:#EFE7E4;font:750 10px var(--sans);letter-spacing:.14em;text-align:center;padding:11px 16px}}
.masthead{{border-bottom:1px solid var(--rule)}}
.masthead-inner{{max-width:1110px;padding:25px 28px 23px;margin:auto;display:flex;align-items:end;justify-content:space-between;gap:18px}}
.brand{{font:700 clamp(37px,5vw,54px)/.95 var(--serif);letter-spacing:-1.8px;text-decoration:none}}
.brand span{{color:var(--accent)}}
.tagline{{font:750 10px/1.5 var(--sans);letter-spacing:.12em;color:#645B5B}}
.navstrip{{border-bottom:1px solid var(--rule);background:white}}
.navinner{{max-width:1110px;padding:13px 28px;margin:auto;display:flex;justify-content:space-between;gap:15px;font:650 12px var(--sans)}}
.reader{{width:min(100%,820px);margin:auto;padding:46px 30px 80px}}
.kicker{{font:800 11px var(--sans);letter-spacing:.13em;color:var(--accent);text-transform:uppercase}}
h1{{font:500 clamp(38px,5.7vw,65px)/1.06 var(--serif);letter-spacing:-1.6px;margin:22px 0 23px}}
.intro{{font:400 clamp(19px,2.8vw,23px)/1.5 var(--serif);color:#695D5A;margin:0 0 25px}}
.meta{{border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);padding:14px 0;font:550 12px/1.7 var(--sans);color:#706562}}
.meta span{{padding:0 8px;color:#A99B98}}
.mainpoint{{margin:30px 0;background:#F1E7E3;border-left:3px solid var(--accent);padding:20px 25px}}
.mainpoint b{{font:800 10px var(--sans);letter-spacing:.13em;color:var(--accent)}}
.mainpoint p{{font:400 21px/1.48 var(--serif);margin:9px 0 0}}
.article-body{{max-width:710px;font:400 20px/1.68 var(--serif)}}
.article-body h2{{font:500 31px/1.22 var(--serif);letter-spacing:-.5px;margin:42px 0 15px}}
.article-body p{{margin:0 0 23px}}
.source{{border-top:2px solid #45383B;margin-top:45px;padding:20px 0;font:14px/1.7 var(--sans);overflow-wrap:anywhere}}
.source h2{{font:500 26px var(--serif);margin:0 0 12px}}
.disclosure{{font:12px/1.7 var(--sans);color:#6F6462;max-width:670px}}
footer{{background:#30282A;color:#F7F0ED;padding:25px 30px;text-align:center;font:12px var(--sans)}}
footer a{{color:#F7F0ED}}
@media(max-width:520px){{
.masthead-inner{{padding:23px 18px 19px;display:block}}
.brand{{font-size:41px}}.tagline{{font-size:9px;margin-top:9px}}
.navinner{{padding:14px 18px}}
.reader{{padding:30px 18px 60px}}
h1{{font-size:clamp(37px,10vw,48px);letter-spacing:-1px;margin:16px 0}}
.intro{{font-size:20px;line-height:1.45}}
.article-body{{font-size:19px;line-height:1.7}}
.article-body h2{{font-size:28px}}
.mainpoint{{padding:17px 19px}}
}}
</style></head><body>
<div class="utility">THE UK FINANCIAL SERVICES DESK</div>
<header class="masthead"><div class="masthead-inner">
<a class="brand" href="../index.html">THE BRIEF<span>.</span></a>
<span class="tagline">FINANCIAL NEWS, UNDERSTOOD<br> BANKING · INSURANCE · REGULATION</span>
</div></header>
<nav class="navstrip"><div class="navinner"><a href="../index.html">← Latest stories</a><a href="../about.html">About &amp; corrections</a></div></nav>
<main class="reader">
<div class="kicker">{esc(a.get("category",""))} / THE BRIEF ORIGINAL</div>
<h1>{headline}</h1>
<p class="intro">{description}</p>
<div class="meta">News: {esc(news_date)} <span>·</span> Published: {esc(release_date)} <span>·</span> {esc(a.get("source",""))}</div>
<div class="article-body">{body}</div>
<div class="source"><h2>Original evidence</h2>
<p>This report is based on the named primary document. <a href="{esc(a["url"])}" target="_blank" rel="noopener noreferrer">{esc(a.get("source","Primary source"))} — read the original announcement ↗</a></p></div>
<p class="disclosure">This article was generated and screened by an automated newsroom using a primary source. It has not been independently reviewed by a human editor. <a href="../about.html">Read our editorial and corrections policy.</a> Not financial advice.</p>
</main>
<footer><a href="../index.html">THE BRIEF.</a> · UK financial news, understood.</footer>
</body></html>
"""


def build():
    archive = valid_articles()
    records = [a for a in archive if published_same_day(a)]
    today = clock().date().strftime("%-d %B %Y")
    # Empty is the correct edition when no verified original development was
    # announced AND published on this same UK date. Never replay old news.
    page = (ROOT / "index.html").read_text(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "data").mkdir(exist_ok=True)
    (OUT / "story").mkdir(exist_ok=True)

    latest = records[0] if records else None
    first = latest
    # The repository retains a source-mode backup for broken JavaScript.
    # The published build already contains real, readable lead/feed HTML,
    # so NEVER copy the duplicate emergency article-list box into Pages.
    fallback = re.compile(r"\s*<!-- THEBRIEF_STATIC_START -->.*?<!-- THEBRIEF_STATIC_END -->", re.S)
    page, removed = fallback.subn("", page, count=1)
    if removed != 1 or "THEBRIEF_STATIC_START" in page or 'id="static-edition"' in page:
        raise ValueError("Could not remove duplicate repository-only safety section")
    if first:
        lead = ('<article id="lead-story" class="lead-story"><span class="story-kicker">'
            + esc(first.get("category")) + ' / THE LEAD STORY</span><h1><a href="'
            + esc(story_href(first)) + '">' + esc(first["title"])
            + '</a></h1><p class="standfirst">' + esc(first.get("short")) + '</p>'
            + '<p class="meta">Original news: ' + esc(first.get("dateISO"))
            + ' · The Brief published: ' + esc(first.get("published_at", "")[:10]) + '</p>'
            + '<p><a class="cta" href="' + esc(story_href(first)) + '">Read the full article ↗</a></p></article>')
    else:
        lead = ('<article id="lead-story" class="lead-story"><span class="story-kicker">THE BRIEF / '+
            esc(today)+'</span><h1>No verified news from today yet.</h1>'
            '<p class="standfirst">We have not confirmed a new first-party financial-services announcement '
            'dated today in the UK. We will not fill today’s edition with yesterday’s news.</p></article>')
    page = insert_once(page, '<article id="lead-story" class="lead-story"></article>', lead)
    briefing = ''.join(
        '<div class="briefing-story"><span class="brief-number">0' + str(i+1)
        + '</span><div><span class="story-kind">FULL ARTICLE</span>'
        + '<a href="' + esc(story_href(a)) + '">' + esc(a["title"]) + '</a>'
        + '<p>' + esc(a.get("short", "")[:190]) + '</p></div></div>'
        for i, a in enumerate(records[1:3])
    )
    if not briefing:
        briefing = '<p>No verified same-day stories to brief yet.</p>'
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
        '<div class="feed" id="feed">' + ('\n'.join(rows) if rows else '<p class="nothing">No approved first-party reports dated '+esc(today)+' have been published yet.</p>') + '</div>')
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
    if records and not all(x["title"].replace("&", "&amp;") in built for x in records[:5]):
        # Some headlines contain punctuation encoded as entities; check rendered text.
        for a in records[:5]:
            if esc(a["title"]) not in built:
                raise ValueError("Missing pre-rendered headline: " + a["id"])
    if built.count('id="embedded-articles"') != 1:
        raise ValueError("Inline fallback missing")
    if 'id="static-edition"' in built or 'id="latest-published-highlight"' in built:
        raise ValueError("Temporary duplicate headline blocks leaked into public design")
    for a in records:
        if not (OUT / story_href(a)).is_file():
            raise ValueError("Missing public standalone article: " + a["id"])
    print("PUBLIC_BUILD_OK: " + json.dumps({"articles_today": len(records),
        "historical_records_excluded":len(archive)-len(records),
        "latest": latest["id"] if latest else None, "standalone_pages": len(records),
        "pre_rendered_feed": True, "inline_fallback": True}, sort_keys=True))


if __name__ == "__main__":
    build()
