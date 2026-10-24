#!/usr/bin/env python3
"""URL-level scope for The Brief's unattended, source-limited reporting.

This is only the FIRST publication gate. Full-source retrieval, sentence-by-
sentence evidence checking, high-risk language checks and publication audits
must still pass. An RSS headline is never sufficient evidence.
"""
from __future__ import annotations
import re
from urllib.parse import urlsplit

FCA_REPORT = re.compile(r"^/data/(?:complaints-data-\d{4}-h[12]|access-cash-coverage-uk-\d{4}-h[12])/?$", re.I)
FCA_RELEASE = re.compile(r"^/news/press-releases/[a-z0-9-]+/?$", re.I)
FCA_SPEECH = re.compile(r"^/news/speeches/[a-z0-9-]+/?$", re.I)
FCA_CONSULTATION = re.compile(r"^/publications/consultation-papers/[a-z0-9-]+/?$", re.I)
FCA_REVIEW = re.compile(r"^/publications/multi-firm-reviews/[a-z0-9-]+/?$",re.I)
BOE_RELEASE = re.compile(r"^/news/20\d{2}/[a-z]+/[a-z0-9-]+/?$",re.I)
TPR_RELEASES = re.compile(r"^/(?:en/)?media-hub/press-releases/20\d{2}-press-releases/[a-z0-9-]+/?$",re.I)
# Adverse actions against firms/people and allegations are NOT published
# unattended, even when an official regulator announces them.
ADVERSE = re.compile(
    r"(?:^|-)(?:restricts?|fines?|bans?|charged?|allegations?|fraud|"
    r"laundering|sanctions?|investigations?|prosecutions?|enforcement|"
    r"penalties|misconduct|criminal|convictions?|suspends?|censures?|penalises?)(?:-|$)", re.I
)
AVIVA_RELEASE = re.compile(r"^/newsroom/news-and-research-overview/news-releases/20\d{2}/\d{2}/[a-z0-9-]+/?$", re.I)
LLOYDS_RELEASE = re.compile(r"^/media/press-releases/20\d{2}/[a-z0-9-]+(?:/[a-z0-9-]+)?\.html$", re.I)
ISSUER_RNS = re.compile(r"^/announcement/rns/.*?/(?:9835238|9835199|9836547|9836457|9835245|9835194)$", re.I)
TPR_RELEASE = "/media-hub/press-releases/2026-press-releases/tpr-sets-expectations-on-hidden-concentration-risks-in-pension-portfolios"
RATHBONES_RELEASE = "/en-gb/wealth-management/media-centre/rathbones-reports-strong-financial-performance-and-strategic-momentum-third-quarter-trading-update"

def source_lane(url: str) -> str | None:
    """Return a narrow primary-source lane, or None to hold automatically."""
    p = urlsplit(url)
    if p.scheme != "https" or p.username or p.password or p.port not in (None,443):
        return None
    host, path = (p.hostname or "").lower(), p.path
    if host in {"fca.org.uk", "www.fca.org.uk"}:
        if FCA_REPORT.fullmatch(path):
            return "fca_data"
        if FCA_RELEASE.fullmatch(path) and not ADVERSE.search(path.rsplit("/", 1)[-1]):
            return "fca_release"
        # Only verifiable FCA speeches and consultation papers, not generic
        # enforcement notices or third-party interpretation. The writer and
        # publisher must preserve the speech/proposal status and hold legal claims.
        if FCA_SPEECH.fullmatch(path) and not ADVERSE.search(path.rsplit("/", 1)[-1]):
            return "fca_speech"
        if FCA_CONSULTATION.fullmatch(path) and not ADVERSE.search(path.rsplit("/", 1)[-1]):
            return "fca_consultation"
        if FCA_REVIEW.fullmatch(path) and not ADVERSE.search(path.rsplit("/", 1)[-1]):
            return "fca_review"
    if host in {"www.bankofengland.co.uk","bankofengland.co.uk"}:
        if BOE_RELEASE.fullmatch(path) and not ADVERSE.search(path.rsplit("/", 1)[-1]):
            return "boe_release"
    if host in {"www.thepensionsregulator.gov.uk","thepensionsregulator.gov.uk"}:
        if TPR_RELEASES.fullmatch(path) and not ADVERSE.search(path.rsplit("/", 1)[-1]):
            return "tpr_release"
    if host in {"aviva.com", "www.aviva.com"} and AVIVA_RELEASE.fullmatch(path):
        return "company_release"
    if host in {"lloydsbankinggroup.com", "www.lloydsbankinggroup.com"} and LLOYDS_RELEASE.fullmatch(path):
        return "company_release"
    if host in {"standardlifeplc.com", "www.standardlifeplc.com"} and path.startswith("/news-and-views/press-releases/article-page/"):
        return "company_release"
    if host == "committees.parliament.uk" and path.startswith("/committee/697/financial-services-regulation-committee/news/"):
        return "official_release"
    if host == "publications.parliament.uk" and path == "/pa/ld5902/ldselect/ldfsrc/64/6403.htm":
        return "official_release"
    if host in {"www.thepensionsregulator.gov.uk", "thepensionsregulator.gov.uk"} and path == TPR_RELEASE:
        return "official_release"
    if host in {"www.rathbones.com", "rathbones.com"} and path == RATHBONES_RELEASE:
        return "company_release"
    if host in {"www.investegate.co.uk", "investegate.co.uk"} and ISSUER_RNS.fullmatch(path):
        return "issuer_rns"
    return None

def self_test():
    assert source_lane("https://www.fca.org.uk/news/press-releases/fca-calls-private-market-firms-manage-conflicts-interest-line-rapid-growth") == "fca_release"
    assert source_lane("https://www.fca.org.uk/data/access-cash-coverage-uk-2025-h1") == "fca_data"
    assert source_lane("https://www.fca.org.uk/news/press-releases/fca-restricts-6-firms-following-concerns-over-anti-money-laundering-controls") is None
    assert source_lane("https://www.fca.org.uk.evil.com/news/press-releases/test") is None
    assert source_lane("https://www.fca.org.uk/news/speeches/beyond-borders-regulating-risks-we-share") == "fca_speech"
    assert source_lane("https://www.fca.org.uk/publications/consultation-papers/cp26-38-financial-crime-guide-updates") == "fca_consultation"
    assert source_lane("https://www.fca.org.uk/news/speeches/fines-and-sanctions") is None
    assert source_lane("https://www.bankofengland.co.uk/news/2026/october/regulators-unveil-plans-to-simplify-senior-manager-and-certification-regime")=="boe_release"
    assert source_lane("https://www.thepensionsregulator.gov.uk/en/media-hub/press-releases/2026-press-releases/tpr-sets-expectations-on-hidden-concentration-risks-in-pension-portfolios")=="tpr_release"
    assert source_lane("https://www.fca.org.uk/publications/multi-firm-reviews/conflicts-interest-fair-customer-treatment-private-markets")=="fca_review"
    assert source_lane("https://www.bankofengland.co.uk.evil.com/news/2026/october/fake") is None
    assert source_lane("https://www.thepensionsregulator.gov.uk/en/media-hub/press-releases/2026-press-releases/fraud-charges") is None
    assert source_lane("http://www.fca.org.uk/data/complaints-data-2026-h1") is None
    print("PASS: fresh FCA reporting lanes; high-risk enforcement and spoofed sources remain held")

if __name__ == "__main__":
    self_test()
