# Production repair — 26 October 2026

## Scope and observed root causes

The public burgundy/ivory/charcoal pages, Insurance/Banking/About navigation, catch-up, full articles, jargon explanations, source links, archive and rotating explainers are retained. No new public dashboard was added.

The 00:18 production run (40248699883) had 40 working feeds and 450 cached headlines but only one current UK-date candidate. Its Finextra article returned HTTP 403. No draft, review or publication followed. The next run suppressed the cooled-down candidate without carrying its explanation into candidate outcomes, and labelled the result NO_QUALIFYING_NEWS.

The first repaired live cycle, 40257794907, checked 41 feeds and 31 actual newsroom indexes. Its 504 unique discovered URLs were accounted for: 235 outside the current UK date, 98 irrelevant, 13 already published/retired, 154 without a supported article route, and four current relevant candidates. Two source attempts failed (Bloomberg 403; BBC original date older than its RSS date), one Finextra source remained in cooldown, and one current BBC document was completely captured and dated. This is a counted pipeline loss report, not a claim that every cached headline was fresh news.

Further live execution exposed two response losses:

- The Gemini adapter rejected top-level numbered JSON arrays. A response schema now specifies the batch envelope; harmless numbered arrays are normalised before per-article validation.
- The numeric evidence check treated `3.5 percent` as a dimensionless value, rejecting a source-supported `3.5%`. The comparison now recognises `%`, `percent` and `per cent` as the same unit while still rejecting changed values and missing percentage units. The actual saved draft was recovered with an exact source fingerprint, without another writing request. Independent review remains mandatory.

## Implemented changes

- Deterministic commissioning of relevant, dated, accessible developments removes the model significance veto and the commissioning request. Capacity deferrals are retained, not recorded as editorial rejections.
- Batches of up to three articles use one writer request and a separate complete sentence-review request. Source excerpts, figures, dates, proposal/final status, attribution and article fingerprints remain checked.
- Atomic source/draft/review checkpoints are retained in authenticated Actions evidence artifacts for recovery. Full captured publisher text is not committed to the public source repository or copied to Pages. Published audit records retain fingerprints and claim support.
- Source failures have explicit classes and retry times. A blocked source does not prevent other candidates proceeding. Alternative discovery searches the checked source pool and bounded public Bing RSS results; each alternative independently passes full reading and original-date checks. No paywall bypass or proxy reader is used.
- `data/source-registry.json` is the central registry: 41 feeds, 31 newsroom indexes and reviewed article routes. `data/source-health.json` tracks observed feed/index and full-article access separately. QBE and Beazley indexes were reached but yielded zero dated candidates in this observation; they are not claimed as proven article supply.
- A malformed saved bundle is isolated by the publisher. Saved clean drafts survive a temporary model failure and are reviewed on recovery. Already published IDs/URLs remain idempotent.
- Newsroom cron now has two opportunities per hour (11 and 41 minutes). The separate watchdog checks at 7, 27 and 47 minutes and on newsroom completion, with at most two dispatch recoveries per hour. Completed cycles with an editorial hold are not repeatedly dispatched as technical failures.
- `data/reliability.json` aggregates scheduled runs by UK day, weekday/weekend, observed gaps, publication and live visibility. Fourteen days of run history are retained. This does not claim an hourly guarantee during a GitHub-wide scheduler outage.

## Verification evidence

- Initial repair validation: https://github.com/yogeshkaransharma-code/the-brief-financial-news/actions/runs/40257667547 — 28 offline checks and public artifact validation passed.
- Transport validation: https://github.com/yogeshkaransharma-code/the-brief-financial-news/actions/runs/40258092340 — 29 checks passed, including the actual Gemini HTTP adapter with a mocked response; public artifact passed.
- Numeric/recovery correction: https://github.com/yogeshkaransharma-code/the-brief-financial-news/actions/runs/40258585260 — passed.
- Realistic HTML fixture tests use temporary directories only. They exercise a 403 alongside successful sources, a failed model review, next-cycle reuse of source and draft with one review request, actual publication gates, malformed-bundle isolation, duplicate prevention and the UK autumn clock transition. Synthetic fixture articles never enter production data.
- Production run 40257794907 deployed and passed actual HTTP reading plus mobile (390px) and desktop (1440px) checks. It published zero new articles and correctly raised BLOCKED. These checks prove deployment and existing reading paths, not new editorial success.

## Limits still requiring observation

The local Gemini ceiling remains 30 requests per Pacific quota day and seven per run; no paid provider or higher allowance was enabled. Batching improves potential throughput but cannot guarantee 24 productive hourly cycles within that allowance. Scheduled execution, editorial output and live visibility are measured separately.

Blocked sources observed include Finextra, Bloomberg, Parliament, Allianz, ABI and Revolut. One BBC RSS refresh was correctly excluded because its original document was older. Alternative searches did not find a qualifying replacement in the first repaired cycle. Most overnight discoveries were earlier-dated material; none was relabelled as current news.

Multi-day weekday/weekend reliability remains unproven. The reporting is installed; several days of future scheduled observations are required. A passing offline test or a green deployment is not a production-readiness sign-off.

## Observed new production publication

Run https://github.com/yogeshkaransharma-code/the-brief-financial-news/actions/runs/40258639485 completed successfully. One genuine new article was published at 02:21:17 UTC on 26 October from a current-dated BBC source, using one independent review request against the saved source and original Gemini draft.

- Article: https://yogeshkaransharma-code.github.io/the-brief-financial-news/story/ai-bdc84abf4608177f889b.html
- Title: Healey faces strict budget secrecy ahead of crucial fiscal test
- Desk: Banking
- Original source: https://www.bbc.co.uk/news/articles/ck87z4ng2l03o
- Full article: three sections, original-source link and the existing site glossary treatment.
- Production archive: 16 articles; current edition: one article.
- Model ledger after publication: 28/30 requests used for Pacific quota date 25 October; two remain until the normal reset. No quota increase or paid fallback was enabled.

This establishes one source-to-publication recovery on the actual website. Subsequent scheduled and multi-day reliability must still be observed; it is not certified by this one successful run.

## Production commits

- 6b7fdaa10baa9695e38d198ec4eab6388b53ac0d — pipeline recovery, batching, registry, scheduler and diagnostics.
- 353b36f6fc2ecf157af7450925eade50701c35f7 — live Gemini transport correction.
- 1cfb0d902ba49aec7f4d56bd7bbfd9711e63c700 — numeric unit correction and reuse of the actual saved draft.

Live HTTP verification at 02:21:28 UTC confirmed the new full article, and browser checks at 02:22:32 confirmed mobile/desktop access plus BBC HTTP 200. A secondary browser navigation recorded a timeout coverage warning; the main article/source checks passed. Recovery artifacts are selected by creation time, not by numeric artifact ID.
