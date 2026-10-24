#!/usr/bin/env python3
"""Independent real-browser check of the rendered public news on mobile.

This checks actual visible text, click-through and article content, not just
HTTP status or JSON existence. Save screenshots as diagnostic evidence.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from same_day_policy import published_same_day
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
SITE=os.getenv("BRIEF_SITE_URL","https://yogeshkaransharma-code.github.io/the-brief-financial-news/").rstrip("/")+"/"
OUT=ROOT/"browser-evidence"


def main():
    archive=json.loads((ROOT/"data/articles.json").read_text(encoding="utf-8"))
    today=[x for x in archive if published_same_day(x)]
    latest=max(today,key=lambda x:(x.get("published_at",""),x["id"])) if today else None
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        context=browser.new_context(viewport={"width":390,"height":844},
            device_scale_factor=1,is_mobile=True,has_touch=True,
            color_scheme="light",service_workers="block")
        page=context.new_page()
        messages=[]
        page.on("pageerror",lambda error:messages.append(str(error)[:250]))
        page.goto(SITE+"?mobile-reader-verification=same-day",
            wait_until="domcontentloaded",timeout=45000)
        page.wait_for_timeout(2500)
        assert page.locator("#static-edition").count()==0,"Old fallback debug box remains"
        assert page.locator("#lead-story").is_visible(),"Editorial lead not visible"
        visible=page.locator("#home-view").inner_text()
        for old in archive:
            if old["id"] not in {a["id"] for a in today}:
                assert old["title"] not in visible,"Yesterday's article visible in today's news"
        if latest:
            assert latest["title"] in page.locator("#lead-story").inner_text(),"Latest same-day article missing"
            assert page.locator("#feed .news-item").count()>0,"Same-day feed unexpectedly empty"
            target=SITE+"story/"+latest["id"]+".html"
        else:
            assert "No verified news from today yet" in page.locator("#lead-story").inner_text(),\
                "Empty daily edition must be explicit and readable"
            assert page.locator("#feed .news-item").count()==0,\
                "Yesterday's articles carried over to today's feed"
            target=None
        page.screenshot(path=str(OUT/"mobile-home.png"),full_page=True)
        if target:
            page.goto(target,wait_until="domcontentloaded",timeout=45000)
            assert latest["title"] in page.locator("h1").inner_text()
            assert latest["blocks"][0][0] in page.locator("article").inner_text()
            page.screenshot(path=str(OUT/"mobile-article.png"),full_page=True)
        browser.close()
    assert not messages,"Browser JavaScript errors: "+" | ".join(messages)
    print("MOBILE_SAME_DAY_OK:",json.dumps({"articles_today":len(today),
        "old_articles_hidden":len(archive)-len(today),"home":SITE,"story":target}))


if __name__=="__main__":
    main()


if __name__=="__main__":
    main()
