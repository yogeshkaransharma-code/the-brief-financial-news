# Production verification — 25 October 2026

This is a verified rebuild and deployment, **not certification that continuous original-news publication is complete**.

## Reproducible evidence

Production run: https://github.com/yogeshkaransharma-code/the-brief-financial-news/actions/runs/40147450178

- Fifteen offline check groups passed, including 22 expected editorial holds, original-vs-modified date rejection, conflicting dates, UK DST boundaries, unsupported headings, duplicate prevention and a complete mocked writer/reviewer/publisher flow. Fixtures never entered the real publication feed.
- Real GitHub Pages deployment passed. Live HTTP probe found zero qualifying reports for 25 October, ten archived records, ten complete story routes and an accessible historical full article.
- Actual Chromium tests passed at 390 × 844 and 1440 × 844. They checked rendered headlines, complete article paragraphs, no horizontal overflow, JavaScript errors, archive navigation and original evidence. The tested FCA evidence returned HTTP 200 at both viewport widths, with heading “Access to cash coverage in the UK 2025 H1”.
- Browser evidence artifact: `live-reader-evidence-40147450178`, artifact ID 12580464014. It contains homepage/article/original-source screenshots at both sizes and `result.json`. Retention: thirty days.
- Independent manual Chrome inspection confirmed the actual homepage, ten live archive headlines, archive search (“Lloyds” returned two reports), the complete private-markets FCA article, source date/publication date labels, and a working link to the original FCA release. This is separate from local preview checks.
- The maintenance/deployment job passed. The overall run deliberately failed its attention job: **DEGRADED**, zero newly published articles. The “News published” job was skipped. This proves technical success is not represented as news publication.

## Observed unattended limitations

1. Twenty requests had already been recorded against the existing API allowance for 24 October. This rebuild made **zero Gemini requests** in its production verification run. Google's Pacific quota day resets at 07:00 UTC / UK time on 25 October; actual project availability remains Google's decision. No billing settings were changed. The chosen model is documented by Google as offering a free tier, but this environment cannot inspect the project's billing configuration or usage by other applications.
2. No qualifying original development for 25 October was found in that early-Sunday run. A real new Gemini-written, independently reviewed and same-day-published report has therefore **not** been demonstrated under the rebuilt pipeline. The offline integration test proves control flow, not live model reliability or article quality.
3. The GitHub runner read 24 of 25 RSS feeds and 15 of 19 primary indexes. Money Marketing's RSS and the Allianz UK, Parliament, ABI and Revolut indexes returned HTTP 403. Local retrieval results differed. These restrictions were not bypassed; discovery coverage is incomplete and the public status records the failures.
4. A readable index with zero dated candidates is not proof that it contains no new announcement. Hydrated templates, changed paths and ambiguous datelines can reduce discovery. A bounded fallback reads candidate original pages, but it does not render arbitrary newsroom JavaScript. Paywalled or inaccessible reporting is not copied or used as a substitute for original evidence.
5. Publication remains deliberately limited to identifiable primary release lanes with complete readable evidence. Enforcement allegations, consequential legal interpretations, ambiguous data, oversized/incomplete documents and unsupported causal claims are held. It is not comprehensive coverage of everything happening in financial services.
6. Machine review challenges the article against the source; it cannot prove the source is correct or provide human editorial accountability. Existing historical articles carry a legacy verification notice. Their recorded original dates and old interpretations have not all been revalidated under the new policy; one inspected FCA data page yielded conflicting publication signals and would now be held.
7. GitHub scheduling is best-effort. Public status over three hours old is stale; the nightly independent check fails on stale or degraded monitoring. Browser midnight guards remove prior-day articles, but cached HTML with JavaScript disabled can persist until the next Pages build. The static source/publication dates remain visible. Corrections need a checked revision; the issue tracker accepts reports but there is no guaranteed round-the-clock human response.
8. Local request limits bound attempts; they are not a provider-side monetary cap. A force-killed runner before its ledger is committed can lose reservations. One serial production workflow, write-before-call local journalling, always-save steps and conflict-safe Git reconciliation reduce that risk, but cannot guarantee storage during every infrastructure failure.

## Operating contract

Keep today's edition isolated; preserve prior editions; aim for five to ten worthwhile reports only when verified developments and free capacity permit. Review the public status and Actions evidence when a source is blocked or a candidate is held. Never solve an empty edition by changing dates, weakening the evidence gate, silently switching providers or enabling billing.

Next acceptance milestone: a genuinely new UK-calendar-day primary announcement passes real Gemini writing and independent challenge, is committed and deployed automatically, and passes the live browser checks. Until then, end-to-end autonomous publication remains an open acceptance item.

## Immediate launch test — completed 25 October, 00:58 UTC

At the owner's request, the deferred ChatGPT follow-up was cancelled and a separately capped two-request diagnostic ran immediately. This did not reset the twenty-request production counter, change billing or publish historical material.

Run: https://github.com/yogeshkaransharma-code/the-brief-financial-news/actions/runs/40148709835
Result: `data/launch-test.json` records **PASSED**. Gemini 3.5 Flash-Lite returned a real original draft and a separate review of thirteen statements, with zero unresolved editorial flags. Both requests returned content: 1,501 and 2,160 total tokens respectively. The final gate correctly rejected the genuine 23 October source as stale; it also identified a conservative high-risk hold. The test stayed unpublished. Live deployment and mobile/desktop reading checks passed again.

This supersedes the earlier uncertainty about whether the existing key could perform writing and claim review. The earlier 20/20 figure was a local request guard, **not evidence that Gemini itself had rejected service**. Aggregate accounting now includes twenty prior production attempts plus two diagnostic calls. The one-time diagnostic allowance is exhausted and cannot silently repeat.

Still open: actual automatic publication of a qualifying same-day development, and four primary indexes denied to the GitHub runner. There was no qualifying development in the early Sunday check. There is no justification for waiting until Monday to investigate or test; no ChatGPT follow-up is enabled. The previously authorised hourly newsroom remains the site's automatic publication mechanism.
# Saturday launch edition (authorised 25 October)

The owner requested reconstruction from Saturday 24 October at 06:00 UK. A fixed-source launch publisher uses the real Gemini writer and separate statement reviewer, then the same evidence and risk gates. Only this Saturday window is accepted; exact source timestamps are required. The actual publication timestamp is retained. Launch reports are explicitly retrospective and never enter today's feed. The homepage links the launch edition separately through Monday; the archive remains permanent.

The local aggregate request ceiling is now 30 per Pacific quota day, including the two already-recorded diagnostic requests. Each run allows at most seven calls: one commissioning decision plus up to three writer/reviewer pairs. Existing counts are retained. It is our ceiling, not evidence of Google's actual project quota. No billing changes, paid-only models, paid grounding, automatic rewrites or model fallback are authorised. A launch attempt is journalled before the first model call and cannot repeat automatically after a hold or failure.


The initial launch attempt used one Gemini call and was blocked by literal numeric token comparison before review. Version 2 normalises equivalent currency spacing and million/billion notation while retaining value, scale, percentage and currency checks. It retains raw model responses for diagnosis. One versioned retry is permitted for this corrected parser; subsequent failures/holds do not repeat automatically.

Gemini commissioning is now part of the normal production path: all candidates undergo source/date preflight first, then Gemini chooses from the bounded verified pool. Decisions are schema-checked, source-bound and cached. No verified candidates means no selection request. Fewer than three remaining calls means no new selection/writer/reviewer sequence starts. Original discovery remains deterministic RSS/index retrieval and source tracing; Gemini is not using paid search grounding or unrestricted browsing.

### Gemini commissioning and bounded omission test

Run 40150652461 made a real Gemini selection, draft and separate review. Gemini selected the Treasury announcement but held one optional regional sentence (C17). No article was published. The retained draft is source-hash and draft-hash locked for recovery; the disputed sentence can be removed whole and the full remaining article must receive a fresh independent review. This uses one review request rather than another writer call.

The regular pipeline allows at most one such omission only when one flagged body sentence represents at most 20% of the report, contains no explicit limitation/qualification, leaves three non-empty sections and at least 120 words, and request budget remains for a complete new review. Headlines and standfirsts cannot be silently edited. Multiple flags, unresolved disputes or failed rechecks stay held. The seven-call run ceiling and thirty-call daily ceiling still apply.

### Actual Saturday publication verified — 25 October, 01:32 GMT

Run [40150946287](https://github.com/yogeshkaransharma-code/the-brief-financial-news/actions/runs/40150946287) completed maintenance, deployment, live HTTP verification, mobile/desktop reading checks and its actual-publication job successfully. The publication counter is **1**, today's genuine same-day count is **0**, and the permanent archive contains **11** full reports. This is an explicitly retrospective Saturday launch report; it is not a Sunday development.

The published report is [Chancellor unveils major funding package for UK artificial intelligence and security](https://yogeshkaransharma-code.github.io/the-brief-financial-news/story/ai-6d43cd604a058aa7b9da.html). Its original Treasury timestamp is 24 October 05:00:05 UTC / 06:00:05 BST. Actual publication is 25 October 01:31:29 GMT. It contains 240 body words in three sections. Gemini selected the story and wrote the original draft; one optional sentence flagged by its reviewer was removed whole. A fresh Gemini call reviewed all 16 remaining statements with no unresolved flags. Source and published-article hashes, exact supporting passages and the omission record are stored in its editorial audit. The final review used 4,929 input and 732 output tokens.

All 20 offline check groups passed in the real workflow. Actual Chromium checks passed at 390×844 and 1440×844: visible Saturday headline, no old article in today's feed, full article paragraphs, archive navigation, no horizontal overflow, no JavaScript errors, and original Treasury evidence HTTP 200 at both sizes. Independent browser inspection also opened the live homepage, followed its article link, read the full report with both dates, and opened the original Treasury document. Browser evidence artifact: 12583055040; newsroom evidence artifact: 12582595784. A replay smoke check confirmed an already-published launch exits before creating a budget meter or issuing a model request.

Aggregate request accounting is 27/30 for the Pacific quota day: 25 production calls including earlier attempts and two one-time diagnostic calls. The successful recovery used one new review request and reused the existing Gemini selection and draft. No billing changes were made. This is a local count; Google project billing state and authoritative quota remain uninspected.

Remaining acceptance limits: the normal hourly path has not yet produced a verified Sunday announcement; the real selection test contained one eligible, manually discovered Saturday source rather than a multi-source automatically discovered pool. Five to ten worthwhile daily reports has not been demonstrated. Four primary indexes still return HTTP 403 from the runner (UK Parliament, Allianz UK, ABI, Revolut UK), although all 25 RSS feeds worked in this run. Current eligibility is restricted to complete, dated, allowed primary documents and cautious risk lanes; adverse/legal reports and unsupported or complex documents remain held. Separate calls to the same Gemini model can share mistakes and do not constitute human certification. Legacy archive reports retain their explicit earlier-system verification notices. GitHub cron is best-effort, not an exact scheduling guarantee; monitoring exposes failures but does not provide a permanently available human editor or repair every external service fault. The project is not yet declared launch-ready.

## Follow-on source expansion — 25 October 2026, 02:42 UTC

After the earlier Work run, a follow-on ChatGPT session merged [PR #1](https://github.com/yogeshkaransharma-code/the-brief-financial-news/pull/1) as commit `49dd0275ecb2b7031dbbf9b63c75133d0a058938`. Source discovery now includes the official Hiscox Group release desk and Chubb UK newsroom, with a narrow, numeric-item-only Chubb article URL rule and tests rejecting lookalike hostnames and listing/search URLs. Existing UK original-source dates, autonomous editorial selection, separate Gemini writing/review and final approval gates remain unchanged.

The [live deployment and test run 40155384306](https://github.com/yogeshkaransharma-code/the-brief-financial-news/actions/runs/40155384306) passed all 20 offline test groups, Pages deployment, live full-article HTTP reading and actual Chromium checks at 390px and 1440px. The runner retrieved **25/25 RSS feeds**, and **17/21 primary indexes**; Hiscox returned one dated original lead, Chubb returned none in the admissible date window. The same four index hosts (UK Parliament, Allianz UK, ABI, Revolut UK) returned HTTP 403. They remain explicitly reported as discovery gaps, not ignored or bypassed.

**No qualifying UK-calendar-day announcement was discovered at 02:41 UTC on Sunday 25 October.** There were zero new Gemini requests, zero new Sunday articles and eleven persistent complete archive reports. The full maintenance job was successful but the overall workflow correctly marked itself DEGRADED via the explicit attention step. It would be false to claim end-to-end unattended Sunday publication or five articles/day from this run.

The next acceptance requirement is unchanged: observe and verify a genuinely new qualifying same-day primary announcement progressing automatically through actual Gemini commissioning, writing, independent review, immutable publication, live full-story loading and mobile/desktop browser checks. Source coverage also needs improvement without treating blocked or undated originals as verified.
