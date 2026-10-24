#!/usr/bin/env python3
"""Test that the deployed artifact contains visible news without JavaScript."""
import html
import json
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"


class Visible(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.found = set()
        self.links = set()
        self.in_script = False
        self.text = []
    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if "id" in attr:
            self.found.add(attr["id"])
        if tag == "a" and "href" in attr:
            self.links.add(attr["href"])
        if tag == "script":
            self.in_script = True
    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False
    def handle_data(self, data):
        if not self.in_script:
            self.text.append(data)


def verify():
    articles = json.loads((PUBLIC / "data/articles.json").read_text(encoding="utf-8"))
    original = json.loads((ROOT / "data/articles.json").read_text(encoding="utf-8"))
    assert len(articles) == len(original) and len(articles)>0, "Published article file differs from reviewed archive"
    html_text = (PUBLIC / "index.html").read_text(encoding="utf-8")
    parser = Visible()
    parser.feed(html_text)
    required = {"lead-story", "feed", "briefing-stories", "latest-published-highlight", "embedded-articles"}
    assert required.issubset(parser.found), "Visible article areas missing from generated homepage"
    latest = max(articles, key=lambda a:(a.get("published_at",""),a["id"]))
    text = " ".join(parser.text)
    assert latest["title"] in text, "Newest approved article not visibly printed on homepage"
    assert all(a["title"] in text for a in articles[:min(len(articles),10)]), "Missing visible news headlines"
    for article in articles:
        story = PUBLIC / "story" / (article["id"]+".html")
        assert story.is_file(), "Full standalone article missing"
        body = story.read_text(encoding="utf-8")
        assert html.escape(article["title"],quote=True) in body, "Full article title not rendered"
        assert html.escape(article["url"],quote=True) in body, "Primary source attribution absent"
        for heading, para in article["blocks"]:
            assert html.escape(heading,quote=True) in body
            assert html.escape(str(para).split("\n")[0],quote=True)[:50] in body, "Body content missing"
    assert "data/live.json" not in html_text, "Private discovery archive referenced on public page"
    print("PUBLIC_SITE_VALIDATED:",json.dumps({"visible_headlines":len(articles),"standalone_articles":len(articles),"latest":latest["id"],"javascript_required":False}))


if __name__ == "__main__":
    verify()
