# The Brief system audit — 25 October 2026

Baseline: main `9fbd1f33494bb536e8c45112e7691911691fc703`. Inspected all 53 tracked text files, three workflows, ten published article records, eleven approval records, discovery data and retry ledger; inspected the actual public homepage in Chrome. No production changes preceded this audit.

## Evidence and root causes

* The actual homepage shows zero articles on 25 October. `build_public.py` filters the public JSON AND generated story routes to same-day records. `sync_fallback.py` also deletes historical story pages. Ten published records survive in GitHub but have no public archive or routes.
* Latest newsroom run 40143330963 / job 121019431193 completed green with zero candidates, zero drafts and zero published articles. All deployment steps were skipped. Health issues only warnings. The separate collector deploys an empty edition and labels itself “Collect and publish financial news”.
* Two scheduled workflows collect the same feeds and share a deployment queue. Production runs execute the full historical test suite every hour. Multiple generations of publishing helpers, hard-coded launch sources and obsolete commentary obscure the real path.
* The retained daily API budget is 20/20 on UTC date 24 October. Writer and reviewer each cost a request. Hidden capacity fallback can consume a second request for either stage. There is no request spacing, durable per-call journal, token usage record, or structured handling of Retry-After. Reset is UTC although Google's RPD reset is Pacific time. Old failed calls and repeated repairs have consumed capacity; model names in README, defaults and workflows disagree.
* Company listing dates are accepted without checking the original article's publication metadata. `published_date` can take any time element, including a related story or modified timestamp. Original source date precision is represented using invented midday timestamps internally. Date-only information must stay date-only.
* Candidate selection and timestamp recovery use UTC dates in several places even though the final gate uses Europe/London. The client midnight guard only runs every ten minutes and cached no-JavaScript HTML may outlive the edition.
* 21 RSS feeds exist, but only three are specialist industry outlets. Primary discovery has 13 indexes and publication scope has several one-off exact URLs. Individual source errors are not surfaced to readers. “No news” cannot be inferred from failed discovery.
* Independent review does challenge every headline/standfirst/body sentence using exact source passage IDs. Numeric and denominator checks, fingerprint binding and high-risk holds are valuable and should be retained. However headings and optional glossary definitions escape sentence review, and exact passage matching is not independent confirmation of company claims.
* Public build retains approved articles only, but publisher truncates the canonical archive at 150 records. The daily article cap is actually per run. Approval records retain hashes but not the source snapshot/full review, which are lost when 14-day artifacts expire.
* Existing browser test targets `article` on a page whose reading wrapper is `main`, so a real article would fail that test. On empty days it passes without opening any article or source. HTTP probes also skip every article when today's edition is empty.
* Existing presentation has a coherent paper/burgundy editorial style, useful explainers and accessible mobile breakpoints. Preserve that identity while restoring archive navigation, full reading pages, source dates, coverage filters and operational transparency.

## Rebuild design

One serial hourly pipeline: free discovery → original document/date verification → budgeted Gemini writer → separate sceptical claim challenge → deterministic publication gate → durable provenance → dated editions and archive → Pages deploy → live HTTP and mobile browser verification. Publication outcome is separate from deployment health and recorded as PUBLISHED, NO_QUALIFYING_NEWS, BLOCKED or DEGRADED. A green maintenance run must not be labelled publication.

Keep Gemini, disable other providers and implicit fallback, enforce bounded calls before network requests, persist ledger even on failure, respect retry time and Pacific reset, and leave billing untouched. Ten articles/day is an upper bound, five is an editorial aim, not a requirement to invent content. No new article can be demonstrated without a qualifying same-day primary development; fixtures are explicitly offline and must never enter production.

## Verification baseline

Local source checks initially blocked by the scratch interpreter lacking BeautifulSoup; use the installed primary runtime. Provenance validator passes for ten existing article fingerprints. Public build and public verifier both pass while serving zero articles and zero story pages: this confirms the tests did not measure archive availability or useful publication. Later validation and live evidence are recorded separately in OPERATIONS.md / workflow artifacts.
