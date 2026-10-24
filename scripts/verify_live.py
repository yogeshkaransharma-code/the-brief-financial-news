#!/usr/bin/env python3
"""Post-deployment probe: prove that GitHub Pages serves actual readable articles.

An Actions green tick cannot substitute for a visible article. Fail the workflow
when the public HTML, article archive or full story route is missing or stale.
"""
import datetime as dt
import html
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = os.getenv("BRIEF_SITE_URL", "https://yogeshkaransharma-code.github.io/the-brief-financial-news/").rstrip("/")+"/"


def read(url):
    request = urllib.request.Request(url, headers={
        "User-Agent":"TheBriefLiveDeploymentCheck/1.0",
        "Cache-Control":"no-cache",
        "Pragma":"no-cache"
    })
    with urllib.request.urlopen(request, timeout=15) as response:
        content = response.read(950_000).decode("utf-8")
        return content


def probe():
    local = json.loads((ROOT/"data/articles.json").read_text(encoding="utf-8"))
    if not local:
        raise RuntimeError("No articles in approved archive; public edition must not be empty")
    latest = max(local, key=lambda a:(a.get("published_at",""),a["id"]))
    slug = latest["id"]+".html"
    key = str(int(dt.datetime.now(dt.timezone.utc).timestamp()))
    issues = []
    for attempt in range(1,13):
        try:
            homepage = read(SITE+"?publication-check="+key+"-"+str(attempt))
            archive = json.loads(read(SITE+"data/articles.json?publication-check="+key+"-"+str(attempt)))
            full_story = read(SITE+"story/"+urllib.parse.quote(slug)+"?publication-check="+key+"-"+str(attempt))
            if not isinstance(archive,list) or latest["id"] not in {x.get("id") for x in archive}:
                raise AssertionError("Latest audited article is missing from public data file")
            if ('id="embedded-articles"' not in homepage or
                    '<article id="lead-story"' not in homepage or
                    '<div class="feed" id="feed">' not in homepage or
                    html.escape(latest["title"],quote=True) not in homepage):
                raise AssertionError("Latest article is not visibly embedded in the actual editorial homepage")
            hero=homepage.split('<article id="lead-story"',1)[1].split('</article>',1)[0]
            if html.escape(latest["title"],quote=True) not in hero:
                raise AssertionError("Newest approved report is missing from the lead-story panel")
            if 'id="static-edition"' in homepage or 'id="latest-published-highlight"' in homepage:
                raise AssertionError("Temporary duplicate debug news panels remain on the public website")
            if (html.escape(latest["title"],quote=True) not in full_story
                    or html.escape(latest["url"],quote=True) not in full_story):
                raise AssertionError("Public full article page is unavailable or missing source attribution")
            print("LIVE_PUBLIC_SITE_OK: "+json.dumps({
                "latest_id":latest["id"],
                "latest_title":latest["title"],
                "public_article_count":len(archive),
                "home":SITE,
                "article_url":SITE+"story/"+slug,
                "attempt":attempt,
            },ensure_ascii=False))
            return
        except Exception as ex:
            issues.append(f"{type(ex).__name__}: {str(ex)[:170]}")
            print(f"LIVE_PUBLIC_SITE_RETRY: {attempt}/12 {issues[-1]}",flush=True)
            if attempt!=12:
                time.sleep(8)
    raise RuntimeError("GitHub Pages deployment failed reader verification: "+issues[-1])


if __name__ == "__main__":
    probe()
