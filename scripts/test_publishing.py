#!/usr/bin/env python3
"""Offline smoke test of the human-approved publishing path; no real articles changed."""
import datetime as dt
import json
from pathlib import Path
import tempfile
import publish_reviewed


def main():
    paragraph = " ".join(["An official consultation proposes possible changes and invites feedback before final requirements are published."] * 10)
    ident = "ai-" + "1" * 20
    a = {"id": ident, "title": "Regulator consults on possible changes for financial services firms",
         "short": "An official consultation is considering possible changes, and people working at affected firms should read the proposal before making plans.",
         "source": "FCA", "url": "https://www.fca.org.uk/publications/consultation-papers/fictional-smoke-test",
         "status": "Proposal", "dateISO": dt.datetime.now(dt.timezone.utc).date().isoformat(),
         "category": "Regulation", "kind": "original", "ai_assisted": True,
         "editorial_status": "DRAFT", "blocks": [[str(i), paragraph] for i in range(5)]}
    evidence = [{"claim": "An official consultation discusses potential financial rules",
                 "source_excerpt": "An official consultation proposes possible changes and invites feedback before final requirements"}] * 4
    doc = {"draft": a, "audit": {"article_id": ident, "source_url": a["url"], "verbatim_source_checks": evidence}}
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        path = root / (ident + ".json")
        path.write_text(json.dumps(doc), encoding="utf-8")
        publish_reviewed.PUBLISHED = root / "articles.json"
        article = publish_reviewed.publish(path, ident)
        stored = json.loads(publish_reviewed.PUBLISHED.read_text(encoding="utf-8"))
        assert len(stored) == 1 and stored[0]["id"] == article["id"]
        assert "PUBLISHED" in stored[0]["editorial_status"]
        try:
            publish_reviewed.publish(path, ident)
        except ValueError as error:
            assert "already been published" in str(error)
        else:
            raise AssertionError("The script allowed a duplicate article")
    print("PASS: reviewed article is added only once to the publication feed")


if __name__ == "__main__":
    main()
