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
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "live.json"
NOW = dt.datetime.now(dt.timezone.utc)
HEADERS = {"User-Agent": "TheBriefNewsReader/0.1 (RSS reader; source attribution retained)", "Accept": "application/rss+xml,application/atom+xml,text/xml,application/xml"}

GOVERNMENT = {"HM Treasury", "Department for Work and Pensions",
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
    ("Department for Work and Pensions", "https://www.gov.uk/government/organisations/department-for-work-pensions.atom", "Regulation"),
    ("Competition and Markets Authority", "https://www.gov.uk/government/organisations/competition-and-markets-authority.atom", "Regulation"),
    ("Department for Business and Trade", "https://www.gov.uk/government/organisations/department-for-business-and-trade.atom", "Regulation"),
    ("Department for Science, Innovation and Technology", "https://www.gov.uk/government/organisations/department-for-science-innovation-and-technology.atom", "Technology"),
    # Media feeds are lead discovery only. They are NOT source evidence.
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml", "Banking"),
    ("Sky Business", "https://feeds.skynews.com/feeds/rss/business.xml", "Banking"),
    ("The Guardian Business", "https://www.theguardian.com/uk/business/rss", "Banking"),
    ("Financial Times", "https://www.ft.com/rss/home", "Banking"),
    ("Bloomberg Markets", "https://feeds.bloomberg.com/markets/news.rss", "Banking"),
    ("Wall Street Journal Markets", "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain", "Banking"),
    ("MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_topstories", "Banking"),
    ("The Economist Finance", "https://www.economist.com/finance-and-economics/rss.xml", "Banking"),
    ("Finextra", "https://www.finextra.com/rss/headlines.aspx", "Banking"),
    ("Finextra payments", "https://www.finextra.com/rss/channel.aspx?channel=payments", "Banking"),
    ("Insurance Business UK", "https://www.insurancebusinessmag.com/uk/rss/", "Insurance"),
    ("Commercial Risk", "https://www.commercialriskonline.com/feed/", "Insurance"),
    # Artemis serves copyright-only summaries; not suitable for an on-site briefing.
]

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
    if re.search(r"\b(fca|pra|regulat\w*|consultation|rulebook|supervis\w*|compliance|enforc\w*|sanction\w*)\b", s):
        return "Regulation"
    if re.search(r"\b(insur\w*|broker\w*|underwrit\w*|reinsur\w*|lloyd.s|mga|claims?|premium\w*|pensions?)\b", s):
        return "Insurance"
    if re.search(r"\b(fintech|insurtech|artificial intelligence|cyber\w*|digital|software|blockchain)\b", s):
        return "Technology"
    return fallback

def parse(xml_bytes, name, fallback):
    doc = ET.fromstring(xml_bytes)
    rss = doc.findall(".//item")
    atom = not bool(rss)
    entries = rss if rss else doc.findall("{http://www.w3.org/2005/Atom}entry")
    output = []
    for entry in entries[:65]:
        if atom:
            ns = "{http://www.w3.org/2005/Atom}"
            title = text_of(entry, [ns + "title"])
            description = text_of(entry, [ns + "summary", ns + "content"])
            date = text_of(entry, [ns + "published", ns + "updated"])
            alternatives = [x.attrib.get("href", "") for x in entry.findall(ns + "link")
                            if x.attrib.get("href") and x.attrib.get("rel", "alternate") in ("alternate", "")]
            link = alternatives[0] if alternatives else ""
        else:
            title = text_of(entry, ["title"])
            description = text_of(entry, ["description"])
            date = text_of(entry, ["pubDate", "{http://purl.org/dc/elements/1.1/}date"])
            link = text_of(entry, ["link"])
        headline = clean(title)[:230]
        summary = clean(description)[:400]
        if name in GOVERNMENT and not GOVERNMENT_FINANCE_HEADLINE.search(headline):
            continue
        if name in BROADER_MEDIA and not FOCUSED_NEWS.search(headline+" "+summary):
            continue
        # Some feeds contain only an author line, a copyright notice, or no usable
        # explanation. These aren't useful news briefings for our readers.
        if (not summary or len(summary) < 45
                or re.match(r"(?i)^(author\s*:|this content is copyright|copyright notice|read more\b)", summary)):
            # A government agency's short Atom summary still identifies an
            # official URL; it must NEVER be used for article evidence.
            if name in GOVERNMENT and len(headline)>=25:
                summary="Original government announcement. The full official document must be retrieved and verified before reporting."
            else:
                continue
        published = parse_date(date)
        url = urllib.parse.urlsplit(link)
        if not headline or not published or not (url.scheme == "https" and url.hostname) or url.username or url.password:
            continue
        if published > NOW + dt.timedelta(days=1) or NOW - published > dt.timedelta(days=70):
            continue
        uid = hashlib.sha256(link.split("#")[0].encode()).hexdigest()[:20]
        output.append({
            "id": "feed-" + uid, "kind": "source",
            "title": headline, "short": summary[:290] if summary else "Read this update at the original publisher.",
            "excerpt": summary, "url": link, "source": name,
            "category": categorise(headline, fallback),
            "dateISO": published.date().isoformat(),
            "published_at": published.isoformat(), "status": "Source update",
        })
    return output

def main():
    try:
        prior = json.loads(DEST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        prior = {"items": []}
    # Keep the archive clear of previous boilerplate and copyright notices.
    seen = {
        x["id"]: x for x in prior.get("items", [])
        if x.get("id") and len(x.get("short") or "") >= 45
        and not re.match(r"(?i)^(author\s*:|this content is copyright|copyright notice|read more\b)", x.get("short") or "")
        and (x.get("source") not in GOVERNMENT
             or GOVERNMENT_FINANCE_HEADLINE.search(x.get("title","")))
    }
    successes, errors = [], []
    for name, url, category in FEEDS:
        try:
            request = urllib.request.Request(url, headers=HEADERS)
            try:
                with urllib.request.urlopen(request, timeout=18) as response:
                    raw = response.read(2000000)
            except urllib.error.HTTPError as exc:
                if exc.code not in (406, 415):
                    raise
                # Some publishers reject a narrowly specified RSS Accept header.
                fallback_headers = dict(HEADERS)
                fallback_headers["Accept"] = "*/*"
                with urllib.request.urlopen(urllib.request.Request(url, headers=fallback_headers), timeout=18) as response:
                    raw = response.read(2000000)
            updates = parse(raw, name, category)
            if not updates and name not in GOVERNMENT:
                raise ValueError("No recent usable items")
            # A government feed can be healthy but have no financial-services
            # headlines today. This is an empty relevant result, not a failure.
            seen.update({x["id"]: x for x in updates})
            successes.append({"name": name, "items": len(updates)})
        except Exception as exc:
            errors.append({"source": name, "error": str(exc)[:140]})
            logging.warning("%s: %s", name, exc)
    if not successes:
        raise SystemExit("All feeds failed; keep existing data unchanged")
    # Preserve primary-source candidates when dozens of commercial publishers
    # post in the same hour. They are much more useful than another media lead.
    recent = sorted(seen.values(),key=lambda x: (
        x.get("source") in OFFICIAL_FEED_NAMES, x.get("published_at","")
    ),reverse=True)
    results, fingerprints = [], set()
    for item in recent:
        fp = re.sub(r"[^a-z0-9]", "", item["title"].lower())[:125]
        if fp in fingerprints:
            continue
        fingerprints.add(fp)
        results.append(item)
        if len(results) >= 450:
            break
    output = {"generated_at": NOW.isoformat(), "sources_checked": successes, "items": results, "errors": errors, "status": "live" if not errors else "partial"}
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Feeds working: {len(successes)}/{len(FEEDS)}; stories: {len(results)}")

if __name__ == "__main__":
    main()
