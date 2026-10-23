#!/usr/bin/env python3
"""Conservative financial-context checks independent of the AI verifier.

These detect *specific* discrepancies and must never be sold as a complete
accounting, legal, or semantic fact-check.
"""
from __future__ import annotations
import re

SENTENCE=re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9£])|\n+")

def concerns(article, captured):
    text="\n".join([article.get("title",""),article.get("short","")] +
                   [body for heading,body in article.get("blocks",[])])
    issues=[]
    path=article.get("url","").lower()
    if "complaints" in path and re.search(r"\bclosed complaints were upheld\b",captured,re.I):
        for line in SENTENCE.split(text):
            if re.search(r"\b(?:upheld|found in favour)\b",line,re.I) and re.search(
                r"\b(?:cases|complaints) received\b",line,re.I
            ):
                issues.append("Uphold-rate denominator is 'closed complaints' in detailed FCA data; article says received")
                break
    # Rounded summary statistics can produce a different delta from the FCA's
    # separately computed published percentage-point figure. Do not call one
    # *false* without raw data, but hold any unqualified, non-reconciling claim.
    for line in SENTENCE.split(text):
        for match in re.finditer(
            r"(\d+(?:\.\d+)?)%.{0,140}?(\d+(?:\.\d+)?)\s+percentage points?.{0,140}?(\d+(?:\.\d+)?)%",
            line,re.I
        ):
            current=float(match.group(1))
            claimed_delta=float(match.group(2))
            previous=float(match.group(3))
            if abs(abs(previous-current)-claimed_delta)>0.055:
                issues.append(
                    "Percentage-point change does not reconcile with quoted rounded rates; "
                    "underlying unrounded data and explanatory qualification required"
                )
    return issues

def self_test():
    article={"url":"https://www.fca.org.uk/data/complaints-data-2026-h1",
        "title":"FCA complaint figures","short":"The regulator published data.",
        "blocks":[["Findings","Firms found in favour of complainants in just over half of cases received. "
        "Specifically, 54.8% were upheld, 0.8 percentage points below the 55.5% prior rate."]]}
    source="1,003,011 complaints upheld. 54.8% of closed complaints were upheld."
    issues=concerns(article,source)
    assert len(issues)==2,issues
    article["blocks"][0][1]="The FCA says 54.8% of CLOSED complaints were upheld."
    assert not concerns(article,source)
    print("PASS: material complaints-denominator confusion and non-reconciling rounded rates flagged")

if __name__=="__main__":
    self_test()
