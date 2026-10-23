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
           "rathbones.com", "www.rathbones.com"}
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

def html_extract(raw, source_url):
    soup = BeautifulSoup(raw, "html.parser")
    for x in soup.select("script,style,noscript,nav,header,footer,aside,form,svg,button"):
        x.decompose()
    main = soup.select_one("main") or soup.select_one("article") or soup.select_one('[role="main"]') or soup.body
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
        # Regulators sometimes put body text directly in DIVs rather than P
        # elements. This still reads only the page's main editorial content.
        fallback=clean_text(main.get_text(" ",strip=True))
        if len(fallback)>len(text):
            text=fallback
    # Company newsrooms put promotional boilerplate, investor disclosures and
    # recommendations after the actual release. Remove unrelated later cards
    # rather than letting them contaminate the model's story.
    if urlsplit(source_url).hostname in {"www.aviva.com","aviva.com"}:
        for stop in ("\n\nEnquiries:", "\n\nNotes to editors:", "\n\nMore from our Newsroom"):
            if stop in text: text=text.split(stop,1)[0]
    if len(text)<850:
        raise SourceError(f"Insufficient official article content ({len(text)} characters); cannot responsibly draft")
    # Some FCA charts and data widgets render figures inside DIV/SPAN content,
    # not paragraph or table tags. Preserve the *entire* official main text if
    # it contains numeric tokens absent from our structured extraction.
    complete_main=clean_text(main.get_text(" ",strip=True))
    amount=re.compile(r"(?<![\w])(?:£|\$)?\d+(?:[.,]\d+)*(?:%|bn|m|k)?(?![\w])",re.I)
    numbers=lambda value: {m.group().lower().replace(",","") for m in amount.finditer(value)}
    if numbers(complete_main)-numbers(text):
        proposed=text+"\n\n[ADDITIONAL MAIN-PAGE CHART AND FIGURE TEXT]\n"+complete_main
        if len(proposed)>MAX_TEXT:
            raise SourceError("Important chart text exceeds full-source context limit; held without truncation")
        text=proposed
    if len(text)>MAX_TEXT:
        raise SourceError("Full HTML exceeds safe model context; no silent truncation")
    attachments=[]
    for a in main.find_all("a",href=True):
        url=urljoin(source_url, a["href"])
        if permitted(url) and urlsplit(url).path.lower().endswith(".pdf"):
            label=clean_text(a.get_text(" ", strip=True)).lower()
            attachments.append((url,label))
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
    docs=[final]
    if "pdf" in ctype or final.lower().endswith(".pdf"):
        text=pdf_extract(raw)
        extraction="full PDF text (selectable pages)"
    elif "html" in ctype:
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
    return Source(final,docs,text,extraction,hashlib.sha256(text.encode("utf-8")).hexdigest(),notes,True)

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
    print("PASS: approved-host restrictions, chart/span figures, HTML extraction and no silent truncation")

if __name__=="__main__":
    self_test()
