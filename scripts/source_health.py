"""Persistent observed accessibility per discovery endpoint and article host."""
from urllib.parse import urlsplit

def update(previous,feeds,coverage,events,now):
    records=previous.get('sources',{})
    def record(key,ok,reason='',candidates=0):
        row=records.setdefault(key,{'successes':0,'failures':0,'candidates':0})
        row['successes' if ok else 'failures']+=1;row['candidates']+=candidates
        row['last_checked']=now.isoformat();row['last_result']='accessible' if ok else str(reason)[:300]
        if ok:row['last_success']=now.isoformat()
    for row in feeds.get('sources_checked',[]):record(row['url'],True,candidates=row.get('items',0))
    for row in feeds.get('errors',[]):
        if isinstance(row,dict) and row.get('url'):record(row['url'],False,row.get('error'))
    for row in coverage:
        record(row['url'],row.get('result')=='read',row.get('reason',''),row.get('candidates',0))
    for row in events:
        if row.get('stage')!='source' or not row.get('source'):continue
        key='article-host:'+str(urlsplit(row['source']).hostname)
        if row['result']=='source verified' and row.get('capture_method')=='retrieved':record(key,True,candidates=1)
        elif row['result']=='held back':record(key,False,row.get('classification') or row.get('reason'))
    return {'checked_at':now.isoformat(),'sources':records,
            'needs_supplement':[k for k,v in records.items() if v['failures']>=3 and v['failures']>v['successes']*2],
            'note':'Observed discovery and full-article access are separate. A working RSS feed does not establish article accessibility.'}
