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
    assert 'archive.html' in home and 'status.html' in home
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
    assert (public/'status.html').is_file()
    desk=json.loads((public/'data/hourly-desk.json').read_text())
    desk_html=(public/'hourly.html').read_text()
    assert 'href="hourly.html"' in home and 'The hourly desk.' in desk_html
    assert desk['mode'] in {'TODAY_VERIFIED','DATED_CONTEXT','EMPTY'}
    assert desk['edition_date']==__import__('same_day_policy').clock().date().isoformat()
    for item in desk['items']:
        assert item['id'] in {a['id'] for a in canonical},'Hourly desk includes unapproved reporting'
        assert html.escape(item['title'],quote=True) in desk_html,'Hourly story missing'
        assert item['original_date'] in desk_html,'Hourly story missing its original date'
    assert 'id="publisher-desk"' not in home
    assert not (public/'data/headlines.json').exists(),'Internal research headlines leaked into public output'
    print('PUBLIC_ARTIFACT_VALIDATED:',json.dumps({'today':len(edition),'archive':len(archive),'complete_stories':len(canonical)}))
if __name__=='__main__':verify()

