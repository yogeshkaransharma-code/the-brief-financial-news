#!/usr/bin/env python3
"""Independent real-browser check of the rendered public news on mobile.

This checks actual visible text, click-through and article content, not just
HTTP status or JSON existence. Save screenshots as diagnostic evidence.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
SITE=os.getenv("BRIEF_SITE_URL","https://yogeshkaransharma-code.github.io/the-brief-financial-news/").rstrip("/")+"/"
OUT=ROOT/"browser-evidence"


def main():
    approved=json.loads((ROOT/"data/articles.json").read_text(encoding="utf-8"))
    assert approved,"There are no editorially approved full articles"
    latest=max(approved,key=lambda x:(x.get("published_at",""),x["id"]))
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        context=browser.new_context(
            viewport={"width":390,"height":844},
            device_scale_factor=1,
            is_mobile=True,
            has_touch=True,
            color_scheme="light",
            service_workers="block")
        page=context.new_page()
        messages=[]
        page.on("pageerror",lambda error: messages.append(str(error)[:250]))
        page.goto(SITE+"?mobile-reader-verification=20261024",
            wait_until="domcontentloaded",timeout=45000)
        page.wait_for_timeout(3500)
        assert page.locator("#static-edition").count()==0,"Temporary emergency list spoiled the mobile design"
        assert page.locator("#latest-published-highlight").count()==0,"Redundant latest-story panel is still present"
        assert page.locator("#lead-story").is_visible(),"Editorial lead story is not visible on mobile"
        assert latest["title"] in page.locator("#lead-story").inner_text(),\
            "Latest published original article isn't the lead story on mobile"
        assert page.locator("#briefing-stories .briefing-story").count()>0,"Sixty-second briefing is empty"
        assert page.locator("#feed .news-item").count()>0,"No articles are visibly rendered in main news feed"
        assert page.locator("#feed .news-item").first.is_visible(),"News feed is not visible to mobile readers"
        page.screenshot(path=str(OUT/"mobile-home.png"),full_page=True)
        target=SITE+"story/"+latest["id"]+".html"
        page.goto(target,wait_until="domcontentloaded",timeout=45000)
        page.wait_for_timeout(500)
        assert latest["title"] in page.locator("h1").inner_text(),"Full story headline is not rendered"
        assert latest["blocks"][0][0] in page.locator("article").inner_text(),"Full story body is missing"
        assert page.get_by_text("Original evidence").count() or page.get_by_text("Original source").count(),\
            "Attribution to primary source is not visible"
        page.screenshot(path=str(OUT/"mobile-article.png"),full_page=True)
        browser.close()
    if messages:
        raise AssertionError("Homepage JavaScript crashed in a real mobile browser: "+" | ".join(messages)[:500])
    print("MOBILE_READER_OK:",json.dumps({"latest":latest["id"],"home":SITE,
          "story":target,"screenshots":["mobile-home.png","mobile-article.png"],
          "articles_in_archive":len(approved)}))


if __name__=="__main__":
    main()
