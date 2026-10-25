"""Adversarial dates, failure outcomes and writer→review→publisher integration. Offline only."""
import copy
import datetime as dt
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from source_dates import published_date,verify_announcement
from same_day_policy import clock,source_issued_today,published_same_day
from newsroom_health import assess
from newsroom_v2 import make_article,review_until_resolved,article_sentences,source_passages
from test_autonomous import prepared
import publish_autonomous as auto


def main():
    assert published_date('<main><h1>Report</h1><p>Updated 25 October 2026</p><aside><time datetime="2026-10-25">Today</time></aside></main>') is None
    original='<meta property="article:published_time" content="2026-10-22T09:00:00Z"><meta property="article:modified_time" content="2026-10-25T10:00:00Z">'
    assert published_date(original)[0]=='2026-10-22'
    assert published_date('<script type="application/ld+json">{"@type":"WebSite","datePublished":"2026-10-25"}</script>') is None
    try:published_date(original+'<meta name="datePublished" content="2026-10-24">')
    except ValueError:pass
    else:raise AssertionError('Conflicting original dates accepted')
    # BST boundary and the repeated hour on the day the clocks change.
    assert source_issued_today({'dateISO':'2026-10-24','source_time_precision':'timestamp','source_published_at':'2026-10-24T23:30:00Z'},dt.datetime(2026,10,25,0,15,tzinfo=dt.timezone.utc))
    assert not source_issued_today({'dateISO':'2026-10-24','source_time_precision':'date'},dt.datetime(2026,10,25,0,15,tzinfo=dt.timezone.utc))
    for hour in [0,1,2]:assert clock(dt.datetime(2026,10,25,hour,30,tzinfo=dt.timezone.utc)).date()==dt.date(2026,10,25)
    now=dt.datetime.now(dt.timezone.utc)
    report={'first_party_indexes_checked':17,'fresh_unpublished_source_candidates':0}
    pub={'published':[]};feeds={'sources_checked':[{}]}
    assert assess([],report,now,pub,feeds)['outcome']=='NO_QUALIFYING_NEWS'
    assert assess([],dict(report,first_party_discovery_errors=['timeout']),now,pub,feeds)['outcome']=='DEGRADED'
    assert assess([],dict(report,fresh_unpublished_source_candidates=1),now,pub,feeds)['outcome']=='BLOCKED'
    base=prepared();a=base['draft']
    doc=SimpleNamespace(url=a['url'],document_urls=[a['url']],text=base['captured_source_excerpt'],evidence_sha256=base['audit']['source_sha256'],extraction='HTML main content',notes=[],publication_date=(a['dateISO'],a['dateISO'],'date'))
    item={'title':a['title'],'source':a['source'],'url':a['url'],'category':a['category'],'dateISO':a['dateISO'],'source_time_precision':'date'}
    item=verify_announcement(item,doc,now)
    stale=copy.copy(doc);stale.publication_date=('2026-10-22','2026-10-22','date')
    try:verify_announcement(item,stale,now)
    except ValueError:pass
    else:raise AssertionError('A fresh listing refreshed an old original document')
    written=make_article({'headline':a['title'],'standfirst':a['short'],'sections':[{'heading':h,'text':p} for h,p in a['blocks']]},item,doc)
    refs=list(source_passages(doc.text))
    def reviewer(prompt):
        return {'reviews':[{'id':s['id'],'verdict':'SUPPORTED','source_id':refs[i%len(refs)],'issue':''} for i,s in enumerate(article_sentences(written))]}
    bundle,passed=review_until_resolved(item,doc,written,gemini=reviewer)
    assert passed,bundle.get('editorial_flags')
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder);(root/'data').mkdir();(root/'generated-drafts').mkdir()
        (root/'data/articles.json').write_text('[]')
        (root/'generated-drafts'/(written['id']+'.json')).write_text(json.dumps(bundle))
        result=auto.publish(root)
        assert len(result['published'])==1
        article=json.loads((root/'data/articles.json').read_text())[0]
        assert published_same_day(article)
        assert not auto.publish(root)['published']
    def sceptic(prompt):
        r=reviewer(prompt);r['reviews'][2]['verdict']='INSUFFICIENT';r['reviews'][2]['issue']='Unproven heading';return r
    held,ok=review_until_resolved(item,doc,written,gemini=sceptic)
    assert not ok and auto.eligible(held)
    print('PASS: original-vs-modified dates, DST, failure outcomes, all-heading review, full mocked publication and duplicate prevention')
if __name__=='__main__':main()
