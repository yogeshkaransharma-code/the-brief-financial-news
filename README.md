# The Brief — autonomous UK financial-services newsroom

**Website:** https://yogeshkaransharma-code.github.io/the-brief-financial-news/

## Editorial restart — 23 October 2026

We have deliberately **cleared the previous public article archive, six prewritten articles and 30 static explainers**. The publication starts again with only articles generated and autonomously published by the newsroom's AI.

**What readers see:** complete, original on-site AI-written articles about UK banking, insurance, regulation and related financial technology, with original-source links, accurate source dates and explicit disclosure of machine-only review. The homepage, lead story, 60-second briefing, search and categories use **only** `data/articles.json` entries with `ai_assisted: true` and `publication_method: "autonomous"`. If no story passes the checks, the page explains that fact; we do not fill it with copied RSS headlines.

**What readers do not see:** raw RSS summaries or source headlines masquerading as articles, prewritten generic explainers, old manually curated stories, failed AI drafts, article previews awaiting human sign-off.

## The AI runs the newsroom, not the user

The `Autonomous financial news desk` GitHub Action checks and writes news six times daily (03:13, 07:13, 11:13, 15:13, 19:13 and 23:13 UTC) and can be manually dispatched. GitHub's schedule is best-effort; a run only publishes articles that pass its evidence checks. The underlying `Collect and publish financial news` workflow keeps the **research/discovery feed** `data/live.json` up to date. It is NOT the public original-article feed.

The autonomous newsroom:

1. Discovers official source announcements from identified publishers, including regulator feeds and first-party insurer/bank newsroom listings.
2. Retrieves the relevant public first-party HTML or supported PDF, recording original URLs and extraction limits. It refuses to silently treat truncated sources as complete.
3. Uses Gemini to write an original article in plain British English.
4. Separately challenges individual statements against captured source text and exact excerpts. Attempts up to two targeted article revisions if claims cannot be supported.
5. Performs conservative deterministic source, figure, denominator, document-integrity and high-risk-language checks.
6. Attempts up to three fully reviewed articles per run. Publishes only eligible articles, with provenance and a version-locked machine-review audit; otherwise holds them rather than inventing facts or using news-feed summaries.

### Coverage that may publish unattended

Only specifically allowed primary-source paths can currently publish automatically, including **Lloyds Banking Group and Aviva releases**, selected first-party company announcements, non-adverse **FCA press releases**, and particular FCA reporting pages. Enforcement accusations and unverified consequential claims remain held. More financial-services sources and story types require careful integration and tested risk controls. Discovering an RSS headline does **not** mean the article is approved or that the original source is accessible. Regulation that changes legal duties, allegations and consequential/uncorroborated claims remain on hold.

This is **real AI-driven publication**, not a hand-authored static site, but the eligible source set is not yet equivalent to comprehensive UK financial-services news coverage. The daily free Gemini tier may also limit how many candidates can be written or revised. No system can guarantee that every AI-produced claim is error-free; the source and the model may both contain mistakes. Machine-reviewed coverage must never be represented as human-editor-approved or independently certified.

## Clean-edition safeguards

- `data/articles.json` was reset to `[]`; old reviewed-article JSON audit files were deleted.
- `data/retired-source-urls.json` blocks the original pre-reset articles from being quietly republished.
- `scripts/verify_site.py` refuses to deploy any manually curated content, prewritten explainer collection, raw source-feed story, old source URL or article not published by the autonomous AI workflow.
- `scripts/verify_approved_articles.py` validates that each autonomous article matches a signed machine-review record and exact article hash.
- `scripts/test_autonomous.py` and `scripts/test_editorial_benchmark.py` test duplicate prevention, narrow source allowlists, source evidence and selected adversarial faults.
- `data/live.json` remains a discovery cache only. Visitors do not see it as a story list.

Removing content from the current published branch **does not erase old versions from the repository's Git history, GitHub Actions archives or third-party search caches**. The new public edition and publication feed do not reference or display the removed pieces.

## Repository map

- `index.html` — lightweight self-contained article-first website.
- `data/articles.json` — public archive of completed autonomous AI articles.
- `data/live.json` — internal hourly research leads, not published stories.
- `data/retired-source-urls.json` — URLs from the superseded edition.
- `scripts/update_feeds.py` — feed discovery.
- `scripts/first_party_sources.py` — original company newsroom discovery.
- `scripts/source_retrieval.py` — bounded first-party document retrieval.
- `scripts/newsroom_v2.py` — Gemini writer, separate sentence review, bounded revision and evidence-repair loop.
- `scripts/publication_scope.py` — limited, reusable primary-source eligibility rules that exclude high-risk enforcement releases.
- `scripts/editorial_gate.py`, `scripts/financial_consistency.py` — mechanical pre-publication checks.
- `scripts/publish_autonomous.py` — source-limited automatic publisher.
- `data/editorial-audits/` — machine review records created only for newly published articles.
- `editorial/EDITORIAL_STANDARDS.md` and `editorial/VERIFICATION_AND_PUBLICATION_PROTOCOL.md` — accuracy, sourcing and accountability standards.

The AI workflow needs the configured GitHub Actions secret `GEMINI_API_KEY`; never expose the key in files, articles or public commits. It currently requests `gemini-3.6-flash`, with configured model fallbacks; model availability and free-tier limits can change. GitHub Actions scheduling is best-effort, not minute-precise.

## Publication ethics

The Brief attributes first-party claims, avoids copying protected third-party articles and distinguishes regulatory proposals from binding decisions. It is not affiliated with the organisations covered and does not provide personal investment or financial advice. Material mistakes require prompt correction, and an unattended corrections/withdrawal mechanism is **not yet a completed feature**.
