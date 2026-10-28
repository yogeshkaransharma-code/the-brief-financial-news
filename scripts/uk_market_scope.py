"""UK insurance and banking relevance, using the complete source.

Ordinary industry news qualifies. Domestic financial publications and products
supply useful context; overseas stories need a UK market connection.
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
    r"investment\w*|asset manager\w*|fund\w*|wealth|tax\w*|Budget|ISAs?|Chancellor|Treasury|regulat\w*|"
    r"claims?|premiums?|interest rates?|econom\w*|inflation|savings?|business\w*)\b",re.I)
# A clear foreign subject cannot borrow an incidental mention of the UK.
FOREIGN_HEADLINE = re.compile(
    r"\b(?:US|U\.S\.|American|United States|Iowa|Texas|Florida|Georgia|California|New York|"
    r"Boston|Utah|Bermuda|Cayman Islands|Singapore|Dubai|United Arab Emirates|UAE|Canada|Canadian|San Francisco|Philippines|Hong Kong|India|Indian|Italian|Italy|Turkish|T[uü]rkiye|Turkey|"
    r"France|French|Oman|South Korea|Korean|APAC|Asia-Pacific|Mexico|Gulf of Mexico|"
    r"Middle East|European Commission|European Union|EU|Africa|African|Australia|"
    r"Japan|Japanese|Saudi|Iran|Iranian|New Jersey|Strait of Hormuz)\b",re.I)
UK_EFFECT = re.compile(
    r"\b(?:UK|U\.K\.|United Kingdom|British|Britain|English|Scottish|Welsh|London|"
    r"Lloyd['’]s|FCA|PRA)\b[^.!?\n]*\b(?:market|insurer\w*|broker\w*|bank\w*|"
    r"customer\w*|business\w*|operation\w*|regulat\w*|policy|policies|cover|"
    r"distribution|branch\w*|pricing|capacity|lending|claim\w*|premium\w*|"
    r"financ\w*|investment\w*|pension\w*|underwriting|headquarter\w*|based)\b"
    r"|\b(?:market|insurer\w*|broker\w*|bank\w*|customer\w*|business\w*|"
    r"operation\w*|regulat\w*|policy|policies|cover|distribution|branch\w*|"
    r"pricing|capacity|lending|claim\w*|premium\w*|financ\w*|investment\w*|"
    r"pension\w*|underwriting|headquarter\w*|based)\b[^.!?\n]*"
    r"\b(?:UK|U\.K\.|United Kingdom|British|Britain|English|Scottish|Welsh|London|Lloyd['’]s)\b",
    re.I)
# For events centred overseas, the nationality of a global firm is not
# enough: only UK operations, UK customers, UK market rules or London-market
# capacity/pricing count as a demonstrable British-market consequence.
FOREIGN_UK_IMPACT = re.compile(
    r"\b(?:UK|U\.K\.|United Kingdom|London)(?:-based)?\b[^.!?\n]*"
    r"\b(?:market|insur\w*|broker\w*|bank\w*|business\w*|customer\w*|"
    r"operation\w*|policy|cover|capacity|underwriting|pricing|distribution|lending|"
    r"regulat\w*|pension\w*|acquisition|deal)\b"
    r"|\b(?:market|insur\w*|broker\w*|bank\w*|business\w*|customer\w*|"
    r"operation\w*|policy|cover|capacity|underwriting|pricing|distribution|lending|"
    r"regulat\w*|pension\w*|acquisition|deal)\b[^.!?\n]*\b(?:UK|U\.K\.|United Kingdom|London)\b",
    re.I)

FOREIGN_UK_ACTION = re.compile(
    r"\b(?:affect\w*|impact\w*|chang\w*|acquir\w*|purchas\w*|buy\w*|bought|"
    r"expand\w*|launch\w*|suppl\w*|provid\w*|offer\w*|underwrit\w*|invest\w*|"
    r"regulat\w*|operat\w*|withdraw\w*|target\w*|reduc\w*|increas\w*|"
    r"enter\w*|sell\w*|settle\w*|clos\w*|fund\w*|deliver\w*|seek\w*|secur\w*)\b", re.I)

# Cash ISAs and the British fiscal institutions behind UK Budget decisions are
# domestic financial subjects even when a journalist's headline omits "UK".
# They must be evidenced in the report itself, not merely appended by AI.
UK_FINANCIAL_POLICY = re.compile(
    r"\b(?:cash\s+ISAs?|ISAs?|ISA\s+allowance|individual\s+savings\s+accounts?|"
    r"HM\s+Treasury|Chancellor\s+of\s+the\s+Exchequer)\b",re.I
)

UK_AUTHORITIES = {
    "fca.org.uk", "bankofengland.co.uk", "thepensionsregulator.gov.uk",
    "financial-ombudsman.org.uk", "ukfinance.org.uk", "abi.org.uk"
}

def _strip_attribution(text):
    return re.sub(r"^\s*According to [^,]{1,95},\s*", "", str(text or ""),flags=re.I)

UK_SPECIALIST_HOSTS = {
    "insuranceage.co.uk", "insurancetimes.co.uk", "professionalpensions.com",
    "investmentweek.co.uk", "moneymarketing.co.uk", "mortgagesolutions.co.uk"
}
UK_POLICY = re.compile(
    r"\b(?:OBR|Office for Budget Responsibility|HMRC|HM Treasury|"
    r"Chancellor of the Exchequer|cash ISAs?|individual savings accounts?|"
    r"VCTs?|venture capital trusts?|pension triple lock|"
    r"Mineworkers.? Pension Scheme|Pension Protection Fund)\b", re.I)

def uk_market_reason(item, source_text=""):
    """Assess the whole report, without an opening-paragraph or word-gap veto."""
    title=str(item.get("title") or "")
    short=_strip_attribution(item.get("short") or "")
    text=_strip_attribution(source_text) if source_text else title+" "+short
    host=(urlsplit(str(item.get("url") or "")).hostname or "").lower().removeprefix("www.")
    if not (FINANCE.search(title+" "+text) or named_financial_institution(title)):
        return ""
    if host in UK_AUTHORITIES:
        return "UK financial authority publication"
    # A negated comparison is not an assertion that the UK product is affected.
    evidence=re.sub(r"(?i)\bnot (?:UK|British|United Kingdom)\b[^.!?\n]*","",text)
    if UK_POLICY.search(evidence):
        return "UK financial product, pensions or fiscal policy"
    if FOREIGN_HEADLINE.search(title):
        # Read every paragraph. Foreign news is eligible when the source
        # describes activity involving UK markets, businesses or customers.
        for paragraph in re.split(r"\n+",evidence):
            if re.search(r"(?i)\b(?:career began|career started|started at|previously worked)\b",paragraph):
                continue
            if FOREIGN_UK_IMPACT.search(paragraph) and FOREIGN_UK_ACTION.search(paragraph):
                return "Overseas development involving UK financial markets or businesses"
        return ""
    if UK.search(evidence):
        return "UK financial subject established in the full source"
    if host in UK_SPECIALIST_HOSTS and not FOREIGN_HEADLINE.search(evidence[:600]):
        return "Domestic financial news from a UK specialist publication"
    # UK firms' ordinary announcements need not repeat their home country.
    if UK_BUSINESS.search(evidence) and not FOREIGN_HEADLINE.search(evidence[:600]):
        return "UK financial institution development"
    return ""

def in_uk_scope(item,source_text=""):
    return bool(uk_market_reason(item,source_text))

def public_article_in_scope(article):
    # Published wording is all we retain on public pages. Never assume that a
    # UK-registered publisher, a UK source date or a global finance brand implies
    # a connection to the British market.
    if article.get('uk_market_basis'):return True  # Established from the captured source before writing.
    blocks=article.get("blocks") or []
    body=" ".join(str(x[1]) for x in blocks if isinstance(x,list) and len(x)>1)
    return in_uk_scope(article,body)

# Discovery priority is NOT editorial approval. Headlines from recognised UK
# financial firms and UK specialist publications should be read before general
# international feeds, but all must still establish a factual UK connection.
UK_BUSINESS = re.compile(
    r"\b(?:Aviva|NatWest|Barclays|HSBC|Lloyds Banking|Nationwide|Legal & General|"
    r"Royal London|M&G|Quilter|Admiral|Direct Line|Hiscox|Beazley|Ardonagh|"
    r"Howden|BIBA|British Insurance Brokers|ABI|FCA|PRA|FSCS|"
    r"Bank of England|UK Finance|UK Budget|HM Treasury)\b", re.I)
UK_TRADE_PUBLISHERS = {
    "Insurance Business UK", "Insurance Times", "Insurance Age",
    "Professional Pensions", "Investment Week", "Money Marketing",
    "Mortgage Solutions", "The Guardian Banking", "The Guardian Insurance",
    "The Guardian Money", "BBC Business", "Sky Business"
}

def discovery_priority(item):
    """Rank which source to READ first; never determine publication eligibility."""
    title=str(item.get("title") or "")
    host=(urlsplit(str(item.get("url") or "")).hostname or "").lower().removeprefix("www.")
    if host in UK_AUTHORITIES or UK.search(title) or UK_BUSINESS.search(title):
        return 2
    if str(item.get("source") or "") in UK_TRADE_PUBLISHERS:
        return 1
    return 0

def sample_uk_first(candidates,attempts,now,limit=40):
    """Use source-read budget on fresh UK leads before cooling/global leads.

    Leave some places for international developments that truly affect UK
    markets. Reuse existing fair-source ordering within each priority group.
    """
    from newsroom_state import cooling
    from media_sources import diverse
    eligible=[item for item in candidates if not cooling(attempts.get(item["url"],{}),now)]
    cooling_items=[item for item in candidates if cooling(attempts.get(item["url"],{}),now)]
    priorities=[ [i for i in eligible if discovery_priority(i)==score] for score in (2,1,0) ]
    selected=[]
    for pool,quota in zip(priorities,(28,8,4)):
        selected.extend(diverse(pool,min(quota,limit-len(selected))))
    # Unused slots return to UK sources before exhausting general coverage.
    for pool in priorities+[cooling_items]:
        if len(selected)>=limit:break
        remainder=[i for i in pool if i not in selected]
        selected.extend(diverse(remainder,limit-len(selected)))
    return selected

def named_financial_institution(title):
    """Recognise a sector firm's own announcement without requiring jargon.

    Only a title signal. The source, UK market evidence and original publication
    date are independently checked before any writing or publishing.
    """
    from market_coverage import ORGANISATIONS
    text=str(title or "")
    return any(re.search(r"(?<!\w)"+re.escape(name)+r"(?!\w)",text,re.I)
               for group in ORGANISATIONS.values()
               for name,host in group if len(name)>=4)
