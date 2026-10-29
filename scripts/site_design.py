"""Public presentation only: two industry desks, a shared masthead and sourced term explanations.

Original editorial category and provenance are preserved in data/articles.json.
"""
from __future__ import annotations
import html
import re

# Shared, attributed London imagery. Editorial decoration, never an event photo.
WESTMINSTER_PHOTO="https://upload.wikimedia.org/wikipedia/commons/f/fc/Big_Ben_after_sunset.jpg"
WESTMINSTER_CREDIT="hozinja / Wikimedia Commons · CC BY 2.0"
WESTMINSTER_CREDIT_URL="https://commons.wikimedia.org/wiki/File:Big_Ben_after_sunset.jpg"
ST_PAULS_PHOTO="https://upload.wikimedia.org/wikipedia/commons/thumb/7/70/St_Paul%27s_Cathedral_from_Tate_Modern_2018-01-31.jpg/960px-St_Paul%27s_Cathedral_from_Tate_Modern_2018-01-31.jpg"
ST_PAULS_CREDIT="Colin / Wikimedia Commons · CC BY-SA"
ST_PAULS_CREDIT_URL="https://commons.wikimedia.org/wiki/File:St_Paul%27s_Cathedral_from_Tate_Modern_2018-01-31.jpg"
CITY_PHOTO="https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/Skyline_of_London_in_September_2024.jpg/960px-Skyline_of_London_in_September_2024.jpg"
CITY_CREDIT="Choinowski / Wikimedia Commons · CC BY-SA 4.0"
CITY_CREDIT_URL="https://commons.wikimedia.org/wiki/File:Skyline_of_London_in_September_2024.jpg"

INSURANCE_PHOTO=ST_PAULS_PHOTO
BANK_PHOTO="https://upload.wikimedia.org/wikipedia/commons/thumb/f/f5/Banco_de_Inglaterra%2C_Londres%2C_Inglaterra%2C_2014-08-11%2C_DD_141_%28cropped%29.JPG/960px-Banco_de_Inglaterra%2C_Londres%2C_Inglaterra%2C_2014-08-11%2C_DD_141_%28cropped%29.JPG"
BANK_CREDIT="Diego Delso, delso.photo · CC BY-SA"
BANK_CREDIT_URL="https://commons.wikimedia.org/wiki/File:Banco_de_Inglaterra,_Londres,_Inglaterra,_2014-08-11,_DD_141_(cropped).JPG"
LLOYDS_CREDIT_URL="https://www.lloyds.com/insights/media-centre/photo-gallery"

# Verified reusable context photographs. Never claim that a historical building
# photograph shows the current news event; always credit the photographer.
LLOYDS_BUILDING_PHOTO="https://upload.wikimedia.org/wikipedia/commons/d/d3/LloydsOfLondon.JPG"
LLOYDS_BUILDING_CREDIT="Atak Kara / Wikimedia Commons · CC BY 3.0"
LLOYDS_BUILDING_CREDIT_URL="https://commons.wikimedia.org/wiki/File:LloydsOfLondon.JPG"

def home_photo_for(article):
    """A source-credited illustrative setting, not a purported event photograph.

    For imagery tied to an actual development, the newsroom would need an
    independently licensed/verified photo. Do not borrow publisher images.
    """
    title=str(article.get("title","")).lower()
    # Clearly labelled historical setting photography, not an image of this
    # publication date's reported event.
    if desk_for(article)=="Insurance" and re.search(r"\b(?:flood|storm|weather|climate[- ]related)\w*\b",title):
        image=("https://commons.wikimedia.org/wiki/Special:FilePath/Flooded_houses,_Chertsey_(geograph_3812479).jpg?width=1280",
               "Flooded houses in Chertsey in 2014",
               "Alan Hunt / Geograph · CC BY-SA 2.0",
               "https://commons.wikimedia.org/wiki/File:Flooded_houses,_Chertsey_(geograph_3812479).jpg")
    elif re.search(r"\b(?:fca|bank of england|interest rate|lending|bank|savings plan|mortgage)\b",title):
        image=(BANK_PHOTO,"The Bank of England in London",BANK_CREDIT,BANK_CREDIT_URL)
    elif re.search(r"\b(?:chancellor|budget|parliament|treasury|government|tax)\b",title):
        image=(WESTMINSTER_PHOTO,"The Palace of Westminster in London",WESTMINSTER_CREDIT,WESTMINSTER_CREDIT_URL)
    elif re.search(r"\b(?:reinsur|underwriting|lloyd|broker)\w*\b",title):
        image=(LLOYDS_BUILDING_PHOTO,"The Lloyd's building in London",LLOYDS_BUILDING_CREDIT,LLOYDS_BUILDING_CREDIT_URL)
    elif re.search(r"\b(?:insurance|insurer|pension|claims?|annuit|protection)\w*\b",title):
        image=(ST_PAULS_PHOTO,"St Paul's Cathedral and London's financial district",ST_PAULS_CREDIT,ST_PAULS_CREDIT_URL)
    else:
        image=(CITY_PHOTO,"The City of London skyline",CITY_CREDIT,CITY_CREDIT_URL)
    src,alt,credit,url=image
    return {"src":src,"alt":alt+" — illustrative, not the reported event",
            "credit":credit,"credit_url":url}

INSURANCE_TERMS=r"\b(?:insur\w*|underwrit\w*|reinsur\w*|broker\w*|mga|claims?|premium\w*|protection|annuit\w*|solvency|pension provider|standard life|gwp)\b"
BANK_TERMS=r"\b(?:bank\w*|lending|mortgage\w*|deposits?|interest rates?|building societ\w*|payments?|liquidit\w*|capital|asset management|wealth|market\w*|credit|borrow\w*)\b"

def desk_for(a):
    raw=str(a.get("category","")).lower()
    if raw in {"insurance","brokers"}:return "Insurance"
    # Presentation-only correction for a cyber insurance broker/underwriting
    # report that the writing model labelled Banking. The signed record is
    # unchanged; a general business continuity report is not a banking story.
    source_url=str(a.get("url","")).lower()
    headings=" ".join(str(row[0]) for row in a.get("blocks",[]) if isinstance(row,(list,tuple)) and row)
    if (raw=="banking" and "insurancebusinessmag.com/uk/news/cyber/" in source_url
            and re.search(r"implications for insurers and brokers",headings,re.I)
            and not re.search(r"\b(?:bank|lender|mortgage|deposits|interest rates?)\b",str(a.get("title","")),re.I)):
        return "Insurance"
    if raw in {"banking","wealth"}:return "Banking"
    title=str(a.get("title",""))
    t_ins=bool(re.search(INSURANCE_TERMS,title,re.I))
    t_bank=bool(re.search(BANK_TERMS,title,re.I))
    if t_ins and not t_bank:return "Insurance"
    if t_bank and not t_ins:return "Banking"
    if raw=="pensions":
        return "Insurance" if re.search(r"(?i)annuity|life insurer|pension provider|workplace pension|protection",title) else "Banking"
    if t_ins and t_bank:
        return "Insurance" if re.search(r"(?i)insur\w*|broker\w*|underwrit\w*|mga",title[:95]) else "Banking"
    details=str(a.get("short",""))[:500]
    return "Insurance" if re.search(INSURANCE_TERMS,details,re.I) and not re.search(BANK_TERMS,details,re.I) else "Banking"

TERMS=(
 ("FCA","Financial Conduct Authority — the UK regulator overseeing the conduct of financial services firms."),
 ("PRA","Prudential Regulation Authority — the Bank of England regulator focused on the safety and soundness of major financial firms."),
 ("MGA","Managing general agent — an intermediary that can arrange and sometimes underwrite cover on an insurer's behalf, within delegated authority."),
 ("underwriting","The process of assessing risk and deciding whether to offer insurance, on what terms and at what price."),
 ("reinsurance","Insurance purchased by insurers to share part of their own exposure to large claims."),
 ("premium","The amount paid for an insurance policy."),
 ("combined ratio","An insurance measure comparing claims and operating costs with premiums earned; below 100% generally indicates an underwriting profit."),
 ("GWP","Gross written premium — the total value of premiums an insurer writes before deductions such as reinsurance."),
 ("ring-fencing","Rules requiring certain large banking groups to separate core retail banking operations from some riskier activities."),
 ("capital buffer","Extra capital a financial institution holds to absorb unexpected losses."),
 ("fiscal headroom","The margin the government has against its own fiscal rules, based on economic forecasts."),
 ("private markets","Investments that are not traded on public exchanges, such as private equity, private credit and infrastructure."),
 ("basis points","A basis point is one-hundredth of a percentage point; 100 basis points equal one percentage point."),
 ("persistency","The proportion of insurance policies that remain in force over a defined period."),
 ("annuity","A financial product that provides regular income, usually in retirement."),
 ("National Insurance","UK contributions paid by workers and employers to help fund state benefits and services. It is not a commercial insurance policy."),
 ("VAT","Value Added Tax — a tax added to the sale price of most goods and services."),
 ("basis point","One-hundredth of a percentage point; for example, a 25-basis-point rate rise is 0.25 percentage points."),
 ("base rate","The Bank of England's benchmark interest rate, which influences borrowing and saving rates."),
 ("APE","Annual premium equivalent — a common insurance sales measure that combines regular premiums with a share of single premiums."),
)
def terms_for(a,limit=4):
    combined=" ".join([str(a.get("title","")),str(a.get("short",""))]+[str(p) for _,p in a.get("blocks",[])])
    out=[]
    for term,meaning in TERMS:
        pat=r"(?i)\b"+re.escape(term)+r"s?\b"
        if re.search(pat,combined):
            out.append([term,meaning])
        if len(out)>=limit:break
    return out

def credit(section):
    if section=="Insurance":
        return 'Photograph: <a href="'+ST_PAULS_CREDIT_URL+'" target="_blank" rel="noopener noreferrer">'+ST_PAULS_CREDIT+'</a> · sector illustration, not event evidence'
    return 'Photograph: <a href="'+BANK_CREDIT_URL+'" target="_blank" rel="noopener noreferrer">'+BANK_CREDIT+'</a> · sector illustration, not event evidence'

def visual(section,*,css_class="tb-article-visual"):
    src=INSURANCE_PHOTO if section=="Insurance" else BANK_PHOTO
    alt="St Paul's Cathedral and the City of London" if section=="Insurance" else "The Bank of England building in London"
    return '<figure class="'+css_class+'"><img src="'+html.escape(src,quote=True)+'" alt="'+alt+'" loading="lazy" decoding="async"><figcaption>'+credit(section)+'</figcaption></figure>'

def header(prefix="",active="",with_controls=False):
    nav="".join('<a href="'+prefix+target+'"'+(' aria-current="page"' if active==name else '')+'>'+name+'</a>' for name,target in (("Home","index.html"),("Insurance","insurance.html"),("Banking","banking.html"),("About","about.html")))
    controls=('<button id="search-toggle" aria-label="Search articles" title="Search articles" type="button"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></svg></button><button hidden id="saved-toggle" type="button">Saved <span id="saved-number">0</span></button>' if with_controls else '<button type="button" class="tb-nav-search" title="Search all reports" aria-label="Search all reports" onclick="location.href=&quot;'+prefix+'archive.html?search=1&quot;"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></svg></button>')
    return ('<header class="tb-header"><div class="tb-utility"><div class="tb-utility-inner"><span><i class="tb-utility-marker"></i> THE UK INSURANCE &amp; BANKING DESK</span><span id="edition-date">INDEPENDENT UK NEWS</span></div></div>'
    '<div class="tb-mast"><div class="tb-brand"><a class="tb-logo" href="'+prefix+'index.html"'+(' id="logo"' if with_controls else '')+'>THE BRIEF<span>.</span></a><p class="tb-tag">INSURANCE AND BANKING, CLEARLY EXPLAINED.</p></div></div>'
    '<nav class="tb-nav tb-section-nav" aria-label="Primary navigation">'+nav+controls+'</nav><div class="tb-divider"></div><span id="freshness" hidden></span></header>')

def footer(prefix="",with_controls=False):
    items=('<button id="footer-about" hidden type="button">About</button><a id="footer-top" href="#home">Back to top ↑</a>' if with_controls else '<a href="'+prefix+'index.html">Back to the latest ↑</a>')
    return '<footer class="tb-footer"><div class="tb-footer-inner"><div><a class="tb-footer-logo" href="'+prefix+'index.html">THE BRIEF<span>.</span></a><p>Insurance and banking, clearly explained. Not financial advice.</p></div><div class="tb-footer-links"><a href="'+prefix+'archive.html">Earlier reports</a><a href="'+prefix+'about.html">About &amp; corrections</a><a href="'+prefix+'privacy.html">Privacy</a>'+items+'</div></div></footer>'
