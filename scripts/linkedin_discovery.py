"""Public search-indexed LinkedIn news leads; no LinkedIn login or feed scraping.

Search results are discovery metadata only. Only a separate accessible article
from the existing source registry can enter the writing pipeline.
"""
from __future__ import annotations
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit,urlencode,unquote
import urllib.request
import xml.etree.ElementTree as ET
from newsroom_state import atomic_json,cooling
from publication_scope import source_lane
from media_sources import canonical_url,publisher
from source_fallback import tokens

MODE='public_search_index_only'
LIMITATION='Partial public search-index coverage; not a LinkedIn feed, private-post access or complete company-page monitoring.'

def post_url(value):
    try:
        p=urlsplit(value)
        if p.scheme!='https' or p.username or p.password or p.port not in (None,443):return None
        if not re.fullmatch(r'(?:www\.|[a-z]{2,3}\.)?linkedin\.com',p.hostname or ''):return None
        path=unquote(p.path)
        if not (re.fullmatch(r'/(?:posts|pulse)/[^/?#]{10,}/?',path) or re.fullmatch(r'/feed/update/urn:li:(?:activity|share):\d+/?',path)):return None
        return urlunsplit(('https','www.linkedin.com',p.path.rstrip('/'),'',''))
    except (ValueError,TypeError):return None

def search_rows(query):
    """The public search index is the only HTTP origin contacted here."""
    url='https://www.bing.com/search?'+urlencode({'q':query,'format':'rss','count':20})
    class SearchRedirects(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,req,fp,code,msg,headers,newurl):
            p=urlsplit(newurl)
            if p.scheme!='https' or p.hostname!='www.bing.com':raise ValueError('Search redirected outside the discovery origin')
            return super().redirect_request(req,fp,code,msg,headers,newurl)
    req=urllib.request.Request(url,headers={'User-Agent':'TheBrief-PublicNewsDiscovery/1.0'})
    with urllib.request.build_opener(SearchRedirects()).open(req,timeout=10) as response:
        raw=response.read(500001)
    if len(raw)>500000:raise ValueError('Search index response exceeds size limit')
    return [{'title':(n.findtext('title') or '').strip(),'url':(n.findtext('link') or '').strip()}
            for n in ET.fromstring(raw).findall('.//item')][:20]

def clean_title(title):
    value=re.sub(r'\s*[|]\s*LinkedIn.*$','',str(title),flags=re.I)
    value=re.sub(r'\s+posted on the topic.*$','',value,flags=re.I)
    return re.sub(r'\s+',' ',value).strip()[:240]

def candidate(lead,row):
    """Search snippets and index dates must never become publication evidence."""
    url=canonical_url(row.get('url',''))
    if not source_lane(url) or post_url(url):return None
    title=clean_title(row.get('title',''))
    shared=tokens(lead['title']) & tokens(title)
    if len(shared)<2:return None
    return {'title':title,'url':url,'source':publisher(url) or urlsplit(url).hostname,
            'category':lead['desk'],'kind':'linkedin_discovery_lead',
            'discovery_method':'linkedin_public_search','source_date_unresolved':True,
            'source_time_precision':'unknown','dateISO':'','published_at':'',
            'found_via':lead['url'],'discovered_via':[lead['url']]}

def discover(root,now=None,*,search=search_rows):
    root=Path(root);now=now or dt.datetime.now(dt.timezone.utc)
    def read(path,default):
        try:return json.loads(path.read_text())
        except (OSError,ValueError):return default
    config=read(root/'data/source-registry.json',{}).get('linkedin_discovery',{})
    report={'mode':MODE,'limitation':LIMITATION,'checked_at':now.isoformat(),'enabled':bool(config.get('enabled')),
            'queries_checked':0,'queries_failed':0,'index_rows':0,'linkedin_posts_found':0,
            'new_posts_found':0,'resolution_searches':0,'matched_source_candidates':0,'events':[]}
    if not report['enabled']:return [],report
    state_path=root/'data/linkedin-discovery.json'
    state=read(state_path,{'queries':{},'leads':{}})
    queries=state.setdefault('queries',{});leads=state.setdefault('leads',{})
    due=[q for q in config.get('queries',[]) if not cooling(queries.get(q['id'],{}),now)]
    due.sort(key=lambda q:queries.get(q['id'],{}).get('checked_at',''))
    for q in due[:min(8,int(config.get('max_queries_per_run',4)))]:
        row={'checked_at':now.isoformat(),'retry_after':(now+dt.timedelta(minutes=60)).isoformat()}
        report['queries_checked']+=1
        try:
            results=search('site:linkedin.com/posts/ '+q['terms'])
            report['index_rows']+=len(results);found=0
            for result in results:
                url=post_url(result.get('url',''));title=clean_title(result.get('title',''))
                if not url or not title:continue
                found+=1
                if url not in leads:
                    leads[url]={'url':url,'title':title,'desk':q['desk'],'first_seen':now.isoformat(),'matched_sources':[]}
                    report['new_posts_found']+=1
                leads[url].update(last_seen=now.isoformat(),title=title)
            row.update(result='SEARCH_COMPLETED',posts_found=found)
            report['linkedin_posts_found']+=found
            report['events'].append({'query':q['id'],'result':'SEARCH_COMPLETED','index_rows':len(results),'posts_found':found})
        except Exception as error:
            row.update(result='SEARCH_FAILED',error=str(error)[:240],retry_after=(now+dt.timedelta(minutes=30)).isoformat())
            report['queries_failed']+=1
            report['events'].append({'query':q['id'],'result':'SEARCH_FAILED','reason':str(error)[:240]})
        queries[q['id']]=row
    cutoff=(now-dt.timedelta(days=7)).isoformat()
    leads={u:v for u,v in leads.items() if v.get('last_seen','')>=cutoff}
    # Each lead is resolved through normal publisher search, never by requesting
    # a LinkedIn page, an authenticated endpoint, a mirror or a post cache.
    pending=[v for v in leads.values() if not cooling({'retry_after':v.get('resolve_after')},now)]
    pending.sort(key=lambda v:v.get('last_resolution',''))
    for lead in pending[:min(8,int(config.get('max_resolutions_per_run',4)))]:
        lead['last_resolution']=now.isoformat();lead['resolve_after']=(now+dt.timedelta(hours=4)).isoformat()
        report['resolution_searches']+=1
        try:
            results=search(lead['title'][:180]+' -site:linkedin.com')
            matches=[value for row in results if (value:=candidate(lead,row))]
            lead['matched_sources']=matches[:2]
            lead['result']='SOURCE_CANDIDATES_FOUND' if matches else 'NO_ACCESSIBLE_SOURCE_LOCATED'
            report['events'].append({'post_url':lead['url'],'result':lead['result'],'source_candidates':len(lead['matched_sources'])})
        except Exception as error:
            lead['result']='SOURCE_SEARCH_FAILED';lead['resolve_after']=(now+dt.timedelta(minutes=30)).isoformat()
            report['events'].append({'post_url':lead['url'],'result':'SOURCE_SEARCH_FAILED','reason':str(error)[:240]})
    output=[];seen=set()
    for lead in sorted(leads.values(),key=lambda v:v['last_seen'],reverse=True):
        for item in lead.get('matched_sources',[]):
            if item['url'] in seen:continue
            output.append(item);seen.add(item['url'])
    output=output[:24]
    report['matched_source_candidates']=len(output)
    report['coverage_status']='UNAVAILABLE' if report['queries_checked'] and report['queries_failed']==report['queries_checked'] else 'PARTIAL_PUBLIC_INDEX'
    state.update(mode=MODE,limitation=LIMITATION,checked_at=now.isoformat(),queries=queries,leads=dict(list(leads.items())[-300:]),latest=report)
    atomic_json(state_path,state)
    atomic_json(root/'generated-drafts/linkedin-discovery-report.json',report)
    return output,report

if __name__=='__main__':
    # Read-only live integration probe: no writing model, article publication,
    # LinkedIn HTTP request or durable production state mutation.
    import tempfile,shutil
    base=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder);(root/'data').mkdir()
        shutil.copyfile(base/'data/source-registry.json',root/'data/source-registry.json')
        items,report=discover(root)
        print('LINKEDIN_PUBLIC_DISCOVERY:',json.dumps(report,ensure_ascii=False))
        print('LINKEDIN_MATCHED_SOURCES:',json.dumps(items,ensure_ascii=False))
        if not report['linkedin_posts_found']:
            for query in ['site:linkedin.com/posts insurance','site:linkedin.com/posts bank partnership','"LinkedIn" "Aviva" "insurance"']:
                try:print('LINKEDIN_SEARCH_DIAGNOSTIC:',json.dumps({'query':query,'rows':search_rows(query)[:5]}))
                except Exception as error:print('LINKEDIN_SEARCH_DIAGNOSTIC:',str(error))
            try:
                from bs4 import BeautifulSoup
                url='https://html.duckduckgo.com/html/?'+urlencode({'q':'site:linkedin.com/posts insurance partnership'})
                req=urllib.request.Request(url,headers={'User-Agent':'TheBrief-PublicNewsDiscovery/1.0'})
                with urllib.request.urlopen(req,timeout=10) as response:
                    raw=response.read(500000)
                    print('LINKEDIN_SECOND_INDEX_STATUS:',response.status)
                soup=BeautifulSoup(raw,'html.parser')
                print('LINKEDIN_SECOND_INDEX_RESULTS:',json.dumps([{'title':a.get_text(' ',strip=True),'url':a.get('href')} for a in soup.select('a.result__a')][:5]))
                print('LINKEDIN_SECOND_INDEX_TITLE:',soup.title.get_text(' ',strip=True) if soup.title else '')
            except Exception as error:print('LINKEDIN_SECOND_INDEX_ERROR:',str(error))
