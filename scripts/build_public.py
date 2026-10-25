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
from same_day_policy import published_same_day, clock, original_date, date_in_uk
import shutil
import datetime as dt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public"


def esc(value):
    return html.escape("" if value is None else str(value), quote=True)


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
                and len(a["blocks"]) >= 2):
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
    news_date = original_date(a).strftime("%-d %B %Y")
    release_date = date_in_uk(a["published_at"]).strftime("%-d %B %Y")
    archived = original_date(a) != clock().date()
    archive_notice = ('<p class="disclosure"><strong>ARCHIVE · Earlier edition.</strong> This is historical reporting, not today’s news.</p>' if archived else "")
    if not a.get("date_evidence"):
        archive_notice += '<p class="disclosure">Legacy report: source dating and claims were screened by the earlier system and have not been revalidated under the current controls. Dates below are retained as originally recorded.</p>'
    if a.get('retrospective_launch'):
        archive_notice += '<p class="disclosure"><strong>Saturday launch edition · 24 October 2026.</strong> This report was prepared retrospectively from an announcement issued after 6am UK on Saturday. The publication timestamp below records when The Brief actually published it.</p>'
    media=a.get("status")=="Original reporting"
    source_caption="Original reporting" if media else "Original announcement"
    source_description=("This report summarises attributed journalism from the named publisher. The Brief did not independently verify every corporate claim." if media else "This report is based on the named primary document.")
    source_link_text="read the original report" if media else "read the original announcement"
    publication_stamp=dt.datetime.fromisoformat(a['published_at'].replace('Z','+00:00')).astimezone(__import__('zoneinfo').ZoneInfo('Europe/London')).strftime('%-d %B %Y, %H:%M %Z')
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
.brand{{font-size:41px}}.tagline{{display:block;font-size:9px;margin-top:9px}}
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
<nav class="navstrip"><div class="navinner"><a href="../index.html">← Today</a><a href="../archive.html">Archive</a><a href="../about.html">About &amp; corrections</a></div></nav>
<main class="reader"><article>
{archive_notice}
<div class="kicker">{esc(a.get("category",""))} / THE BRIEF ORIGINAL</div>
<h1>{headline}</h1>
<p class="intro">{description}</p>
<div class="meta">{source_caption}: <time datetime="{esc(a["dateISO"])}">{esc(news_date)}</time> <span>·</span> Published: <time datetime="{esc(a["published_at"])}">{esc(publication_stamp)}</time> <span>·</span> {esc(a.get("source",""))}</div>
<div class="article-body">{body}</div>
<div class="source"><h2>Original evidence</h2>
<p>{source_description} <a href="{esc(a["url"])}" target="_blank" rel="noopener noreferrer">{esc(a.get("source","Primary source"))} — {source_link_text} ↗</a></p></div>
<p class="disclosure">This article was generated and screened by an automated newsroom using the linked original source. It has not been independently reviewed by a human editor. <a href="../about.html">Read our editorial and corrections policy.</a> Not financial advice.</p>
</article></main>
<footer><a href="../index.html">THE BRIEF.</a> · UK financial news, understood.</footer>
</body></html>
"""


def archive_page(records,edition=None):
    prefix='../' if edition else ''
    title=('Edition · '+edition) if edition else 'The archive.'
    rows=[]
    for day in sorted({original_date(a).isoformat() for a in records},reverse=True):
        cards=[]
        for a in records:
            if original_date(a).isoformat()!=day:continue
            cards.append('<article data-category="'+esc(a['category'])+'"><span class="kicker">'+esc(a['category'])+'</span><h2><a href="'+prefix+story_href(a)+'">'+esc(a['title'])+'</a></h2><p>'+esc(a['short'])+'</p><small>Original announcement: '+esc(day)+' · Published by The Brief: '+esc(date_in_uk(a['published_at']))+' · '+esc(a['source'])+'</small></article>')
        rows.append('<section><h2 class="edition"><a href="'+prefix+'edition/'+day+'.html">'+esc(day)+' edition ↗</a></h2>'+''.join(cards)+'</section>')
    body='<p class="intro">Earlier developments, kept in their dated editions. Nothing here is presented as today’s news.</p>'
    if any(a.get('retrospective_launch') for a in records):
        body+='<p class="note"><strong>Saturday launch edition · 24 October 2026, from 6am UK.</strong> These launch reports were prepared retrospectively. Each article shows the original announcement date and its actual publication timestamp.</p>'
    body+='<p class="note">Reports from the earlier publishing system are retained with their recorded dates and a legacy verification notice. They have not been re-certified under the new controls.</p>'
    body+='<label for="archive-search">Search the archive</label><input id="archive-search" type="search" placeholder="Company, subject or keyword"><label for="archive-category">Subject</label><select id="archive-category"><option>Everything</option>'+''.join('<option>'+x+'</option>' for x in ['Banking','Insurance','Brokers','Pensions','Regulation','Technology'])+'</select><p id="archive-count" role="status">'+str(len(records))+' reports</p>'
    body+=''.join(rows) or '<p>No earlier editions yet.</p>'
    script="""<script>
const q=document.querySelector('#archive-search'),c=document.querySelector('#archive-category');
function filter(){let n=0;document.querySelectorAll('article[data-category]').forEach(a=>{a.hidden=!(a.textContent.toLowerCase().includes(q.value.toLowerCase())&&(c.value==='Everything'||a.dataset.category===c.value));if(!a.hidden)n++});document.querySelectorAll('section').forEach(s=>s.hidden=![...s.querySelectorAll('article')].some(a=>!a.hidden));document.querySelector('#archive-count').textContent=n+' reports'}q.oninput=filter;c.onchange=filter;
</script>"""
    return utility_page(title,body,prefix)+script


def utility_page(title,body,prefix=''):
    return '<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+' — The Brief</title><style>'+"""
:root{--paper:#F8F5EF;--ink:#272323;--accent:#87404B;--rule:#DED8D0}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.65 Arial,sans-serif}a{color:inherit;text-underline-offset:4px;text-decoration-color:var(--accent)}header{border-bottom:1px solid var(--rule);padding:25px max(20px,calc((100% - 1100px)/2));background:#fff}header a{font:bold 40px Georgia,serif;text-decoration:none;white-space:nowrap}nav{display:flex;gap:24px;flex-wrap:wrap;margin-top:18px}nav a{font:600 13px Arial,sans-serif}main{max-width:900px;margin:auto;padding:50px 24px 90px}h1{font:normal clamp(42px,8vw,68px)/1.1 Georgia,serif;letter-spacing:-1.7px}h2{font:normal 28px/1.25 Georgia,serif}article{padding:24px 0;border-bottom:1px solid var(--rule)}article p{color:#665b59}.kicker,label{font:bold 11px Arial,sans-serif;letter-spacing:.1em;color:var(--accent)}small{font-size:12px;color:#6b5f5c}.intro{font:23px/1.5 Georgia,serif}.note{border-left:3px solid var(--accent);padding:12px 18px;background:#F0E7E3;font-size:13px}.edition{border-bottom:2px solid var(--ink);margin-top:40px;padding-bottom:12px}.edition a{font:600 14px Arial,sans-serif}label{display:block;margin:18px 0 6px}input,select{font:16px Arial,sans-serif;width:100%;padding:12px;border:1px solid #bcaeaa;background:#fff;color:var(--ink)}input:focus-visible,a:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:4px}[hidden]{display:none!important}table{width:100%;border-collapse:collapse}td,th{padding:12px;text-align:left;border-bottom:1px solid var(--rule);overflow-wrap:anywhere}footer{background:#30282A;color:#fff;padding:30px;text-align:center;font-size:12px}@media(max-width:520px){main{padding:28px 18px 60px}h1{font-size:43px}h2{font-size:25px}}
"""+'</style></head><body><header><a href="'+prefix+'index.html">THE BRIEF<span style="color:#87404B">.</span></a><nav aria-label="Primary"><a href="'+prefix+'index.html">Today</a><a href="'+prefix+'archive.html">Archive</a><a href="'+prefix+'about.html">About</a><a href="'+prefix+'status.html">Newsroom status</a></nav></header><main><h1>'+esc(title)+'</h1>'+body+'</main><footer>THE BRIEF. · Financial news, understood.</footer></body></html>'


def status_page():
    path=ROOT/'data/status.json'
    state=json.loads(path.read_text()) if path.exists() else {'outcome':'UNVERIFIED','checked_at':'No production run recorded'}
    fields=[('Editorial outcome',state.get('editorial_outcome',state.get('outcome'))),('This artifact',state.get('technical_status','See workflow result')),('Publisher links',state.get('publisher_links',0)),('Articles held',state.get('articles_held',0)),('Last check (UTC)',state.get('checked_at')),('UK edition date',state.get('uk_date')),('Newsroom outcome',state.get('outcome')),('New articles this run',state.get('published_this_run',0)),('Articles today',state.get('genuine_same_day_articles',0)),('Primary indexes checked',state.get('primary_indexes_checked',0)),('Primary index failures',state.get('primary_index_failures',0)),('RSS feeds working',state.get('feeds_working',0)),('RSS feed failures',state.get('feed_failures',0)),('Production requests / daily cap',str(state.get('ai_budget',{}).get('production_requests_today',state.get('ai_budget',{}).get('requests_today_including_this_run','unknown')))+' / '+str(state.get('ai_budget',{}).get('daily_limit','unknown'))),('One-time diagnostic requests / cap',str(state.get('launch_diagnostic_allowance',{}).get('requests',0))+' / 2'),('Source candidates found',state.get('fresh_source_candidates',0)),('Unpublished real-model test',state.get('launch_test',{}).get('result','NOT_RUN'))]
    rows=''.join('<tr><th>'+esc(k)+'</th><td>'+esc(v)+'</td></tr>' for k,v in fields)
    selection=state.get('editorial_selection',{})
    rows+='<tr><th>Gemini editorial selection</th><td>'+esc(selection.get('result','NOT_RECORDED'))+'</td></tr>'
    rows+='<tr><th>Saturday launch edition</th><td>'+esc(state.get('launch_edition',{}).get('result','NOT_RUN'))+'</td></tr>'
    body='<p class="intro">Publication and technical checks are different measures. An empty edition is never counted as successful news publication.</p><table>'+rows+'</table><p class="note">This status describes the recorded run, not a guarantee of continuing service. GitHub schedules can be delayed. If the last check is over three hours old, monitoring is stale.</p><p><a href="https://github.com/yogeshkaransharma-code/the-brief-financial-news/actions">Inspect live workflow results and diagnostic artifacts ↗</a></p>'
    if state.get('discovery_errors'):
        body+='<h2>Source access issues</h2><ul>'
        for error in state['discovery_errors']:
            label=(error.get('source','Source')+': '+error.get('error','Unavailable')) if isinstance(error,dict) else str(error)
            body+='<li>'+esc(label)+'</li>'
        body+='</ul>'
    acceptance=state.get('launch_acceptance',{})
    if acceptance:
        body+='<h2>Launch evidence: '+esc(acceptance.get('result'))+'</h2><p>'+esc(', '.join(acceptance.get('pending',[])).replace('_',' '))+'</p>'
    history=state.get('previous_verified_runs',[])
    if history:
        body+='<h2>Verified run history</h2><table><tr><th>Checked</th><th>Trigger</th><th>Technical result</th><th>Editorial result</th><th>Articles / links</th></tr>'
        for r in reversed(history):
            body+='<tr><td><a href="'+esc(r.get('run_url'))+'">'+esc(r.get('checked_at'))+'</a></td><td>'+esc(r.get('event'))+'</td><td>'+esc(r.get('technical_status'))+'</td><td>'+esc(r.get('editorial_outcome'))+'</td><td>'+esc(r.get('published_this_run',0))+' / '+esc(r.get('publisher_links',0))+'</td></tr>'
        body+='</table>'
    body+='<p>The current artifact is built before deployment checks. The linked workflow and verified history record the subsequent live result.</p>'
    return utility_page('Inside the newsroom.',body)


def publisher_panel():
    path=ROOT/'data/headlines.json'
    desk=json.loads(path.read_text()) if path.exists() else {}
    from same_day_policy import source_issued_today
    links=[x for x in desk.get('items',[]) if source_issued_today(x)]
    rows=''.join('<article data-desk-category="'+esc(x['category'])+'" style="padding:16px 0;border-bottom:1px solid var(--rule)"><div class="news-cat">SOURCE-LINKED HEADLINE · '+esc(x['category'])+'</div><h3 style="font:500 25px/1.25 Georgia,serif;margin:8px 0"><a href="'+esc(x['url'])+'" rel="noopener noreferrer" target="_blank">'+esc(x['title'])+' ↗</a></h3><p class="meta">'+esc(x['source'])+' · Publisher feed date: '+esc(x['dateISO'])+'</p></article>' for x in links)
    return '<section id="publisher-desk" aria-label="Source-linked headlines" style="border-top:2px solid var(--ink);margin:26px 0;padding:24px 0"><span class="section-kicker">THE WIDER NEWS DESK</span><h2 style="font:400 36px Georgia,serif;margin:8px 0">Source-linked headlines</h2><p>Reports at other publishers. These links supplement The Brief’s original articles above. Feed dates have not been independently verified against every article.</p><p class="meta">Desk checked: '+esc(desk.get('checked_at','Not recorded'))+' · <a href="sources.html">Explore our sources</a></p><label for="desk-subject">Subject </label><select id="desk-subject"><option>Everything</option>'+''.join('<option>'+x+'</option>' for x in sorted({x['category'] for x in links}))+'</select><div>'+ (rows or '<p>No qualifying publisher headlines dated today in the latest discovery run.</p>')+'</div><script>document.querySelector("#desk-subject").onchange=function(){document.querySelectorAll("[data-desk-category]").forEach(x=>x.hidden=this.value!=="Everything"&&x.dataset.deskCategory!==this.value)}</script></section>'


def sources_page():
    from source_catalog import catalog
    data=catalog(ROOT)
    body='<p class="intro">Search the configured discovery routes. Recognition of a publisher is not proof that its website was successfully read. Blocked sources remain coverage warnings while other routes continue.</p><label for="source-search">Find a publisher, sector or discovery route</label><input id="source-search" type="search" placeholder="Insurance, regulator, RSS…"><div>'
    for x in data['sources']:
        body+='<article data-source-row><h2><a href="'+esc(x['url'])+'">'+esc(x['name'])+'</a></h2><p>'+esc(x['category'])+' · '+esc(x['method'])+' · '+esc(x['observed'])+'</p></article>'
    body+='</div><script>document.querySelector("#source-search").oninput=function(){document.querySelectorAll("[data-source-row]").forEach(x=>x.hidden=!x.textContent.toLowerCase().includes(this.value.toLowerCase()))}</script>'
    (OUT/'data/sources.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    return utility_page('Our source registry.',body)


def build():
    archive = valid_articles()
    records = [a for a in archive if published_same_day(a)]
    today = clock().date().strftime("%-d %B %Y")
    # Empty is the correct edition when no verified original development was
    # announced AND published on this same UK date. Never replay old news.
    page = (ROOT / "index.html").read_text(encoding="utf-8")
    if OUT.exists():shutil.rmtree(OUT)
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
            '<p class="standfirst">We have not approved an original financial-services article based on evidence '
            'dated today in the UK. <a href="archive.html">Read earlier editions in the archive →</a></p></article>')
    page = insert_once(page, '<article id="lead-story" class="lead-story"></article>', lead)
    briefing = ''.join(
        '<div class="briefing-story"><span class="brief-number">0' + str(i+1)
        + '</span><div><span class="story-kind">FULL ARTICLE</span>'
        + '<a href="' + esc(story_href(a)) + '">' + esc(a["title"]) + '</a>'
        + '<p>' + esc(a.get("short", "")[:190]) + '</p></div></div>'
        for i, a in enumerate(records[:3])
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
        '<div class="feed" id="feed">' + ('\n'.join(rows) if rows else '<p class="nothing">No approved original reports dated '+esc(today)+' have been published yet.</p>') + '</div>')
    page = insert_once(page, '<div class="news-count" id="news-count"></div>',
        '<div class="news-count" id="news-count">' + str(len(records)) + ' articles</div>')
    payload = json.dumps(records, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    page = insert_once(page, '<script type="application/json" id="curated-data">[]</script>',
        '<script type="application/json" id="curated-data">[]</script>\n'
        '<script type="application/json" id="embedded-articles">' + payload + '</script>')
    page=insert_once(page,'<section id="context" class="understand"',publisher_panel()+'<section id="context" class="understand"')
    (OUT / "index.html").write_text(page, encoding="utf-8")
    (OUT/'sources.html').write_text(sources_page(),encoding='utf-8')
    headline_path=ROOT/'data/headlines.json'
    if headline_path.exists():shutil.copy2(headline_path,OUT/'data/headlines.json')
    import os,subprocess
    source_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    (OUT/'data/build.json').write_text(json.dumps({'run_id':os.getenv('GITHUB_RUN_ID','local'),'source_sha':source_sha,'built_at':dt.datetime.now(dt.timezone.utc).isoformat()})+'\n')
    (OUT / "about.html").write_text((ROOT / "about.html").read_text(encoding="utf-8"), encoding="utf-8")
    (OUT / "data/articles.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "data/archive.json").write_text(json.dumps(archive,ensure_ascii=False,indent=2)+"\n")
    (OUT / "archive.html").write_text(archive_page(archive),encoding="utf-8")
    (OUT / "edition").mkdir(exist_ok=True)
    for day in sorted({original_date(a).isoformat() for a in archive}):
        selected=[a for a in archive if original_date(a).isoformat()==day]
        (OUT / "edition" / (day+".html")).write_text(archive_page(selected,day),encoding="utf-8")
    status_path=ROOT/"data/status.json"
    if status_path.exists():shutil.copy2(status_path,OUT/"data/status.json")
    (OUT/"status.html").write_text(status_page(),encoding="utf-8")
    for a in archive:
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
        "archived_records":len(archive)-len(records),
        "latest": latest["id"] if latest else None, "standalone_pages": len(archive),
        "pre_rendered_feed": True, "inline_fallback": True}, sort_keys=True))


if __name__ == "__main__":
    build()


