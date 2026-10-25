"""Public presentation only: two industry desks, a shared masthead and sourced term explanations.

Original editorial category and provenance are preserved in data/articles.json.
"""
from __future__ import annotations
import html
import re

INSURANCE_PHOTO="https://assets.lloyds.com/media/132451df-42c2-4426-9aca-3a7d5549a8a1/Lloyds_Underwriting-Room_3_Landscape.jpg"
BANK_PHOTO="https://upload.wikimedia.org/wikipedia/commons/thumb/f/f5/Banco_de_Inglaterra%2C_Londres%2C_Inglaterra%2C_2014-08-11%2C_DD_141_%28cropped%29.JPG/960px-Banco_de_Inglaterra%2C_Londres%2C_Inglaterra%2C_2014-08-11%2C_DD_141_%28cropped%29.JPG"
BANK_CREDIT="Diego Delso, delso.photo · CC BY-SA"
BANK_CREDIT_URL="https://commons.wikimedia.org/wiki/File:Banco_de_Inglaterra,_Londres,_Inglaterra,_2014-08-11,_DD_141_(cropped).JPG"
LLOYDS_CREDIT_URL="https://www.lloyds.com/insights/media-centre/photo-gallery"

INSURANCE_TERMS=r"\b(?:insur\w*|underwrit\w*|reinsur\w*|broker\w*|mga|claims?|premium\w*|protection|annuit\w*|solvency|pension provider|standard life|gwp)\b"
BANK_TERMS=r"\b(?:bank\w*|lending|mortgage\w*|deposits?|interest rates?|building societ\w*|payments?|liquidit\w*|capital|asset management|wealth|market\w*|credit|borrow\w*)\b"

def desk_for(a):
    raw=str(a.get("category","")).lower()
    if raw in {"insurance","brokers"}:return "Insurance"
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
        return 'Photograph: <a href="'+LLOYDS_CREDIT_URL+'" target="_blank" rel="noopener noreferrer">Lloyd’s media gallery</a> · sector illustration, not event evidence'
    return 'Photograph: <a href="'+BANK_CREDIT_URL+'" target="_blank" rel="noopener noreferrer">'+BANK_CREDIT+'</a> · sector illustration, not event evidence'

def visual(section,*,css_class="tb-article-visual"):
    src=INSURANCE_PHOTO if section=="Insurance" else BANK_PHOTO
    alt="Lloyd’s of London underwriting room" if section=="Insurance" else "The Bank of England building in London"
    return '<figure class="'+css_class+'"><img src="'+html.escape(src,quote=True)+'" alt="'+alt+'" loading="lazy" decoding="async"><figcaption>'+credit(section)+'</figcaption></figure>'

def header(prefix="",active="",with_controls=False):
    nav="".join('<a href="'+prefix+target+'"'+(' aria-current="page"' if active==name else '')+'>'+name+'</a>' for name,target in (("Insurance","insurance.html"),("Banking","banking.html"),("About","about.html")))
    controls=('<button id="search-toggle" aria-label="Search articles" title="Search articles" type="button"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></svg></button><button hidden id="saved-toggle" type="button">Saved <span id="saved-number">0</span></button>' if with_controls else "")
    return ('<header class="tb-header"><div class="tb-utility"><div class="tb-utility-inner"><span><i class="tb-utility-marker"></i> THE UK INSURANCE &amp; BANKING DESK</span><span id="edition-date">INDEPENDENT UK NEWS</span></div></div>'
    '<div class="tb-mast"><div><a class="tb-logo" href="'+prefix+'index.html"'+(' id="logo"' if with_controls else '')+'>THE BRIEF<span>.</span></a><p class="tb-tag">INSURANCE. BANKING. UNDERSTOOD.</p></div>'
    '<nav class="tb-nav" aria-label="Primary navigation">'+nav+controls+'</nav></div><div class="tb-divider"></div><span id="freshness" hidden></span></header>')

def footer(prefix="",with_controls=False):
    items=('<button id="footer-about" hidden type="button">About</button><a id="footer-top" href="#home">Back to top ↑</a>' if with_controls else '<a href="'+prefix+'index.html">Back to the latest ↑</a>')
    return '<footer class="tb-footer"><div class="tb-footer-inner"><div><a class="tb-footer-logo" href="'+prefix+'index.html">THE BRIEF<span>.</span></a><p>Insurance and banking, clearly explained. Not financial advice.</p></div><div class="tb-footer-links"><a href="'+prefix+'archive.html">Earlier reports</a><a href="'+prefix+'about.html">About &amp; corrections</a>'+items+'</div></div></footer>'
