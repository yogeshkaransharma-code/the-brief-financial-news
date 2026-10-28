"""Presentation-only story hierarchy for The Brief.

Never edits article content, source facts, dates, editorial statuses or the archive.
This heuristic is editorial triage, not a verified relevance assessment.
"""
import re

UK = re.compile(r"\b(?:UK|United Kingdom|British|Britain|England|English|Scottish|Scotland|Welsh|Wales|Northern Ireland|London|Manchester|Birmingham|Leeds|Bristol|FCA|PRA|Bank of England|Financial Ombudsman|Lloyd['’]?s of London|UK Budget)\b", re.I)
BIG = re.compile(r"\b(?:regulator|regulation|consultation|court rules|court ruling|acquisition|merger|earnings|results|profit|capital|underwriting|claims|insolvenc|business lending|interest rates|FCA|PRA|financial distress)\b", re.I)
ROUTINE = re.compile(r"\b(?:appoints|appointed|promotion|promotes|names|webinar|award|shortlist|demo day)\b", re.I)
FOREIGN = re.compile(r"\b(?:US|U\.S\.|American|Florida|Georgia|California|New York|Utah|Boston|Hong Kong|APAC|Asia-Pacific)\b", re.I)

def priority(a):
    """Evidence-based UK/title relevance; small boost for substantive headlines."""
    title = str(a.get("title", ""))
    summary = str(a.get("short", ""))
    source = str(a.get("source", ""))
    points = 0
    if UK.search(title):points += 14
    elif UK.search(summary):points += 5
    if re.search(r"\b(?:Financial Conduct Authority|Prudential Regulation Authority|Bank of England|FCA|PRA)\b", source, re.I):
        points += 12
    if BIG.search(title):points += 4
    if ROUTINE.search(title):points -= 5
    if FOREIGN.search(title) and not UK.search(title):points -= 4
    # In particular, do not replace a newer relevant report with a much older one:
    # the caller already supplies published articles from a single UK calendar day.
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
