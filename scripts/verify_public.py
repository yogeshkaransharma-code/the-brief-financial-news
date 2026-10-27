"""Validate the artifact's edition isolation, full archive and readable story pages."""
import html
import json
import re
from pathlib import Path
from same_day_policy import published_same_day
ROOT=Path(__file__).resolve().parents[1]

def verify():
    public=ROOT/'public'
    canonical=json.loads((ROOT/'data/articles.json').read_text())
    edition=json.loads((public/'data/articles.json').read_text())
    archive=json.loads((public/'data/archive.json').read_text())
    assert {x['id'] for x in edition}=={x['id'] for x in canonical if published_same_day(x)}
    assert {x['id'] for x in archive}=={x['id'] for x in canonical},'Historical articles lost'
    home=(public/'index.html').read_text();archive_html=(public/'archive.html').read_text()
    from reader_experience import lead_article, other_briefs
    from reader_analytics import token_from_env, BEACON_URL
    assert (public/'privacy.html').is_file(), 'Privacy page missing'
    privacy=(public/'privacy.html').read_text(encoding='utf-8')
    assert 'Cloudflare Web Analytics' in privacy and 'About and corrections page' in privacy
    assert 'href="privacy.html"' in home, 'Footer has no readable privacy link'
    assert 'rankHighlights(originals)[0]' in home, 'Client-side homepage ignores UK-focused lead'
    today_list=[a for a in canonical if published_same_day(a)]
    today_list.sort(key=lambda a:(a.get('published_at',''),a.get('dateISO',''),a['id']),reverse=True)
    front_lead=lead_article(today_list)
    if front_lead:
        from html import escape
        hero=home.split('<article id="lead-story"',1)[1].split('</article>',1)[0]
        assert escape(front_lead['title'],quote=True) in hero, 'Lead has not followed UK relevance ranking'
        if len(today_list)>1:
            briefing=home.split('<div id="briefing-stories" class="briefing-stories">',1)[1].split('<a href="#latest"',1)[0]
            assert escape(front_lead['title'],quote=True) not in briefing, 'Lead repeated in 60-second brief'
    assert 'data-desk="' in home, 'Sector cues missing from news rows'
    # Today's date belongs to the edition header; avoid repeating identical
    # source/publication calendar dates on every card or lead.
    assert 'Original news:' not in home and 'The Brief published:' not in home, 'Repeated date metadata on homepage'
    assert 'class="date-separator"' not in home, 'Daily edition contains duplicate day header'
    assert "$('edition-date').textContent=d.toLocaleDateString" not in home, 'Masthead reintroduces daily date'
    assert 'id="issue-date"' in home, 'Edition must retain one readable date'
    for a in canonical:
        story=(public/'story'/(a['id']+'.html')).read_text(encoding='utf-8')
        from same_day_policy import original_date, date_in_uk
        byline=story.split('<div class="meta">',1)[1].split('</div>',1)[0]
        if original_date(a)==date_in_uk(a['published_at']):
            assert byline.count(original_date(a).strftime('%-d %B %Y'))==1, 'Story repeats identical day'
            assert 'Source:' not in byline and 'The Brief:' not in byline, 'Same-day publication doubles byline'
        else:
            assert 'Source:' in byline and 'The Brief:' in byline, 'Different source/publication dates hidden'

    token=token_from_env()
    pages=list(public.rglob('*.html'))
    if token:
        assert pages and all(page.read_text().count(BEACON_URL)==1 for page in pages), 'Analytics beacon missing from a page'
    else:
        assert all(BEACON_URL not in page.read_text() for page in pages), 'Unexpected analytics beacon before owner setup'
    from xml.etree import ElementTree as ET
    from seo_metadata import BASE
    sitemap = public / 'sitemap.xml'
    assert sitemap.is_file(), 'Missing public sitemap'
    assert (public/'robots.txt').is_file() and BASE+'sitemap.xml' in (public/'robots.txt').read_text(), 'Missing sitemap discovery hint'
    root = ET.parse(sitemap).getroot()
    urls = [node.text for node in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
    expected = {BASE, BASE+'about.html', BASE+'insurance.html', BASE+'banking.html',
                BASE+'archive.html', BASE+'sources.html',BASE+'privacy.html'}
    expected.update(BASE+'story/'+a['id']+'.html' for a in canonical)
    expected.update(BASE+'edition/'+day+'.html' for day in {a['dateISO'] for a in canonical})
    assert set(urls)==expected and len(urls)==len(set(urls)), 'Sitemap routes do not match real pages'
    for uri in urls:
        assert uri.startswith(BASE), 'Wrong sitemap host'
        relative=uri.removeprefix(BASE) or 'index.html'
        document=(public/relative).read_text(encoding='utf-8')
        assert '<link rel="canonical" href="'+uri+'">' in document, 'Canonical mismatch: '+relative
        assert '<meta property="og:title"' in document, 'Missing readable share title: '+relative
    for a in canonical:
        document=(public/'story'/(a['id']+'.html')).read_text(encoding='utf-8')
        assert '"@type":"NewsArticle"' in document and '"citation":' in document, 'NewsArticle source metadata missing'
    current_home=re.sub(r'<section id="launch-edition".*?</section>','',home,flags=re.S)
    if 'id="launch-edition"' in home:
        assert 'Prepared retrospectively; actual publication times' in home
    assert 'insurance.html' in home and 'banking.html' in home
    assert 'status.html' not in home and 'hourly.html' not in home
    assert '<section id="context" class="understand" aria-label=' in home, 'New here section is absent/hidden'
    assert 'Explore 18 more explanations' in home, 'Explainer archive link missing'
    for a in canonical:
        escaped=html.escape(a['title'],quote=True)
        assert escaped in archive_html,'Archive headline absent'
        if not published_same_day(a):assert escaped not in current_home,'Historical headline leaked into today'
        story=(public/'story'/(a['id']+'.html')).read_text()
        assert escaped in story and html.escape(a['url'],quote=True) in story
        assert '<main class="reader"><article>' in story
        assert 'tb-article-visual' not in story, 'Generic unrelated photo in article'
        for h,p in a['blocks']:assert html.escape(h,quote=True) in story and html.escape(p,quote=True) in story
    if not edition:assert 'No verified news from today yet' in home
    assert not (public/'data/live.json').exists() and 'data/live.json' not in home
    assert not (public/'status.html').exists(), 'Internal newsroom dashboard accidentally published'
    assert not (public/'hourly.html').exists(), 'Duplicate hourly reading page was published'
    assert (public/'assets/site.css').is_file(), 'Shared burgundy stylesheet absent'
    assert (public/'about.html').is_file() and (public/'sources.html').is_file()
    for section in ['Insurance','Banking']:
        path=public/(section.lower()+'.html')
        page=path.read_text(encoding='utf-8')
        assert '<h1>'+section+'.</h1>' in page
        assert 'class="tb-header"' in page and 'status.html' not in page
        matches=[a for a in archive if a['desk_section']==section]
        for article in matches:assert html.escape(article['title'],quote=True) in page
        assert page.count('<article data-category=')==len(matches)

    for a in archive:
        assert a['desk_section'] in {'Insurance','Banking'}, 'Third public category leaked'
    for a in edition:
        if a.get('display_glossary'):
            story=(public/'story'/(a['id']+'.html')).read_text()
            assert 'Jargon, explained.' in story, 'Story glossary missing'
    assert 'id="publisher-desk"' not in home
    assert not (public/'data/headlines.json').exists(),'Internal research headlines leaked into public output'
    print('PUBLIC_ARTIFACT_VALIDATED:',json.dumps({'today':len(edition),'archive':len(archive),'complete_stories':len(canonical)}))
if __name__=='__main__':verify()

