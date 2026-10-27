"""Offline design, ranking and analytics safeguards; no network or provider calls."""
from pathlib import Path
from tempfile import TemporaryDirectory
from reader_analytics import install, beacon, token_from_env, TOKEN_NAME
from reader_experience import lead_article, other_briefs, priority
from unittest.mock import patch

def main():
    items=[
      {"id":"1","title":"Florida company appoints chief officer","short":"The US appointment", "source":"Overseas News"},
      {"id":"2","title":"FCA consults on UK insurance sales rules","short":"Consultation affects UK firms","source":"Financial Conduct Authority"},
      {"id":"3","title":"US insurer reports results","short":"US figures", "source":"Overseas News"},
    ]
    assert lead_article(items)["id"]=="2"
    assert all(x["id"]!="2" for x in other_briefs(items,items[1])), "Briefing repeats the lead"
    assert other_briefs(items[:1],items[0])==items[:1], "Quiet edition must still show the one story"
    assert lead_article([]) is None
    assert priority(items[1]) > priority(items[0])
    with patch.dict("os.environ",{TOKEN_NAME:""},clear=False):
        assert token_from_env()==""
    with patch.dict("os.environ",{TOKEN_NAME:"not-a-token"},clear=False):
        try:token_from_env()
        except ValueError:pass
        else:raise AssertionError("Invalid beacon token silently accepted")
    token="0123456789abcdef0123456789abcdef"
    with TemporaryDirectory() as td:
        public=Path(td);(public/"story").mkdir()
        for path in (public/"index.html",public/"story"/"sample.html"):
            path.write_text("<!doctype html><html><head><title>Test</title></head><body>OK</body></html>")
        assert install(public,"")["mode"]=="not_connected"
        assert not (public/"index.html").read_text().count("cloudflareinsights")
        assert install(public,token)["pages"]==2
        for file in (public/"index.html",public/"story"/"sample.html"):
            text=file.read_text()
            assert text.count("cloudflareinsights.com/beacon.min.js")==1
            assert 'data-cf-beacon=' in text
            assert '<script type="module"' in text, 'Cloudflare requires modern module beacon'
            assert text.index('cloudflareinsights.com/beacon.min.js') < text.index('</body>'), 'Beacon after body end'
            assert text.index('cloudflareinsights.com/beacon.min.js') > text.index('</head>'), 'Beacon should be in body'
    print("PASS: grounded UK lead, distinct briefings, invalid token rejection, site-wide opt-in analytics")
if __name__=="__main__":main()
