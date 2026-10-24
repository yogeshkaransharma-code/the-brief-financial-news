#!/usr/bin/env python3
"""Keep the repository's own index.html readable, irrespective of Pages source mode.

Only already-approved original articles may be mirrored. No generated/held draft,
private discovery feed or unapproved summary is included. The main HTML remains
the canonical template for the richer public build.
"""
from __future__ import annotations
from pathlib import Path
from build_public import ROOT, esc, valid_articles, standalone_story, story_href

BEGIN = "<!-- THEBRIEF_STATIC_START -->"
END = "<!-- THEBRIEF_STATIC_END -->"


def sync():
    articles=valid_articles()
    latest=max(articles,key=lambda a:(a.get("published_at",""),a["id"]))
    headlines=[]
    for a in articles[:20]:
        href=esc(story_href(a))
        headlines.append(
            '<li style="margin:12px 0 14px">'
            '<a href="'+href+'" style="font-weight:650;color:#44383b">'
            +esc(a["title"])+'</a>'
            '<div style="font-size:11px;color:#776969;margin-top:4px">'
            'News: '+esc(a.get("dateISO",""))+' · Published: '+esc(a.get("published_at","")[:10])
            +' · '+esc(a.get("category",""))+'</div></li>'
        )
    section=(
        '<section id="static-edition" aria-label="Published news edition" '
        'style="background:#fff;border:1px solid #dfd4cf;padding:24px 27px;margin:25px 0 6px">'
        '<p style="margin:0;color:#87404b;font-size:11px;letter-spacing:.13em;font-weight:800">'
        'THE BRIEF · PUBLISHED STORIES · '+str(len(articles))+' ARTICLES</p>'
        '<h2 style="font:500 clamp(29px,4vw,41px)/1.17 Georgia,serif;margin:12px 0">'
        '<a style="color:#332b2e;text-decoration:underline;text-decoration-color:#ad8790" href="'
        +esc(story_href(latest))+'">'+esc(latest["title"])+'</a></h2>'
        '<p style="font-size:15px;color:#685a5b;margin:10px 0">'
        +esc(latest.get("short",""))+'</p>'
        '<p style="font-size:12px;color:#776969;margin:10px 0">'
        'Original news: '+esc(latest.get("dateISO",""))
        +' · Published by The Brief: '+esc(latest.get("published_at","")[:10])
        +'</p>'
        '<p><a href="'+esc(story_href(latest))+
        '" style="color:#87404b;font-weight:750">Read the full report →</a></p>'
        '<details style="border-top:1px solid #e6dddd;padding-top:13px;margin-top:19px" open>'
        '<summary style="font-weight:700;cursor:pointer">All published articles</summary>'
        '<ol style="padding-left:22px;margin-bottom:0">'+''.join(headlines)+'</ol>'
        '</details></section>'
    )
    path=ROOT/"index.html"
    text=path.read_text(encoding="utf-8")
    if text.count(BEGIN)!=1 or text.count(END)!=1:
        raise ValueError("Main homepage static edition markers missing or duplicated")
    prefix,remainder=text.split(BEGIN,1)
    _,suffix=remainder.split(END,1)
    updated=prefix+BEGIN+"\n"+section+"\n"+END+suffix
    if updated!=text:
        path.write_text(updated,encoding="utf-8")
    story_dir=ROOT/"story"
    story_dir.mkdir(exist_ok=True)
    for a in articles:
        path=story_dir/(a["id"]+".html")
        rendered=standalone_story(a)
        if not path.exists() or path.read_text(encoding="utf-8")!=rendered:
            path.write_text(rendered,encoding="utf-8")
    print("REPOSITORY_SITE_SYNC:",len(articles),"approved static full stories; latest",latest["id"])


if __name__=="__main__":
    sync()
