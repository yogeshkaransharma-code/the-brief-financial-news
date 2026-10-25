#!/usr/bin/env python3
"""Bounded, fail-closed retrieval of original FCA / Bank of England documents.

Only public official hosts are permitted. A source is never silently truncated.
No paywall bypass, social scraping or secondary article reproduction.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from io import BytesIO
import hashlib
import re
from urllib.parse import urljoin, urlsplit
import urllib.request
from bs4 import BeautifulSoup

ALLOWED = {"fca.org.uk", "www.fca.org.uk", "bankofengland.co.uk", "www.bankofengland.co.uk",
           "aviva.com", "www.aviva.com", "lloydsbankinggroup.com", "www.lloydsbankinggroup.com",
           "standardlifeplc.com", "www.standardlifeplc.com",
           "committees.parliament.uk", "publications.parliament.uk", "www.investegate.co.uk", "investegate.co.uk",
           "thepensionsregulator.gov.uk", "www.thepensionsregulator.gov.uk",
           "rathbones.com", "www.rathbones.com",
           "allianz.co.uk", "www.allianz.co.uk", "munichre.com", "www.munichre.com", "www.gov.uk", "gov.uk", "hsbc.com", "www.hsbc.com", "natwestgroup.com", "www.natwestgroup.com", "financial-ombudsman.org.uk", "www.financial-ombudsman.org.uk",
           "abi.org.uk", "www.abi.org.uk", "ukfinance.org.uk", "www.ukfinance.org.uk"}
from source_registry import EXTRA_HOSTS
ALLOWED |= EXTRA_HOSTS
from market_coverage import recognised_original_hosts
ALLOWED |= recognised_original_hosts()
# Original newspaper reporting is evidence of its attributed reporting,
# not an official corporate announcement or independent corroboration.
ALLOWED |= {"www.theguardian.com","theguardian.com",
            "www.bbc.co.uk","bbc.co.uk","www.bbc.com","bbc.com"}
UA = "TheBriefResearch/0.2 (public official documents; editorial attribution)"
MAX_BYTES = 3_000_000
MAX_TEXT = 43_000
MAX_PDF_PAGES = 35

class SourceError(ValueError):
    pass

def permitted(url):
    p = urlsplit(url)
    return p.scheme == "https" and p.hostname in ALLOWED and not p.username and not p.password and p.port in (None, 443)

class OfficialRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not permitted(newurl):
            raise SourceError("Refusing a redirect outside approved official HTTPS hosts")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def retrieve_bytes(url, accept="text/html,application/pdf"):
    if not permitted(url):
        raise SourceError("Source is not an approved official HTTPS URL")
    opener = urllib.request.build_opener(OfficialRedirects())
    with opener.open(urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept}), timeout=22) as response:
        if not permitted(response.geturl()):
            raise SourceError("Non-official redirect")
        length = int(response.headers.get("Content-Length") or "0")
        if length > MAX_BYTES:
            raise SourceError("Official document exceeds supported size; editorial review required")
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise SourceError("Source too large; refused partial capture")
        return raw, response.headers.get("Content-Type", "").lower(), response.geturl()

def clean_text(value):
    return re.sub(r"\s+", " ", value).strip()

@dataclass
class Source:
    url: str
    document_urls: list[str]
    text: str
    extraction: str
    evidence_sha256: str
    notes: list[str]
    complete_capture: bool
    publication_date: tuple | None = None

def html_extract(raw, source_url):
    soup = BeautifulSoup(raw, "html.parser")
    for x in soup.select("script,style,noscript,nav,header,footer,aside,form,svg,button"):
        x.decompose()
    # Prefer a substantial article element to a full main container. Some
    # newsroom templates put unrelated cards and 100s of navigation links in
    # main, which otherwise swamps the real release with duplicate chart data.
    page_main = soup.select_one("main") or soup.select_one('[role="main"]') or soup.body
    article = soup.select_one("main article") or soup.select_one("article")
    main = (article if article and len(clean_text(article.get_text(" ",strip=True)))>=850
            else page_main)
    if main is None:
        raise SourceError("No readable official HTML document body")
    parts=[]
    seen=set()
    for el in main.find_all(["h1","h2","h3","h4","p","li","dt","dd","tr"]):
        if el.find_parent(["p","li","tr"]) is not None:
            continue
        text=clean_text(el.get_text(" ", strip=True))
        if len(text)<16 or text in seen:
            continue
        seen.add(text)
        parts.append(text)
    text="\n\n".join(parts)
    if len(text)<850:
        # Some regulator pages are hydrated outside their template's tiny
        # <main> shell. Use a readable article/body fallback, but never
        # remove the requirement for substantial independently captured text.
        alternatives=[main.get_text(" ",strip=True)]
        if article is not None:
            alternatives.append(article.get_text(" ",strip=True))
        if soup.body is not None:
            alternatives.append(soup.body.get_text(" ",strip=True))
        fallback=max((clean_text(part) for part in alternatives),key=len,default="")
        if 850<=len(fallback)<=MAX_TEXT and len(fallback)>len(text):
            text=fallback
    # Company newsrooms put promotional boilerplate, investor disclosures and
    # recommendations after the actual release. Remove unrelated later cards
    # rather than letting them contaminate the model's story.
    if urlsplit(source_url).hostname in {"www.aviva.com","aviva.com"}:
        for stop in ("\n\nEnquiries:", "\n\nNotes to editors:", "\n\nMore from our Newsroom"):
            if stop in text: text=text.split(stop,1)[0]
    # A consultation landing page may be short because the full published
    # document is the PDF it links to. Discover that official attachment
    # before rejecting the page as thin. The PDF must still be read in full.
    attachments=[]
    # Short consultation pages sometimes put their PDF link outside the main
    # shell. Search the same official page's anchors, never an external site.
    pdf_area=(soup if "/consultation" in urlsplit(source_url).path.lower() else main)
    for anchor in pdf_area.find_all("a",href=True):
        url=urljoin(source_url,anchor["href"])
        if permitted(url) and urlsplit(url).path.lower().endswith(".pdf"):
            label=clean_text(anchor.get_text(" ",strip=True)).lower()
            attachments.append((url,label))
    if len(text)<850 and not ("/consultation" in urlsplit(source_url).path.lower() and attachments):
        raise SourceError(f"Insufficient official article content ({len(text)} characters); cannot responsibly draft")
    # Some FCA charts and data widgets render figures inside DIV/SPAN content,
    # not paragraph or table tags. Preserve the *entire* official main text if
    # it contains numeric tokens absent from our structured extraction.
    complete_main=clean_text(main.get_text(" ",strip=True))
    amount=re.compile(r"(?<![\w])(?:£|\$)?\d+(?:[.,]\d+)*(?:%|bn|m|k)?(?![\w])",re.I)
    numbers=lambda value: {m.group().lower().replace(",","") for m in amount.finditer(value)}
    if numbers(complete_main)-numbers(text):
        # Keep one complete rendition, not a second copy of the same body.
        # The old code appended the complete body after its paragraph extract,
        # doubling the size and falsely rejecting long FCA review pages.
        if len(complete_main)>MAX_TEXT:
            raise SourceError("Important chart text exceeds full-source context limit; held without truncation")
        text=complete_main
    if len(text)>MAX_TEXT:
        raise SourceError("Full HTML exceeds safe model context; no silent truncation")
    return text, attachments

def pdf_extract(raw):
    try:
        from pypdf import PdfReader
        pdf = PdfReader(BytesIO(raw), strict=False)
        if pdf.is_encrypted:
            raise SourceError("Encrypted official PDF requires editorial review")
        if len(pdf.pages)>MAX_PDF_PAGES:
            raise SourceError("Official PDF exceeds page limit; no truncated draft")
        pages=[]
        for i,page in enumerate(pdf.pages,1):
            extracted=clean_text(page.extract_text(extraction_mode="layout") or "")
            if len(extracted)<30:
                raise SourceError(f"PDF page {i} has no usable selectable text")
            pages.append(f"[OFFICIAL PDF, PAGE {i}]\n{extracted}")
        whole="\n\n".join(pages)
        if len(whole)>MAX_TEXT or len(whole)<850:
            raise SourceError("PDF text is too large or thin; no partial AI read")
        return whole
    except SourceError:
        raise
    except Exception as error:
        raise SourceError(f"PDF extraction failed: {type(error).__name__}") from error

def read_source(url):
    raw, ctype, final=retrieve_bytes(url)
    notes=[]
    publication_date=None
    docs=[final]
    if "pdf" in ctype or final.lower().endswith(".pdf"):
        text=pdf_extract(raw)
        extraction="full PDF text (selectable pages)"
    elif "html" in ctype:
        from source_dates import published_date
        publication_date=published_date(raw)
        text, links=html_extract(raw, final)
        extraction="HTML main content"
        path=urlsplit(final).path.lower()
        # Consultation landing pages often only preview a linked policy PDF.
        # Do not mistake a short landing page for its complete consultation.
        if "/consultation" in path or "/policy-statements/" in path:
            relevant=[(u,label) for u,label in links
                      if "consultation paper" in label or "full document" in label
                      or "download" in label or u.split("/")[-1].lower().startswith(("cp","ps"))]
            unique=list(dict.fromkeys(u for u,_ in relevant))
            if unique:
                if len(unique)>1:
                    raise SourceError("Several central PDFs linked; needs human source selection")
                pdf_url=unique[0]
                pdf_raw,pdf_type,pdf_final=retrieve_bytes(pdf_url,"application/pdf")
                if "pdf" not in pdf_type and not pdf_final.lower().endswith(".pdf"):
                    raise SourceError("Linked official primary document was not a PDF")
                pdf_text=pdf_extract(pdf_raw)
                if len(text)+len(pdf_text)>MAX_TEXT:
                    raise SourceError("HTML and PDF together exceed full-reading limit")
                text=text+"\n\n[LINKED PRIMARY DOCUMENT]\n"+pdf_text
                docs.append(pdf_final)
                extraction="complete HTML and linked official PDF"
            else:
                notes.append("No central PDF identified automatically; verify additional attachments before approval")
    else:
        raise SourceError("Unsupported official document format; no draft")
    return Source(final,docs,text,extraction,hashlib.sha256(text.encode("utf-8")).hexdigest(),notes,True,publication_date)

def self_test():
    assert permitted("https://www.fca.org.uk/news/a")
    for url in ("https://fake-fca.org.uk/","http://www.fca.org.uk","https://www.fca.org.uk.evil.test/","https://www.fca.org.uk@evil.test/"):
        assert not permitted(url)
    html=b"<main><h1>Official update</h1><p>"+b"Details of the regulatory announcement and how it affects a defined group of firms. "*18+b"</p></main>"
    text,_=html_extract(html,"https://www.fca.org.uk/news/a")
    assert "announcement" in text
    richer=b"<main><h1>Published data</h1><p>"+b"The FCA's published reporting covers regulated financial firms and aggregate consumer complaints. "*17+b"</p><div class='chart'><span>54.8%</span></div></main>"
    captured,_=html_extract(richer,"https://www.fca.org.uk/data/complaints-data-2026-h1")
    assert "54.8%" in captured, "Figure embedded outside paragraphs must not disappear"
    duplicate=b"<main><p>"+b"Regulated institutions published an official reporting update. "*200+b"</p><div><span>51.4%</span></div></main>"
    full,_=html_extract(duplicate,"https://www.fca.org.uk/data/complaints-data-2026-h1")
    assert "51.4%" in full and len(full)<14000,"Avoid doubling long official text when charts appear"
    brief=b'<main><h1>Financial crime guide consultation</h1><a href="https://www.fca.org.uk/content/dam/fca/documents/consultation-papers/cp26-38.pdf">Download the consultation paper PDF</a></main>'
    partial,links=html_extract(brief,"https://www.fca.org.uk/publications/consultation-papers/cp26-38-financial-crime-guide-updates")
    assert len(partial)<850 and len(links)==1 and links[0][0].endswith(".pdf"),"Thin official consultation must be able to discover its complete linked PDF"
    print("PASS: approved-host restrictions, chart/span figures, HTML extraction and no silent truncation")

if __name__=="__main__":
    self_test()

