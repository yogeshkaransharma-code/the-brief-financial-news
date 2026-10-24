#!/usr/bin/env python3
"""Read limited first-party financial company newsrooms, not third-party media."""
from __future__ import annotations
import datetime as dt
import re
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
from source_retrieval import retrieve_bytes
from publication_scope import source_lane

INDEXES=(
    ("Aviva","Insurance","https://www.aviva.com/newsroom/"),
    ("Lloyds Banking Group","Banking","https://www.lloydsbankinggroup.com/media/press-releases.html"),
    ("UK Parliament","Regulation","https://committees.parliament.uk/committee/697/financial-services-regulation-committee/news/"),
    ("The Pensions Regulator","Regulation","https://www.thepensionsregulator.gov.uk/media-hub/press-releases"),
    ("Allianz UK","Insurance","https://www.allianz.co.uk/news-and-insight/news.html"),
    ("Munich Re","Insurance","https://www.munichre.com/en/company/media-relations/media-information-and-corporate-news.html"),
    ("HSBC","Banking","https://www.hsbc.com/news-and-views/news/media-releases"),
    ("NatWest Group","Banking","https://www.natwestgroup.com/news-and-insights/news-room/press-releases.html"),
    ("Financial Ombudsman Service","Regulation","https://www.financial-ombudsman.org.uk/who-we-are/data-insight/news"),
)
MON={"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"sept":9,"oct":10,"nov":11,"dec":12}
DATE=re.compile(r"\b([0-3]?\d)\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+(20\d\d)\b",re.I)
MONTH_FIRST=re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+([0-3]?\d),?\s+(20\d\d)\b",re.I)

def official_release(url, source):
    p=urlsplit(url)
    if p.scheme!="https" or p.username or p.password:return False
    if source=="Aviva":
        return p.hostname in {"www.aviva.com","aviva.com"} and "/newsroom/news-and-research-overview/news-releases/" in p.path
    if source=="The Pensions Regulator":
        return source_lane(url)=="tpr_release"
    if source=="Financial Ombudsman Service":
        return source_lane(url)=="ombudsman_release"
    if source in {"HSBC","NatWest Group"}:
        return source_lane(url)=="company_release"
    if source in {"Allianz UK","Munich Re"}:
        return source_lane(url)=="company_release"
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
        if source in {"Allianz UK","Munich Re","HSBC","NatWest Group","Financial Ombudsman Service"} and (len(title)<25 or title.lower() in {"read more","more information","discover more"}):
            node=anchor
            for _ in range(4):
                node=node.parent if getattr(node,"parent",None) else node
                headings=node.find_all(["h2","h3","h4"]) if hasattr(node,"find_all") else []
                if len(headings)==1:
                    title=" ".join(headings[0].get_text(" ",strip=True).split())
                    if len(title)>=25:break
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
            m2=MONTH_FIRST.search(context)
            if (m or m2) and len(context)<900:
                try:
                    if m:
                        month=m.group(2)
                        date=dt.date(int(m.group(3)),MON[month[:4].lower()] if month.lower().startswith("sept") else MON[month[:3].lower()],int(m.group(1)))
                    else:
                        month=m2.group(1)
                        date=dt.date(int(m2.group(3)),MON[month[:4].lower()] if month.lower().startswith("sept") else MON[month[:3].lower()],int(m2.group(2)))
                    break
                except (KeyError,ValueError):pass
        if date is None and source=="Munich Re":
            # Munich Re uses a dated, issuer-controlled press release URL.
            # This is not the date from a secondary media article.
            m=re.search(r"/media-release-(20\d{2})-(\d{2})-(\d{2})\.html$",url,re.I)
            if m:
                try:date=dt.date(int(m.group(1)),int(m.group(2)),int(m.group(3)))
                except ValueError:pass
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
    tpr=b'''<main><article><a href="/en/media-hub/press-releases/2026-press-releases/tpr-publishes-new-investment-guidance"><h3>TPR publishes new investment guidance for workplace pension trustees</h3></a><p>Saturday 24 October 2026</p></article></main>'''
    found=parse_listing(tpr,"The Pensions Regulator","Regulation","https://www.thepensionsregulator.gov.uk/media-hub/press-releases",today=dt.date(2026,10,24))
    assert len(found)==1 and found[0]["dateISO"]=="2026-10-24",found
    a=b'''<article><span>Oct 23, 2026</span><h3>Allianz UK and Superscript expand commercial insurance distribution</h3><a href="/news-and-insight/news/allianz-uk-superscript-commercial-insurance.html">Read more</a></article>'''
    result=parse_listing(a,"Allianz UK","Insurance","https://www.allianz.co.uk/news-and-insight/news.html",today=dt.date(2026,10,24))
    assert len(result)==1 and result[0]["dateISO"]=="2026-10-23",result
    m=b'''<article><span>October 23, 2026</span><h3>Munich Re reports quarterly profit and updates annual guidance</h3><a href="/en/company/media-relations/media-information-and-corporate-news/media-information/2026/media-release-2026-10-23.html">More information</a></article>'''
    mr=parse_listing(m,"Munich Re","Insurance","https://www.munichre.com/en/company/media-relations/media-information-and-corporate-news.html",today=dt.date(2026,10,24))
    assert len(mr)==1 and mr[0]["dateISO"]=="2026-10-23",mr
    undated=b'''<article><h3>Munich Re reports quarterly profit and updates annual guidance</h3><a href="/en/company/media-relations/media-information-and-corporate-news/media-information/2026/media-release-2026-10-23.html">More information</a></article>'''
    recovered=parse_listing(undated,"Munich Re","Insurance","https://www.munichre.com/en/company/media-relations/media-information-and-corporate-news.html",today=dt.date(2026,10,24))
    assert len(recovered)==1 and recovered[0]["dateISO"]=="2026-10-23",recovered
    hsbc=b'''<main><article><h3><a href="/news-and-views/news/media-releases/2026/bank-reports-third-quarter-results">HSBC reports its third quarter financial results and revenue growth</a></h3><p>24 Oct 2026</p></article></main>'''
    h=parse_listing(hsbc,"HSBC","Banking","https://www.hsbc.com/news-and-views/news/media-releases",today=dt.date(2026,10,24))
    assert len(h)==1 and h[0]["dateISO"]=="2026-10-24",h
    nw=b'''<main><article><h3><a href="/news-and-insights/news-room/press-releases/2026/natwest-business-banking-report-shows-growth.html">NatWest Group publishes new survey of business banking customers</a></h3><span>24 Oct 2026</span></article></main>'''
    n=parse_listing(nw,"NatWest Group","Banking","https://www.natwestgroup.com/news-and-insights/news-room/press-releases.html",today=dt.date(2026,10,24))
    assert len(n)==1 and n[0]["dateISO"]=="2026-10-24",n
    fos=b'''<main><article><h3><a href="/who-we-are/data-insight/news/financial-ombudsman-reports-complaints-growth">Financial Ombudsman Service reports latest complaints trends</a></h3><p>24 October 2026</p></article></main>'''
    fo=parse_listing(fos,"Financial Ombudsman Service","Regulation","https://www.financial-ombudsman.org.uk/who-we-are/data-insight/news",today=dt.date(2026,10,24))
    assert len(fo)==1 and fo[0]["dateISO"]=="2026-10-24",fo
    print("PASS: first-party announcement titles, date validation, official URL allowlist")

if __name__=="__main__":
    self_test()
