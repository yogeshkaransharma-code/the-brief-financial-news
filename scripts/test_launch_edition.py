"""A retrospective edition must never invent a publication clock or enter today."""
import copy
import datetime as dt
import json
from pathlib import Path
import tempfile
from test_autonomous import prepared
from newsroom_v2 import canonical,numeric_tokens
from same_day_policy import published_same_day
from publish_autonomous import eligible,publish
from verify_approved_articles import validate

def main():
    bundle=prepared();a=bundle['draft'];audit=bundle['audit']
    a.update(dateISO='2026-10-24',date='2026-10-24',source_time_precision='timestamp',source_published_at='2026-10-24T05:00:05+00:00')
    a['date_evidence']={'url':a['url'],'value':a['source_published_at'],'precision':'timestamp','method':'offline test original date'}
    audit['date_evidence']=a['date_evidence']
    audit['source_number_tokens']=sorted(numeric_tokens(bundle['captured_source_excerpt']+' '+audit['source_title']+' '+a['dateISO']))
    audit['draft_sha256']=canonical(a)
    assert not eligible(bundle,edition_date='2026-10-24'),eligible(bundle,edition_date='2026-10-24')
    assert eligible(bundle,edition_date='2026-10-23'),'Arbitrary past edition accepted'
    if dt.datetime.now(dt.timezone.utc).date()!=dt.date(2026,10,24):
        assert eligible(bundle),'Historical article entered normal current-day publishing'
    early=copy.deepcopy(bundle);early['draft']['source_published_at']='2026-10-24T04:59:00+00:00'
    early['audit']['draft_sha256']=canonical(early['draft'])
    assert eligible(early,edition_date='2026-10-24'),'Before-6am source entered launch edition'
    undated=copy.deepcopy(bundle);undated['draft']['source_time_precision']='date'
    undated['audit']['draft_sha256']=canonical(undated['draft'])
    assert eligible(undated,edition_date='2026-10-24'),'Date-only source invented an hour'
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder);(root/'data').mkdir();drafts=root/'drafts';drafts.mkdir()
        (root/'data/articles.json').write_text('[]');(drafts/(a['id']+'.json')).write_text(json.dumps(bundle))
        result=publish(root,folder=drafts,edition_date='2026-10-24')
        assert len(result['published'])==1
        published=json.loads((root/'data/articles.json').read_text())[0]
        assert dt.datetime.fromisoformat(published['published_at'])>dt.datetime.now(dt.timezone.utc)-dt.timedelta(minutes=1)
        assert not published_same_day(published),'Retrospective report entered today feed'
        assert not publish(root,folder=drafts,edition_date='2026-10-24')['published'],'Duplicate published'
        published['source_published_at']='2026-10-24T04:00:00+00:00'
        (root/'data/articles.json').write_text(json.dumps([published]))
        try:validate(root)
        except ValueError:pass
        else:raise AssertionError('Changed source clock passed approval lock')
    print('PASS: fixed launch date, 6am boundary, exact source time, actual publication time, today isolation and duplicate prevention')

if __name__=='__main__':main()
