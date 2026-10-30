#!/usr/bin/env python3
"""Publish readable HTML directly, with JavaScript as an enhancement only.

Run after provenance and editorial audit validation. Public Pages contains only
approved original articles, not the private RSS discovery feed or held drafts.
"""
from __future__ import annotations
import html
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import quote
from same_day_policy import published_same_day, clock, original_date, date_in_uk
from site_design import desk_for, terms_for, header, footer as site_footer, visual, home_photo_for, CITY_PHOTO, CITY_CREDIT, CITY_CREDIT_URL, ST_PAULS_PHOTO, CITY_PHOTO, BANK_PHOTO, WESTMINSTER_PHOTO
from reader_experience import lead_article, other_briefs
from reader_analytics import install as install_analytics, token_from_env
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
                and len(a["blocks"]) >= (1 if a.get('independent_review') is False else 2)):
            raise ValueError("Unapproved or incomplete article in public build")
    # Preserve the full signed article ledger internally; never expose
    # unrelated overseas news on today's page, desks, archives or story URLs.
    from uk_market_scope import public_article_in_scope
    scoped=[a for a in records if public_article_in_scope(a)]
    note_path=ROOT/"data/editorial-context.json"
    notes=json.loads(note_path.read_text(encoding="utf-8")).get("notes",{}) if note_path.exists() else {}
    if not isinstance(notes,dict) or set(notes)-{a["id"] for a in records}:
        raise ValueError("Invalid public editorial context")
    enriched=[]
    for a in scoped:
        note=notes.get(a["id"],a.get("reader_takeaway",""))
        if not isinstance(note,str) or len(note.split())>85:
            raise ValueError("Invalid context note")
        enriched.append(dict(a,desk_section=desk_for(a),display_glossary=a.get("glossary") or terms_for(a),
                             reader_takeaway=note,public_href=story_href(a),publication="The Financial Edition"))
    return sorted(enriched,key=lambda a:(a.get("published_at",""),a.get("dateISO",""),a["id"]),reverse=True)


def story_href(a):
    text=unicodedata.normalize("NFKD",a["title"]).encode("ascii","ignore").decode().lower()
    slug=re.sub(r"[^a-z0-9]+","-",text).strip("-")[:72].rstrip("-") or "report"
    return "story/" + slug + "-" + a["id"][3:9] + ".html"


def legacy_story_href(a):
    return "story/" + a["id"] + ".html"


def legacy_redirect(a):
    target=esc(story_href(a).split("/",1)[1])
    return ('<!doctype html><html lang="en-GB"><head><meta charset="utf-8">'
            '<meta name="robots" content="noindex"><meta http-equiv="refresh" content="0; url='+target+'">'
            '<title>Article moved — The Financial Edition</title></head><body><a href="'+target+'">Read the article</a></body></html>')


def article_body(a):
    out = []
    for section_number, (heading, paragraph) in enumerate(a["blocks"], start=1):
        out.append('<h2 id="report-section-' + str(section_number) + '">' + esc(heading) + "</h2>")
        for part in re.split(r"\n\s*\n", str(paragraph)):
            if part.strip():
                out.append("<p>" + esc(part.strip()) + "</p>")
    return "\n".join(out)


def standalone_story(a,related=None):
    """Magazine-style sourced article. Sector colour never replaces the shared brand."""
    section=a.get('desk_section') or desk_for(a)
    desk=section.lower()
    news_date=original_date(a).strftime('%-d %B %Y')
    published_local=dt.datetime.fromisoformat(a['published_at'].replace('Z','+00:00')).astimezone(__import__('zoneinfo').ZoneInfo('Europe/London'))
    publication_stamp=published_local.strftime('%-d %B %Y, %H:%M %Z')
    byline_date=(esc(news_date)+' · '+esc(published_local.strftime('%H:%M %Z')) if original_date(a)==published_local.date()
                 else 'Source: '+esc(news_date)+' · The Financial Edition: '+esc(publication_stamp))
    archived=original_date(a)!=clock().date()
    note=('<p class="archive-note"><strong>ARCHIVE · Earlier edition.</strong> This is earlier reporting, not today’s news.</p>' if archived else '')
    if not a.get('date_evidence'):
        note+='<p class="archive-note">Legacy report: the source date and claims have not been revalidated under the current controls.</p>'
    if a.get('retrospective_launch'):
        note+='<p class="archive-note">Saturday launch edition prepared retrospectively; the recorded publication time is accurate.</p>'
    is_media=a.get("status")=="Original reporting"
    source_description=("This article draws on reporting by the named publisher, with the original article linked below." if is_media
        else "This article is based on the original announcement or document linked below.")
    disclosure='A source-based explanation, with attribution to the original material.'
    terms=a.get('display_glossary') or terms_for(a)
    definitions=''.join('<dt>'+esc(t)+'</dt><dd>'+esc(d)+'</dd>' for t,d in terms)
    glossary_html=('<section class="tb-glossary"><h2>Jargon, explained.</h2><dl>'+definitions+'</dl></section>' if definitions else '')
    # Legacy stories lack a distinct, source-grounded consequence. Never
    # repeat the standfirst and call it new UK-specific context.
    takeaway=(a.get('reader_takeaway') or '').strip()
    context_box=('<section class="tb-uk-context"><h3>Why it matters</h3><p>'
                 +esc(takeaway)+'</p></section>' if takeaway else '')
    # Use actual section headings as navigation, rather than repeating article sentences.
    # A one-section brief has no artificial summary panel.
    outline_html=''
    if len(a['blocks'])>1:
        outline_links=''.join('<li><a href="#report-section-'+str(i)+'">'+esc(heading)+'</a></li>'
                              for i,(heading,_) in enumerate(a['blocks'],start=1))
        outline_html='<nav class="tb-key-points tb-report-outline" aria-label="In this report"><h2>In this report</h2><ol>'+outline_links+'</ol></nav>'
    related=[x for x in (related or []) if x.get('id')!=a['id'] and x.get('desk_section')==section][:2]
    related_html=(''.join('<a href="../'+esc(story_href(x))+'">'+esc(x['title'])+'<span>Read report ↗</span></a>' for x in related))
    word_count=sum(len(str(para).split()) for _,para in a['blocks'])
    estimated_minutes=max(1,round(word_count/220))
    source_color='Insurance' if section=='Insurance' else 'Banking'
    return f"""<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#261E22"><meta name="description" content="{esc(a.get('short',''))}">
<title>{esc(a['title'])} — The Financial Edition</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&amp;family=Newsreader:wght@400;500;600;700&amp;display=swap" rel="stylesheet">
<link rel="stylesheet" href="../assets/site.css">
</head><body class="tb-reading-page tb-{desk}-reading">{header("../",section)}
<main class="reader"><article>{note}
<nav class="tb-breadcrumbs" aria-label="Breadcrumbs"><a href="../index.html">Home</a><span>›</span><a href="../{desk}.html">{esc(section)}</a><span>›</span><span>Latest reporting</span></nav>
<div class="tb-story-layout"><div class="tb-story-main">
<div class="kicker tb-story-kicker">{esc(section)} <span> / EXPLAINED</span></div>
<h1>{esc(a['title'])}</h1>
<div class="meta">By The Financial Edition · {byline_date} · {esc(a.get('source',''))} · {estimated_minutes} min read</div>
{visual(section)}
<div class="article-body">{article_body(a)}</div>
{glossary_html}
<div class="source tb-source-evidence"><h2>Original source</h2>
<p>{esc(source_description)} You can follow the link to check the underlying detail.</p>
<a href="{esc(a['url'])}" target="_blank" rel="noopener noreferrer">{esc(a.get('source','Original publisher'))} — read the original source ↗</a></div>
<p class="disclosure">{esc(disclosure)} <a href="../about.html">Our standards and corrections policy</a>. Not financial advice.</p>
</div><aside class="tb-story-aside" aria-label="Article at a glance">
{outline_html}
{context_box}
<section class="tb-related"><h3>Read next</h3>{related_html if related_html else '<a href="../'+desk+'.html">More '+esc(section)+' news ↗</a>'}</section>
</aside></div>
</article></main>{site_footer("../")}</body></html>"""

def archive_page(records,edition=None,search=False):
    prefix='../' if edition else ''
    title=('Search reports.' if search else ('Edition · '+edition if edition else 'The archive.'))
    rows=[]
    for day in sorted({original_date(a).isoformat() for a in records},reverse=True):
        cards=[]
        for a in records:
            if original_date(a).isoformat()!=day:continue
            search_text=' '.join([str(a.get(k,'')) for k in ('title','short','source','desk_section')] + [str(piece) for block in a.get('blocks',[]) if isinstance(block,(list,tuple)) for piece in block])
            cards.append('<article data-category="'+esc(a['desk_section'])+'" data-search="'+esc(search_text)+'"><span class="kicker">'+esc(a['desk_section'])+'</span><h2><a href="'+prefix+story_href(a)+'">'+esc(a['title'])+'</a></h2><p>'+esc(a['short'])+'</p><small>'+esc(a['source'])+(' · Published by The Financial Edition: '+esc(date_in_uk(a['published_at'])) if date_in_uk(a['published_at'])!=original_date(a) else '')+'</small></article>')
        rows.append('<section>'+('' if edition else '<h2 class="edition"><a href="'+prefix+'edition/'+day+'.html">'+esc(day)+' edition ↗</a></h2>')+''.join(cards)+'</section>')
    body=('<p class="intro">Search every published report across UK insurance and banking, including earlier editions. Search by company, subject, headline or words from a report.</p>' if search else '<p class="intro">Earlier developments, kept in their dated editions. Nothing here is presented as today’s news.</p>')
    if any(a.get('retrospective_launch') for a in records):
        body+='<p class="note"><strong>Saturday launch edition · 24 October 2026, from 6am UK.</strong> These launch reports were prepared retrospectively. Each article shows the original announcement date and its actual publication timestamp.</p>'
    body+='<p class="note">Reports from the earlier publishing system are retained with their recorded dates and a legacy verification notice. They have not been re-certified under the new controls.</p>'
    body+='<label for="archive-search">Search the archive</label><input id="archive-search" type="search" placeholder="Company, subject or keyword"><label for="archive-category">Subject</label><select id="archive-category"><option>Everything</option>'+''.join('<option>'+x+'</option>' for x in ['Insurance','Banking'])+'</select><p id="archive-count" role="status">'+str(len(records))+' reports</p>'
    body+='<div id="archive-list">'+(''.join(rows) or '<p>No earlier editions yet.</p>')+'</div><p id="archive-empty" role="status" hidden>No matching reports. Try another company, subject or keyword.</p>'
    script="""<script>
const q=document.querySelector('#archive-search'),c=document.querySelector('#archive-category');
const count=document.querySelector('#archive-count'),empty=document.querySelector('#archive-empty');
const cards=[...document.querySelectorAll('#archive-list article[data-category]')];
function filter(){
 const terms=q.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
 let n=0;
 cards.forEach(a=>{
  const words=(a.dataset.search||a.textContent).toLocaleLowerCase();
  const visible=terms.every(term=>words.includes(term))&&(c.value==='Everything'||a.dataset.category===c.value);
  a.hidden=!visible;if(visible)n++;
 });
 document.querySelectorAll('#archive-list>section').forEach(s=>{
  s.hidden=![...s.querySelectorAll('article[data-category]')].some(a=>!a.hidden);
 });
 count.textContent=n+' '+(n===1?'report':'reports');
 empty.hidden=n!==0;
}
q.addEventListener('input',filter);c.addEventListener('change',filter);
const params=new URLSearchParams(location.search);
const requested=params.get('category');
if(requested&&[...c.options].some(o=>o.value===requested))c.value=requested;
const query=params.get('q');
function restoreSearch(){
 if(query)q.value=query.slice(0,200);
 filter();
}
restoreSearch();
document.addEventListener('DOMContentLoaded',restoreSearch);
window.addEventListener('pageshow',restoreSearch);
if(query||params.has('search')){q.focus({preventScroll:true});q.scrollIntoView({block:'start'});}
</script>"""
    page=utility_page(title,body,prefix)
    if page.count('</body>')!=1:
        raise ValueError('Archive layout missing closing body')
    return page.replace('</body>',script+'</body>')


def utility_page(title,body,prefix='',active=''):
    """Single editorial layout for archive, dated editions and source information."""
    return ('<!doctype html><html lang="en-GB"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="theme-color" content="#332B2E"><title>'+esc(title)+' — The Financial Edition</title>'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;family=Newsreader:wght@400;500;600;700&amp;display=swap" rel="stylesheet">'
        '<link rel="stylesheet" href="'+prefix+'assets/site.css"></head><body class="tb-utility-page">'
        +header(prefix,active)+'<main class="tb-page"><span class="kicker">INSURANCE &amp; BANKING / THE FINANCIAL EDITION</span><h1>'+esc(title)+'</h1>'+body+'</main>'
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


def desk_topic(a,section):
    text=(a.get('title','')+' '+a.get('short','')).lower()
    if re.search(r'regulat|fca|pra|ombudsman|government|consultation|court|ruling|policy|treasury',text):
        return 'Regulation'
    if re.search(r'appoint|names? |promot|chief executive|director|leader|head of',text):
        return 'People' if section=='Insurance' else 'Companies'
    if re.search(r'market|premium|reinsur|pricing|rate|profit|investment|capital|claims?|mortgage|lending|inflation|currency|fx',text):
        return 'Markets' if section=='Insurance' else 'Economy'
    return 'Companies'


def desk_page(records,section):
    """One masthead, one editorial grid, subtle separate desk identities."""
    from site_design import (ST_PAULS_PHOTO,CITY_PHOTO,BANK_PHOTO,WESTMINSTER_PHOTO,
                             ST_PAULS_CREDIT_URL,CITY_CREDIT_URL,BANK_CREDIT_URL,WESTMINSTER_CREDIT_URL)
    # Today's desk is distinct from previous dated editions.
    selected=[a for a in records if a['desk_section']==section and published_same_day(a)]
    desk=section.lower()
    intro=('The latest developments shaping UK insurers, brokers, underwriting, claims and regulation.' if section=='Insurance'
        else 'The latest developments shaping UK banks, lenders, financial markets and the wider economy.')
    image=ST_PAULS_PHOTO if section=='Insurance' else CITY_PHOTO
    credit=ST_PAULS_CREDIT_URL if section=='Insurance' else CITY_CREDIT_URL
    credit_name='Colin' if section=='Insurance' else 'Choinowski'
    buttons=['Latest','Regulation','Markets' if section=='Insurance' else 'Economy','Companies']
    if section=='Insurance':buttons.append('People')
    tabs=''.join('<button type="button" class="tb-desk-tab'+(' active' if v=='Latest' else '')+'" data-topic="'+v+'" aria-pressed="'+('true' if v=='Latest' else 'false')+'">'+v+'</button>' for v in buttons)
    # Use several accredited London images as illustrations, not pseudo-event photography.
    thumbnail_images=([WESTMINSTER_PHOTO,ST_PAULS_PHOTO,CITY_PHOTO,BANK_PHOTO] if section=='Insurance'
                      else [BANK_PHOTO,CITY_PHOTO,WESTMINSTER_PHOTO,ST_PAULS_PHOTO])
    cards=[]
    for i,a in enumerate(selected):
        published=dt.datetime.fromisoformat(a['published_at'].replace('Z','+00:00')).astimezone(__import__('zoneinfo').ZoneInfo('Europe/London'))
        stamp=original_date(a).strftime('%-d %b %Y') if original_date(a)!=clock().date() else published.strftime('%H:%M')
        topic=desk_topic(a,section)
        cards.append('<article data-category="'+esc(section)+'" data-topic="'+esc(topic)+'" class="tb-desk-story">'
            '<a class="tb-desk-image" href="'+story_href(a)+'"><img src="'+esc(thumbnail_images[i%len(thumbnail_images)])+'" alt="Illustrative photograph of London, not the event" loading="lazy" decoding="async"></a>'
            '<div class="tb-desk-story-copy"><span class="tb-desk-category">'+esc(topic)+'</span>'
            '<h2><a href="'+story_href(a)+'">'+esc(a['title'])+'</a></h2>'
            '<p>'+esc(a.get('short',''))+'</p><small>'+esc(a.get('source',''))+' · '+esc(stamp)+'</small></div></article>')
    body=('<section class="tb-desk-hero"><img src="'+esc(image)+'" alt="London skyline, illustrative sector photography" decoding="async">'
          '<div class="tb-desk-hero-copy"><span class="tb-desk-label">'+esc(section.upper())+'</span>'
          '<h1>'+esc(section)+'.</h1><p>'+esc(intro)+'</p><div class="tb-desk-hero-rule"></div></div></section>'
          '<p class="tb-desk-credit">Illustrative photograph: <a href="'+esc(credit)+'" target="_blank" rel="noopener noreferrer">'+esc(credit_name)+' / Wikimedia Commons</a> · CC BY-SA. Not an event photograph.</p>'
          '<nav class="tb-desk-tabs" aria-label="Browse '+esc(section)+' reports">'+tabs
          +'<a href="archive.html?category='+esc(section)+'">All reports ↗</a></nav>'
          '<p class="tb-desk-edition-note">Today’s '+esc(section.lower())+' reports only · '+esc(clock().strftime('%-d %B %Y'))+'. <a href="archive.html?category='+esc(section)+'">Earlier editions</a>.</p>'
          '<div class="tb-desk-stories">'+''.join(cards)+'</div>'
          '<button type="button" id="tb-desk-more" class="tb-desk-more" hidden>Show more reports ↓</button>'
          '<p class="tb-desk-empty"'+('' if not selected else ' hidden')+'>'
          + ('No '+esc(section.lower())+' reports have been published today. <a href="archive.html?category='+esc(section)+'">Browse earlier editions</a>.' if not selected else 'No reports match this topic today. <button type="button" id="tb-reset-desk">Show all today’s reports</button>.')
          + '</p>'
          '<p class="tb-desk-image-credits">Article photographs are illustrative, not pictures of the news events. Image credits: '
          '<a href="'+WESTMINSTER_CREDIT_URL+'" target="_blank" rel="noopener noreferrer">hozinja</a>, '
          '<a href="'+ST_PAULS_CREDIT_URL+'" target="_blank" rel="noopener noreferrer">Colin</a>, '
          '<a href="'+CITY_CREDIT_URL+'" target="_blank" rel="noopener noreferrer">Choinowski</a> and '
          '<a href="'+BANK_CREDIT_URL+'" target="_blank" rel="noopener noreferrer">Diego Delso</a>, via Wikimedia Commons (CC BY / CC BY-SA).</p>'
          '<p class="tb-desk-older"><a href="archive.html?category='+esc(section)+'">Browse the complete archive ↗</a></p>')
    js="""<script>
const deskCards=[...document.querySelectorAll('.tb-desk-story')];
let deskTopic='Latest',deskLimit=7;
function renderDesk(){
  let matched=0,visible=0;
  deskCards.forEach(card=>{
    const eligible=deskTopic==='Latest'||card.dataset.topic===deskTopic;
    if(eligible)matched++;
    card.hidden=!(eligible&&matched<=deskLimit);
    if(!card.hidden)visible++;
  });
  const more=document.querySelector('#tb-desk-more');
  more.hidden=matched<=deskLimit;
  more.textContent='Show more reports ↓';
  document.querySelector('.tb-desk-empty').hidden=matched>0;
}
document.querySelectorAll('.tb-desk-tab').forEach(button=>button.addEventListener('click',()=>{
  deskTopic=button.dataset.topic;deskLimit=7;
  document.querySelectorAll('.tb-desk-tab').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',String(b===button))});
  renderDesk();
}));
document.querySelector('#tb-desk-more').addEventListener('click',()=>{deskLimit+=7;renderDesk()});
const resetDesk=document.querySelector('#tb-reset-desk');
if(resetDesk)resetDesk.addEventListener('click',()=>document.querySelector('.tb-desk-tab').click());
renderDesk();
</script>"""
    return ('<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="theme-color" content="#261E22"><meta name="description" content="'+esc(intro)+'"><title>'+esc(section)+' — The Financial Edition</title>'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&amp;family=Newsreader:wght@400;500;600;700&amp;display=swap" rel="stylesheet">'
        '<link rel="stylesheet" href="assets/site.css"></head><body class="tb-desk-view tb-'+desk+'-desk">'
        +header('',section)+'<main class="tb-page tb-desk-page">'+body+'</main>'+site_footer()+js+'</body></html>')

def sources_page():
    from source_catalog import catalog
    data=catalog(ROOT)
    body=('<p class="intro">These are the publishers and official sources we follow for UK banking and insurance news. Each report links to the material it draws on. Inclusion here does not mean we have independently verified every claim made by a source.</p>'
          '<section id="publication-method"><h2>How reports are prepared</h2><p>The Financial Edition was founded and is directed by Yogesh Karan Sharma. Reports are developed from credited published material with the help of writing software. They can be published without a separate human review of each article and are not independently fact-checked. Source dates, relevance and duplication are checked, and readers can follow the links to examine the original material.</p></section>'
          '<label for="source-search">Find a publisher or subject</label><input id="source-search" type="search" placeholder="Insurance, banking, regulator…"><div>')
    for x in data['sources']:
        body+='<article data-source-row><h2><a href="'+esc(x['url'])+'">'+esc(x['name'])+'</a></h2><p>'+esc(x['category'])+' · '+esc(x['method'])+' · '+esc(x['observed'])+'</p></article>'
    body+='</div><script>document.querySelector("#source-search").oninput=function(){document.querySelectorAll("[data-source-row]").forEach(x=>x.hidden=!x.textContent.toLowerCase().includes(this.value.toLowerCase()))}</script>'
    (OUT/'data/sources.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    return utility_page('Our source registry.',body)


def build():
    archive = valid_articles()
    records = [dict(a, home_image=home_photo_for(a)) for a in archive if published_same_day(a)]
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
    first = lead_article(records)
    featured_ids={a["id"] for a in [r for r in records if first is None or r["id"]!=first["id"]][:4]}
    def art_credit(a, large=False):
        photo=a["home_image"]
        caption='<figcaption>Illustrative photograph, not the news event · <a href="'+esc(photo["credit_url"])+'" target="_blank" rel="noopener noreferrer">'+esc(photo["credit"])+'</a></figcaption>'
        image='<img src="'+esc(photo["src"])+'" alt="'+esc(photo["alt"])+'" decoding="async"'+(' fetchpriority="high"' if large else ' loading="lazy"')+'>'
        if large:
            return '<figure class="tb-lead-art">'+image+caption+'</figure>'
        return '<figure class="tb-report-art"><a href="'+esc(story_href(a))+'" aria-label="Read report: '+esc(a["title"])+'">'+image+'</a>'+caption+'</figure>'
    # The repository retains a source-mode backup for broken JavaScript.
    # The published build already contains real, readable lead/feed HTML,
    # so NEVER copy the duplicate emergency article-list box into Pages.
    fallback = re.compile(r"\s*<!-- THEBRIEF_STATIC_START -->.*?<!-- THEBRIEF_STATIC_END -->", re.S)
    page, removed = fallback.subn("", page, count=1)
    if removed != 1 or "THEBRIEF_STATIC_START" in page or 'id="static-edition"' in page:
        raise ValueError("Could not remove duplicate repository-only safety section")
    if first:
        lead = ('<article id="lead-story" class="lead-story with-photo"><span class="story-kicker">'
            + esc(first.get("desk_section")) + ' / THE LEAD STORY</span><h1><a href="'
            + esc(story_href(first)) + '">' + esc(first["title"])
            + '</a></h1><p class="standfirst">' + esc(first.get("short")) + '</p>'
            + '<p class="meta">' + esc(first.get('source','')) + ' · ' + esc(dt.datetime.fromisoformat(first['published_at'].replace('Z','+00:00')).astimezone(__import__('zoneinfo').ZoneInfo('Europe/London')).strftime('%H:%M')) + '</p>'
            + '<p><a class="cta" href="' + esc(story_href(first)) + '">Read the full story →</a></p>'+art_credit(first,large=True)+'</article>')
    else:
        # Retain the approved photographic newspaper layout on a quiet
        # morning, without pretending any historical article is new.
        lead = ('<article id="lead-story" class="lead-story with-photo"><span class="story-kicker">THE FINANCIAL EDITION / YOUR UK FINANCIAL DESK</span>'
            '<h1>Understand the news that shapes your money.</h1>'
            '<p class="standfirst">Today’s lead report is still being prepared. Explore earlier reporting or build your financial knowledge below.</p>'
            '<a class="cta" href="archive.html">Explore earlier reporting →</a>'
            '<p class="meta">A new UK edition, updated as verified reports become available.</p>'
            '<figure class="tb-lead-art"><img src="'+esc(CITY_PHOTO)+'" alt="The City of London skyline, a general editorial illustration"'
            ' fetchpriority="high" decoding="async"><figcaption>London skyline · <a href="'+esc(CITY_CREDIT_URL)+'" target="_blank" rel="noopener noreferrer">'+esc(CITY_CREDIT)+'</a> · not today’s news event</figcaption></figure></article>')
    page = insert_once(page, '<article id="lead-story" class="lead-story"></article>', lead)
    briefing = ''.join(
        '<div class="briefing-story" data-desk="'+esc(a.get("desk_section"))+'"><span class="brief-number">0' + str(i+1)
        + '</span><div><span class="tb-brief-desk">'+esc(a.get("desk_section"))+'</span>'
        + '<a href="' + esc(story_href(a)) + '">' + esc(a["title"]) + '</a>'
        + '<p>' + esc(a.get("reader_takeaway") or a.get("short", "")) + '</p>'
        + '</div></div>'
        for i, a in enumerate(other_briefs(records, first, limit=4))
    )
    if first and not briefing:
        briefing='<p class="tb-briefing-empty">Our lead story is today’s only published report. No other developments have been added.</p>'
    if not briefing:
        briefing = ('<div class="tb-empty-guide"><p>While today’s briefing is being prepared:</p>'
            '<a href="archive.html"><b>ARCHIVE</b><span>Read previous editions →</span></a>'
            '<a href="#context"><b>EXPLAINERS</b><span>Understand financial basics →</span></a></div>')
    page = insert_once(page,
        '<div id="briefing-stories" class="briefing-stories"></div>',
        '<div id="briefing-stories" class="briefing-stories">' + briefing + '</div>')
    rows = []
    for i, a in enumerate(records[:15]):
        featured=a["id"] in featured_ids
        rows.append(
            '<article class="news-item'+(' has-photo' if featured else '')+'" data-desk="'+esc(a.get('desk_section'))+'">'+(art_credit(a) if featured else '')+'<div class="story-ordinal">' + str(i+1).zfill(2)
            + '</div><div><div class="news-cat">' + esc(a.get("desk_section")) + ' · EXPLAINED</div>'
            + '<h3><a href="' + esc(story_href(a)) + '">' + esc(a["title"]) + '</a></h3>'
            + '<p class="summary">' + esc(a.get("short")) + '</p>'
            + '<p class="meta">' + esc(a.get('source','')) + ' · ' + esc(dt.datetime.fromisoformat(a['published_at'].replace('Z','+00:00')).astimezone(__import__('zoneinfo').ZoneInfo('Europe/London')).strftime('%H:%M')) + '</p></div></article>'
        )
    page = insert_once(page, '<div class="feed" id="feed"></div>',
        '<div class="feed" id="feed">' + ('\n'.join(rows) if rows else '<p class="nothing">No reports published today. <a href="archive.html">Read earlier editions</a>.</p>') + '</div>')
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
    (OUT / "search.html").write_text(archive_page(archive,search=True),encoding="utf-8")
    (OUT / "insurance.html").write_text(desk_page(archive,'Insurance'),encoding="utf-8")
    (OUT / "banking.html").write_text(desk_page(archive,'Banking'),encoding="utf-8")
    (OUT / "edition").mkdir(exist_ok=True)
    for day in sorted({original_date(a).isoformat() for a in archive}):
        selected=[a for a in archive if original_date(a).isoformat()==day]
        (OUT / "edition" / (day+".html")).write_text(archive_page(selected,day),encoding="utf-8")
    status_path=ROOT/"data/status.json"
    if status_path.exists():shutil.copy2(status_path,OUT/"data/status.json")
    for a in archive:
        (OUT / story_href(a)).write_text(standalone_story(a,archive), encoding="utf-8")
        (OUT / legacy_story_href(a)).write_text(legacy_redirect(a), encoding="utf-8")
    privacy_body = (
        '<p class="intro">We want to understand which stories readers find useful without collecting unnecessary information about them.</p>'
        '<h2>Website traffic measurement</h2>'
        '<p>We use Cloudflare Web Analytics once the site owner has connected the service. It measures aggregated page views, visitor estimates, popular pages, broad geographic areas and referral sources. '
        'Cloudflare states that its Web Analytics service does not use cookies or collect visitors’ personal data. '
        'These statistics are estimates, not an exact count of every human reader. Browser blocking and automated traffic can affect measurements.</p>'
        '<p>Until analytics is configured and the optional beacon is active, no audience figures are collected by this feature and we cannot reconstruct earlier visits.</p>'
        '<h2>On-device reading preferences</h2>'
        '<p>Saved stories and followed desk preferences may be stored in your browser so the reading experience works on that device. '
        'We do not receive those lists through the analytics setup.</p>'
        '<h2>Questions and corrections</h2>'
        '<p>For a question about this website, or to report a factual error, see our <a href="about.html">About and corrections page</a>.</p>'
    )
    (OUT / "privacy.html").write_text(utility_page("Privacy and website measurement.", privacy_body), encoding="utf-8")
    analytics_result = install_analytics(OUT, token_from_env())
    print("READER_ANALYTICS:", json.dumps(analytics_result))
    from seo_metadata import add_search_discovery
    add_search_discovery(OUT, archive)


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



