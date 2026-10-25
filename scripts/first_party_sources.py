#!/usr/bin/env python3
"""Read limited first-party financial company newsrooms, not third-party media."""
from __future__ import annotations
import datetime as dt
import re
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
from source_retrieval import retrieve_bytes
from publication_scope import source_lane
from source_registry import EXTRA_INDEXES
from same_day_policy import clock
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    ("Association of British Insurers","Insurance","https://www.abi.org.uk/media-hub"),
    ("UK Finance","Banking","https://www.ukfinance.org.uk/news-and-insight/press-release"),
    ("Financial Conduct Authority","Regulation","https://www.fca.org.uk/news"),
    ("Bank of England","Banking","https://www.bankofengland.co.uk/news/latest-and-upcoming"),
)
INDEXES += EXTRA_INDEXES
MON={"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"sept":9,"oct":10,"nov":11,"dec":12}
DATE=re.compile(r"\b([0-3]?\d)(?:st|nd|rd|th)?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+(20\d\d)\b",re.I)
MONTH_FIRST=re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+([0-3]?\d),?\s+(20\d\d)\b",re.I)
DOT_DATE=re.compile(r"\b([0-3]?\d)\.([01]?\d)\.(20\d\d)\b")
SLASH_DATE=re.compile(r"\b([0-3]?\d)/([01]?\d)/(20\d\d)\b")

def official_release(url, source):
    p=urlsplit(url)
    if p.scheme!="https" or p.username or p.password:return False
    if source in {x[0] for x in EXTRA_INDEXES}:
        return source_lane(url) is not None
    if source=="Association of British Insurers":
        return source_lane(url)=="industry_release" and p.hostname in {"abi.org.uk","www.abi.org.uk"}
    if source=="UK Finance":
        return source_lane(url)=="industry_release" and p.hostname in {"ukfinance.org.uk","www.ukfinance.org.uk"}
    if source=="Financial Conduct Authority":
        return source_lane(url) in {"fca_release","fca_consultation","fca_review","fca_speech","fca_data","regulatory_policy","regulatory_proposal","regulatory_report","regulatory_finding","official_release"}
    if source=="Bank of England":
        return source_lane(url) in {"boe_release","pra_publication"}
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
    today=today or clock().date()
    soup=BeautifulSoup(content,"html.parser")
    found=[]
    for anchor in soup.select("a[href]"):
        url=urljoin(base,anchor["href"]).split("#")[0]
        if not official_release(url,source):continue
        title=" ".join(anchor.get_text(" ",strip=True).split())
        if source=="Association of British Insurers":
            # The ABI hub mixes opinion with releases. Only release-labelled
            # cards enter the automated newsroom, never member-only commentary.
            if not re.match(r"(?i)^press release\s*\|",title):
                continue
            title=re.sub(r"(?i)^press release\s*\|\s*\d{1,2}\.\d{1,2}\.20\d{2}\s*","",title).strip()
        if (source in {x[0] for x in EXTRA_INDEXES} or source in {"Allianz UK","Munich Re","HSBC","NatWest Group","Financial Ombudsman Service"}) and (len(title)<25 or title.lower() in {"read more","more information","discover more"}):
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
        for _ in range(5):
            if not getattr(node,"parent",None):break
            node=node.parent
            context=" ".join(node.get_text(" ",strip=True).split())[:1100]
            m=DATE.search(context)
            m2=MONTH_FIRST.search(context)
            m3=DOT_DATE.search(context)
            m4=SLASH_DATE.search(context)
            if (m or m2 or m3 or m4) and len(context)<900:
                try:
                    if m:
                        month=m.group(2)
                        date=dt.date(int(m.group(3)),MON[month[:4].lower()] if month.lower().startswith("sept") else MON[month[:3].lower()],int(m.group(1)))
                    elif m2:
                        month=m2.group(1)
                        date=dt.date(int(m2.group(3)),MON[month[:4].lower()] if month.lower().startswith("sept") else MON[month[:3].lower()],int(m2.group(2)))
                    else:
                        dated=m3 if m3 else m4
                        date=dt.date(int(dated.group(3)),int(dated.group(2)),int(dated.group(1)))
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
        if source_lane(url) in {'pra_publication','regulatory_policy','regulatory_proposal','regulatory_report','regulatory_finding'}:effective_category='Regulation'
        found.append({"title":title,"url":url,"dateISO":date.isoformat(),"published_at":date.isoformat(),
                      "source":source,"category":effective_category,"kind":"first_party_announcement","source_time_precision":"date"})
    unique={}
    for entry in found:
        unique.setdefault(entry["url"],entry)
    return list(unique.values())

def discover():
    items=[];problems=[];coverage=[]
    def fetch(index):
        source,category,url=index
        raw,ctype,final=retrieve_bytes(url)
        if "html" not in ctype:raise ValueError("Index is not HTML")
        records=parse_listing(raw,source,category,final)
        # Hydrated or undated card layouts: read up to three release links and
        # obtain their original dates from the actual documents, without AI.
        if not records:
            from source_dates import published_date
            from source_trace import official_headline
            soup=BeautifulSoup(raw,"html.parser")
            urls=list(dict.fromkeys(urljoin(final,a["href"]).split("#")[0] for a in soup.select("a[href]")
                if official_release(urljoin(final,a["href"]),source)))
            for link in urls[:3]:
                try:
                    content,content_type,real=retrieve_bytes(link)
                    dated=published_date(content);title=official_headline(content)
                    if dated and title:
                        day,stamp,precision=dated
                        if 0<=(clock().date()-dt.date.fromisoformat(day)).days<=21:
                            records.append({"title":title,"url":real,"dateISO":day,"published_at":stamp,"source_published_at":stamp,"source_time_precision":precision,"source":source,"category":"Regulation" if source_lane(real) in {'pra_publication','regulatory_policy','regulatory_proposal','regulatory_report','regulatory_finding'} else category,"kind":"first_party_announcement"})
                except Exception:continue
        return source,records
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures={pool.submit(fetch,index):index for index in INDEXES}
        for future in as_completed(futures):
            source,category,url=futures[future]
            try:
                _,records=future.result();items.extend(records)
                coverage.append({"source":source,"url":url,"candidates":len(records),"result":"read"})
                print(f"FIRST_PARTY_DISCOVERY {source}: {len(records)} dated original leads")
            except Exception as e:
                issue=f"{source}: {type(e).__name__} {str(e)[:100]}"
                problems.append(issue);coverage.append({"source":source,"url":url,"result":"failed","reason":str(e)[:140]})
                print("FIRST_PARTY_BLOCKED "+issue)
    from pathlib import Path
    import json
    out=Path(__file__).resolve().parents[1]/"generated-drafts"
    out.mkdir(exist_ok=True)
    (out/"primary-discovery.json").write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+"\n")
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
    abi=b'''<main><article><a href="/media-hub/news-post/insurers-share-practical-steps-ahead-of-storms">Press release | 24.10.2026 Insurers share practical steps ahead of storms</a></article><article><a href="/media-hub/news-post/commentary">Opinion | 24.10.2026 The insurance market needs reform</a></article></main>'''
    a=parse_listing(abi,"Association of British Insurers","Insurance","https://www.abi.org.uk/media-hub",today=dt.date(2026,10,24))
    assert len(a)==1 and a[0]["dateISO"]=="2026-10-24" and a[0]["title"]=="Insurers share practical steps ahead of storms",a
    uk=b'''<main><article><span>24 Oct 2026</span><h3><a href="/news-and-insight/press-release/banks-report-customer-payment-trends">Banks report fresh customer payment trends</a></h3></article></main>'''
    f=parse_listing(uk,"UK Finance","Banking","https://www.ukfinance.org.uk/news-and-insight/press-release",today=dt.date(2026,10,24))
    assert len(f)==1 and f[0]["dateISO"]=="2026-10-24",f
    fca=b'''<main><article><h3><a href="/news/press-releases/fca-outlines-new-bank-account-rules">FCA outlines new bank account rules for firms</a></h3><span>23/10/2026</span></article></main>'''
    f=parse_listing(fca,"Financial Conduct Authority","Regulation","https://www.fca.org.uk/news",today=dt.date(2026,10,24))
    assert len(f)==1 and f[0]["dateISO"]=="2026-10-23",f
    boe=b'''<main><article><a href="/news/2026/october/bank-of-england-announces-new-market-guidance">Bank of England announces new market guidance for banks</a><span>22 October 2026</span></article></main>'''
    b=parse_listing(boe,"Bank of England","Banking","https://www.bankofengland.co.uk/news/latest-and-upcoming",today=dt.date(2026,10,24))
    assert len(b)==1 and b[0]["dateISO"]=="2026-10-22",b
    hiscox=b'''<article><p>24th October 2026</p><h3><a href="/news/press-releases/2026/24-10-26">Hiscox announces new specialist insurance protection for UK businesses</a></h3></article>'''
    hx=parse_listing(hiscox,"Hiscox Group","Insurance","https://www.hiscoxgroup.com/news/press-releases",today=dt.date(2026,10,25))
    assert len(hx)==1 and hx[0]["dateISO"]=="2026-10-24",hx
    assert official_release("https://www.hiscoxgroup.com/news/press-releases/2026/24-10-26","Hiscox Group")
    assert not official_release("https://www.hiscoxgroup.com.evil.net/news/press-releases/2026/24-10-26","Hiscox Group")
    chubb=b'''<article><p>Oct 24, 2026</p><h3><a href="/news-releases?item=122864">Chubb introduces updated broker trading terms for UK commercial clients</a></h3></article>'''
    cx=parse_listing(chubb,"Chubb UK","Insurance","https://news.uk.chubb.com/news-releases",today=dt.date(2026,10,25))
    assert len(cx)==1 and cx[0]["dateISO"]=="2026-10-24",cx
    assert not official_release("https://news.uk.chubb.com/news-releases?category=778","Chubb UK")
    assert not official_release("https://news.uk.chubb.com/news-releases?item=122864&evil=1","Chubb UK")
    # Live-domain-shaped examples: independent issuer newsrooms, not media content.
    admiral=b'''<article><p>24 October 2026</p><h3>Admiral Business expands intermediary access to SME insurance products</h3><a href="/news-releases/news-release-details/admiral-business-expands-intermediary-access">Read More</a></article>'''
    aa=parse_listing(admiral,"Admiral Group","Insurance","https://www.admiralgroup.co.uk/media/news-releases-and-media-contacts",today=dt.date(2026,10,25))
    assert len(aa)==1 and aa[0]["dateISO"]=="2026-10-24",aa
    retail=b'''<article><h3><a href="/news-and-insights/2026/lloyds-business-banking-expands-sme-finance.html">Lloyds Business Banking expands SME finance for regional firms</a></h3><span>Lloyds Retail 24 Oct 2026</span></article>'''
    rb=parse_listing(retail,"Lloyds Bank Retail","Banking","https://www.lloydsbank.com/news-and-insights.html",today=dt.date(2026,10,25))
    assert len(rb)==1 and rb[0]["dateISO"]=="2026-10-24",rb
    market=b'''<article><h3><a href="/insights/media-centre/press-releases/lloyds-brokers-market-update-2026">Lloyd's market publishes new broker trading arrangements</a></h3><span>24 October 2026</span></article>'''
    ll=parse_listing(market,"Lloyd's Market","Insurance","https://www.lloyds.com/insights/media-centre/press-releases",today=dt.date(2026,10,25))
    assert len(ll)==1 and ll[0]["dateISO"]=="2026-10-24",ll
    assert not official_release("https://www.lloyds.com.attacker.invalid/insights/media-centre/press-releases/test","Lloyd's Market")
    assert not official_release("https://www.admiralgroup.co.uk/news-releases/news-release-details/test?preview=true","Admiral Group")
    assert not official_release("https://www.lloydsbank.com/news-and-insights.html","Lloyds Bank Retail")
    assert not official_release("https://www.lloyds.com/insights/media-centre/press-releases","Lloyd's Market")
    ageas=b'''<article><p>9 October 2026</p><h3><a href="/press-releases/2026-press-releases/ageas-esure-boards-independent-non-executive-directors/">Ageas and esure Boards appoint two Independent Non-Executive Directors</a></h3></article>'''
    ag=parse_listing(ageas,"Ageas UK","Insurance","https://www.ageas.co.uk/press-releases/",today=dt.date(2026,10,25))
    assert len(ag)==1 and ag[0]["dateISO"]=="2026-10-09",ag
    lma=b'''<article><h3><a href="/lma-and-iua-launch-joint-healthcare-claims-group-to-strengthen-market-expertise/">LMA and IUA launch Joint Healthcare Claims Group to strengthen market expertise</a></h3><p>07 October 2026</p></article>'''
    lm=parse_listing(lma,"Lloyd's Market Association","Insurance","https://lmalloyds.com/insights-resources/press-releases/",today=dt.date(2026,10,25))
    assert len(lm)==1 and lm[0]["dateISO"]=="2026-10-07",lm
    mga=b'''<article><h3><a href="/mgaa-appoints-padda-consulting-as-uk-compliance-and-regulatory-partner/">MGAA appoints Padda Consulting as UK Compliance and Regulatory Partner</a></h3><p>28th July 2026</p></article>'''
    assert not parse_listing(mga,"Managing General Agents Association","Brokers","https://mgaa.co.uk/news/",today=dt.date(2026,10,25)), "Old MGA news must not be fresh"
    ga=b'''<article><h3><a href="/news/news-details/2026/Arthur-J--Gallagher--Co--Acquires-Bridge-Insurance-Brokers-Limited/default.aspx">Gallagher acquires commercial insurance brokers in the United Kingdom</a></h3><p>16 April 2026</p></article>'''
    assert len(parse_listing(ga,"Gallagher Investor Relations","Brokers","https://investor.ajg.com/news/default.aspx",today=dt.date(2026,4,16)))==1
    assert not official_release("https://investor.ajg.com.evil.invalid/news/news-details/2026/fake/default.aspx","Gallagher Investor Relations")
    assert not official_release("https://lmalloyds.com/insights-resources/press-releases/","Lloyd's Market Association")
    assert not official_release("https://www.howdengroup.com/news-insights?draft=1","Howden Broking Group")
    print("PASS: first-party regulator, banking and insurance indexed source discovery")

if __name__=="__main__":
    self_test()
