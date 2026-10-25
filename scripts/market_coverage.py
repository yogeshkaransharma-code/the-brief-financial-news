"""Source-domain directory for The Brief's UK-focused market radar.

A directory entry means an institution's official domain is recognisable when
found through a source citation. It does NOT mean we poll this firm hourly or
that every page on that domain is safe or publishable. The direct index roster
in source_registry.py separately defines independently collected newsrooms.

Only strict press/news publication paths, first-party retrieval, explicit
original dates, complete source text, and downstream independent review permit
an article. No general social feeds, paywall circumvention or site-wide trust.
"""
from __future__ import annotations
import re
from urllib.parse import urlsplit

ORGANISATIONS = {
    "Insurers and protection": (
        ("AXA UK", "axa.co.uk"),
        ("Aviva", "aviva.com"),
        ("Allianz UK", "allianz.co.uk"),
        ("Zurich UK", "zurich.co.uk"),
        ("RSA Insurance", "rsainsurance.co.uk"),
        ("QBE Insurance", "qbe.com"),
        ("Chubb", "chubb.com"),
        ("AIG", "aig.com"),
        ("Ageas UK", "ageas.co.uk"),
        ("Hiscox", "hiscoxgroup.com"),
        ("Admiral Group", "admiralgroup.co.uk"),
        ("Direct Line Group", "directlinegroup.co.uk"),
        ("esure", "esuregroup.com"),
        ("LV=", "lv.com"),
        ("Royal London", "royallondon.com"),
        ("Legal & General", "legalandgeneral.com"),
        ("Phoenix Group", "thephoenixgroup.com"),
        ("Canada Life", "canadalife.co.uk"),
        ("Scottish Widows", "scottishwidows.co.uk"),
        ("Unum UK", "unum.co.uk"),
        ("MetLife", "metlife.com"),
        ("Bupa", "bupa.com"),
        ("Vitality", "vitality.co.uk"),
        ("Covéa Insurance", "coveainsurance.co.uk"),
        ("Markerstudy", "markerstudy.com"),
        ("Hastings Direct", "hastingsdirect.com"),
        ("AXA XL", "axaxl.com"),
        ("Tokio Marine HCC", "tmhcc.com"),
        ("MS Amlin", "msamlin.com"),
        ("Brit Insurance", "britinsurance.com"),
        ("Beazley", "beazley.com"),
        ("Hiscox UK", "hiscox.co.uk"),
        ("Generali", "generali.com"),
        ("Prudential plc", "prudentialplc.com"),
    ),
    "Brokers and intermediaries": (
        ("Howden", "howdengroup.com"),
        ("Marsh", "marsh.com"),
        ("Aon", "aon.com"),
        ("WTW", "wtwco.com"),
        ("Gallagher", "ajg.com"),
        ("Lockton", "lockton.com"),
        ("Ardonagh", "theardonaghgroup.com"),
        ("PIB Group", "pibgroup.co.uk"),
        ("Jensten", "jensten.co.uk"),
        ("Clear Group", "thecleargroup.com"),
        ("Miller", "miller-insurance.com"),
        ("McGill and Partners", "mcgillpartners.com"),
        ("Brown & Brown", "brownandbrown.com"),
        ("Acrisure", "acrisure.com"),
        ("Oneglobal", "oneglobalbroking.com"),
        ("BMS Group", "bmsgroup.com"),
        ("Brokerslink", "brokerslink.com"),
        ("Ryan Specialty", "ryanspecialty.com"),
        ("SRG", "specialistrisk.com"),
        ("Verlingue", "verlingue.co.uk"),
        ("A-Plan (legacy Howden brand)", "aplan.co.uk"),
        ("Arthur J Gallagher Investor Relations", "investor.ajg.com"),
    ),
    "MGAs and market infrastructure": (
        ("DUAL", "dualgroup.com"),
        ("Pen Underwriting", "penunderwriting.co.uk"),
        ("CFC", "cfc.com"),
        ("K2 International", "k2int.com"),
        ("Volante Global", "volanteglobal.com"),
        ("Flood Re", "floodre.co.uk"),
        ("Pool Re", "poolre.co.uk"),
        ("Lloyd's Market", "lloyds.com"),
        ("Lloyd's Market Association", "lmalloyds.com"),
        ("Managing General Agents Association", "mgaa.co.uk"),
        ("BIBA", "biba.org.uk"),
        ("Association of British Insurers", "abi.org.uk"),
        ("International Underwriting Association", "iua.co.uk"),
        ("LIIBA", "liiba.co.uk"),
        ("London Market Group", "lmg.london"),
        ("Chartered Insurance Institute", "cii.co.uk"),
        ("Insurance Fraud Bureau", "insurancefraudbureau.org"),
        ("UK Finance", "ukfinance.org.uk"),
    ),
    "Reinsurers": (
        ("Swiss Re", "swissre.com"),
        ("Munich Re", "munichre.com"),
        ("Hannover Re", "hannover-re.com"),
        ("SCOR", "scor.com"),
        ("RenaissanceRe", "renre.com"),
        ("RGA", "rgare.com"),
    ),
    "Banks, building societies and lenders": (
        ("Barclays", "barclays.com"),
        ("HSBC", "hsbc.com"),
        ("NatWest Group", "natwestgroup.com"),
        ("Lloyds Banking Group", "lloydsbankinggroup.com"),
        ("Santander UK", "santander.co.uk"),
        ("Nationwide", "nationwide.co.uk"),
        ("Virgin Money", "virginmoney.com"),
        ("Monzo", "monzo.com"),
        ("Starling Bank", "starlingbank.com"),
        ("Revolut", "revolut.com"),
        ("Metro Bank", "metrobankonline.co.uk"),
        ("TSB", "tsb.co.uk"),
        ("Co-operative Bank", "co-operativebank.co.uk"),
        ("Handelsbanken", "handelsbanken.co.uk"),
        ("Coutts", "coutts.com"),
        ("Allica Bank", "allica.bank"),
        ("Atom Bank", "atombank.co.uk"),
        ("Zopa", "zopa.com"),
        ("Shawbrook", "shawbrook.co.uk"),
        ("Aldermore", "aldermore.co.uk"),
        ("Paragon Bank", "paragonbank.co.uk"),
        ("Standard Chartered", "sc.com"),
        ("Goldman Sachs", "goldmansachs.com"),
        ("JPMorgan Chase", "jpmorganchase.com"),
        ("Citi", "citigroup.com"),
        ("UBS", "ubs.com"),
        ("Deutsche Bank", "db.com"),
        ("BNP Paribas", "group.bnpparibas"),
    ),
    "Payments and fintech": (
        ("Wise", "wise.com"),
        ("ClearBank", "clear.bank"),
        ("Checkout.com", "checkout.com"),
        ("Adyen", "adyen.com"),
        ("Visa", "visa.com"),
        ("Mastercard", "mastercard.com"),
        ("PayPal", "paypal.com"),
        ("Stripe", "stripe.com"),
        ("GoCardless", "gocardless.com"),
        ("SumUp", "sumup.com"),
    ),
    "Regulators and public bodies": (
        ("Financial Conduct Authority", "fca.org.uk"),
        ("Bank of England and PRA", "bankofengland.co.uk"),
        ("The Pensions Regulator", "thepensionsregulator.gov.uk"),
        ("Financial Ombudsman Service", "financial-ombudsman.org.uk"),
        ("Financial Services Compensation Scheme", "fscs.org.uk"),
        ("Payment Systems Regulator", "psr.org.uk"),
        ("Information Commissioner's Office", "ico.org.uk"),
        ("Office for National Statistics", "ons.gov.uk"),
        ("Pension Protection Fund", "ppf.co.uk"),
        ("Pensions Ombudsman", "pensions-ombudsman.org.uk"),
    ),
}

ORIGINAL_HOSTS = {
    host.lower(): group
    for group, organisations in ORGANISATIONS.items()
    for _name, host in organisations
}
# Distinct named newsroom/release paths only, not /about, /products, /
# or any user-supplied arbitrary URL under a well-known financial brand.
ORIGINAL_NEWS_PATH = re.compile(
    r"^/(?:news|newsroom|press-releases|press-release|media|media-centre|"
    r"news-and-insights|news-insights|investor-relations)/"
    r"(?:[a-z0-9_-]+/){0,5}[a-z0-9_-]{12,}"
    r"(?:\\.(?:html|aspx))?/?$", re.I
)

def directory_lane(url):
    p=urlsplit(url)
    host=(p.hostname or "").lower().removeprefix("www.")
    if p.scheme!="https" or p.username or p.password or p.port not in (None,443) or p.query:
        return None
    group=ORIGINAL_HOSTS.get(host)
    if not group or not ORIGINAL_NEWS_PATH.fullmatch(p.path):
        return None
    if group in {"MGAs and market infrastructure","Regulators and public bodies"}:
        return "official_release"
    return "company_release"

def recognised_original_hosts():
    return set(ORIGINAL_HOSTS)|{"www."+h for h in ORIGINAL_HOSTS}

def self_test():
    assert len(ORIGINAL_HOSTS)>=110,len(ORIGINAL_HOSTS)
    assert directory_lane("https://www.qbe.com/news/press-releases/example-substantive-announcement")=="company_release"
    assert directory_lane("https://www.mgaa.co.uk/news/example-substantive-announcement")=="official_release"
    for url in (
        "https://qbe.com.evil.test/news/press-releases/example-substantive-announcement",
        "http://qbe.com/news/press-releases/example-substantive-announcement",
        "https://qbe.com/insurance-products/something-completely-unrelated",
        "https://www.qbe.com/news/press-releases/?page=3",
        "https://www.qbe.com/news/press-releases/example-substantive-announcement?preview=1",
        "https://qbe.com@other.example/news/example-substantive-announcement",
    ):
        assert directory_lane(url) is None,url
    print("PASS: sector-wide official-domain coverage directory and narrow citation-only release paths")
if __name__=="__main__":self_test()
