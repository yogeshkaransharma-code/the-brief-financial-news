"""Offline regression for The Brief's exclusive UK insurance/banking remit."""
from uk_market_scope import in_uk_scope,public_article_in_scope,uk_market_reason

def article(title,short="",url="https://www.insurancejournal.com/news/international/2026/10/27/123456.htm",body=""):
    return {"title":title,"short":short,"url":url,"category":"Insurance",
            "blocks":[["Report",body]] if body else []}

def main():
    yes=[
        article("FCA announces changes to UK insurance distribution","",url="https://www.fca.org.uk/news/press-releases/distribution-update"),
        article("High Court allows London broker negligence case to proceed","A London restaurant group is pursuing a broker."),
        article("Guidewire agrees to buy hyperexponential for US$1.7 billion",
            "Guidewire will acquire the London-based pricing and underwriting platform."),
        article("UK bank changes mortgage rates", "The UK lender updated mortgages."),
        article("Chancellor announces plans for cash ISA allowances",
            "The Chancellor is expected to retain the cash ISA allowance.",
            body="The Treasury said the cash ISA allowance will remain available to British savers."),
        article("Chancellor delivers Budget with pledges on living costs and ISAs",
            "The Chancellor announced support on household energy bills and ISAs.",
            body="The government dropped plans to cut the Cash ISA allowance from £20,000 to £12,000."),
        article("International insurer expands UK underwriting capacity",
            "The insurer will add UK underwriting capacity for London market brokers."),
        article("San Francisco MGA seeks London market capacity",
            "The US insurer is seeking underwriting capacity from London market partners for UK businesses.",
            body="The San Francisco startup is seeking capacity from London market insurers to provide cover for UK clients."),
        article("Pensions contributions face change","British pension savers would see an increase in contributions."),
    ]
    # Real production rejection shapes: domestic Budget/pension reporting,
    # ordinary announcements and a UK effect deep in the complete source.
    yes.extend([
        article("Budget 26: Government changes DC consolidation",
            "The Budget changes defined contribution pension arrangements.",
            url="https://www.professionalpensions.com/news/4538007/budget-pensions"),
        article("Budget 26: VCT tax relief unchanged",
            "VCT investors retain the existing tax relief.",
            url="https://www.investmentweek.co.uk/news/4537995/budget-vct"),
        article("Tax treatment of pension death benefits changes",
            "HMRC announced the tax treatment for pension benefits."),
        article("Reinsurance capacity agreement announced", "A capacity agreement was announced.",
            body=("The reinsurer outlined its distribution arrangements. "*90)+"The agreement provides cover for UK commercial customers."),
        article("US insurer launches new distribution arrangement", "The insurer announced a new distribution arrangement.",
            body=("The insurer outlined underwriting arrangements. "*90)+"The insurer will provide cover to UK businesses."),
    ])
    for row in yes[-2:]:
        assert in_uk_scope(row,row["blocks"][0][1]), "Full-source UK connection was ignored"
    # These two deliberately have no UK signal in their discovery snippets.
    late_source_yes=yes[-2:];yes=yes[:-2]
    no=[
        article("Fire and explosion occur at Quaker Oats plant in Iowa","A blaze occurred in Cedar Rapids."),
        article("California regulator sets up biodiversity and insurance risk commission","California is examining insured losses."),
        article("Italian insurance market adapts to nat cat scheme","Italian brokers adjust domestic commercial cover."),
        article("Lockton appoints new US casualty leader","Lockton named a leader for its American division."),
        article("European Commission unveils climate insurance programme","EU businesses will be affected."),
        article("Hong Kong insurer reports premium growth","Hong Kong premiums rose."),
        article("Jeremy England Lee moves to Lockton Re Bermuda as Chairman",
                "A Bermuda appointment. The executive started at Lloyd's in 1978.",
                body="The new leader will relocate to Bermuda. His career began at Lloyd's in London."),
        article("LRQA acquires Hong Kong-based Omega Compliance",
                "UK-based global company LRQA expands its Asian operations.",
                body="UK-based LRQA acquired a Hong Kong supply chain auditing firm to expand in Asia."),
        article("UK publisher reports Texas lawsuit","The Texas Attorney General has sued a company.","https://www.insurancebusinessmag.com/uk/news/industry/texas-lawsuit.aspx"),
        article("Aviva opens US specialty insurance unit","The British insurer says the new unit operates in California."),
        article("US fiscal budget includes new savings products","The American government revised its local tax-free accounts.",
                body="The American budget concerns savings accounts in California, not UK cash ISAs."),
        article("US insurer reports results", "Markets in the United Kingdom also have insurers."),
    ]
    for row in yes:
        assert in_uk_scope(row,row["short"]),("Incorrectly held UK story",row["title"])
        assert public_article_in_scope(row),("Incorrectly hidden UK story",row["title"])
    for row in no:
        assert not in_uk_scope(row,row["short"]),("Unrelated overseas story accepted",row["title"])
        assert not public_article_in_scope(row),("Unrelated overseas story public",row["title"])
    from media_sources import relevant
    assert relevant({"title":"Jewellery-loss claims jump during Halloween week",
        "url":"https://www.aviva.com/newsroom/news-and-research-overview/news-releases/2026/10/claims/"})
    assert relevant({"title":"Lloyds uses AI to strengthen customer fraud support",
        "url":"https://www.lloydsbankinggroup.com/media/press-releases/2026/lloyds/fraud.html"})
    from publication_scope import source_lane
    assert source_lane("https://www.finextra.com/pressarticle/111487/payments-partnership")
    for row in late_source_yes:assert public_article_in_scope(row)
    unknown=article("Insurer changes intermediary model","A new distribution arrangement was introduced.")
    assert not in_uk_scope(unknown, "Insurer changes intermediary model worldwide.")
    assert in_uk_scope(unknown, "The UK insurance market will receive a new intermediary distribution arrangement.")
    fake=article("UK underwriting reform","Regulatory reform announced.")
    assert not in_uk_scope(fake,"An overseas government announces new rules."), "UK not in captured source; do not trust unsupported title"
    assert in_uk_scope(fake,"The UK insurance regulator publishes revised underwriting guidance.")
    regulated=article("FCA warns clone investment provider","",url="https://www.fca.org.uk/news/warnings/example")
    assert uk_market_reason(regulated,"The watchdog issued a warning.")
    from uk_market_scope import named_financial_institution
    assert named_financial_institution("Marsh names Andy Start CBE as Senior Advisor")
    assert named_financial_institution("Aviva appoints commercial insurance director")
    assert not named_financial_institution("US farm equipment business opens a plant")
    # A worldwide source must not crowd out fresh UK leads merely because its
    # older URL is in cooldown; reserve space for evidenced global UK effects.
    import datetime as dt
    from uk_market_scope import discovery_priority, sample_uk_first
    now=dt.datetime(2026,10,27,20,tzinfo=dt.timezone.utc)
    local=[
        {"title":"FCA changes insurance reporting", "source":"FCA",
         "url":"https://www.fca.org.uk/news/press-releases/change", "category":"Insurance","published_at":"2026-10-27T12:00:00Z"},
        {"title":"HSBC reports third-quarter results", "source":"Sky Business",
         "url":"https://news.sky.com/story/hsbc-results-123456", "category":"Banking","published_at":"2026-10-27T11:00:00Z"},
        {"title":"Pension scheme announces new services", "source":"Professional Pensions",
         "url":"https://www.professionalpensions.com/news/12345678/service", "category":"Banking","published_at":"2026-10-27T10:00:00Z"},
        {"title":"Global broker transaction with a London-market impact", "source":"Reinsurance News",
         "url":"https://www.reinsurancene.ws/global-broker-deal/", "category":"Insurance","published_at":"2026-10-27T09:00:00Z"}
    ]
    cooled=[
        {"title":f"Foreign business report {i}", "source":"Insurance Journal",
         "url":f"https://www.insurancejournal.com/news/international/2026/10/27/{i}.htm",
         "category":"Insurance","published_at":"2026-10-27T19:00:00Z"}
        for i in range(38)
    ]
    attempts={item["url"]:{"retry_after":"2026-10-28T04:00:00+00:00"} for item in cooled}
    selected=sample_uk_first(cooled+local,attempts,now,limit=4)
    assert {x["url"] for x in selected}=={x["url"] for x in local}, "Cooled international URLs used available UK source slots"
    assert discovery_priority(local[0])==2 and discovery_priority(local[1])==2
    assert discovery_priority(local[2])==1 and discovery_priority(local[3])==2
    # The same source-reading budget retains international candidates when
    # there is not enough current UK supply.
    selected=sample_uk_first([local[-1],cooled[0]],{},now,limit=2)
    assert {x["url"] for x in selected}=={local[-1]["url"],cooled[0]["url"]}

    print("PASS: UK-only published and discovered scope, overseas rejections, grounded international impact, official UK authority and unsupported headline protection")

if __name__=="__main__":main()
