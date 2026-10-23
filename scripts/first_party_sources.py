#!/usr/bin/env python3
"""Read limited first-party financial company newsrooms, not third-party media."""
from __future__ import annotations
import datetime as dt
import re
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
from source_retrieval import retrieve_bytes

INDEXES=(
    ("Aviva","Insurance","https://www.aviva.com/newsroom/"),
    ("Lloyds Banking Group","Banking","https://www.lloydsbankinggroup.com/media/press-releases.html"),
    ("UK Parliament","Regulation","https://committees.parliament.uk/committee/697/financial-services-regulation-committee/news/"),
)
MON={"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"sept":9,"oct":10,"nov":11,"dec":12}
DATE=re.compile(r"\b([0-3]?\d)\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+(20\d\d)\b",re.I)

def official_release(url, source):
    p=urlsplit(url)
    if p.scheme!="https" or p.username or p.password:return False
    if source=="Aviva":
        return p.hostname in {"www.aviva.com","aviva.com"} and "/newsroom/news-and-research-overview/news-releases/" in p.path
    if source=="UK Parliament":
        return p.hostname=="committees.parliament.uk" and bool(re.fullmatch(
            r"/committee/697/financial-services-regulation-committee/news/\d+/[a-z0-9-]+/?",p.path
        ))
    return p.hostname in {"www.lloydsbankinggroup.com","lloydsbankinggroup.com"} and "/media/press-releases/" in p.path and p.path.endswith(".html")

def parse_listing(content,source,section,base,today=None):
    today=today or dt.datetime.now(dt.timezone.utc).date()
    soup=BeautifulSoup(content,"html.parser")
    found=[]
    for anchor in soup.select("a[href]"):
        url=urljoin(base,anchor["href"]).split("#")[0]
        if not official_release(url,source):continue
        title=" ".join(anchor.get_text(" ",strip=True).split())
        if source=="UK Parliament":
            # Listings often wrap a heading, summary and calendar date inside
            # the same link; take the actual headline, not concatenated prose.
            heading=anchor.find(re.compile(r"^h[1-6]$"))
            if heading:
                title=" ".join(heading.get_text(" ",strip=True).split())
            else:
                title=re.split(r"\s+The Financial Services Regulation Committee\s+",title,maxsplit=1)[0]
        if not 25<=len(title)<=190 or title.lower() in {"read more","read press release"}:continue
        node=anchor
        date=None
        for _ in range(4):
            if not getattr(node,"parent",None):break
            node=node.parent
            context=" ".join(node.get_text(" ",strip=True).split())[:1100]
            m=DATE.search(context)
            if m and len(context)<900:
                try:
                    date=dt.date(int(m.group(3)),MON[m.group(2)[:4].lower()] if m.group(2).lower().startswith("sept") else MON[m.group(2)[:3].lower()],int(m.group(1)))
                    break
                except (KeyError,ValueError):pass
        if not date or not 0<=(today-date).days<=21:continue
        effective_category=("Insurance" if source=="UK Parliament" and re.search(r"insurance|claims|underwriting|protection",title,re.I) else section)
        found.append({"title":title,"url":url,"dateISO":date.isoformat(),"published_at":date.isoformat()+"T12:00:00+00:00",
                      "source":source,"category":effective_category,"kind":"first_party_announcement","source_time_precision":"date"})
    unique={}
    for entry in found:
        unique.setdefault(entry["url"],entry)
    return list(unique.values())

def discover():
    items=[]
    problems=[]
    for source,category,url in INDEXES:
        try:
            raw,ctype,final=retrieve_bytes(url)
            if "html" not in ctype:raise ValueError("Index is not HTML")
            records=parse_listing(raw,source,category,final)
            items.extend(records)
            print(f"FIRST_PARTY_DISCOVERY {source}: {len(records)} recent original announcements")
        except Exception as e:
            problems.append(f"{source}: {type(e).__name__} {str(e)[:100]}")
    return items,problems

def self_test():
    raw=b'''<main><section><h2><a href="/newsroom/news-and-research-overview/news-releases/2026/10/example-insurance-update/">Aviva launches new insurance service for customers</a></h2><p>16 Oct 2026</p></section></main>'''
    found=parse_listing(raw,"Aviva","Insurance","https://www.aviva.com/newsroom/",today=dt.date(2026,10,23))
    assert len(found)==1 and found[0]["dateISO"]=="2026-10-16",found
    assert not official_release("https://www.aviva.com.evil.com/newsroom/news-and-research-overview/news-releases/2026/10/x","Aviva")
    parliament=b'''<section><a href="/committee/697/financial-services-regulation-committee/news/218442/financial-services-regulation-committee-publishes-report-on-home-and-travel-insurance-regulation/"><h3>Financial Services Regulation Committee publishes report on home and travel insurance regulation</h3><p>23 October 2026</p></a></section>'''
    p=parse_listing(parliament,"UK Parliament","Regulation","https://committees.parliament.uk/committee/697/financial-services-regulation-committee/news/",today=dt.date(2026,10,23))
    assert len(p)==1 and p[0]["dateISO"]=="2026-10-23" and p[0]["category"]=="Insurance",p
    assert not official_release("https://committees.parliament.uk.evil.com/committee/697/financial-services-regulation-committee/news/218442/bogus/","UK Parliament")
    print("PASS: first-party announcement titles, date validation, official URL allowlist")

if __name__=="__main__":
    self_test()
