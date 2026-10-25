"""User-authorised Saturday launch reconstruction; real Gemini, real timestamps.

Fixed date and source manifest, one writer call and one separate reviewer call.
This path never changes today's feed or fabricates a Saturday publication time.
"""
import datetime as dt
import json
import os
from pathlib import Path
from ai_cost_guard import CallBudget,preflight_source
from model_providers import fetch_ai,ACTIVE_MODEL
from newsroom_v2 import write_prompt,make_article,review_until_resolved,omit_flagged_context,canonical
from source_retrieval import read_source
from source_dates import verify_announcement
from publish_autonomous import publish,eligible
from editorial_selection import choose

ROOT=Path(__file__).resolve().parents[1]
DAY='2026-10-24'
SOURCE='https://www.gov.uk/government/news/chancellor-unveils-britains-ambitious-plan-for-ai'

def run(root=ROOT):
    root=Path(root);dest=root/'data/launch-edition.json'
    articles=json.loads((root/'data/articles.json').read_text())
    existing=[a for a in articles if a.get('retrospective_launch') and a.get('url')==SOURCE]
    if existing:
        print('LAUNCH_EDITION_ALREADY_PUBLISHED:',existing[0]['id']);return
    if dest.exists():
        previous=json.loads(dest.read_text())
        if previous.get('attempted') and previous.get('version',1)>=3:
            print('LAUNCH_EDITION_HELD: previous attempt retained; no automatic repeat');return
    report={'version':3,'edition_date':DAY,'window_start':'2026-10-24T06:00:00+01:00',
            'retrospective':True,'result':'STARTED','published':[],
            'run_id':os.getenv('GITHUB_RUN_ID','local'),'checked_at':dt.datetime.now(dt.timezone.utc).isoformat()}
    ledger_path=root/'data/newsroom-attempts.json'
    ledger=json.loads(ledger_path.read_text());meter=CallBudget(ledger,per_run=3,path=ledger_path)
    folder=root/'generated-drafts/launch-edition';folder.mkdir(parents=True,exist_ok=True)
    try:
        doc=read_source(SOURCE)
        item={'url':SOURCE,'title':'Chancellor unveils Britain’s ambitious plan for AI',
              'source':'HM Treasury','category':'Technology','dateISO':DAY,'source_time_precision':'date'}
        item=verify_announcement(item,doc,dt.datetime.fromisoformat('2026-10-24T23:59:59+01:00'))
        preflight_source(item,doc)
        issue=dt.datetime.fromisoformat(item['source_published_at'])
        if issue<dt.datetime.fromisoformat(report['window_start']):raise ValueError('Source predates 6am launch')
        recovery_path=root/'editorial/launch-draft-recovery.json'
        recovery=json.loads(recovery_path.read_text()) if recovery_path.exists() else None
        if meter.remaining()<(1 if recovery else 3):raise ValueError('Insufficient allowance for a complete editorial sequence')
        report.update(attempted=True,source_url=SOURCE,original_source_time=item['source_published_at'],model=ACTIVE_MODEL)
        dest.write_text(json.dumps(report,indent=2)+'\n')
        selected,decision=choose([(item,doc)],ledger,meter,fetch_ai,edition_date=DAY,max_stories=1)
        report['editorial_selection']=decision
        if not selected:raise ValueError('Gemini declined this source for the launch edition')
        (folder/'original-source.txt').write_text(doc.text)
        if recovery:
            if (recovery['source_sha256']!=doc.evidence_sha256 or recovery['draft_sha256']!=canonical(recovery['draft'])
                or recovery['draft']['url']!=SOURCE):raise ValueError('Held draft or original evidence changed; cannot reuse it')
            article=omit_flagged_context(recovery['draft'],recovery['flags'])
            if article is None:raise ValueError('The held draft cannot be safely shortened')
            report['reused_gemini_draft']=True
        else:
            output=meter.call(fetch_ai,write_prompt(item,doc)+'\nEDITORIAL FOCUS: Write one concise report on the announced investment in British AI companies and AI/cyber security. Preserve announced funding versus delivered spending. Attribute ambitions and projected benefits to the Treasury. Do not add financial-services implications absent from the source. Avoid covering every programme or stakeholder quote. Omit the glossary.')
            (folder/'writer-response.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
            article=make_article(output,item,doc)
        bundle,passed=review_until_resolved(item,doc,article,gemini=lambda p:meter.call(fetch_ai,p))
        if recovery:
            bundle['audit']['editorial_omissions']=[{'text':recovery['flags'][0]['sentence'],'reason':recovery['flags'][0]['reason'],'method':'Whole optional sentence removed; remaining article independently re-reviewed'}]
        (folder/(article['id']+'.json')).write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n')
        holds=eligible(bundle,edition_date=DAY)
        if not passed or holds:
            report.update(result='HELD',holds=holds,flags=bundle.get('editorial_flags',[]))
        else:
            result=publish(root,folder=folder,edition_date=DAY)
            report.update(result='PUBLISHED' if result['published'] else 'HELD',published=result['published'],holds=result['held'])
    except Exception as exc:
        report.update(result='BLOCKED',error=type(exc).__name__+': '+str(exc)[:500])
    report.update(requests_this_attempt=meter.run_used,api_budget=meter.snapshot())
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (folder/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('LAUNCH_EDITION_RESULT:',json.dumps(report,ensure_ascii=False))
    if report['result']!='PUBLISHED':raise RuntimeError('Launch edition did not publish: '+report['result'])

if __name__=='__main__':run()
