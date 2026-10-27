"""Public, honest SEO metadata and sitemap for the GitHub Pages project.

Only actual generated reader pages go in the sitemap. This is discovery support,
not a guarantee of indexing, Google News eligibility or a human editorial review.
"""
from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET

BASE = "https://yogeshkaransharma-code.github.io/the-brief-financial-news/"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ET.register_namespace("", SITEMAP_NS)


def absolute(path: str) -> str:
    return BASE + ("" if path == "index.html" else path)


def _json_script(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return '<script type="application/ld+json">' + payload + "</script>"


def _meta(page_path: Path, rel: str, title: str, description: str, schema: dict | None = None) -> None:
    import html
    document = page_path.read_text(encoding="utf-8")
    if document.count("</head>") != 1:
        raise ValueError("Missing/ambiguous head for " + rel)
    if 'rel="canonical"' in document:
        raise ValueError("Conflicting canonical metadata in " + rel)
    from_url = absolute(rel)
    additions = [
        '<link rel="canonical" href="' + html.escape(from_url, quote=True) + '">',
        '<meta property="og:type" content="' + ("article" if rel.startswith("story/") else "website") + '">',
        '<meta property="og:site_name" content="The Brief">',
        '<meta property="og:title" content="' + html.escape(title, quote=True) + '">',
        '<meta property="og:description" content="' + html.escape(description, quote=True) + '">',
        '<meta property="og:url" content="' + html.escape(from_url, quote=True) + '">',
    ]
    if schema:
        additions.append(_json_script(schema))
    document = document.replace("</head>", "\n" + "\n".join(additions) + "\n</head>", 1)
    page_path.write_text(document, encoding="utf-8")


def add_search_discovery(out: Path, articles: list[dict]) -> None:
    """Called after a complete site build; does not mutate source content."""
    by_id = {a["id"]: a for a in articles}
    paths = ["index.html", "about.html", "insurance.html", "banking.html", "archive.html", "sources.html", "privacy.html"]
    paths += sorted(p.relative_to(out).as_posix() for p in (out / "edition").glob("*.html"))
    paths += sorted(p.relative_to(out).as_posix() for p in (out / "story").glob("*.html"))

    site_schema = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "The Brief",
        "url": BASE,
        "inLanguage": "en-GB",
        "description": "Independent UK insurance and banking news, explained clearly.",
        "publisher": {"@type": "Organization", "name": "The Brief", "url": BASE},
    }
    entries = []
    for rel in paths:
        page = out / rel
        if not page.is_file():
            raise ValueError("Sitemap cannot list nonexistent page: " + rel)
        name = "The Brief — UK insurance and banking news"
        desc = "Insurance and banking news explained in plain British English."
        structured = site_schema if rel == "index.html" else None
        modified = None
        if rel == "about.html":
            name = "About The Brief"
            desc = "Our purpose, coverage, sources and corrections."
        elif rel == "insurance.html":
            name = "Insurance news — The Brief"
            desc = "UK insurance, intermediaries, underwriting, claims and industry developments."
        elif rel == "banking.html":
            name = "Banking news — The Brief"
            desc = "UK banking, lending, payments and regulation."
        elif rel == "archive.html":
            name = "The Brief archive"
            desc = "Earlier UK insurance and banking news, kept with their original dates."
        elif rel == "privacy.html":
            name = "Privacy — The Brief"
            desc = "The Brief website privacy and audience measurement information."
        elif rel == "sources.html":
            name = "Sources — The Brief"
            desc = "Source publications and original evidence behind The Brief."
        elif rel.startswith("edition/"):
            name = "The Brief edition — " + rel.split("/")[-1][:-5]
            desc = "Dated insurance and banking news from The Brief."
        elif rel.startswith("story/"):
            ident = rel.removeprefix("story/").removesuffix(".html")
            if ident not in by_id:
                raise ValueError("Unrecognised article page in SEO build: " + rel)
            a = by_id[ident]
            name = str(a["title"])
            desc = str(a.get("short") or "")
            modified = str(a.get("updated_at") or a["published_at"])
            structured = {
                "@context": "https://schema.org",
                "@type": "NewsArticle",
                "mainEntityOfPage": {"@type": "WebPage", "@id": absolute(rel)},
                "headline": name,
                "description": desc,
                "datePublished": a["published_at"],
                "inLanguage": "en-GB",
                "articleSection": a.get("desk_section") or a.get("category") or "Financial services",
                "publisher": {"@type": "Organization", "name": "The Brief", "url": BASE},
                "author": {"@type": "Organization", "name": "The Brief", "url": BASE},
                "citation": a.get("source_url") or a["url"],
                "isAccessibleForFree": True,
            }
            if a.get("updated_at"):
                structured["dateModified"] = a["updated_at"]
        _meta(page, rel, name, desc, structured)
        entries.append((rel, modified))

    root = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    for rel, modified in entries:
        entry = ET.SubElement(root, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(entry, f"{{{SITEMAP_NS}}}loc").text = absolute(rel)
        if modified:
            # Only actual article publication/edit timestamps are used.
            ET.SubElement(entry, f"{{{SITEMAP_NS}}}lastmod").text = modified
    ET.ElementTree(root).write(out / "sitemap.xml", encoding="utf-8", xml_declaration=True)

    (out / "robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: " + BASE + "sitemap.xml\n", encoding="utf-8")
