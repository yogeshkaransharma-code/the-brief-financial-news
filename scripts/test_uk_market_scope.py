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
        article("International insurer expands UK underwriting capacity",
            "The insurer will add UK underwriting capacity for London market brokers."),
        article("Pensions contributions face change","British pension savers would see an increase in contributions."),
    ]
    no=[
        article("Fire and explosion occur at Quaker Oats plant in Iowa","A blaze occurred in Cedar Rapids."),
        article("California regulator sets up biodiversity and insurance risk commission","California is examining insured losses."),
        article("Italian insurance market adapts to nat cat scheme","Italian brokers adjust domestic commercial cover."),
        article("Lockton appoints new US casualty leader","Lockton named a leader for its American division."),
        article("European Commission unveils climate insurance programme","EU businesses will be affected."),
        article("Hong Kong insurer reports premium growth","Hong Kong premiums rose."),
        article("UK publisher reports Texas lawsuit","The Texas Attorney General has sued a company.","https://www.insurancebusinessmag.com/uk/news/industry/texas-lawsuit.aspx"),
        article("Aviva opens US specialty insurance unit","The British insurer says the new unit operates in California."),
        article("US insurer reports results", "Markets in the United Kingdom also have insurers."),
    ]
    for row in yes:
        assert in_uk_scope(row,row["short"]),("Incorrectly held UK story",row["title"])
        assert public_article_in_scope(row),("Incorrectly hidden UK story",row["title"])
    for row in no:
        assert not in_uk_scope(row,row["short"]),("Unrelated overseas story accepted",row["title"])
        assert not public_article_in_scope(row),("Unrelated overseas story public",row["title"])
    unknown=article("Insurer changes intermediary model","A new distribution arrangement was introduced.")
    assert not in_uk_scope(unknown, "Insurer changes intermediary model worldwide.")
    assert in_uk_scope(unknown, "The UK insurance market will receive a new intermediary distribution arrangement.")
    fake=article("UK underwriting reform","Regulatory reform announced.")
    assert not in_uk_scope(fake,"An overseas government announces new rules."), "UK not in captured source; do not trust unsupported title"
    assert in_uk_scope(fake,"The UK insurance regulator publishes revised underwriting guidance.")
    regulated=article("FCA warns clone investment provider","",url="https://www.fca.org.uk/news/warnings/example")
    assert uk_market_reason(regulated,"The watchdog issued a warning.")
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
