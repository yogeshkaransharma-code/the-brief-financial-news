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
    if lead is None:return []
    picks = [a for a in articles if a["id"] != lead["id"]]
    # Preference for useful distinct sectors in short briefings, not artificial quotas.
    chosen = picks[:limit]
    return chosen if chosen else [lead]
