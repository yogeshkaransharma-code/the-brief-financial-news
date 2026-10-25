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

The local aggregate request ceiling is now 24 per Pacific quota day, including the two already-recorded diagnostic requests. This allows one production writer/reviewer pair after the 22 recorded calls. It is our ceiling, not evidence of Google's actual project quota. No billing changes, paid-only models, paid grounding, automatic rewrites or model fallback are authorised. A launch attempt is journalled before the first model call and cannot repeat automatically after a hold or failure.

