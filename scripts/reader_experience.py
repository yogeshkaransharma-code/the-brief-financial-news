"""Presentation-only story hierarchy for The Brief.

Never edits article content, source facts, dates, editorial statuses or the archive.
This heuristic is editorial triage, not a verified relevance assessment.
"""
import re

UK = re.compile(r"\b(?:UK|United Kingdom|British|Britain|England|English|Scottish|Scotland|Welsh|Wales|Northern Ireland|London|Manchester|Birmingham|Leeds|Bristol|FCA|PRA|Bank of England|Financial Ombudsman|Lloyd['’]?s of London|UK Budget)\b", re.I)
BIG = re.compile(r"\b(?:regulator|regulation|consultation|court rules|court ruling|acquisition|merger|earnings|results|profit|capital|underwriting|claims|insolvenc|business lending|interest rates|FCA|PRA|financial distress)\b", re.I)
ROUTINE = re.compile(r"\b(?:appoints|appointed|promotion|promotes|names|webinar|award|shortlist|demo day)\b", re.I)
FOREIGN = re.compile(r"\b(?:US|U\.S\.|American|Florida|Georgia|California|New York|Utah|Boston|Hong Kong|APAC|Asia-Pacific)\b", re.I)
# Presentation only: a warning about one named scam or clone firm belongs in
# Latest Reporting, not ahead of broader UK market developments on the cover.
SINGLE_FIRM_WARNING = re.compile(r"\b(?:unauthorised firm|unauthorized firm|clone firm|fake firm|unregistered firm)\b", re.I)
DOMAIN_IN_TITLE = re.compile(r"\b(?:www\.|[a-z0-9-]+\.(?:com|co\.uk|net|org|io)\b)", re.I)
BUDGET_MARKET = re.compile(r"\b(?:chancellor|budget|treasury|fiscal statement)\b.*\b(?:borrow\w*|fiscal|bank\w*|pension\w*|tax\w*|funding)\b", re.I)

def priority(a):
    """Presentation-only proxy for practical UK significance, not fact-checking.

    A regulator's name alone does not make a routine announcement the lead.
    Evidence of wider customer or commercial impact counts more, while a
    small appointment cannot automatically outrank substantive market news.
    """
    title = str(a.get("title", ""))
    summary = str(a.get("short", ""))
    source = str(a.get("source", ""))
    status = str(a.get("status", ""))
    points = 0
    if UK.search(title):
        points += 7
    elif UK.search(summary):
        points += 3
    if re.search(r"\b(?:interest rates?|lending costs?|capital requirements?|new rules?|final rules?|regulatory change|claims costs?|profit warning|earnings|financial results|losses|underwriting|premiums?|reinsurance|merger|acquisition|insolvency|funding|business lending|customer redress)\b", title, re.I):
        points += 7
    if re.search(r"\b(?:customers?|policyholders?|borrowers?|brokers?|businesses|firms|households|employers|employees|lenders)\b", summary, re.I):
        points += 3
    if re.search(r"\b(?:Financial Conduct Authority|Prudential Regulation Authority|Bank of England|FCA|PRA)\b", source, re.I):
        points += 2
    if re.search(r"\b(?:published policy|confirmed announcement)\b", status, re.I):
        points += 2
    if ROUTINE.search(title):
        points -= 11
    if SINGLE_FIRM_WARNING.search(title):
        points -= 18
    if DOMAIN_IN_TITLE.search(title):
        points -= 8
    if BUDGET_MARKET.search(title):
        points += 10
    if FOREIGN.search(title) and not UK.search(title):
        points -= 6
    return points

def lead_article(articles):
    if not articles:return None
    # Preserve publication recency as tiebreaker; do not touch the actual feed order.
    return max(enumerate(articles), key=lambda pair:(priority(pair[1]), -pair[0]))[1]

def other_briefs(articles, lead, limit=3):
    """Up to three *other* reports, with both desks represented when available.

    Do not repeat the hero or manufacture extra stories on a quiet news day.
    Preserve the supplied newest-first order except when making room for
    the other sector, and never fill space with archive articles.
    """
    if lead is None or limit <= 0:
        return []
    eligible = [a for a in articles if a["id"] != lead["id"]]
    picked = eligible[:limit]
    lead_sector = lead.get("desk_section") or lead.get("category")
    if picked and lead_sector:
        other = next((a for a in eligible
                      if (a.get("desk_section") or a.get("category")) in {"Insurance", "Banking"}
                      and (a.get("desk_section") or a.get("category")) != lead_sector), None)
        if other is not None and all(a["id"] != other["id"] for a in picked):
            picked[-1] = other
            keep = {a["id"] for a in picked}
            picked = [a for a in eligible if a["id"] in keep]
    return picked
