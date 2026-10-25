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
    current_home=re.sub(r'<section id="launch-edition".*?</section>','',home,flags=re.S)
    if 'id="launch-edition"' in home:
        assert 'Prepared retrospectively; actual publication times' in home
    assert 'insurance.html' in home and 'banking.html' in home
    assert 'status.html' not in home and 'hourly.html' not in home
    for a in canonical:
        escaped=html.escape(a['title'],quote=True)
        assert escaped in archive_html,'Archive headline absent'
        if not published_same_day(a):assert escaped not in current_home,'Historical headline leaked into today'
        story=(public/'story'/(a['id']+'.html')).read_text()
        assert escaped in story and html.escape(a['url'],quote=True) in story
        assert '<main class="reader"><article>' in story
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

