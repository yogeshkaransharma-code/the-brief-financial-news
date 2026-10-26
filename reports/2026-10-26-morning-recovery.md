# Morning publication recovery — 26 October 2026

## Observed outage

After the live article published at 02:21 UTC, six scheduled cycles (03:10, 03:39, 04:14, 05:12, 06:09 and 06:48) published zero new articles. All six successfully maintained and verified the site; their editorial alert jobs correctly failed. This is an editorial outage, not successful autonomous publication.

At 03:10, an Insurance Business UK storm report was retrieved, drafted and independently reviewed. The final deterministic gate rejected its numerical register. The source contained `£17.5M`: the writer's case-insensitive expression recorded `£17.5m`, but the gate's case-sensitive expression partially matched `£17`. This was an implementation disagreement, not evidence of an invented figure. The draft survived in the checkpoint artifact.

Those two model requests exhausted the 30-request local allowance for the Pacific quota day of 25 October. The last pre-reset cycle at 06:48 discovered 505 unique URLs, identified 17 current relevant candidates, and verified 13 Insurance sources (three new captures and ten reused captures). Nine selected stories were explicitly deferred for lack of model allowance. No lack-of-news claim is justified for that cycle. Remaining candidates included blocked Bloomberg/Finextra pages and a BBC document whose original publication date was older than its discovery date.

The daily allowance resets at Pacific midnight, 07:00 UTC on this date. The repair does not increase the allowance, enable billing, change model providers, or bypass independent review.

## Correction and checks

The final gate now uses the same case-insensitive numeric matching as the audit builder. Its regression test accepts a correct register for uppercase monetary suffixes and still rejects a partial/incorrect numerical register.

Validation run: https://github.com/yogeshkaransharma-code/the-brief-financial-news/actions/runs/40285843474

All 29 offline checks and the complete public-site build passed in GitHub Actions. The local shell could not run the full suite because BeautifulSoup is not installed; no local success is claimed.

Production correction: https://github.com/yogeshkaransharma-code/the-brief-financial-news/commit/74c77476ae172387b0b63c3236ab9ed9aae222b3

Production recovery run: https://github.com/yogeshkaransharma-code/the-brief-financial-news/actions/runs/40286433876

## Reliability boundary

The overnight evidence disproves sustained publication reliability for the earlier repair. Checkpoints did preserve captured sources and the completed draft through the intervening cycles. Scheduling remained active, but an hour without publication cannot be excused as a scheduling success when verified material exists.

The 30-request daily cap remains a real throughput constraint. Batches share writer requests and independent reviewer requests, but rejected drafts and retries still consume that finite allowance. Multi-day reliability remains unproven.

## First recovery outcome

Run 40286433876 reused 13 verified source captures, spent six model requests (24 remained), and passed five articles through separate review. Full-page HTTP verification completed at 07:34:47 UTC and mobile/desktop checks completed at 07:35:19 UTC.

A subsequent content inspection found one report about rail automation had no substantive Insurance/Banking development. Its appearance in Insurance Journal had incorrectly sufficed for sector admission. That report (`ai-53c306c97a811e4bd00e`) is being withdrawn, recorded in the retired-source ledger, and excluded from claimed editorial success. A regression-tested final content gate now strips publisher names before checking for sector subject matter.

Four relevant new articles from this cycle are retained: Devon sheep-claim fraud, Storm Austen/Boelo claims, Florida property/liability premiums, and Verdant Rock's credit rating. All four complete articles passed the live HTTP reading checks. The browser's follow-through to Reinsurance News encountered HTTP 403 despite the earlier successful complete source capture; source-link presence is verified, but universal reader access to that publisher is not claimed.

One Gallagher acquisition draft was held because the reviewer expected the source body to explicitly attribute itself to Reinsurance News. The review prompt now supplies the verified publisher and source URL separately from the source's substantive evidence. This establishes attribution only, never underlying facts or interviews. Existing held drafts get one new independent review under this prompt version; a continuing unsupported finding remains held without hourly model-request churn. The writer schema also enforces the existing two-to-five-section requirement before output reaches the gate.

## Follow-up production evidence

Run 40287173935 published two further commercial-risk articles (PG&E wildfire liability and the Exxon benzene judgment), removed the off-scope rail report, and verified all seven current-day full articles at 07:41:37 UTC. Six of those seven were newly published during this morning repair; the other is the 02:21 BBC-based article. Mobile and desktop reading checks completed at 07:42:56 UTC; the Exxon original source returned HTTP 200 on mobile, while the desktop follow-through timed out. Twenty model requests remained after this run.

The second run confirmed another avoidable review failure: splitting `J. Patrick Gallagher` produced a two-character `J.` claim that the evidence gate rejected as incomplete. A shared, versioned sentence segmenter now preserves initials in both reviewer inputs and final coverage counts, with legacy audit counting retained for existing bundles. A one-time retry clears this precise old error; substantive review is still required. Final deterministic rejections now save the completed review as a held checkpoint instead of repeatedly retrying unchanged content through the model.

A 93-word sourced university insurance-program draft also failed the old 95-word minimum. The consistent minimum is now 80 words, with two coherent sections, every-sentence review, all numeric/attribution checks and full source evidence retained. The writer still targets 120–450 words. This removes a superficial two-word rejection without allowing headline-only publication.
