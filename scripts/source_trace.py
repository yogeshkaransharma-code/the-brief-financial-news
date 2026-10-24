#!/usr/bin/env python3
"""Find first-party evidence linked by reputable financial-news reporting.

Secondary coverage is a DISCOVERY SIGNAL only. We never submit third-party
article text to Gemini, copy it onto our website or treat it as proof. A
published story must still pass the existing original-source evidence gate.
"""
from __future__ import annotations
import datetime as dt
import json
import re
from urllib.parse import urljoin, urlsplit, urlunsplit
import urllib.request
from bs4 import BeautifulSoup
from publication_scope import source_lane
from source_retrieval import retrieve_bytes

NEWS_HOSTS = {
    "finextra.com", "www.finextra.com",
    "insurancebusinessmag.com", "www.insurancebusinessmag.com",
    "commercialriskonline.com", "www.commercialriskonline.com",
    "bbc.co.uk", "www.bbc.co.uk", "bbc.com", "www.bbc.com",
    "news.sky.com", "theguardian.com", "www.theguardian.com",
    "ft.com", "www.ft.com", "bloomberg.com", "www.bloomberg.com",
    "wsj.com", "www.wsj.com", "marketwatch.com", "www.marketwatch.com",
    "economist.com", "www.economist.com",
}
UA = "TheBrief-SourceResearch/0.3 (citation tracing; no article reproduction)"
MAX_NEWS_BYTES = 800_000
REVIEW_LIMIT = 12
STOP = set("the a an of in for on at from by to is are will new says uk us and or as it with its report reports latest after amid over under against company firm firms financial insurance bank banking regulator industry group year month".split())
DATE_RE = re.compile(r"^20\d{2}-\d\d-\d\d(?:T[^ ]+)?")
BAD_LINK = re.compile(r"(?:advert|sponsor|privacy|terms|register|account|contact|careers|share|cookies|home|login)",re.I)

class NoExternalRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if not reputable(newurl):
            raise ValueError("Secondary article redirects outside the known news outlet")
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def reputable(url):
    p=urlsplit(url)
    return p.scheme=="https" and p.hostname in NEWS_HOSTS and not p.username and not p.password and p.port in (None,443)

def normal_url(url):
    p=urlsplit(url)
    return urlunsplit((p.scheme,p.netloc,p.path,p.query,""))

def meaningful_terms(text):
    return {x for x in re.findall(r"[a-z]{4,}",text.lower()) if x not in STOP}

def overlap(headline, link_label, official_url):
    terms=meaningful_terms(headline)
    context=meaningful_terms(link_label+" "+urlsplit(official_url).path.replace("-"," "))
    shared=terms & context
    # Two distinctive matching terms or one plus an explicit official-source
    # citation. A generic homepage/regulator footer isn't sufficient evidence.
    return len(shared)

def editorial_area(soup):
    return soup.find("article") or soup.find("main") or soup.select_one('[role="main"]') or soup

def extract_original_links(markup,news_url,title):
    """Return carefully ranked on-page citations, never broad site navigation."""
    soup=BeautifulSoup(markup,"html.parser")
    area=editorial_area(soup)
    for node in area.select("nav,header,footer,aside,script,style,form"):
        node.decompose()
    ranked={}
    for anchor in area.select("a[href]"):
        official=normal_url(urljoin(news_url,anchor.get("href","")))
        lane=source_lane(official)
        if not lane:continue
        label=" ".join(anchor.get_text(" ",strip=True).split())[:180]
        surrounding=anchor.parent.get_text(" ",strip=True)[:250] if anchor.parent else label
        if BAD_LINK.search(label) or BAD_LINK.search(urlsplit(official).path.split("/")[-1]):
            continue
        score=overlap(title,label+" "+surrounding,official)
        cite=bool(re.search(r"(?i)\b(source|original|press release|announcement|fca|pra|regulator|results|official|statement|report|published|consultation)\b",label))
        if score < 2 or (not cite and score<3):
            continue
        ranked[official]=max(ranked.get(official,0),score+(2 if cite else 0))
    return [u for u,_ in sorted(ranked.items(),key=lambda x:-x[1])[:3]]

def official_headline(markup):
    """Never allow a newspaper's framing to become the primary source title."""
    soup=BeautifulSoup(markup,"html.parser")
    title=soup.select_one("main h1, article h1, h1")
    if title:
        headline=" ".join(title.get_text(" ",strip=True).split())
        if 20<=len(headline)<=220:return headline
    for meta in soup.select('meta[property="og:title"][content]'):
        headline=" ".join(meta["content"].split())
        if 20<=len(headline)<=220:return headline
    return None

def published_date(markup):
    """Official source metadata only. No dates inherited from news coverage."""
    soup=BeautifulSoup(markup,"html.parser")
    candidates=[]
    for meta in soup.select("meta[content]"):
        prop=(meta.get("property") or meta.get("name") or meta.get("itemprop") or "").lower()
        if prop in {"article:published_time","datepublished","datecreated","pubdate","dc.date.issued","dc.date"}:
            candidates.append(meta.get("content",""))
    for node in soup.select('time[datetime]')[:8]:
        candidates.append(node.get("datetime",""))
    for node in soup.select('script[type="application/ld+json"]')[:6]:
        try:
            data=json.loads(node.string or node.get_text())
            stack=data if isinstance(data,list) else [data]
            for record in stack:
                if isinstance(record,dict):
                    candidates.append(record.get("datePublished",""))
                    if isinstance(record.get("@graph"),list):
                        candidates.extend(x.get("datePublished","") for x in record["@graph"] if isinstance(x,dict))
        except (TypeError,ValueError):
            pass
    for raw in candidates:
        raw=str(raw).strip()
        if not DATE_RE.match(raw):continue
        try:
            stamp=dt.datetime.fromisoformat(raw.replace("Z","+00:00"))
            precision="timestamp" if "T" in raw and stamp.tzinfo else "date"
            date=stamp.date().isoformat()
            return date,(stamp.astimezone(dt.timezone.utc).isoformat() if precision=="timestamp" else date+"T12:00:00+00:00"),precision
        except ValueError:
            continue
    return None

def get_reputable_page(url):
    if not reputable(url):raise ValueError("Not an approved news lead")
    opener=urllib.request.build_opener(NoExternalRedirects())
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html"})
    with opener.open(req,timeout=12) as response:
        final=response.geturl()
        if not reputable(final):raise ValueError("News URL redirected outside allowed hosts")
        if "html" not in response.headers.get("Content-Type","").lower():raise ValueError("News lead is not HTML")
        raw=response.read(MAX_NEWS_BYTES+1)
        if len(raw)>MAX_NEWS_BYTES:raise ValueError("News lead exceeds size limit")
        return raw,final

def find_originals(leads,now=None,limit=REVIEW_LIMIT):
    """Screen fresh third-party leads and return dated official originals.

    This is best-effort discovery. Missing citations, inaccessible pages, and
    ambiguous release dates are recorded, NOT worked around by speculation.
    """
    from fresh_sources import eligible_today
    now=now or dt.datetime.now(dt.timezone.utc)
    out=[]; events=[]; seen=set()
    fresh=[]
    for lead in leads:
        if reputable(lead.get("url","")) and eligible_today(lead,now):
            fresh.append(lead)
    # Focus on news about our remit; RSS "finance" streams include many distant
    # consumer and international announcements not relevant to UK readers.
    fresh.sort(key=lambda x:(
        0 if x.get("category") in ("Insurance","Regulation") else 1,
        -(dt.datetime.fromisoformat(x["published_at"].replace("Z","+00:00")).timestamp())
    ))
    for lead in fresh[:limit]:
        try:
            markup,real_url=get_reputable_page(lead["url"])
            urls=extract_original_links(markup,real_url,lead["title"])
            if not urls:
                events.append({"headline":lead["title"],"result":"no traceable original linked"})
                continue
            added=0
            for url in urls:
                if url in seen:continue
                try:
                    raw,ctype,final=retrieve_bytes(url,"text/html")
                    if "html" not in ctype or source_lane(final) is None:
                        continue
                    date=published_date(raw)
                    source_title=official_headline(raw)
                    if not source_title:
                        events.append({"headline":lead["title"],"result":"official headline could not be established"})
                        continue
                    if not date:
                        events.append({"headline":lead["title"],"result":"original date could not be independently established"})
                        continue
                    dateISO,published_at,precision=date
                    primary={"title":source_title,"url":final,"dateISO":dateISO,
                             "published_at":published_at,"source":urlsplit(final).hostname,
                             "source_time_precision":precision,"category":lead["category"],
                             "kind":"traced_primary_source","found_via":real_url}
                    if not eligible_today(primary,now):continue
                    out.append(primary);seen.add(final);added+=1
                    break
                except Exception as error:
                    events.append({"headline":lead["title"],"result":"original unavailable","reason":str(error)[:150]})
            if added:
                events.append({"headline":lead["title"],"result":"official source traced"})
            elif not any(x.get("headline")==lead["title"] for x in events):
                events.append({"headline":lead["title"],"result":"original not fresh or not readable"})
        except Exception as error:
            events.append({"headline":lead.get("title"),"result":"news lead inaccessible","reason":str(error)[:150]})
    return out,events

def self_test():
    base="https://www.finextra.com/newsarticle/48600/fca-publishes-bank-capital-consultation"
    official="https://www.fca.org.uk/news/press-releases/fca-publishes-bank-capital-consultation"
    html=("<article><h1>FCA publishes bank capital consultation</h1>"
          "<p>For source details, see the <a href='"+official+"'>FCA original announcement on bank capital consultation</a>.</p></article>").encode()
    urls=extract_original_links(html,base,"FCA publishes bank capital consultation")
    assert urls==[official],urls
    assert not reputable("https://www.finextra.com.evil.test/x")
    assert not reputable("http://www.finextra.com/x")
    assert reputable("https://www.bbc.co.uk/news/business-10000000")
    assert reputable("https://www.ft.com/content/1234")
    assert not reputable("https://www.ft.com.evil.test/content/1234")
    assert not extract_original_links(b'<article><a href="https://www.fca.org.uk/">FCA</a></article>',base,"Banks consider new approach")
    dated=b'<html><head><meta property="article:published_time" content="2026-10-24T09:30:00+01:00"></head></html>'
    assert published_date(dated)==("2026-10-24","2026-10-24T08:30:00+00:00","timestamp")
    assert published_date(b"<html>27 years ago</html>") is None
    assert official_headline(b"<main><h1>Company publishes original financial results for the quarter</h1></main>")=="Company publishes original financial results for the quarter"
    print("PASS: reputable-lead restrictions, citation relevance and official-only release dating")

if __name__=="__main__":
    self_test()
