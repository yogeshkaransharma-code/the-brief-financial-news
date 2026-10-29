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
    assert other_briefs(items[:1],items[0])==[], "Do not duplicate the only lead story"
    assert lead_article([]) is None
    assert priority(items[1]) > priority(items[0])
    substantive={"id":"market","title":"NatWest reports business lending losses",
                 "short":"UK borrowers and businesses face higher borrowing costs","source":"NatWest Group"}
    routine={"id":"personnel","title":"FCA appoints director",
             "short":"The regulator names a new director","source":"Financial Conduct Authority"}
    assert lead_article([routine,substantive])["id"]=="market", "Routine regulator story displaced material banking news"
    fca_domain={"id":"scam","title":"FCA warns consumers over unauthorised firm www.hedgemarksecuritiesllc.com",
                "short":"The FCA issued a warning about a single unregistered business",
                "source":"Financial Conduct Authority"}
    fiscal={"id":"budget","title":"Chancellor Healey announces £65bn in additional borrowing in autumn fiscal statement",
            "short":"The UK chancellor confirmed additional borrowing in a fiscal statement",
            "source":"BBC Business"}
    assert lead_article([fca_domain,fiscal])["id"]=="budget", "Individual FCA scam warning displaced UK fiscal development"
    assert priority(fca_domain)<priority(fiscal)
    assert priority(fca_domain)<priority(substantive)
    # A hydrated homepage should keep its ranking aligned with the server.
    client=(Path(__file__).resolve().parents[1]/'index.html').read_text()
    assert 'const singleFirmWarning=' in client
    assert 'const domainInTitle=' in client
    assert 'if(singleFirmWarning.test(title))points-=18' in client
    assert 'if(budgetMarket.test(title))points+=10' in client
    across=[
        {"id":"lead","title":"UK insurer reports a policy change","category":"Insurance"},
        {"id":"next1","title":"First follow-up","category":"Insurance"},
        {"id":"next2","title":"Second follow-up","category":"Insurance"},
        {"id":"next3","title":"Third follow-up","category":"Insurance"},
        {"id":"bank","title":"UK lender's results","category":"Banking"},
    ]
    chosen=other_briefs(across,across[0])
    assert len(chosen)==3 and {a["id"] for a in chosen}=={"next1","next2","bank"}, "Other sector should get a place"
    assert all(a["id"]!="lead" for a in chosen)
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
