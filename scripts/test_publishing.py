#!/usr/bin/env python3
"""Offline approval-to-publication smoke test; never writes the live article feed."""
import json
from pathlib import Path
import tempfile
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
        article = publish_reviewed.publish(path, identity)
        published = json.loads(publish_reviewed.PUBLISHED.read_text(encoding="utf-8"))
        assert len(published) == 1 and published[0]["id"] == article["id"]
        assert published[0]["editorial_status"].startswith("PUBLISHED:")
        try:
            publish_reviewed.publish(path, identity)
        except ValueError as error:
            assert "already been published" in str(error)
        else:
            raise AssertionError("Duplicate publish was allowed")
    print("PASS: reviewed single-article publication and duplicate rejection")


if __name__ == "__main__":
    main()
