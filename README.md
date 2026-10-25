# The Brief

[Read The Brief](https://yogeshkaransharma-code.github.io/the-brief-financial-news/) · [Archive](https://yogeshkaransharma-code.github.io/the-brief-financial-news/archive.html) · [Source registry](https://yogeshkaransharma-code.github.io/the-brief-financial-news/sources.html) · [Newsroom status](https://yogeshkaransharma-code.github.io/the-brief-financial-news/status.html)

A UK financial-services publication covering banking, insurance, reinsurance, brokers, MGAs, pensions, wealth, financial technology and regulation. Gemini commissions original articles, writes them in British English and reviews their claims in a separate evidence-based request. Articles disclose automated production and link to their sources.

## Production workflow

`.github/workflows/ai-newsroom.yml` discovers, commissions, writes, reviews, publishes and deploys every hour. GitHub may delay scheduled starts. A successful hourly check is not a promise of a significant new development every hour. `public-site-health.yml` independently checks the deployed site hourly.

1. Discover through RSS/Atom, official newsrooms, regulators, government, original newspaper journalism and specialist industry publications. Source failures are isolated. Recognised organisations and configured polling routes are separate concepts.
2. Retrieve accessible original evidence, including original journalism without a corresponding corporate press release. Exact publisher domains and supported article routes live in `scripts/media_sources.py`; the official directory and index registry supply complementary discovery. Access controls and paywalls are not bypassed.
3. Verify the original publication date on the document itself. RSS dates, modification dates and unrelated dates cannot certify an original article's freshness. Preserve proposals, forecasts, reported statements and allegations accurately.
4. Send a diverse selection of complete, date-verified documents to Gemini for commissioning. It ranks worthwhile developments, rejects publicity and duplicates, and records reasons. Unknown candidates and incomplete decisions are rejected. Changing source pools do not reset cached document-specific rejections.
5. Write complete original articles and separately challenge every headline, standfirst, section heading and sentence against captured evidence. Deterministic controls check dates, figures, coverage, integrity and attribution. Disputed consequential reporting without corroboration is held; official enforcement findings require explicit attribution.
6. Publish approved articles using their actual source and publication dates. Today's edition contains same-day UK developments; older material remains in the accurately dated searchable archive. There is no daily article-count ceiling.
7. Maintain source-linked headlines internally for discovery and commissioning. The public publication contains complete The Brief articles; external headlines never become artificial article pages or public headline filler.
8. Deploy real HTML reading pages to GitHub Pages. Check the exact deployment run, all current article bodies, archive access and the original-article homepage. Check mobile and desktop presentation after code changes and new articles, including archive search, subject filters and source-registry search.

## Costs and retries

Only the existing Gemini Actions secret and configured Gemini model are used. No billing settings, paid search or provider fallback are enabled.

The durable allowance is **seven requests per run and 30 per Pacific quota day**, including failed requests. A commissioning batch costs one request, followed by one writer and one separate reviewer request per draft. The allowance can support several articles in a run; it does not impose an article quota or promise a particular output count. Calls are reserved before execution, spaced and recorded with token usage.

Per-source cooldowns, unchanged-pool caching, document-specific rejection caching, duplicate checks and provider circuit breakers control retries. Daily allowance exhaustion remains visible. The local allowance is not Google's authoritative project quota or billing meter. Recurring launch-only diagnostics and retrospective launch jobs are removed from the production workflow.

## Operational evidence

Editorial results and technical delivery are separate:

- `data/status.json`: editorial outcome, source coverage warnings, candidates, commissions, holds, published article count, internal discovery leads and request consumption.
- `data/run-history.json`: observed deployment, live HTTP reading and browser outcomes after the checks finish.
- `data/launch-acceptance.json`: evidence checkpoint for repeated successful scheduled runs, original Gemini publication verified live, sector breadth, verified article delivery and mobile/desktop reading. It remains pending until observed evidence supports each criterion.

The public status artifact is built before its own deployment checks. It labels this timing, links to the current workflow, and includes verified history from preceding runs. Missing reports, failed pipeline stages, model pauses, failed deployments and unreadable live content produce actionable failing workflow results. Individual unavailable sources produce coverage warnings while working routes continue. GitHub's normal notifications apply; no external messaging integration is assumed.

A code-triggered run, mocked test, green deployment or publisher-link refresh cannot by itself establish launch acceptance or continuous editorial performance.

## Validation

```sh
python -m pip install -r scripts/requirements-newsroom.txt
python scripts/run_checks.py
python scripts/build_public.py
python scripts/verify_public.py
python scripts/verify_live.py
```

Production browser checks run at 390px and 1440px and preserve screenshots as Actions artifacts. A failed external publisher screenshot is recorded separately from The Brief's own article readability.

## Data and accountability

- `data/articles.json`: complete approved article archive.
- `data/editorial-audits/`: immutable article/source fingerprints, date evidence and reviewed claims.
- `data/live.json`: private-to-the-site discovery cache; the repository itself is public.
- `generated-drafts/`: source evidence, held drafts and reports preserved in 90-day Actions artifacts.
- `public/data/articles.json`: today's qualifying original articles.
- `public/data/archive.json`, `archive.html`, `edition/YYYY-MM-DD.html`, `story/ID.html`: dated editions and full reading pages.
- `sources.html` and `public/data/sources.json`: searchable configured discovery routes with available observation status.

Legacy and explicitly labelled retrospective material remains in its dated archive with its original notices. Restoring access does not certify old claims. Machine review does not guarantee factual truth or imply human approval. [Report a correction](https://github.com/yogeshkaransharma-code/the-brief-financial-news/issues/new?title=Correction%20request) with the article link and evidence; checked revisions must update the approval record and show a correction notice.
