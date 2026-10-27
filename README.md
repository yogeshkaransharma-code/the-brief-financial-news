# The Brief

[Read The Brief](https://yogeshkaransharma-code.github.io/the-brief-financial-news/) · [Archive](https://yogeshkaransharma-code.github.io/the-brief-financial-news/archive.html) · [Source registry](https://yogeshkaransharma-code.github.io/the-brief-financial-news/sources.html) · [Newsroom status](https://yogeshkaransharma-code.github.io/the-brief-financial-news/status.html)

A UK publication covering UK insurance and banking, with original source-based articles and clearly linked evidence. The newsroom uses Gemini for a single writing pass and checks source completeness, publication dates, routing and duplicate stories. It does **not** commission a separate AI claim review or routinely obtain human editorial sign-off. The writing brief calls for natural British English, proportionate headlines and practical context only when supported by the source.

## Production workflow

`.github/workflows/ai-newsroom.yml` discovers, selects, writes, checks publication eligibility, publishes and deploys on a recurring schedule. GitHub may delay scheduled starts. A successful hourly check is not a promise of a significant new development every hour. `public-site-health.yml` independently checks the deployed site hourly.

1. Discover through RSS/Atom, official newsrooms, regulators, government, original newspaper journalism and specialist industry publications. Source failures are isolated. Recognised organisations and configured polling routes are separate concepts.
2. Retrieve accessible original evidence, including original journalism without a corresponding corporate press release. Exact publisher domains and supported article routes live in `scripts/media_sources.py`; the official directory and index registry supply complementary discovery. Access controls and paywalls are not bypassed.
3. Verify the original publication date on the document itself. RSS dates, modification dates and unrelated dates cannot certify an original article's freshness. Preserve proposals, forecasts, reported statements and allegations accurately.
4. Select relevant, date-verified source documents using deterministic source/diversity and duplicate controls. Selection currently does **not** involve an AI newsworthiness review; it can therefore include routine announcements.
5. Ask Gemini to write original source-based articles in a single request, using the grounded British newsroom voice rules in `scripts/single_pass.py`. Before publication, deterministic controls check source integrity, routing, original date and duplicate identity. There is **no** separate sentence-by-sentence review; this is a known accuracy limitation.
6. Publish eligible articles using their actual source and publication dates. Today's edition contains same-day UK developments; older material remains in the accurately dated searchable archive. There is no daily article-count ceiling.
7. Maintain source-linked headlines internally for discovery and selection. The public publication contains complete The Brief articles; external headlines never become artificial article pages or public headline filler.
8. Deploy real HTML reading pages to GitHub Pages. Check the exact deployment run, all current article bodies, archive access and the original-article homepage. Check mobile and desktop presentation after code changes and new articles, including archive search, subject filters and source-registry search.

## Hourly edition and sector reading desks

Every newsroom run now writes `data/hourly-desk.json` and deploys a complete `hourly.html` briefing page with the actual refresh time. The briefing uses **already published** full articles and keeps their original dates visible. The hourly briefing is a new edition/checkpoint, **not** a claim that a brand-new article or event occurred every hour. On quiet days, context is explicitly dated; the same-day homepage never republishes an old development as breaking news. No Gemini requests are used to rebuild the briefing.

The homepage has four insurance/banking/broker/regulatory entry points which open appropriately filtered, dated archive reports. Desktop and mobile tests verify the category path, hourly reading page, chronological integrity and source evidence. Original article publication continues through the single-pass Gemini writer and deterministic source/date checks.

The writing brief is deliberately more commercially grounded: intermediary partnerships, insurer and MGA capacity, underwriting, claims, banking operations and leadership changes are eligible, not only major regulatory statements. Small announcements must stay small; practical implications must not be invented. Sources are captured and date-checked but their claims are not independently verified.

**Capacity reality:** the local ceiling is seven model requests per run, while Google controls the actual free-tier daily allowance. Up to three articles can be written per request. There is no local daily request ceiling and no separate reviewer call; provider limits and genuine source availability still constrain publication. Hourly deployment on GitHub is best-effort and may be delayed. Neither a local request cap nor a successful deployment establishes provider quota, guaranteed genuine news supply, or a permanent exact-time publishing SLA. Do not increase billing, drop source evidence or silently change dates just to meet a posting target.

## Costs and retries

Only the existing Gemini Actions secret and configured Gemini model are used. No billing settings, paid search or provider fallback are enabled.

The local allowance is **seven requests per run**, including failed requests, with no local daily cap. One writing request can contain up to three sources. There is no AI commissioning or reviewer call in the current production route. The allowance can support several articles in a run; it does not impose an article quota or promise a particular output count. Calls are reserved before execution, spaced and recorded with token usage.

Per-source cooldowns, recovery checkpoints, duplicate checks and provider circuit breakers control retries. Provider throttling remains visible. The local allowance is not Google's authoritative project quota or billing meter. Recurring launch-only diagnostics and retrospective launch jobs are removed from the production workflow.

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
- `data/editorial-audits/`: source and article fingerprints, date evidence and recorded automated screening; these records do not represent independent claim review.
- `data/live.json`: private-to-the-site discovery cache; the repository itself is public.
- `generated-drafts/`: source evidence, held drafts and reports preserved in 90-day Actions artifacts.
- `public/data/articles.json`: today's qualifying original articles.
- `public/data/archive.json`, `archive.html`, `edition/YYYY-MM-DD.html`, `story/ID.html`: dated editions and full reading pages.
- `sources.html` and `public/data/sources.json`: searchable configured discovery routes with available observation status.

Legacy and explicitly labelled retrospective material remains in its dated archive with its original notices. Restoring access does not certify old claims. Automated source/date checks do not guarantee factual truth or imply human approval. [Report a correction](https://github.com/yogeshkaransharma-code/the-brief-financial-news/issues/new?title=Correction%20request) with the article link and evidence; checked revisions must update the approval record and show a correction notice.
