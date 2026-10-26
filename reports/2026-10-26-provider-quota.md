# Removal of the artificial daily request cap — 26 October 2026

The owner explicitly instructed removal of the application's 30-request daily ceiling. The default daily cap is now `None`; Gemini's actual provider quota remains authoritative. No API key, provider, model, billing setting or paid service was changed.

Usage is still counted and persisted. A ledger already at 30 resumes at request 31; it is not reset or relabelled. Public/internal status reports `daily_limit: null`, `remaining_today: null` and `daily_limit_source: provider`, rather than presenting the app's former cap as Google's quota.

The existing seven-request per-run bound, 15-second request spacing, single-pass batched writing, bounded source retries and provider-429 cooldown remain. A provider refusal stops additional model calls in that cycle. This change does not bypass Google quotas or establish whether the account is on a free or billed tier.

Validation: all 31 offline checks and the full site build passed:
https://github.com/yogeshkaransharma-code/the-brief-financial-news/actions/runs/40422016555

Regression tests cover existing usage at 30 advancing to 31, preserving counts across runs, the per-run ceiling, explicit optional local limits, provider-429 backoff, zero additional calls during cooldown, and status output with no daily application ceiling.

Deployed commit:
https://github.com/yogeshkaransharma-code/the-brief-financial-news/commit/01ea0a8c3c5f7812358efd42062e29732d9ec48f

Production run:
https://github.com/yogeshkaransharma-code/the-brief-financial-news/actions/runs/40422093999

## Observed production result

The existing Gemini API accepted all three requests after the former ceiling: requests 31, 32 and 33 each returned a writing response. Eight articles were published from those three calls; one response had no usable article body and was retained as a technical failure without a rewrite request.

All eight new full articles were verified on production at 23:48:49 UTC. The live edition contained 30 current-day articles and the archive contained 45. Mobile and desktop reading checks passed at 23:49:19 UTC; the linked Guardian source returned HTTP 200 in both checks. The maintenance job completed successfully.

This confirms that the application ceiling, rather than a Google rejection at request 30, was blocking these calls. It does not establish unlimited provider quota or the account's billing tier. No billing configuration was changed.

Example published article:
https://yogeshkaransharma-code.github.io/the-brief-financial-news/story/ai-88472fe6e9e03e100833.html
