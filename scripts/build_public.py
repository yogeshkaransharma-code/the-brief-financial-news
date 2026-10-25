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
from site_design import desk_for, terms_for, header, footer as site_footer, visual
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
    return sorted([dict(a, desk_section=desk_for(a), display_glossary=(a.get("glossary") or terms_for(a))) for a in records], key=lambda a: (a.get("published_at", ""), a.get("dateISO", ""), a["id"]), reverse=True)


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
    """A complete, source-linked reading page under the shared burgundy masthead."""
    section=a.get("desk_section") or desk_for(a)
    news_date=original_date(a).strftime("%-d %B %Y")
    publication_stamp=dt.datetime.fromisoformat(a['published_at'].replace('Z','+00:00')).astimezone(__import__('zoneinfo').ZoneInfo('Europe/London')).strftime('%-d %B %Y, %H:%M %Z')
    archived=original_date(a)!=clock().date()
    note=('<p class="archive-note"><strong>ARCHIVE · Earlier edition.</strong> This is earlier reporting, not today’s news.</p>' if archived else '')
    if not a.get("date_evidence"):
        note+='<p class="archive-note">Legacy report: the source date and claims have not been revalidated under the current controls.</p>'
    if a.get("retrospective_launch"):
        note+='<p class="archive-note">Saturday launch edition prepared retrospectively; the recorded publication time is accurate.</p>'
    is_media=a.get("status")=="Original reporting"
    source_description=("This article summarises attributed journalism by the named publisher. The Brief has not independently verified every underlying claim." if is_media
        else "This article is based on the original announcement or document below.")
    terms=a.get("display_glossary") or terms_for(a)
    definitions=(''.join('<dt>'+esc(t)+'</dt><dd>'+esc(d)+'</dd>' for t,d in terms))
    glossary_html=('<section class="tb-glossary"><h2>Jargon, explained.</h2><dl>'+definitions+'</dl></section>' if definitions else '')
    return f"""<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#332B2E"><meta name="description" content="{esc(a.get('short',''))}">
<title>{esc(a['title'])} — The Brief</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&amp;family=Newsreader:wght@400;500;600;700&amp;display=swap" rel="stylesheet">
<link rel="stylesheet" href="../assets/site.css">
<style>
.reader{{width:min(100%,840px);margin:auto;padding:44px 28px 95px}}
.reader .kicker{{font:800 11px var(--sans);letter-spacing:.14em;color:#87404B;text-transform:uppercase}}
.reader h1{{font:500 clamp(38px,5.1vw,62px)/1.08 var(--display);letter-spacing:-1.45px;margin:18px 0 20px}}
.reader .intro{{font:400 clamp(19px,2.1vw,24px)/1.46 var(--display);color:#655956;margin:0 0 23px}}
.reader .meta{{padding:13px 0;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);font:12px/1.7 var(--sans);color:#766a65}}
.reader .article-body{{font:400 20px/1.72 var(--display);max-width:735px}}
.reader .article-body h2{{font:500 31px/1.23 var(--display);letter-spacing:-.5px;margin:35px 0 12px}}
.reader .article-body p{{margin:0 0 23px}}
.reader .archive-note{{font:13px/1.65 var(--sans);background:#f1e7e3;color:#654d52;border-left:3px solid #87404B;padding:12px 17px}}
.reader .disclosure{{font:12px/1.7 var(--sans);color:#766966;margin-top:23px}}
.reader a{{text-underline-offset:4px;text-decoration-color:#b48a91}}
@media(max-width:600px){{.reader{{padding:30px 19px 70px}}.reader .article-body{{font-size:19px}}.reader .article-body h2{{font-size:26px}}}}
</style></head>
<body class="tb-reading-page">{header("../")}
<main class="reader"><article>{note}<div class="kicker">{esc(section)} / THE BRIEF REPORT</div>
<h1>{esc(a['title'])}</h1><p class="intro">{esc(a.get('short',''))}</p>
<div class="meta">Original source date: <time datetime="{esc(a['dateISO'])}">{esc(news_date)}</time> · Published by The Brief: <time datetime="{esc(a['published_at'])}">{esc(publication_stamp)}</time> · {esc(a.get('source',''))}</div>
{visual(section)}
<div class="article-body">{article_body(a)}</div>
{glossary_html}
<div class="source tb-source-evidence"><h2>Original source</h2>
<p>{esc(source_description)} This photograph is contextual imagery, not evidence of the reported event.</p>
<a href="{esc(a['url'])}" target="_blank" rel="noopener noreferrer">{esc(a.get('source','Original publisher'))} — read the original source ↗</a></div>
<p class="disclosure">Prepared and machine-screened by an automated newsroom; no human editorial review is claimed. <a href="../about.html">Our standards and corrections policy</a>. Not financial advice.</p>
</article></main>{site_footer("../")}</body></html>"""


def archive_page(records,edition=None):
    prefix='../' if edition else ''
    title=('Edition · '+edition) if edition else 'The archive.'
    rows=[]
    for day in sorted({original_date(a).isoformat() for a in records},reverse=True):
        cards=[]
        for a in records:
            if original_date(a).isoformat()!=day:continue
            cards.append('<article data-category="'+esc(a['desk_section'])+'"><span class="kicker">'+esc(a['desk_section'])+'</span><h2><a href="'+prefix+story_href(a)+'">'+esc(a['title'])+'</a></h2><p>'+esc(a['short'])+'</p><small>Original announcement: '+esc(day)+' · Published by The Brief: '+esc(date_in_uk(a['published_at']))+' · '+esc(a['source'])+'</small></article>')
        rows.append('<section><h2 class="edition"><a href="'+prefix+'edition/'+day+'.html">'+esc(day)+' edition ↗</a></h2>'+''.join(cards)+'</section>')
    body='<p class="intro">Earlier developments, kept in their dated editions. Nothing here is presented as today’s news.</p>'
    if any(a.get('retrospective_launch') for a in records):
        body+='<p class="note"><strong>Saturday launch edition · 24 October 2026, from 6am UK.</strong> These launch reports were prepared retrospectively. Each article shows the original announcement date and its actual publication timestamp.</p>'
    body+='<p class="note">Reports from the earlier publishing system are retained with their recorded dates and a legacy verification notice. They have not been re-certified under the new controls.</p>'
    body+='<label for="archive-search">Search the archive</label><input id="archive-search" type="search" placeholder="Company, subject or keyword"><label for="archive-category">Subject</label><select id="archive-category"><option>Everything</option>'+''.join('<option>'+x+'</option>' for x in ['Insurance','Banking'])+'</select><p id="archive-count" role="status">'+str(len(records))+' reports</p>'
    body+=''.join(rows) or '<p>No earlier editions yet.</p>'
    script="""<script>
const q=document.querySelector('#archive-search'),c=document.querySelector('#archive-category');
function filter(){let n=0;document.querySelectorAll('article[data-category]').forEach(a=>{a.hidden=!(a.textContent.toLowerCase().includes(q.value.toLowerCase())&&(c.value==='Everything'||a.dataset.category===c.value));if(!a.hidden)n++});document.querySelectorAll('section').forEach(s=>s.hidden=![...s.querySelectorAll('article')].some(a=>!a.hidden));document.querySelector('#archive-count').textContent=n+' reports'}q.oninput=filter;c.onchange=filter;
const requested=new URLSearchParams(location.search).get('category');
if(requested&&[...c.options].some(o=>o.value===requested)){c.value=requested;filter()}
</script>"""
    page=utility_page(title,body,prefix)
    if page.count('</body>')!=1:
        raise ValueError('Archive layout missing closing body')
    return page.replace('</body>',script+'</body>')


def utility_page(title,body,prefix=''):
    """Single editorial layout for archive, dated editions and source information."""
    return ('<!doctype html><html lang="en-GB"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="theme-color" content="#332B2E"><title>'+esc(title)+' — The Brief</title>'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;family=Newsreader:wght@400;500;600;700&amp;display=swap" rel="stylesheet">'
        '<link rel="stylesheet" href="'+prefix+'assets/site.css"></head><body class="tb-utility-page">'
        +header(prefix)+'<main class="tb-page"><span class="kicker">INSURANCE &amp; BANKING / THE BRIEF</span><h1>'+esc(title)+'</h1>'+body+'</main>'
        +site_footer(prefix)+'</body></html>')


def status_page():
    path=ROOT/'data/status.json'
    state=json.loads(path.read_text()) if path.exists() else {'outcome':'UNVERIFIED','checked_at':'No production run recorded'}
    fields=[('Editorial outcome',state.get('editorial_outcome',state.get('outcome'))),('This artifact',state.get('technical_status','See workflow result')),('Internal discovery leads',state.get('discovery_headlines',0)),('Articles held',state.get('articles_held',0)),('Last check (UTC)',state.get('checked_at')),('UK edition date',state.get('uk_date')),('Newsroom outcome',state.get('outcome')),('New articles this run',state.get('published_this_run',0)),('Articles today',state.get('genuine_same_day_articles',0)),('Primary indexes checked',state.get('primary_indexes_checked',0)),('Primary index failures',state.get('primary_index_failures',0)),('RSS feeds working',state.get('feeds_working',0)),('RSS feed failures',state.get('feed_failures',0)),('Production requests / daily cap',str(state.get('ai_budget',{}).get('production_requests_today',state.get('ai_budget',{}).get('requests_today_including_this_run','unknown')))+' / '+str(state.get('ai_budget',{}).get('daily_limit','unknown'))),('One-time diagnostic requests / cap',str(state.get('launch_diagnostic_allowance',{}).get('requests',0))+' / 2'),('Source candidates found',state.get('fresh_source_candidates',0)),('Unpublished real-model test',state.get('launch_test',{}).get('result','NOT_RUN'))]
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
        body+='<h2>Verified run history</h2><table><tr><th>Checked</th><th>Trigger</th><th>Technical result</th><th>Editorial result</th><th>Articles</th></tr>'
        for r in reversed(history):
            body+='<tr><td><a href="'+esc(r.get('run_url'))+'">'+esc(r.get('checked_at'))+'</a></td><td>'+esc(r.get('event'))+'</td><td>'+esc(r.get('technical_status'))+'</td><td>'+esc(r.get('editorial_outcome'))+'</td><td>'+esc(r.get('published_this_run',0))+'</td></tr>'
        body+='</table>'
    body+='<p>The current artifact is built before deployment checks. The linked workflow and verified history record the subsequent live result.</p>'
    return utility_page('Inside the newsroom.',body)


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
    (OUT / "assets").mkdir(exist_ok=True)
    shutil.copy2(ROOT/"assets/site.css",OUT/"assets/site.css")

    page = insert_once(page,"<!-- HOURLY_DESK_INSERT -->","")
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
            + esc(first.get("desk_section")) + ' / THE LEAD STORY</span><h1><a href="'
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
            + '</div><div><div class="news-cat">' + esc(a.get("desk_section")) + ' · OUR REPORT</div>'
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
    (OUT / "index.html").write_text(page, encoding="utf-8")
    (OUT/'sources.html').write_text(sources_page(),encoding='utf-8')
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


