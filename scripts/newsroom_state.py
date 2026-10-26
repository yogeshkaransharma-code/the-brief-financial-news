"""Atomic, resumable checkpoints and classified, bounded retry policy.

Full sources stay in restricted Actions evidence artifacts, never in Pages or
the public Git repository. Only attempt metadata is committed to data/.
"""
from __future__ import annotations
from dataclasses import asdict
import datetime as dt
import hashlib
import json
from pathlib import Path
import urllib.error

POLICY = 'newsroom-recovery-2026-10-26-v1'

def atomic_json(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temp.replace(path)

def identity(url):
    return hashlib.sha256(url.encode()).hexdigest()[:20]

def classify(error):
    code=getattr(error,'code',getattr(error,'status',None));text=str(error).lower()
    if code in {401,402,403,451} or any(x in text for x in ('http error 403','paywall','access restricted')):
        return 'ACCESS_RESTRICTED'
    if code in {404,410}:return 'NOT_FOUND'
    if code==429:return 'RATE_LIMITED'
    if code in {500,502,503,504} or isinstance(error,(TimeoutError,ConnectionError,OSError)):
        return 'TEMPORARY_FAILURE'
    if any(x in text for x in ('date','today','announced')):return 'DATE_UNVERIFIED'
    if any(x in text for x in ('content','capture','document','source','pdf')):return 'EVIDENCE_UNUSABLE'
    return 'INVALID_RESPONSE'

def defer(attempts,url,error,now,stage='source'):
    previous=attempts.get(url,{})
    kind=classify(error);count=min(int(previous.get('failures',0))+1,8)
    minutes={'ACCESS_RESTRICTED':360,'NOT_FOUND':1440,'DATE_UNVERIFIED':120,
             'EVIDENCE_UNUSABLE':240,'RATE_LIMITED':30}.get(kind,min(15*2**(count-1),240))
    retry=getattr(error,'retry_seconds',None)
    if retry and kind=='RATE_LIMITED':minutes=max(1,min(float(retry)/60,1440))
    record={'attempted_at':now.isoformat(),'retry_after':(now+dt.timedelta(minutes=minutes)).isoformat(),
            'last_result':str(error)[:360],'classification':kind,'stage':stage,'failures':count,'policy':POLICY}
    attempts[url]=record
    return record

def cooling(record,now):
    try:return dt.datetime.fromisoformat(record['retry_after'])>now
    except (KeyError,TypeError,ValueError):return False

class Checkpoints:
    def __init__(self,folder):
        self.folder=Path(folder)/'checkpoints';self.folder.mkdir(parents=True,exist_ok=True)
    def read(self,url):
        try:
            value=json.loads((self.folder/(identity(url)+'.json')).read_text())
            doc=value['document']
            if value.get('policy')!=POLICY or doc['url']!=url:return None
            if hashlib.sha256(doc['text'].encode()).hexdigest()!=doc['evidence_sha256']:return None
            return value
        except (OSError,ValueError,KeyError,TypeError):return None
    def save(self,item,document,**state):
        value=self.read(item['url']) or {}
        value.update(policy=POLICY,item=item,document=asdict(document),**state)
        atomic_json(self.folder/(identity(item['url'])+'.json'),value)
        return value

def restore(archive,destination):
    """Only bounded checkpoint/bundle JSON; never overwrite reports or code."""
    import zipfile
    destination=Path(destination);count=0;total=0
    with zipfile.ZipFile(archive) as source:
        for entry in source.infolist():
            path=Path(entry.filename)
            allowed=(len(path.parts)==2 and path.parts[0]=='checkpoints') or (len(path.parts)==1 and path.name.startswith('ai-'))
            if not allowed or path.is_absolute() or '..' in path.parts or path.suffix!='.json':continue
            total+=entry.file_size
            if entry.file_size>2_000_000 or total>30_000_000:raise ValueError('Recovery artifact exceeds limits')
            value=json.loads(source.read(entry))
            atomic_json(destination/path,value);count+=1
    return count

if __name__=='__main__':
    import sys
    print('RECOVERED_CHECKPOINTS:',restore(sys.argv[1],sys.argv[2]))
