#!/usr/bin/env python3
"""Collect short, attributed RSS updates for a free static financial-news site."""
from __future__ import annotations
import datetime as dt
import email.utils
import hashlib
import html
from html.parser import HTMLParser
import json
import logging
from pathlib import Path
import re
import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "live.json"
NOW = dt.datetime.now(dt.timezone.utc)
HEADERS = {"User-Agent": "TheBriefNewsReader/0.1 (RSS reader; source attribution retained)", "Accept": "application/rss+xml,application/atom+xml,text/xml,application/xml"}

GOVERNMENT = {"HM Revenue & Customs","Office for National Statistics","HM Treasury", "Department for Work and Pensions",
              "Competition and Markets Authority", "Department for Business and Trade",
              "Department for Science, Innovation and Technology"}
# Government sites publish energy, childcare, visas and many other topics.
# To avoid irrelevant automated pieces, a government HEADLINE must explicitly
# concern financial services, savings, investment, pensions or market rules.
GOVERNMENT_FINANCE_HEADLINE = re.compile(
    r"(?i)\b(bank\w*|insur\w*|reinsur\w*|broker\w*|financ\w*|"
    r"pension\w*|retirement|mortgage\w*|consumer credit|"
    r"payment\w*|saving\w*|stock market\w*|capital market\w*|"
    r"wealth management|investment\w*|investor\w*|"
    r"financial regulation|fintech|fraud|fca|pra|"
    r"funding for small businesses|business lending|economic forecast|"
    r"interest rate|financial services)\b"
)
# The newsroom is UK financial services, not every general business headline.
FOCUSED_NEWS = re.compile(
    r"(?i)\b(uk|britain|british|england|london|bank\w*|insur\w*|"
    r"broker\w*|financ\w*|fintech|payment\w*|invest\w*|"
    r"pension\w*|asset manag\w*|wealth|mortgage\w*|"
    r"lending|credit|budget|interest rate|inflation|regulat\w*|"
    r"capital market\w*|stock market|ftse|sterling|"
    r"fca|pra|boe|treasury|taxation|savings?|reinsur\w*|"
    r"fund manag\w*|insurtech|fintech|underwrit\w*)\b"
)
BROADER_MEDIA = {"BBC Business","Sky Business","The Guardian Business",
                 "The Guardian Money","The Guardian Insurance","The Guardian Banking",
                 "Financial Times","Bloomberg Markets","Wall Street Journal Markets",
                 "MarketWatch","The Economist Finance"}
OFFICIAL_FEED_NAMES = {"FCA","FCA publications","Bank of England","PRA"} | GOVERNMENT


FEEDS = [
    ("FCA", "https://www.fca.org.uk/news/rss.xml", "Regulation"),
    ("FCA publications", "https://www.fca.org.uk/publications/rss.xml", "Regulation"),
    ("Bank of England", "https://www.bankofengland.co.uk/rss/news", "Banking"),
    ("PRA", "https://www.bankofengland.co.uk/rss/prudential-regulation-publications", "Regulation"),
    # Government releases are direct official evidence candidates, not media reports.
    ("HM Treasury", "https://www.gov.uk/government/organisations/hm-treasury.atom", "Regulation"),
    ("HM Revenue & Customs", "https://www.gov.uk/government/organisations/hm-revenue-customs.atom", "Regulation"),
    ("Office for National Statistics", "https://www.gov.uk/government/organisations/office-for-national-statistics.atom", "Banking"),
    ("Department for Work and Pensions", "https://www.gov.uk/government/organisations/department-for-work-pensions.atom", "Regulation"),
    ("Competition and Markets Authority", "https://www.gov.uk/government/organisations/competition-and-markets-authority.atom", "Regulation"),
    ("Department for Business and Trade", "https://www.gov.uk/government/organisations/department-for-business-and-trade.atom", "Regulation"),
    ("Department for Science, Innovation and Technology", "https://www.gov.uk/government/organisations/department-for-science-innovation-and-technology.atom", "Technology"),
    # Media feeds are lead discovery only. They are NOT source evidence.
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml", "Banking"),
    ("Sky Business", "https://feeds.skynews.com/feeds/rss/business.xml", "Banking"),
    ("The Guardian Business", "https://www.theguardian.com/uk/business/rss", "Banking"),
    ("The Guardian Money", "https://www.theguardian.com/money/rss", "Banking"),
    ("The Guardian Insurance", "https://www.theguardian.com/business/insurance/rss", "Insurance"),
    ("The Guardian Banking", "https://www.theguardian.com/business/banking/rss", "Banking"),
    ("Financial Times", "https://www.ft.com/rss/home", "Banking"),
    ("Bloomberg Markets", "https://feeds.bloomberg.com/markets/news.rss", "Banking"),
    ("Wall Street Journal Markets", "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain", "Banking"),
    ("MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_topstories", "Banking"),
    # Economist RSS requires paid access; not requested on the free unattended path.
    ("Finextra", "https://www.finextra.com/rss/headlines.aspx", "Banking"),
    ("Finextra payments", "https://www.finextra.com/rss/channel.aspx?channel=payments", "Banking"),
    ("Insurance Business UK", "https://www.insurancebusinessmag.com/uk/rss/", "Insurance"),
    ("Commercial Risk", "https://www.commercialriskonline.com/feed/", "Insurance"),
    ("Reinsurance News", "https://www.reinsurancene.ws/feed/", "Insurance"),
    ("Insurance Journal", "https://www.insurancejournal.com/rss/news/", "Insurance"),
    ("Insurance Times", "https://www.insurancetimes.co.uk/insurance-times-rss/1388.rss", "Insurance"),
    ("Insurance Age", "https://www.insuranceage.co.uk/feeds/rss/category/broker", "Brokers"),
    ("Professional Pensions", "https://www.professionalpensions.com/feeds/rss", "Pensions"),
    ("Investment Week", "https://www.investmentweek.co.uk/feeds/rss", "Wealth"),
    ("Money Marketing", "https://www.moneymarketing.co.uk/feed/", "Wealth"),
    ("Mortgage Solutions", "https://www.mortgagesolutions.co.uk/feed/", "Banking"),
    # The Paypers /rss currently returns HTML; do not claim it is a working feed.
    # Artemis serves copyright-only summaries; not suitable for an on-site briefing.
]

# Persistent publisher catalogue in GitHub. Add reliable sources here instead of
# editing the core importer every time. Feed names/URLs are strictly validated:
# a GitHub listing is a discovery route, not permission to publish its contents.
def registered_feeds(path=ROOT / "data" / "publisher-feeds.json"):
    from urllib.parse import urlsplit, parse_qs
    payload=json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version")!=1 or not isinstance(payload.get("feeds"),list):
        raise ValueError("Unrecognised publisher feed registry")
    result=[];names=set();urls=set()
    approved_channels={"retail","wholesale","execution","risk","security","wealth","transaction","cards",
                       "payments","ai","markets"}
    for record in payload["feeds"]:
        if not isinstance(record,dict):raise ValueError("Invalid publisher record")
        name,url,category=(record.get("name"),record.get("url"),record.get("category"))
        if not all(isinstance(x,str) and x for x in (name,url,category)):
            raise ValueError("Missing publisher details")
        if category not in {"Insurance","Banking"} or len(name)>90:
            raise ValueError("Only the two editorial desks are supported")
        u=urlsplit(url)
        if not (u.scheme=="https" and u.hostname=="www.finextra.com"
                and u.path=="/rss/channel.aspx" and not u.fragment and not u.username
                and not u.password and u.port in (None,443)
                and set(parse_qs(u.query))=={"channel"}
                and len(parse_qs(u.query)["channel"])==1
                and parse_qs(u.query)["channel"][0] in approved_channels):
            raise ValueError("Feed requires an individually reviewed publisher origin and route: "+url)
        if name in names or url in urls:
            raise ValueError("Duplicate RSS discovery source: "+name)
        names.add(name);urls.add(url)
        result.append((name,url,category))
    return result

# Existing direct regulator, insurer, broker, BBC and trade feeds are retained.
# The registry extends the feed desk; it is versioned source memory, not AI memory.
FEEDS.extend(registered_feeds())


class CleanHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.words = []
    def handle_data(self, data):
        self.words.append(data)
    def handle_starttag(self, tag, attrs):
        if tag in ("p", "br", "div", "li"):
            self.words.append(" ")

def clean(value):
    p = CleanHTML()
    try:
        p.feed(html.unescape(value or ""))
        return re.sub(r"\s+", " ", " ".join(p.words)).strip()
    except Exception:
        return re.sub(r"<[^>]+>", "", value or "").strip()

def text_of(node, options):
    for key in options:
        child = node.find(key)
        if child is not None and child.text and child.text.strip():
            return child.text.strip()
    return ""

def parse_date(value):
    try:
        d = email.utils.parsedate_to_datetime(value)
        if d:
            return (d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)).astimezone(dt.timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    except (TypeError, ValueError, AttributeError):
        pass
    # FCA uses local British dates such as "Thursday, October 22, 2026 - 22:01".
    try:
        return dt.datetime.strptime(value.strip(), "%A, %B %d, %Y - %H:%M").replace(tzinfo=ZoneInfo("Europe/London")).astimezone(dt.timezone.utc)
    except (TypeError, ValueError, AttributeError):
        return None

def categorise(headline, fallback):
    # The official FCA and PRA feeds are regulatory updates even when
    # their headlines mention technology or insurance.
    if fallback == "Regulation":
        return "Regulation"
    s = headline.lower()
    if re.search(r"\b(pension\w*|retirement)\b",s):return "Pensions"
    if re.search(r"\b(asset manag\w*|wealth manag\w*|fund manag\w*|investment trust\w*)\b",s):return "Wealth"
    if re.search(r"\b(broker\w*|intermediar\w*|mga[s]?)\b",s):return "Brokers"
    if re.search(r"\b(fca|pra|regulat\w*|consultation|rulebook|supervis\w*|compliance|enforc\w*|sanction\w*)\b", s):
        return "Regulation"
    if re.search(r"\b(insur\w*|broker\w*|underwrit\w*|reinsur\w*|lloyd.s|mga|pensions?)\b", s):
        return "Insurance"
    if re.search(r"\b(fintech|insurtech|artificial intelligence|cyber\w*|digital|software|blockchain)\b", s):
        return "Technology"
    return fallback

def parse(xml_bytes, name, fallback):
    doc = ET.fromstring(xml_bytes)
    rss = doc.findall(".//item")
    atom = not bool(rss)
    entries = rss if rss else doc.findall("{http://www.w3.org/2005/Atom}entry")
    if not rss and doc.tag not in {'{http://www.w3.org/2005/Atom}feed','rss','{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF'}:
        raise ValueError('Response is not an RSS or Atom feed')
    output = []
    for entry in entries[:65]:
        if atom:
            ns = "{http://www.w3.org/2005/Atom}"
            title = text_of(entry, [ns + "title"])
            description = text_of(entry, [ns + "summary", ns + "content"])
            original_date = text_of(entry, [ns + "published"])
            date = original_date or text_of(entry, [ns + "updated"])
            date_basis = 'published' if original_date else 'modified'
            alternatives = [x.attrib.get("href", "") for x in entry.findall(ns + "link")
                            if x.attrib.get("href") and x.attrib.get("rel", "alternate") in ("alternate", "")]
            link = alternatives[0] if alternatives else ""
        else:
            title = text_of(entry, ["title"])
            description = text_of(entry, ["description"])
            date = text_of(entry, ["pubDate", "{http://purl.org/dc/elements/1.1/}date"])
            date_basis = 'published'
            link = text_of(entry, ["link"])
        headline = clean(title)[:230]
        summary = clean(description)[:400]
        if name in GOVERNMENT and not GOVERNMENT_FINANCE_HEADLINE.search(headline):
            continue
        from media_sources import relevant
        # Some feeds contain only an author line, a copyright notice, or no usable
        # explanation. These aren't useful news briefings for our readers.
        if (not summary or len(summary) < 45
                or re.match(r"(?i)^(author\s*:|this content is copyright|copyright notice|read more\b)", summary)):
            # A government agency's short Atom summary still identifies an
            # official URL; it must NEVER be used for article evidence.
            if name in GOVERNMENT and len(headline)>=25:
                summary="Original government announcement. The full official document must be retrieved and verified before reporting."
            else:
                summary="Discovery lead only. Read and verify original evidence before publication."
        published = parse_date(date)
        url = urllib.parse.urlsplit(link)
        if not headline or not published or not (url.scheme == "https" and url.hostname) or url.username or url.password:
            continue
        if published > NOW + dt.timedelta(days=1) or NOW - published > dt.timedelta(days=70):
            continue
        # Strip BBC's RSS campaign tags only on a canonical BBC /news/articles/ URL.
        if name=="BBC Business" and url.hostname in {"www.bbc.co.uk","bbc.co.uk","www.bbc.com","bbc.com"} and re.fullmatch(r"/news/articles/[a-z0-9]{10,24}/?",url.path,re.I):
            link=urllib.parse.urlunsplit((url.scheme,url.netloc,url.path,"",""))
        from media_sources import canonical_url
        link=canonical_url(link)
        # Publisher sections are context, not a licence to take every lifestyle headline.
        # Evaluate the canonical article URL alongside its headline. This preserves
        # a genuinely relevant financial-security report even when its headline
        # omits the words 'bank' and 'insurance'.
        if name in BROADER_MEDIA and not relevant({'title':headline,'url':link}):
            continue
        uid = hashlib.sha256(link.encode()).hexdigest()[:20]
        output.append({
            "id": "feed-" + uid, "kind": "source",
            "title": headline, "short": summary[:290] if summary else "Read this update at the original publisher.",
            "excerpt": summary, "url": link, "source": name,
            "category": categorise(headline, fallback),
            "dateISO": published.date().isoformat(),
            "published_at": published.isoformat(),
            "source_published_at": published.isoformat(),
            "source_time_precision": "date" if re.fullmatch(r"20\d{2}-\d{2}-\d{2}",date.strip()) else "timestamp",
            "discovery_date_basis":date_basis,
            "status": "Source update",
        })
    return output

def canonical_record(item):
    """Replace cached metadata by original URL even when tracking IDs changed."""
    from media_sources import canonical_url
    url=canonical_url(item['url'])
    return dict(item,url=url,id='feed-'+hashlib.sha256(url.encode()).hexdigest()[:20])


def balanced_discovery(items,limit=450):
    """Keep specialist insurance/broker leads from being evicted by general business RSS.

    All leads retain their real publisher/source date and continue through the
    original-document fact checks; this only controls which leads survive RSS storage.
    """
    ranked=sorted(items,key=lambda x:x.get("published_at",""),reverse=True)
    picked=[];seen=set()
    for sector,quota in (("Insurance",95),("Brokers",35)):
        for item in ranked:
            if item.get("category")==sector and item.get("url") not in seen:
                picked.append(item);seen.add(item["url"])
                if sum(x.get("category")==sector for x in picked)>=quota:break
    for item in ranked:
        if len(picked)>=limit:break
        if item.get("url") not in seen:
            picked.append(item);seen.add(item["url"])
    return sorted(picked,key=lambda x:x.get("published_at",""),reverse=True)[:limit]


def main():
    try:
        prior = json.loads(DEST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        prior = {"items": []}
    # Keep the archive clear of previous boilerplate and copyright notices.
    seen = {
        canonical_record(x)["url"]: canonical_record(x) for x in prior.get("items", [])
        if x.get("id") and x.get("url") and len(x.get("short") or "") >= 45
        and not re.match(r"(?i)^(author\s*:|this content is copyright|copyright notice|read more\b)", x.get("short") or "")
        and (x.get("source") not in GOVERNMENT
             or GOVERNMENT_FINANCE_HEADLINE.search(x.get("title","")))
    }
    successes, errors = [], []
    def fetch_feed(feed):
        name,url,category=feed
        request=urllib.request.Request(url,headers=HEADERS)
        try:
            with urllib.request.urlopen(request,timeout=18) as response:raw=response.read(2000000)
        except urllib.error.HTTPError as exc:
            if exc.code not in (406,415):raise
            headers=dict(HEADERS,Accept="*/*")
            with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=18) as response:raw=response.read(2000000)
        return parse(raw,name,category)
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures={pool.submit(fetch_feed,feed):feed for feed in FEEDS}
        for future in as_completed(futures):
            name,url,category=futures[future]
            try:
                updates=future.result()
                seen.update({x["url"]:x for x in updates})
                successes.append({"name":name,"url":url,"items":len(updates)})
            except Exception as exc:
                errors.append({"source":name,"url":url,"error":str(exc)[:140]})
                logging.warning("%s: %s",name,exc)
    if not successes:
        raise SystemExit("All feeds failed; keep existing data unchanged")
    # Preserve primary-source candidates when dozens of commercial publishers
    # post in the same hour. They are much more useful than another media lead.
    recent = sorted(seen.values(),key=lambda x: x.get("published_at",""),reverse=True)
    results, fingerprints = [], set()
    for item in recent:
        fp = re.sub(r"[^a-z0-9]", "", item["title"].lower())[:125]
        if fp in fingerprints:
            continue
        fingerprints.add(fp)
        results.append(item)
        if len(results) >= 2500:
            break
    results=balanced_discovery(results,450)
    output = {"generated_at": NOW.isoformat(), "sources_checked": successes, "items": results, "errors": errors, "status": "live" if not errors else "partial"}
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Feeds working: {len(successes)}/{len(FEEDS)}; stories: {len(results)}")

if __name__ == "__main__":
    main()


