"""Launch-test isolation and stale-date safeguards; no model/network requests."""
import copy
import datetime as dt
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from zoneinfo import ZoneInfo
import launch_canary as canary
from ai_cost_guard import CallBudget,BudgetExhausted
from test_autonomous import prepared
from newsroom_v2 import article_sentences,source_passages
from same_day_policy import clock


def main():
    base=prepared();a=base['draft'];day=(clock().date()-dt.timedelta(days=1)).isoformat()
    item={'title':a['title'],'source':a['source'],'url':a['url'],'category':a['category'],'dateISO':day,'source_time_precision':'date','source_published_at':day,
          'date_evidence':{'url':a['url'],'value':day,'precision':'date','method':'offline test'}}
    doc=SimpleNamespace(url=a['url'],document_urls=[a['url']],text=base['captured_source_excerpt'],evidence_sha256=base['audit']['source_sha256'],extraction='HTML main content',notes=[],publication_date=(day,day,'date'))
    calls=[];written={}
    def ai(prompt):
        calls.append(prompt)
        if len(calls)==1:
            written.update(title=a['title'],short=a['short'],blocks=a['blocks'])
            return {'headline':a['title'],'standfirst':a['short'],'sections':[{'heading':h,'text':p} for h,p in a['blocks']]}
        refs=list(source_passages(doc.text))
        return {'reviews':[{'id':s['id'],'verdict':'SUPPORTED','source_id':refs[i%len(refs)],'issue':''} for i,s in enumerate(article_sentences(written))]}
    bundle,result=canary.exercise(item,doc,ai)
    assert len(calls)==2 and result['result']=='PASSED'
    assert result['old_source_publication_rejected']
    assert bundle['draft']['dateISO']==day,'Canary refreshed a historical date'
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder);(root/'data').mkdir();(root/'data/articles.json').write_text('[]')
        quota=dt.datetime.now(dt.timezone.utc).astimezone(ZoneInfo('America/Los_Angeles')).date().isoformat()
        ledger={'sources':{},'api_budget':{'date':quota,'requests':30,'limit':None},'quota_pause_until':(dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=1)).isoformat()}
        (root/'data/newsroom-attempts.json').write_text(json.dumps(ledger))
        r=canary.run(root)
        assert r['result']=='WAITING' and r['requests_this_attempt']==0
        assert json.loads((root/'data/articles.json').read_text())==[]
        assert not list((root/'generated-drafts').glob('ai-*.json')),'Test draft entered publisher input'
        assert json.loads((root/'data/newsroom-attempts.json').read_text())['api_budget']['requests']==30
    ledger={'api_budget':{'date':quota,'requests':20,'limit':20}}
    meter=CallBudget(ledger,per_run=2,per_day=20)
    for _ in range(2):meter.call(lambda prompt:{'ok':True},'test',diagnostic=True)
    assert ledger['api_budget']['requests']==22 and ledger['api_budget']['limit']==20
    assert ledger['launch_diagnostic_allowance']['requests']==2
    try:meter.call(lambda prompt:None,'third',diagnostic=True)
    except BudgetExhausted:pass
    else:raise AssertionError('A third diagnostic call was allowed')
    try:CallBudget(ledger,per_day=20).call(lambda prompt:None,'production')
    except BudgetExhausted:pass
    else:raise AssertionError('Diagnostic allowance reset the production cap')
    print('PASS: two-call real-model test adapter, historical date preserved, stale publication rejected, provider cooldown respected, usage untouched and drafts isolated')
if __name__=='__main__':main()
