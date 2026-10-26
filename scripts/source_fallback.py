"""Legitimate alternative evidence, never a workaround for publisher restrictions."""
from __future__ import annotations
import re
from urllib.parse import urlsplit
from media_sources import canonical_url
from publication_scope import source_lane

STOP=set('a an the of for to in on and with from by as at is are new uk says said announces announced report reports launches launch expands expand'.split())

def tokens(title):
    return {x for x in re.findall(r'[a-z0-9]+',title.lower()) if len(x)>2 and x not in STOP}

def alternatives(item,pool,limit=3):
    """Discovery similarity proposes a lead; full content/date gates still decide.

    Alternative reports may use a different headline and date. Their own actual
    publication date is mandatory, so yesterday's announcement cannot be relabelled.
    """
    original=canonical_url(item['url']);words=tokens(item.get('title',''));ranked=[];seen={original}
    for row in pool:
        url=canonical_url(row.get('url',''))
        if url in seen or not source_lane(url):continue
        seen.add(url);other=tokens(row.get('title',''));shared=words & other
        score=len(shared)/max(1,min(len(words),len(other)))
        if len(shared)>=3 and score>=0.5:
            ranked.append((score,dict(row,url=url)))
    return [row for _,row in sorted(ranked,key=lambda x:x[0],reverse=True)[:limit]]

def search_alternatives(item,limit=3):
    """Public search RSS is discovery only; only reviewed publisher routes pass.

    No cached article, proxy reader, AMP mirror, login or paywall bypass is used.
    Search dates/excerpts never establish an article's eligibility.
    """
    import urllib.request
    import urllib.parse
    import xml.etree.ElementTree as ET
    query=item.get('title','')[:180]
    url='https://www.bing.com/search?'+urllib.parse.urlencode({'q':query,'format':'rss'})
    request=urllib.request.Request(url,headers={'User-Agent':'TheBriefResearch/0.3 (alternative-source discovery)'})
    with urllib.request.urlopen(request,timeout=10) as response:
        if urlsplit(response.geturl()).hostname!='www.bing.com':raise ValueError('Search redirected outside discovery origin')
        raw=response.read(500001)
    if len(raw)>500000:raise ValueError('Search discovery response exceeds limit')
    rows=[];seen={canonical_url(item['url'])}
    for node in ET.fromstring(raw).findall('.//item'):
        link=canonical_url(node.findtext('link') or '')
        if link in seen or not source_lane(link):continue
        seen.add(link)
        rows.append(dict(item,title=node.findtext('title') or item['title'],url=link,discovery_method='alternative-search',source=publisher_name(link)))
        if len(rows)>=limit:break
    return rows

def publisher_name(url):
    from media_sources import publisher
    return publisher(url) or urlsplit(url).hostname
