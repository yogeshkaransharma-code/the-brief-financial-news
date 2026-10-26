"""Gemini's editorial selection from dated, retrieved source documents.

Discovery and date eligibility are deterministic safeguards. Gemini decides
newsworthiness and priority; its choices cannot introduce an unknown source.
Unchanged source pools reuse the recorded decision rather than spending again.
"""
import hashlib
import json
from ai_newsroom import same_development

def choose(verified,ledger,meter,ai,*,edition_date,max_stories=3):
    """Commission verified relevant developments without a significance veto.

    Full source/date gates run before this function. Writing and independent
    review still reject unsupported claims; overflow is deferred, never rejected.
    """
    from media_sources import diverse
    if not verified:return [],{'result':'NO_VERIFIED_CANDIDATES','requests':0,'selected':[],'skipped':[]}
    chosen=[];deferred=[]
    # Preserve the fair source ordering established by the retrieval stage.
    for item,doc in verified:
        if any(same_development(item,prior[0]) for prior in chosen):
            deferred.append({'url':item['url'],'reason':'Duplicate development in this batch','category':item['category']});continue
        if len(chosen)>=max_stories:
            deferred.append({'url':item['url'],'reason':'Per-run allowance; retained for next cycle','category':item['category']});continue
        chosen.append((item,doc))
    return chosen,{'result':'SELECTED' if chosen else 'DEFERRED','requests':0,'method':'deterministic-source-supported',
                   'selected':[{'url':i['url'],'category':i['category'],'reason':'Relevant current development supported by a complete accessible source'} for i,d in chosen],
                   'skipped':[],'deferred':deferred}

def validate_decision(response,candidates,max_stories):
    if not isinstance(response,dict) or not all(isinstance(response.get(k),list) for k in ('selected','skipped')):
        raise ValueError('Gemini editorial selection returned an invalid decision schema')
    decisions=response['selected']+response['skipped']
    ids=[]
    for row in decisions:
        if not isinstance(row,dict) or row.get('id') not in candidates or not isinstance(row.get('reason'),str) or len(row['reason'].strip())<10:
            raise ValueError('Gemini selected an unknown source or omitted its editorial reason')
        ids.append(row['id'])
    if len(set(ids))!=len(ids) or set(ids)!=set(candidates) or len(response['selected'])>max_stories:
        raise ValueError('Gemini selection omitted, duplicated or over-selected candidates')
    selected=[candidates[row['id']] for row in response['selected']]
    for i,(item,doc) in enumerate(selected):
        if any(same_development(item,prior[0]) for prior in selected[:i]):
            raise ValueError('Gemini selected duplicate developments')
    return selected


