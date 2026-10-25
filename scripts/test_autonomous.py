#!/usr/bin/env python3
"""Safe offline test: no connection to actual FCA data, no publication to live site."""
from __future__ import annotations
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import tempfile

import publish_autonomous as auto
from editorial_fixtures import make_bundle, resign
from newsroom_v2 import canonical
from same_day_policy import source_issued_today, clock

def prepared():
    bundle=make_bundle()
    a,audit=bundle["draft"],bundle["audit"]
    year=dt.datetime.now(dt.timezone.utc).year
    url=f"https://www.fca.org.uk/data/complaints-data-{year}-h1"
    a["url"]=a["source_url"]=url
    a["status"]="Published report"
    a["dateISO"]=a["date"]=clock().date().isoformat()
    a["title"]="FCA publishes fresh complaints statistics for UK regulated firms"
    a["short"]="The Financial Conduct Authority has published aggregate complaints statistics for UK financial firms, with data and reporting limitations clearly identified."
    para=("The FCA has published data about the number of complaints UK financial firms reported. "
          "The material identifies the period covered and explains why customer complaints are tracked. "
          "It separates the total received from cases closed and outlines the meaning of reported redress. "
          "The figures describe aggregate industry activity and should not be used as a single measure of service quality. ")
    a["blocks"]=[["New figures",para*2],["Understanding the measures",para*2],
                 ["How to use this data",para*2]]
    captured="\n\n".join([
        f"Official financial-services complaints release section {i}. "
        "The FCA has published data about the number of complaints UK financial firms reported. "
        "The material identifies the period covered and explains why customer complaints are tracked. "
        "It separates the total received from cases closed and outlines the meaning of reported redress. "
        "The figures describe aggregate industry activity and should not be used as a single measure of service quality."
        for i in range(1,15)
    ])
    bundle["captured_source_excerpt"]=captured
    audit["source_sha256"]=hashlib.sha256(captured.encode()).hexdigest()
    a["source_time_precision"]="date"
    a["date_evidence"]={"url":url,"value":a["dateISO"],"precision":"date","method":"offline fixture"}
    audit["date_evidence"]=a["date_evidence"]
    audit["review_headings"]=True
    audit["source_url"]=url
    audit["article_id"]=a["id"]
    audit["source_title"]=a["title"]
    audit["source_number_tokens"]=sorted({m.group().lower().replace(",","") for m in auto.re.finditer(
        r"(?<![\w])(?:£|\$)?\d+(?:[.,]\d+)*(?:%|bn|m|k)?(?![\w])",
        captured+" "+a["title"]+" "+a["dateISO"],re.I)})
    audit["source_document_urls"]=[url]
    audit["source_extraction"]="HTML main content"
    audit["source_retrieval_limits"]="Full captured material shown; check all relevant linked appendices before approval. "
    audit["verbatim_source_checks"]=[
        {"claim":f"FCA official complaint data section {i} contains reported industry measures",
         "source_excerpt":f"Official financial-services complaints release section {i}. The FCA has published data about"}
        for i in range(1,11)]
    fields=[a["title"],a["short"]]+[v for block in a["blocks"] for v in block]
    n=sum(len([x for x in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9£])|\n+",p) if x.strip()]) for p in fields)
    audit["sentence_review"]={"review_schema":"one-verdict-per-sentence-v2","reviewed_sentence_ids":[f"C{i:02}" for i in range(1,n+1)],
                              "total_sentences":n,"reviewed":n,"supported":n,"held":0}
    bundle["editorial_flags"]=[]
    bundle["revision_history"]=[{"revision":0,"problems":[]}]
    resign(bundle)
    return bundle

def main():
    base=prepared()
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder)
        (root/"data").mkdir()
        (root/"generated-drafts").mkdir()
        (root/"data/articles.json").write_text("[]\n")
        aid=base["draft"]["id"]
        (root/"generated-drafts"/(aid+".json")).write_text(json.dumps(base))
        assert not auto.eligible(base),auto.eligible(base)
        dry=auto.publish(root,dry_run=True)
        assert len(dry["published"])==1
        assert json.loads((root/"data/articles.json").read_text())==[]
        published=auto.publish(root)
        assert len(published["published"])==1
        story=json.loads((root/"data/articles.json").read_text())[0]
        assert story["publication_method"]=="autonomous"
        assert story["reviewed_by"]=="autonomous-evidence-screening"
        assert "no human review" in story["editorial_status"]
        assert len(json.loads((root/"data/articles.json").read_text()))==1
        repeat=auto.publish(root)
        assert not repeat["published"]
        # Reset is permanent: a formerly published source cannot be recycled,
        # even when the original article is removed from the public archive.
        (root/"data/retired-source-urls.json").write_text(json.dumps({
            "urls":[base["draft"]["url"]]
        }),encoding="utf-8")
        (root/"data/articles.json").write_text("[]\n",encoding="utf-8")
        retired=auto.publish(root)
        assert not retired["published"], "Retired pre-reset article was republished"
        assert any("reset legacy" in " ".join(x["reason"]) for x in retired["held"])
        # No same-day source, no article. Publishing a fresh AI rewrite must
        # NEVER refresh yesterday's official announcement.
        stale=copy.deepcopy(base)
        stale["draft"]["dateISO"]=(clock().date()-dt.timedelta(days=1)).isoformat()
        stale["draft"]["date"]=stale["draft"]["dateISO"]
        resign(stale)
        reasons=auto.eligible(stale)
        assert not source_issued_today(stale["draft"]), "Yesterday's source unexpectedly eligible"
        assert reasons, "Yesterday's original source escaped final publication approval"
        future=copy.deepcopy(base)
        future["draft"]["dateISO"]=(clock().date()+dt.timedelta(days=1)).isoformat()
        future["draft"]["date"]=future["draft"]["dateISO"]
        resign(future)
        assert not source_issued_today(future["draft"]), "Tomorrow's source unexpectedly eligible"
        assert auto.eligible(future), "Future-dated source escaped the final gate"
        bad=copy.deepcopy(base)
        bad["draft"]["status"]="Proposal"
        resign(bad)
        assert auto.eligible(bad), "Regulatory proposal was improperly eligible"
        bad["draft"]["url"]="https://www.fca.org.uk/news/speeches/unsafe"
        bad["audit"]["source_url"]=bad["draft"]["url"]
        resign(bad)
        assert auto.eligible(bad), "Speech improperly eligible"
        bad=copy.deepcopy(base)
        bad["draft"]["blocks"][0][1]+=" Firms must comply immediately."
        resign(bad)
        assert auto.eligible(bad), "High-risk claim unexpectedly approved"
    print("PASS: autonomous factual allowlist, integrity audit, no-human disclosure, hold and deduplication")

if __name__=="__main__":
    main()

