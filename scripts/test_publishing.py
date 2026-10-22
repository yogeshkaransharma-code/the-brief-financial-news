#!/usr/bin/env python3
"""Offline approval-to-publication smoke test; never writes the live article feed."""
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch
import publish_reviewed
from editorial_fixtures import make_bundle


def main():
    fixture = make_bundle()
    identity = fixture["draft"]["id"]
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        path = root / (identity + ".json")
        path.write_text(json.dumps(fixture), encoding="utf-8")
        publish_reviewed.PUBLISHED = root / "articles.json"
        publish_reviewed.AUDITS = root / "editorial-audits"
        review = {
            "EDITORIAL_ATTESTATION": "ALL_CHECKS_COMPLETED",
            "GITHUB_ACTOR": "synthetic-test-editor",
            "EDITORIAL_REVIEW_NOTES": "Fictional CI sample: inspected every claim and the original fixture.",
        }
        # The same complete, synthetic article must be rejected without a
        # responsible human attestation; CI must never bypass this gate.
        with patch.dict(os.environ, {}, clear=True):
            try:
                publish_reviewed.publish(path, identity)
                raise AssertionError("Unattested publication was allowed")
            except ValueError as error:
                assert "attestation" in str(error)
        with patch.dict(os.environ, review):
            article = publish_reviewed.publish(path, identity)
            published = json.loads(publish_reviewed.PUBLISHED.read_text(encoding="utf-8"))
            assert len(published) == 1 and published[0]["id"] == article["id"]
            assert published[0]["editorial_status"].startswith("PUBLISHED:")
            assert article["reviewed_by"] == "synthetic-test-editor"
            history = json.loads((publish_reviewed.AUDITS / (identity + ".json")).read_text(encoding="utf-8"))
            assert history["reviewed_draft_sha256"] == fixture["audit"]["draft_sha256"]
            assert history["approved_by_github_actor"] == "synthetic-test-editor"
            try:
                publish_reviewed.publish(path, identity)
            except ValueError as error:
                assert "already been published" in str(error)
            else:
                raise AssertionError("Duplicate publish was allowed")
    print("PASS: human attestation, reviewed fingerprint, single publication and duplicate rejection")


if __name__ == "__main__":
    main()
