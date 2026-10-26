# Single-pass publishing — owner instruction, 26 October 2026

The owner explicitly replaced the earlier independent-review requirement with a read-source, write-once, publish workflow.

Production policy: `newsroom-single-pass-2026-10-26-v1`. The hourly runtime defaults to this policy. Up to three separate complete source documents share one writing request. No AI commissioning, independent reviewer, heading review, numerical register veto, arbitrary article word-count minimum or automatic formatting rewrite is used for new articles. The older review pipeline remains only for historic artifacts and regression tests.

Complete sources and writing responses are checkpointed. Saved usable drafts can publish without another model request. Malformed/empty responses are retained as technical failures instead of repeatedly consuming requests. Unavailable sources and temporary provider failures remain visible; the system cannot publish a complete sourced article when neither source nor usable writing output exists.

Date, duplicate, source identity, non-empty article and Insurance/Banking scope controls remain. Public disclosures and publication records explicitly state that single-pass articles do not receive independent AI or human review. This is not a claim that generated reporting is independently fact-checked.

Validation: all 31 offline checks and full public build passed on the repair branch, including actual publisher integration proving two short, single-section articles from one model call, zero reviewer calls, blocked-source isolation, zero-call saved-draft recovery, truthful disclosure, duplicate/date controls and no malformed-output request loop.

Validation run: https://github.com/yogeshkaransharma-code/the-brief-financial-news/actions/runs/40384180423

Production commit: https://github.com/yogeshkaransharma-code/the-brief-financial-news/commit/ad365726015c6740cc2c9c27446410f444c39d5b

The pre-existing workflow had already consumed today's 30-request local allowance before this deployment. The new policy does not reset the spent allowance, raise the daily cap or authorise paid usage. New writing resumes when allowance is available; saved usable drafts do not require allowance.

## Observed production deployment

Run https://github.com/yogeshkaransharma-code/the-brief-financial-news/actions/runs/40384356977 executed policy `newsroom-single-pass-2026-10-26-v1` with `independent_review: false`. It reused 19 captured sources, made zero model requests and published zero new articles because all 30 current-day requests had already been spent. Source discovery and site deployment continued. The maintenance job, including HTTP and mobile/desktop reading checks, succeeded; the separate editorial alert correctly remained blocked. This proves the deployed policy and site, not a live new model-generated article under that policy. The no-review one-call source-to-publisher path was exercised by the offline integration test; live model validation awaits available quota.
