#!/usr/bin/env python3
"""Keep the repository Pages fallback aligned with today's actual UK news.

Historical audit articles stay in data/articles.json, not on today's public
homepage. No old standalone news pages are carried into the live website.
"""
from __future__ import annotations
from build_public import ROOT, esc, valid_articles, standalone_story, story_href, legacy_story_href, legacy_redirect
from same_day_policy import published_same_day, clock

BEGIN = "<!-- THEBRIEF_STATIC_START -->"
END = "<!-- THEBRIEF_STATIC_END -->"


def sync():
    today=clock().date().strftime("%-d %B %Y")
    archive=valid_articles()
    from uk_market_scope import public_article_in_scope
    articles=[a for a in archive if published_same_day(a) and public_article_in_scope(a)]
    if articles:
        headlines="".join(
            '<li><a href="'+esc(story_href(a))+'">'+esc(a["title"])+'</a></li>'
            for a in articles
        )
        section=('<section id="static-edition" aria-label="Same-day approved news" '
            'style="padding:18px 22px;background:white;margin:20px 0;border-top:2px solid #87404b">'
            '<p style="font:700 11px Arial,sans-serif">VERIFIED UK NEWS · '+esc(today)+'</p>'
            '<ul>'+headlines+'</ul></section>')
    else:
        section=('<section id="static-edition" aria-label="Same-day news status" '
            'style="padding:14px 0;margin:12px 0">'
            '<p style="font:600 12px Arial,sans-serif;color:#87404b">'
            'No verified first-party news dated '+esc(today)+' yet. '
            'Yesterday’s releases are not today’s news.</p></section>')
    path=ROOT/"index.html"
    text=path.read_text(encoding="utf-8")
    if text.count(BEGIN)!=1 or text.count(END)!=1:
        raise ValueError("Homepage same-day markers missing or repeated")
    prefix,tail=text.split(BEGIN,1)
    _,suffix=tail.split(END,1)
    updated=prefix+BEGIN+"\n"+section+"\n"+END+suffix
    if updated!=text:
        path.write_text(updated,encoding="utf-8")
    story_dir=ROOT/"story"
    story_dir.mkdir(exist_ok=True)
    live={story_href(a).split("/",1)[1] for a in archive}
    live.update(legacy_story_href(a).split("/",1)[1] for a in archive)
    for obsolete in story_dir.glob("*.html"):
        if obsolete.name not in live:
            obsolete.unlink()
    for a in archive:
        story=story_dir/story_href(a).split("/",1)[1]
        rendered=standalone_story(a)
        if not story.exists() or story.read_text(encoding="utf-8")!=rendered:
            story.write_text(rendered,encoding="utf-8")
        old=story_dir/legacy_story_href(a).split("/",1)[1]
        redirect=legacy_redirect(a)
        if not old.exists() or old.read_text(encoding="utf-8")!=redirect:
            old.write_text(redirect,encoding="utf-8")
    print("REPOSITORY_SAME_DAY_SYNC:",len(articles),"genuinely same-day original(s); UK date",today)


if __name__=="__main__":
    sync()

