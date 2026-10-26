"""Live HTTP evidence: same-day edition AND historical routes. Never equate empty with published."""
import datetime as dt
import html
import json
import os
import re
from pathlib import Path
import sys
import time
import urllib.request
from same_day_policy import published_same_day,clock
ROOT=Path(__file__).resolve().parents[1]
SITE=os.getenv('BRIEF_SITE_URL','https://yogeshkaransharma-code.github.io/the-brief-financial-news/').rstrip('/')+'/'

def read(url):
    req=urllib.request.Request(url,headers={'User-Agent':'TheBrief-LiveHealth/2.0','Cache-Control':'no-cache'})
    with urllib.request.urlopen(req,timeout=20) as r:return r.read(3000000).decode('utf-8')

def probe():
    canonical=json.loads((ROOT/'data/articles.json').read_text())
    want={a['id'] for a in canonical if published_same_day(a)}
    failure='No response'
    for attempt in range(6):
        try:
            token='?check='+str(int(time.time()))
            home=read(SITE+token)
            current_home=re.sub(r'<section id="launch-edition".*?</section>','',home,flags=re.S)
            if 'id="launch-edition"' in home:assert 'Prepared retrospectively; actual publication times' in home
            today=json.loads(read(SITE+'data/articles.json'+token))
            archive=json.loads(read(SITE+'data/archive.json'+token))
            if '--monitor' in sys.argv:
                # Check the deployed edition against its own build clock.
                # A 00:03 monitor may see the prior day's valid artifact
                # before the first scheduled newsroom refresh. That is
                # NOT evidence of a false-dated article. The existing
                # three-hour staleness check still catches a stuck handover.
                canonical=archive
                build_info=json.loads(read(SITE+'data/build.json'+token))
                artifact_clock=dt.datetime.fromisoformat(build_info['built_at'])
                assert artifact_clock.tzinfo is not None,'Undated deployed build'
                want={a['id'] for a in canonical if published_same_day(a,artifact_clock)}
            assert {a['id'] for a in today}==want,'Live edition differs from eligible same-day articles'
            assert {a['id'] for a in archive}=={a['id'] for a in canonical},'Live archive has missing articles'
            assert all(published_same_day(a) for a in today),'Old article leaked into today'
            assert 'archive.html' in home,'Archive navigation missing'
            for a in canonical:
                if a['id'] not in want:assert html.escape(a['title'],quote=True) not in current_home,'Old headline in today edition'
            archive_page=read(SITE+'archive.html'+token)
            for a in archive:assert html.escape(a['title'],quote=True) in archive_page,'Archived headline missing'
            tested=[]
            selection=today+([archive[0]] if archive and (not today or archive[0]['id']!=today[0]['id']) else [])
            for a in selection:
                story=read(SITE+'story/'+a['id']+'.html'+token)
                assert html.escape(a['title'],quote=True) in story,'Article heading absent'
                assert html.escape(a['url'],quote=True) in story,'Original source link absent'
                assert all(html.escape(p,quote=True) in story for _,p in a['blocks']),'Full article paragraphs missing'
                tested.append(a['id'])
            if not today:assert 'No verified news from today yet' in home,'Empty edition misleading'
            assert 'insurance.html' in home and 'banking.html' in home,'Section navigation missing'
            assert 'href="status.html"' not in home and 'href="hourly.html"' not in home,'Internal/duplicate pages still linked'
            assert '.tb-sector-visual' in read(SITE+'assets/site.css'+token),'Shared visual identity missing'
            for section in ['Insurance','Banking']:
                sector_page=read(SITE+section.lower()+'.html'+token)
                assert '<h1>'+section+'.</h1>' in sector_page,'Sector page missing'
                assert 'class="tb-header"' in sector_page,'Sector page branding missing'
            about=read(SITE+'about.html'+token)
            assert 'class="tb-header"' in about and 'status.html' not in about,'About page has wrong navigation'
            state=json.loads(read(SITE+'data/status.json'+token))
            if os.getenv('GITHUB_RUN_ID') and '--monitor' not in sys.argv:
                build=json.loads(read(SITE+'data/build.json'+token))
                assert build['run_id']==os.environ['GITHUB_RUN_ID'],'Live site is still serving an earlier deployment'
            assert 'id="publisher-desk"' not in home,'External publisher headline panel is still live'
            assert state.get('outcome') in {'PUBLISHED','NO_QUALIFYING_NEWS','BLOCKED','DEGRADED'},'Unknown newsroom outcome'
            if '--monitor' in sys.argv:
                age=dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(state['checked_at'])
                assert age<dt.timedelta(hours=3),'Newsroom monitoring stale for more than three hours'
                assert state['outcome'] not in {'BLOCKED','DEGRADED'},'Latest newsroom outcome needs attention: '+state['outcome']
            print('LIVE_READER_HTTP_OK: '+json.dumps({'uk_date':clock().date().isoformat(),'today':len(today),'archive':len(archive),'full_articles_tested':tested,'newsroom_outcome':state['outcome'],'publication_success':state['outcome']=='PUBLISHED'}))
            return
        except Exception as e:
            failure=str(e);print('Live check attempt',attempt+1,type(e).__name__,failure,flush=True)
            if attempt<5:time.sleep(8)
    raise RuntimeError('Live website verification failed: '+failure)
if __name__=='__main__':probe()

