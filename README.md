# The Brief — UK financial services news

A free, mobile-friendly financial news hub covering insurance, banking, technology and regulation.

**Live website:** https://yogeshkaransharma-code.github.io/the-brief-financial-news/

## Current status

- The GitHub Pages website is deployed.
- The RSS feed is collected and redeployed hourly, subject to GitHub scheduling delays.
- The source-first AI writer, independent sentence checker, revision cycle and autonomous GitHub publisher are installed and running daily.
- Gemini has **actually generated and automatically published** an original Lloyds Banking Group article (GitHub Actions run 39887707343). The public article feed includes the AI-generated piece and its source-review audit.
- The unattended publication lane permits narrow, first-party **banking and insurance announcements from Lloyds Banking Group and Aviva**, alongside defined FCA statistics. It rejects unsupported interpretations, allegations and more complex regulatory coverage; no human approval is falsely claimed.

The site is hosted free in a public GitHub repository. Scheduled GitHub Actions checks available RSS feeds hourly, keeps a deduplicated archive, and redeploys the static website. GitHub schedules are best-effort, not exactly timed.

## Activate the AI newsroom

1. Go to https://aistudio.google.com/api-keys and create a **free-tier** Gemini API key. Select a project that has not enabled paid billing. Verify your model limits in Google AI Studio; free quotas can change.
2. Visit [Actions secrets](https://github.com/yogeshkaransharma-code/the-brief-financial-news/settings/secrets/actions), select **New repository secret**, and set the name to `GEMINI_API_KEY`. Paste the key as its **secret value**, not into source code, public issues, or chat.
3. Visit [AI newsroom workflow](https://github.com/yogeshkaransharma-code/the-brief-financial-news/actions/workflows/ai-newsroom.yml) and select **Run workflow**, branch `main`.
4. Open the completed run. Its `the-brief-ai-drafts` artifact contains up to two full article drafts and an audit report. If the source material is insufficient or the evidence checks fail, the article is held back.

The V2 pilot checks selected official FCA and Bank of England web pages. It first retrieves bounded original HTML and, where confidently identified, a central selectable-text PDF; nothing is silently truncated. Gemini writes a natural original article **without** being forced to invent supporting quotations. A **separate AI request** challenges each headline, summary and article sentence against the captured source, and a deterministic gate checks citation presence, figures, dates, document fingerprints and review coverage. **Those checks are not a substitute for editorial fact-checking.** Drafts are not displayed on the public site. The scheduled pilot runs once a day; the original hourly RSS feed continues independently.

The site loads full original articles from `data/articles.json`. Every item must have a version-locked audit record identifying whether its approval was accountable-human or explicitly autonomous with no human review.

**Free-tier note:** Gemini free-tier inputs and outputs may be used by Google to improve its products. This pipeline should receive only public material, not confidential client information. No billing is enabled by our GitHub code, but verify your Google project's billing settings independently.

## Autonomous AI publishing (active; source-limited)

The daily **Autonomous financial news desk** GitHub Action discovers first-party insurer/bank announcements as well as official regulatory material and runs without a person approving each article:

1. Retrieves bounded original official HTML and PDFs where confidently identified.
2. Gemini writes a complete original, readable British-English article; a separate AI call challenges each article sentence.
3. When specific objections arise, the AI can rewrite and re-verify the article, with at most **two revision rounds**. Failed versions are retained privately for later diagnosis.
4. Deterministic checks reject absent or altered source quotations, unsupported figures, false regulatory-force claims, denominator errors, misleading rounded percentage-point comparisons, changed drafts and incomplete reviews.
5. Only named official regulator statistics and first-party bank/insurer press announcements from the approved **FCA, Lloyds Banking Group and Aviva** paths can publish automatically. Explicit domain/path checks, complete captured HTML, source-date limits, no retrieval warnings, full sentence challenge and zero unresolved errors are required. **Maximum two articles per run.** Consultations, regulatory speeches, allegations, third-party media articles and material needing complex legal interpretation remain unpublished.
6. The automatic publication leaves a machine-specific audit under `data/editorial-audits/`, is deduplicated and visibly labelled **AI-assisted, machine-screened, not human-reviewed** on the website. Any other story stays in the unpublished review artifact.

**Verified production example:** [Lloyds launches Investing in Britain Hub](https://yogeshkaransharma-code.github.io/the-brief-financial-news/#story/ai-041c314db98959584c1a) was written, screened, committed and deployed by the scheduled newsroom itself, not added manually. The originating company press release is identified on the article page.\n\n**Residual risk:** Even after a clean AI-versus-AI check, a source may have ambiguity or the model may misunderstand it. Machine screening is not professional human verification; never claim zero-error publication. This pilot is intentionally very narrow, can publish no articles on a given day and must not silently widen itself. A documented correction/withdrawal process and later human oversight are still needed for a responsible public newsroom.

To pause automatic publication without stopping source discovery, change `AUTO_PUBLICATION_ENABLED` to `0` in `.github/workflows/ai-newsroom.yml` (the publish script otherwise performs a dry run). To expand eligible topics, make a separate researched editorial-policy change and add adversarial tests before editing the allowlist.

## Editorial review and article publication

Outside the narrowly defined FCA factual-statistics pilot above, the automated newsroom is **draft-only**. Its second AI pass is not an independent human fact-check; it flags potential errors. Weak, incomplete or disputed sources and unsupported sentences are held, not approved.

1. Open [Draft plain-English financial news](https://github.com/yogeshkaransharma-code/the-brief-financial-news/actions/workflows/ai-newsroom.yml). A scheduled run takes place each morning, or select **Run workflow** for a manual test.
2. Open a completed run and download its **the-brief-ai-drafts** artifact.
3. Unzip it and open **EDITORIAL-REVIEW.html** in your browser. It contains both *screened* and *held* candidate articles, their complete captured text where available, original document links, sentence-level issues and the sources refused before writing.
4. Compare **every factual claim, deadline, number, regulatory status and suggested implication** with the original source. Do not approve material that is unsupported, inaccurate, misleading or too jargon-heavy. AI and keyword tests cannot replace this judgement.
5. To publish an article you have genuinely reviewed, open [Publish a reviewed article](https://github.com/yogeshkaransharma-code/the-brief-financial-news/actions/workflows/publish-reviewed.yml), choose **Run workflow**, and enter:
   - `draft_run_id`: the numerical run ID from the drafting run page
   - `article_id`: its exact `ai-...` ID as shown in the review packet
   - `approval_phrase`: `APPROVE_AFTER_SOURCE_REVIEW`
   - Three mandatory **YES** confirmations that all material claims, financial/regulatory implications, originality, fairness and wording have been checked
   - `review_notes`: at least 35 characters specifying what you checked. **These notes are retained in the public repository — do not include personal, confidential or secret information.**
6. The workflow checks the exact reviewed draft fingerprint, rejects repeat sources and missing approval evidence, records the GitHub approver and source/article fingerprints in `data/editorial-audits/`, commits the approved article and deploys GitHub Pages. The site promotes recent approved full articles into the lead story and 60-second briefing.

The review packet is stored as a GitHub Actions artifact, not as public website content. Publication is deliberately disabled by default, and the manual workflow publishes **only the selected article**. If the review finds an error, reject that draft and regenerate or revise it; approval must never be used merely because a workflow passed.

Editorial limits: the pilot covers selected FCA and Bank of England documents. The underlying HTML-text reader does not yet process all PDF consultations, nor does it provide unrestricted LinkedIn discovery. Source excerpt matching and numeric checks are imperfect; a human is still responsible for approved accuracy. Expansion to other primary sources and narrowly scoped automatic publication requires additional real-world testing.

## Editorial governance: binding standards and benchmarking

- **[Editorial Standards](editorial/EDITORIAL_STANDARDS.md)**: mission, style, original reporting, source hierarchy, figures, regulatory terminology, attribution, independence and corrections.
- **[Verification and Publication Protocol](editorial/VERIFICATION_AND_PUBLICATION_PROTOCOL.md)**: claim-by-claim evidence register, numerical/regulatory review, source identity and completeness, review state machine, approval record and correction procedure.
- **[Claim Register Template](editorial/CLAIM_REGISTER_TEMPLATE.csv)**: per-claim evidence worksheet for accountable human review; not automatically filled or certified by AI.
- `scripts/test_editorial_benchmark.py`: 22 labelled adversarial cases in CI — invalid sources, false final rules, unsupported amounts, duplicate evidence, modified content and missing metadata must be rejected. Passing only means **those screenable faults were blocked**.
- `scripts/verify_approved_articles.py`: every on-site AI article must match a persistent editorial review record and exact content fingerprint. Unapproved and changed versions block publication.

**Scope limitation:** The new version-locked approval gate covers AI articles entering `data/articles.json`. The six earlier hand-curated articles embedded in `index.html` predate this standard and must be reviewed separately; their presence is not evidence of completed fact-checking under this protocol.

**Do not confuse this with independent factual verification.** A code rule cannot tell whether a plausible paragraph omits a crucial exception or misinterprets a source. Material headlines, claims, numbers, affected populations and implied next steps still require a responsible human to read the actual source. Any high-severity missed error in future benchmark testing blocks expansion of automated publishing.

## Reading experience

- Complete, original articles from selected official sources, readable on our website
- A 60-second catch-up, a combined feed, search, filters and saved stories
- Publicly attributed source-feed updates, clearly labelled as such
- Plain-English background explanations

**Important:** Source-feed updates are not complete republished news articles. Full third-party articles require permissions or original reporting. The automatic feed does not use paid AI services.

## Files

- `index.html`: self-contained premium homepage and reading interface
- `scripts/update_feeds.py`: RSS collector
- `data/live.json`: automatically updated source headlines and short descriptions
- `data/articles.json`: full, approved original articles loaded on-site (currently empty)
- `scripts/ai_newsroom.py`: legacy helpers for Gemini calls, source discovery and historical validation tests
- `scripts/source_retrieval.py`: bounded HTML / selectable-text PDF capture with official-domain restrictions
- `scripts/newsroom_v2.py`: independent writer-and-sentence-review draft-only newsroom
- `.github/workflows/ai-newsroom.yml`: daily draft workflow and action artifacts
- `.github/workflows/hourly-news.yml`: news collection and GitHub Pages deployment

## Editorial limits

Check publisher reuse conditions before expanding feeds. New feed headlines and short snippets are attributed to their sources, but have not been independently verified as original reporting. Review curated articles, the correction procedure and source permissions before promoting the site widely.
