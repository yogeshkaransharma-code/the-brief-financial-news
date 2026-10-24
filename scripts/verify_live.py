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
from same_day_policy import published_same_day, clock

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
    archived=json.loads((ROOT/"data/articles.json").read_text(encoding="utf-8"))
    expected=[a for a in archived if published_same_day(a)]
    wanted={a["id"] for a in expected}
    latest=max(expected,key=lambda a:(a.get("published_at",""),a["id"])) if expected else None
    key=str(int(dt.datetime.now(dt.timezone.utc).timestamp()))
    issues=[]
    for attempt in range(1,13):
        try:
            homepage=read(SITE+"?same-day-publication-check="+key+"-"+str(attempt))
            archive=json.loads(read(SITE+"data/articles.json?same-day-publication-check="+key+"-"+str(attempt)))
            if not isinstance(archive,list):
                raise AssertionError("Published public archive must be a JSON list")
            actual={x.get("id") for x in archive}
            if actual!=wanted:
                raise AssertionError("Site has stale stories or is missing approved same-day stories: public="
                    +str(len(actual))+", eligible="+str(len(wanted)))
            if 'id="embedded-articles"' not in homepage or '<article id="lead-story"' not in homepage:
                raise AssertionError("Actual front page or embedded edition missing")
            if 'id="static-edition"' in homepage or 'id="latest-published-highlight"' in homepage:
                raise AssertionError("Old temporary duplicate layout is back")
            for historical in archived:
                if historical["id"] not in wanted and html.escape(historical["title"],quote=True) in homepage:
                    raise AssertionError("Historical announcement presented as today: "+historical["id"])
            if latest:
                story=read(SITE+"story/"+urllib.parse.quote(latest["id"]+".html")
                    +"?same-day-publication-check="+key+"-"+str(attempt))
                hero=homepage.split('<article id="lead-story"',1)[1].split('</article>',1)[0]
                if html.escape(latest["title"],quote=True) not in hero:
                    raise AssertionError("Newest same-day report missing from editorial lead")
                if (html.escape(latest["title"],quote=True) not in story
                        or html.escape(latest["url"],quote=True) not in story):
                    raise AssertionError("Full same-day article page or attribution missing")
            elif "No verified news from today yet" not in homepage:
                raise AssertionError("Empty UK edition must clearly say no verified same-day news")
            print("LIVE_SAME_DAY_SITE_OK: "+json.dumps({
                "uk_date":clock().date().isoformat(),
                "news_today":len(expected),
                "historical_excluded":len(archived)-len(expected),
                "latest":latest["id"] if latest else None,
                "home":SITE
            },ensure_ascii=False))
            return
        except Exception as exc:
            issues.append(type(exc).__name__+": "+str(exc)[:200])
            print("LIVE_SAME_DAY_RETRY: "+str(attempt)+"/12 "+issues[-1],flush=True)
            if attempt!=12:time.sleep(8)
    raise RuntimeError("Actual live site violates same-day-only rule: "+issues[-1])


if __name__ == "__main__":
    probe()
