"""The Brief's strict UK-market remit.

A UK *publication date* or a UK publisher is not evidence of UK impact.
Require a concrete UK connection in the actual development. No model call,
geolocation inference, British-company-name shortcut or speculative angle.

This conservative screen is a first-pass eligibility check, not fact-checking.
"""
import re
from urllib.parse import urlsplit

# UK locus, consumers, intermediary market or domestic authorities. Avoid a
# bare 'Lloyds' token (it may occur as a name in another market).
UK = re.compile(
    r"\b(?:UK|U\.K\.|United Kingdom|Britain|British|England|English|Scotland|Scottish|Wales|Welsh|"
    r"Northern Ireland|London|Manchester|Birmingham|Leeds|Bristol|Edinburgh|Glasgow|Surrey|"
    r"FCA|PRA|Bank of England|Financial Conduct Authority|Prudential Regulation Authority|"
    r"Financial Ombudsman(?: Service)?|The Pensions Regulator|Lloyd['’]s(?: of London)?|"
    r"Lloyds Banking Group|Nationwide Building Society|FSCS|UK Finance|ABI|"
    r"Association of British Insurers)\b", re.I)
FINANCE = re.compile(
    r"\b(?:insur\w*|broker\w*|underwrit\w*|reinsur\w*|MGA|Lloyd['’]s|pension\w*|"
    r"bank\w*|lending|loan\w*|mortgage\w*|credit|finance|financ\w*|payment\w*|"
    r"investment\w*|asset manager\w*|fund\w*|wealth|tax\w*|Budget|regulat\w*|"
    r"claims?|premiums?|interest rates?|econom\w*|inflation|savings?|business\w*)\b",re.I)
# A clear foreign subject cannot borrow an incidental mention of the UK.
FOREIGN_HEADLINE = re.compile(
    r"\b(?:US|U\.S\.|American|United States|Iowa|Texas|Florida|Georgia|California|New York|"
    r"Boston|Utah|Philippines|Hong Kong|India|Indian|Italian|Italy|Turkish|T[uü]rkiye|Turkey|"
    r"France|French|Oman|South Korea|Korean|APAC|Asia-Pacific|Mexico|Gulf of Mexico|"
    r"Middle East|European Commission|European Union|EU|Africa|African|Australia|"
    r"Japan|Japanese|Saudi|Iran|Iranian|New Jersey|Strait of Hormuz)\b",re.I)
UK_EFFECT = re.compile(
    r"\b(?:UK|U\.K\.|United Kingdom|British|Britain|English|Scottish|Welsh|London|"
    r"Lloyd['’]s|FCA|PRA)\b.{0,85}\b(?:market|insurer\w*|broker\w*|bank\w*|"
    r"customer\w*|business\w*|operation\w*|regulat\w*|policy|policies|cover|"
    r"distribution|branch\w*|pricing|capacity|lending|claim\w*|premium\w*|"
    r"financ\w*|investment\w*|pension\w*|underwriting|headquarter\w*|based)\b"
    r"|\b(?:market|insurer\w*|broker\w*|bank\w*|customer\w*|business\w*|"
    r"operation\w*|regulat\w*|policy|policies|cover|distribution|branch\w*|"
    r"pricing|capacity|lending|claim\w*|premium\w*|financ\w*|investment\w*|"
    r"pension\w*|underwriting|headquarter\w*|based)\b.{0,85}"
    r"\b(?:UK|U\.K\.|United Kingdom|British|Britain|English|Scottish|Welsh|London|Lloyd['’]s)\b",
    re.I)
# For events centred overseas, the nationality of a global firm is not
# enough: only UK operations, UK customers, UK market rules or London-market
# capacity/pricing count as a demonstrable British-market consequence.
FOREIGN_UK_IMPACT = re.compile(
    r"\\b(?:UK|U\\.K\\.|United Kingdom|London)(?:-based)?\\b.{0,85}"
    r"\\b(?:market|insur\\w*|broker\\w*|bank\\w*|business\\w*|customer\\w*|"
    r"operation\\w*|policy|cover|capacity|underwriting|pricing|distribution|lending|"
    r"regulat\\w*|pension\\w*|acquisition|deal|based)\\b"
    r"|\\b(?:market|insur\\w*|broker\\w*|bank\\w*|business\\w*|customer\\w*|"
    r"operation\\w*|policy|cover|capacity|underwriting|pricing|distribution|lending|"
    r"regulat\\w*|pension\\w*|acquisition|deal)\\b.{0,85}\\b(?:UK|U\\.K\\.|United Kingdom|London)\\b",
    re.I)

UK_AUTHORITIES = {
    "fca.org.uk", "bankofengland.co.uk", "thepensionsregulator.gov.uk",
    "financial-ombudsman.org.uk", "ukfinance.org.uk", "abi.org.uk"
}

def _strip_attribution(text):
    return re.sub(r"^\s*According to [^,]{1,95},\s*", "", str(text or ""),flags=re.I)

def uk_market_reason(item, source_text=""):
    """Return an explicit, grounded UK-market basis, else empty string.

    Source text is article text, not publisher, RSS title, footer or feed name.
    Standfirst and body may establish a real UK link missing from the headline.
    In clearly overseas-headlined stories, the UK *impact* must be explicit.
    """
    title=str(item.get("title") or "")
    short=_strip_attribution(item.get("short") or "")
    title_short=" ".join((title, short))
    excerpt=_strip_attribution(str(source_text or ""))[:2400]
    host=(urlsplit(str(item.get("url") or "")).hostname or "").lower().removeprefix("www.")
    if not FINANCE.search(title_short+" "+excerpt[:550]):
        return ""
    if host in UK_AUTHORITIES:
        return "UK financial authority publication"
    if source_text and not UK.search(excerpt[:2200]):
        return ""  # UK assertion in a candidate headline alone is not evidence
    if FOREIGN_HEADLINE.search(title) and not UK.search(title):
        # A comparison or passing reference to London is insufficient. Only
        # evidence that the foreign development operates in/affects UK markets.
        if FOREIGN_UK_IMPACT.search(short) or FOREIGN_UK_IMPACT.search(excerpt[:1300]):
            return "Overseas development with explicitly evidenced UK-market connection"
        return ""
    if UK.search(title):
        return "UK financial-market subject identified in headline"
    if UK_EFFECT.search(short):
        return "UK financial-market subject identified in standfirst"
    if UK_EFFECT.search(excerpt[:1500]):
        return "UK financial-market subject supported by source's opening content"
    return ""

def in_uk_scope(item,source_text=""):
    return bool(uk_market_reason(item,source_text))

def public_article_in_scope(article):
    # Published wording is all we retain on public pages. Never assume that a
    # UK-registered publisher, a UK source date or a global finance brand implies
    # a connection to the British market.
    blocks=article.get("blocks") or []
    body=" ".join(str(x[1]) for x in blocks if isinstance(x,list) and len(x)>1)
    return in_uk_scope(article,body)
