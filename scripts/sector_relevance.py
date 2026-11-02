"""Keep The Financial Edition focused on insurance, banking and connected finance.

A headline about tax, gambling, property or a generic business is not
financial-services news just because it mentions a bank or the Budget.
"""
import re
from urllib.parse import urlsplit

SECTOR = re.compile(
    r"\b(?:bank\w*|building societ\w*|insur\w*|reinsur\w*|underwrit\w*|"
    r"broker\w*|insurance intermediary|MGA[s]?|Lloyd['’]s(?: of London)?|London Market Group|"
    r"mortgage\w*|lend\w*|loan\w*|credit cards?|consumer credit|"
    r"payments?|fintech|financial services?|financial firms?|"
    r"FCA|PRA|Bank of England|financial ombudsman|FSCS|"
    r"pension\w*|retirement funds?|annuit(?:y|ies)|employee benefits?|"
    r"group life|protection insurance|investment\w*|asset manag\w*|"
    r"wealth manag\w*|fund manag\w*|investment funds?|VCTs?|"
    r"cash ISAs?|ISAs?|saving\w* accounts?|deposits?|"
    r"solvency|actuar\w*|premiums?|policyholders?|"
    r"capital markets?|bond markets?|bond yields?|gilts?|"
    r"foreign exchange|FX payments?|private credit|"
    r"Pension Protection Fund|PPF)\b", re.I
)
OFF_TOPIC = re.compile(
    r"\b(?:slot machines?|bingo licen[sc]es?|gambling venues?|casinos?|"
    r"lotter(?:y|ies)|sports betting|horse racing|house prices?|"
    r"housing prices?|housing market|property prices?|below asking price|"
    r"homes? (?:selling|sold|for sale)|homes?\\s+(?:\\w+\\s+){0,8}(?:sell|sold|selling)\\b|property asking prices?|"
    r"shopping vouchers?|retail discount\w*|celebrity|recipe\w*|"
    r"cinema tickets?|football results?)\b", re.I
)
DIRECT_PRODUCT = re.compile(
    r"\b(?:insur\w*|reinsur\w*|mortgage\w*|lend\w*|loans?|"
    r"banking(?: services?| products?| operations?)?|bank accounts?|"
    r"credit cards?|consumer credit|deposits?|payments?|savings accounts?|"
    r"pension\w*|underwrit\w*|broker\w*|asset management|"
    r"wealth management|investment fund\w*|annuities|annuity)\b",re.I
)
GENERAL_ONLY = re.compile(
    r"\b(?:budget|tax|taxation|tax polic\w*|business rates?|"
    r"treasury|chancellor|fiscal|cost of living)\b", re.I
)
FINANCIAL_FIRMS = re.compile(
    r"\b(?:Aviva|AXA|Allianz|Zurich|Chubb|Hiscox|Beazley|"
    r"Admiral|Direct Line|Ageas|Aon|Marsh|Gallagher|Howden|"
    r"Barclays|HSBC|NatWest|Lloyds Banking Group|"
    r"Nationwide|Santander|Monzo|Starling|Coutts|"
    r"Rathbones|Quilter|Legal\s*(?:&|and)\s*General|"
    r"Standard Life|Royal London|M&G|PPF|"
    r"UK Finance|ABI|British Insurance Brokers|BIBA|"
    r"FCA|PRA|Financial Ombudsman|Bank of England)\b",re.I
)
SPECIALIST_HOSTS = {
    "insurancebusinessmag.com", "reinsurancene.ws", "commercialriskonline.com",
    "insurancejournal.com", "insurancetimes.co.uk", "insuranceage.co.uk",
    "professionalpensions.com", "investmentweek.co.uk", "moneymarketing.co.uk",
    "mortgagesolutions.co.uk", "finextra.com"
}


def unsuitable_general_headline(title):
    title = str(title or "")
    if SECTOR.search(title):
        return False
    return bool(OFF_TOPIC.search(title) or GENERAL_ONLY.search(title))


def in_sector_scope(item, source_text=""):
    """Check the actual topic, not the publisher's broad finance reputation."""
    headline = str(item.get("source_title") or item.get("title") or "")
    article_title = str(item.get("title") or "")
    short = str(item.get("short") or "")
    titles = headline + " " + article_title
    # A bank quoted about house prices, gambling or retail is still not
    # a banking story unless the headline concerns an actual financial product.
    if OFF_TOPIC.search(titles) and not DIRECT_PRODUCT.search(titles):
        return False
    if SECTOR.search(titles):
        return True
    if unsuitable_general_headline(titles):
        # Budget headlines can be brief; an explicit pension/banking/insurance
        # subject in the article summary still makes the policy relevant.
        # Gambling, retail and lifestyle headlines remain excluded.
        return not OFF_TOPIC.search(titles) and bool(SECTOR.search(short))
    # Some firm announcements use company names without naming their product.
    # Require an actual financial-services connection in the captured report.
    if FINANCIAL_FIRMS.search(titles):
        return not source_text or bool(SECTOR.search(source_text[:3500]))
    host = (urlsplit(str(item.get("url") or "")).hostname or "").lower().removeprefix("www.")
    if host in SPECIALIST_HOSTS and SECTOR.search(titles + " " + short + " " + str(source_text)[:2200]):
        return True
    return False


def self_test():
    def story(title, **kwargs):
        return dict(title=title, **kwargs)
    assert not in_sector_scope(story("High street slot machine venues could bypass budget tax rise via bingo licences",
                                     url="https://www.theguardian.com/society/2026/nov/01/slot-machine-venues"),
                               "Bingo venues in London face higher tax.")
    assert not in_sector_scope(story("Letters critique budget measures and tax policies"))
    assert not in_sector_scope(story("Eight in 10 homes sell below asking price, Coutts finds"),
                               "Coutts reviewed luxury housing prices in London.")
    assert not in_sector_scope(story("Eight in 10 prime London homes sell below asking price, Coutts reveals"),
                               "Coutts is a private bank reporting on property prices.")
    assert in_sector_scope(story("Mortgage lenders reduce rates as house prices change"))
    assert in_sector_scope(story("UK insurance brokers report cyber policy changes"))
    assert in_sector_scope(story("London Market Group launches Talent Finder for small firms")), "UK insurance market body must remain in scope"
    assert in_sector_scope(story("UK Finance publishes banking-sector tax report"))
    assert in_sector_scope(story("FCA consults on mortgage lending changes"))
    assert in_sector_scope(story("PPF confirms pension protection levy plans"))
    assert in_sector_scope(story("Aviva announces leadership changes"),
                           "Aviva is an insurance company announcing new executives.")
    assert in_sector_scope(story("HSBC reports its quarterly results"), "Banking income and deposits rose.")
    assert in_sector_scope(story("Overseas insurer changes London-market underwriting capacity"))
    assert not in_sector_scope(story("Gambling tax rise in the Budget"))
    print("PASS: financial-sector relevance, pensions/payments and unrelated budget stories")


if __name__ == "__main__":
    self_test()
