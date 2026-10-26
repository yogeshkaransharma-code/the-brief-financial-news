"""Resumable source-to-review runner. Publication remains a separate gate."""
from __future__ import annotations
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import json
from pathlib import Path
import os

from ai_cost_guard import CallBudget, BudgetExhausted, preflight_source
from ai_newsroom import same_development, GeminiAPIError
from editorial_selection import choose
from first_party_sources import discover
from fresh_sources import eligible_today
from media_sources import canonical_url, relevant, diverse, publisher
from model_providers import fetch_ai, ACTIVE_MODEL
from newsroom_batches import draft_batch, review_batch
from newsroom_state import Checkpoints, atomic_json, classify, cooling, defer, identity, POLICY
from publication_scope import source_lane
from same_day_policy import clock
from site_design import desk_for
from source_dates import verify_announcement
from source_fallback import alternatives, search_alternatives
from source_retrieval import Source, read_source
from source_trace import find_originals

def read_json(path,default):
    try:return json.loads(Path(path).read_text())
    except (OSError,ValueError):return default

def run(root=None,now=None,*,discovery=discover,trace=find_originals,reader=read_source,ai=fetch_ai,search=search_alternatives,single_pass=True):
    root=Path(root or Path(__file__).resolve().parents[1]);out=root/'generated-drafts'
    out.mkdir(parents=True,exist_ok=True);now=now or dt.datetime.now(dt.timezone.utc)
    events=[];metrics=Counter();checkpoints=Checkpoints(out)
    ledger_path=root/'data/newsroom-attempts.json';ledger=read_json(ledger_path,{'version':2,'sources':{}})
    attempts=ledger.setdefault('sources',{});meter=CallBudget(ledger,now,path=ledger_path)
    if ledger.get('sentence_segmenter')!=2:
        for url in list(attempts):
            if attempts[url].get('last_result')=='Incomplete evidence record':
                attempts.pop(url)
        ledger['sentence_segmenter']=2
    # One-time recovery from the old transport adapter rejecting JSON arrays.
    # Preserve source checkpoints and the already-charged request reservation.
    if ledger.get('batch_schema_version')!=1:
        for url in list(attempts):
            if 'malformed article response' in attempts[url].get('last_result',''):
                attempts.pop(url)
        ledger['batch_schema_version']=1
    def event(item,result,stage,reason='',**extra):
        row={'title':item.get('title','Pipeline'),'source':item.get('url'),'result':result,'stage':stage,'reason':str(reason)[:500],**extra}
        events.append(row);return row
    def persist():atomic_json(ledger_path,ledger)
    def failure(item,stage,error):
        rec=defer(attempts,item['url'],error,now,stage);persist()
        event(item,'held back',stage,error,classification=rec['classification'],retry_after=rec['retry_after'])
    def call(prompt):
        response=meter.call(ai,prompt,purpose='single_pass_writing' if single_pass else 'production')
        atomic_json(out/'model-responses'/('response-'+str(meter.run_used)+'.json'),response)
        return response
    items=read_json(root/'data/live.json',{}).get('items',[])
    try:first,errors=discovery()
    except Exception as error:first=[];errors=[str(error)];event({},'discovery failed','discovery',error)
    # Secondary journalism is directly eligible. Citation tracing supplements
    # supply only; it never vetoes a credible publisher's own reporting.
    try:traced,trace_events=trace(items,now,limit=12,attempts=ledger.setdefault('research_leads',{}))
    except Exception as error:traced=[];trace_events=[{'result':'trace failed','reason':str(error)}]
    existing=read_json(root/'data/articles.json',[]);published={canonical_url(a['url']) for a in existing}
    retired=set(read_json(root/'data/retired-source-urls.json',{}).get('urls',[]))
    pool={}
    for raw in first+traced+items:
        if not isinstance(raw,dict) or not raw.get('url'):continue
        item=dict(raw,url=canonical_url(raw['url']))
        pool.setdefault(item['url'],item)
    metrics['discovered_unique']=len(pool)
    candidates=[]
    for item in pool.values():
        if item['url'] in published|retired:
            metrics['already_published_or_retired']+=1;event(item,'excluded','eligibility','Already published or retired');continue
        if not source_lane(item['url']):
            metrics['unsupported_route']+=1;event(item,'excluded','eligibility','No reviewed article route in source registry');continue
        if not relevant(item):
            metrics['irrelevant']+=1;event(item,'rejected','eligibility','Outside Insurance/Banking or promotional/lifestyle material');continue
        # RSS dateModified is only a discovery clue, never proof of freshness.
        # Verify the document itself below even for undated/modified leads.
        if not eligible_today(item,now):
            metrics['outside_uk_date']+=1;event(item,'excluded','eligibility','Discovery source date is outside the current UK date',source_date=item.get('dateISO'));continue
        if any(same_development(item,a) and a.get('dateISO')==item.get('dateISO') for a in existing):
            metrics['published_development']+=1;event(item,'duplicate','eligibility','Same development already published');continue
        item['internal_category']=item.get('category');item['category']=desk_for(item)
        candidates.append(item)
    metrics['fresh_relevant_candidates']=len(candidates)
    # Sample fairly and retain all overflow candidates in the discovery ledger.
    sampled=diverse(candidates,40)
    for item in candidates:
        if item not in sampled:event(item,'deferred','source','Bounded source-read allowance; retained for next run')
    def capture(item):
        cached=checkpoints.read(item['url'])
        try:
            if cached:
                doc=Source(**cached['document']);item=verify_announcement(cached['item'],doc,now)
                preflight_source(item,doc)
                return item,doc,None,'checkpoint'
            if cooling(attempts.get(item['url'],{}),now):
                return item,None,None,'cooldown'
            doc=reader(item['url']);original=item['url']
            if doc.url!=original:
                from urllib.parse import urlsplit
                same_host=urlsplit(original).hostname.removeprefix('www.')==urlsplit(doc.url).hostname.removeprefix('www.')
                same_publisher=publisher(original) and publisher(original)==publisher(doc.url)
                if not (same_host or same_publisher) or not source_lane(doc.url):raise ValueError('Redirect changed source identity or article route')
                item=dict(item,url=doc.url,discovered_url=original)
            preflight_source(item,doc);item=verify_announcement(item,doc,now)
            return item,doc,None,'retrieved'
        except Exception as error:return item,None,error,'failed'
    with ThreadPoolExecutor(max_workers=6) as executor:captures=list(executor.map(capture,sampled))
    verified=[];seen=set();fallback_events=[];searches=0
    for item,doc,error,method in captures:
        if error:failure(item,'source',error);metrics['source_failures']+=1
        elif method=='cooldown':
            record=attempts[item['url']];event(item,'retry deferred','source',record.get('last_result',''),classification=record.get('classification','LEGACY_COOLDOWN'),retry_after=record.get('retry_after'));metrics['source_cooldowns']+=1
        if doc is None:
            # Match across all discovery lanes, including dated original releases.
            # Every alternative must independently pass the SAME content/date gates.
            choices=alternatives(item,list(pool.values()))
            record=attempts.get(item['url'],{})
            due=not cooling({'retry_after':record.get('alternative_search_after')},now)
            if searches<3 and due:
                searches+=1
                try:
                    choices+=search(item,limit=3)
                    fallback_events.append({'source':item['url'],'result':'Public alternative search completed','candidates':len(choices)})
                except Exception as error:
                    fallback_events.append({'source':item['url'],'result':'Alternative search unavailable','reason':str(error)[:250]})
                record['alternative_search_after']=(now+dt.timedelta(hours=4)).isoformat()
                attempts[item['url']]=record;persist()
            fallback_events.append({'source':item['url'],'alternatives_found':len(choices),'result':'No matching alternative in checked sources' if not choices else 'Alternative retrieval attempted'})
            for alt in choices:
                if alt['url'] in seen or alt['url'] in published|retired:continue
                alt=dict(alt,category=desk_for(alt),fallback_for=item['url'])
                other,doc,err,method=capture(alt)
                if err:failure(other,'alternative_source',err);continue
                if doc:
                    event(other,'alternative verified','source','Accessible alternative passed original-document date/content checks',fallback_for=item['url']);item=other;break
            if doc is None:continue
        metrics['sources_successfully_retrieved']+=int(method=='retrieved')
        metrics['source_checkpoints_reused']+=int(method=='checkpoint')
        if item['url'] in published|retired or item['url'] in seen:
            event(item,'duplicate','source','Canonical source already published or captured');continue
        seen.add(item['url']);cached=checkpoints.read(item['url'])
        if not cached or cached['document']['evidence_sha256']!=doc.evidence_sha256:
            checkpoints.save(item,doc,status='captured',article=None,bundle=None)
        verified.append((item,doc));event(item,'source verified','source','Complete captured source; original UK publication date validated',source_sha256=doc.evidence_sha256,capture_method=method)
    metrics['verified_original_candidates']=len(verified)
    if single_pass:
        from single_pass import process
        selection=process(verified,root=root,out=out,checkpoints=checkpoints,ledger=ledger,meter=meter,now=now,call=call,event=event,metrics=metrics,failure=failure,persist=persist)
        work=verified
    else:
        # Recover clean bundles before considering cooldowns or model quota.
        work=[]
        for item,doc in verified:
            state=checkpoints.read(item['url']) or {}
            if not state.get('article'):
                from newsroom_v2 import make_article
                for file in (root/'editorial/draft-recovery').glob('*.json'):
                    recovery=read_json(file,{})
                    if recovery.get('source_url')==item['url'] and recovery.get('source_sha256')==doc.evidence_sha256:
                        try:
                            article=make_article(recovery['writer_response'],item,doc)
                            state=checkpoints.save(item,doc,status='drafted',article=article)
                            attempts.pop(item['url'],None)
                            event(item,'draft recovered','recovery','Original saved model response revalidated; independent review still required')
                        except (ValueError,KeyError,TypeError) as error:
                            event(item,'recovery held','recovery',error)
            if state.get('status')=='reviewed' and state.get('bundle'):
                atomic_json(out/('ai-'+identity(item['url'])+'.json'),state['bundle'])
                metrics['reviews_recovered']+=1;event(item,'draft recovered','recovery','Saved reviewed bundle sent to the final publication gate');continue
            if state.get('status')=='held' and state.get('review_policy',1)>=2:
                event(item,'held for review','independent_review',state.get('reason','Unsupported claims; unchanged evidence is not rewritten hourly'));continue
            if state.get('status')=='held':
                event(item,'review retry','independent_review','One re-review under publisher-provenance policy 2; no claims bypassed')
            if cooling(attempts.get(item['url'],{}),now):
                event(item,'retry deferred',attempts[item['url']].get('stage','model'),attempts[item['url']].get('last_result',''),retry_after=attempts[item['url']].get('retry_after'));continue
            work.append((item,doc))
        selected,selection=choose(work,ledger,meter,ai,edition_date=clock(now).date().isoformat(),max_stories=9)
        # A bounded batch of three uses one writer and one separate reviewer call.
        # Already-written articles need only their outstanding review request.
        model_failures=0
        for start in range(0,len(selected),3):
            batch=selected[start:start+3];pending=[];needs=[]
            for item,doc in batch:
                saved=checkpoints.read(item['url']) or {}
                if saved.get('article'):
                    pending.append((item,doc,saved['article']));metrics['drafts_recovered']+=1
                else:needs.append((item,doc))
            paused=cooling({'retry_after':ledger.get('quota_pause_until')},now)
            needed=int(bool(needs))+1
            if paused or meter.remaining()<needed or model_failures>=2:
                for item,doc in batch:event(item,'deferred','model','Provider cooldown' if paused else 'Reserved draft/review allowance unavailable; checkpoint retained')
                metrics['model_deferred']+=len(batch);continue
            stage='writing'
            def written(item,doc,article):
                checkpoints.save(item,doc,status='drafted',article=article)
                pending.append((item,doc,article));metrics['articles_drafted']+=1
                event(item,'drafted','writing','Original article saved before independent review')
            def reviewed(item,doc,article,bundle,passed):
                checkpoints.save(item,doc,status='reviewed' if passed else 'held',article=article,bundle=bundle,review_policy=2,reason='; '.join(x.get('reason','') for x in bundle.get('editorial_flags',[])))
                atomic_json(out/(('' if passed else 'HOLD-')+article['id']+'.json'),bundle)
                if passed:
                    attempts.pop(item['url'],None);metrics['articles_passing_review']+=1
                    event(item,'draft saved','independent_review','Every sentence passed separate source-evidence review; final publication gate follows')
                else:
                    metrics['review_rejected']+=1;event(item,'held for review','independent_review',bundle.get('editorial_flags'))
                persist()
            try:
                if needs:draft_batch(needs,call,written,failure)
                stage='independent_review'
                if pending:review_batch(pending,call,reviewed,failure)
            except Exception as error:
                model_failures+=1
                for item,doc in batch:failure(item,stage,error)
                if isinstance(error,GeminiAPIError) and error.status==429:
                    from newsroom_v2 import next_quota_check
                    ledger['quota_pause_until']=next_quota_check('daily limit' if error.daily else str(error),now).isoformat()
                # Continue source/report processing and other bounded batches after
                # one temporary model error. Completed drafts survive for review.
                persist()
    ledger['sources']={url:value for url,value in attempts.items() if value.get('attempted_at','')>=(now-dt.timedelta(days=7)).isoformat()}
    ledger['version']=2;persist()
    coverage=read_json(out/'primary-discovery.json',[])
    from source_health import update as update_health
    atomic_json(root/'data/source-health.json',update_health(read_json(root/'data/source-health.json',{}),read_json(root/'data/live.json',{}),coverage,events,now))
    report={'generated_at':now.isoformat(),'policy':__import__('single_pass').POLICY if single_pass else POLICY,'model':ACTIVE_MODEL,
      'machine_screened':metrics['articles_passing_review']+metrics['reviews_recovered'],'independent_review':not single_pass,'articles_ready_to_publish':metrics['articles_ready_to_publish'],
      'api_budget':meter.snapshot(),'metrics':dict(metrics),'ai_policy':'Single-pass source-based writing; no independent AI review' if single_pass else 'Legacy writing plus independent review',
      'first_party_indexes_checked':len(coverage),'first_party_discovery_errors':errors,
      'fresh_unpublished_source_candidates':len(candidates),'available_after_retry_cooldowns':len(work),
      'eligible_for_this_run':len(sampled),'verified_original_candidates':len(verified),
      'candidates_by_sector':dict(Counter(i['category'] for i in candidates)),
      'verified_by_sector':dict(Counter(i['category'] for i,d in verified)),
      'editorial_selection':selection,'original_source_trace':trace_events,'source_fallbacks':fallback_events,
      'active_quota_pause_until':ledger.get('quota_pause_until') if cooling({'retry_after':ledger.get('quota_pause_until')},now) else None,
      'items_checked':events}
    atomic_json(out/'run-report.json',report)
    print('NEWSROOM_PIPELINE_METRICS:',json.dumps(report['metrics'],sort_keys=True))
    print('NEWSROOM_SOURCE_FALLBACKS:',json.dumps(fallback_events,ensure_ascii=False))
    print('NEWSROOM_MODEL_BUDGET:',json.dumps(meter.snapshot()))
    return report
