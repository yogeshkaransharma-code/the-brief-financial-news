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

FEEDS = [
    ("FCA", "https://www.fca.org.uk/news/rss.xml", "Regulation"),
    ("FCA publications", "https://www.fca.org.uk/publications/rss.xml", "Regulation"),
    ("Bank of England", "https://www.bankofengland.co.uk/rss/news", "Banking"),
    ("PRA", "https://www.bankofengland.co.uk/rss/prudential-regulation-publications", "Regulation"),
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
            alternatives = [x.attrib.get("href", "") for x in entry.findall(ns + "link") if x.attrib.get("rel", "alternate") == "alternate"]
            link = alternatives[0] if alternatives else ""
        else:
            title = text_of(entry, ["title"])
            description = text_of(entry, ["description"])
            date = text_of(entry, ["pubDate", "{http://purl.org/dc/elements/1.1/}date"])
            link = text_of(entry, ["link"])
        headline = clean(title)[:230]
        summary = clean(description)[:400]
        # Some feeds contain only an author line, a copyright notice, or no usable
        # explanation. These aren't useful news briefings for our readers.
        if (not summary or len(summary) < 45
                or re.match(r"(?i)^(author\s*:|this content is copyright|copyright notice|read more\b)", summary)):
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
            if not updates:
                raise ValueError("No recent usable items")
            seen.update({x["id"]: x for x in updates})
            successes.append({"name": name, "items": len(updates)})
        except Exception as exc:
            errors.append({"source": name, "error": str(exc)[:140]})
            logging.warning("%s: %s", name, exc)
    if not successes:
        raise SystemExit("All feeds failed; keep existing data unchanged")
    recent = sorted(seen.values(), key=lambda x: x.get("published_at", ""), reverse=True)
    results, fingerprints = [], set()
    for item in recent:
        fp = re.sub(r"[^a-z0-9]", "", item["title"].lower())[:125]
        if fp in fingerprints:
            continue
        fingerprints.add(fp)
        results.append(item)
        if len(results) >= 260:
            break
    output = {"generated_at": NOW.isoformat(), "sources_checked": successes, "items": results, "errors": errors, "status": "live" if not errors else "partial"}
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Feeds working: {len(successes)}/{len(FEEDS)}; stories: {len(results)}")

if __name__ == "__main__":
    main()
