# The Brief — UK financial services news

A free, mobile-friendly financial news hub covering insurance, banking, technology and regulation.

**Live website:** https://yogeshkaransharma-code.github.io/the-brief-financial-news/

## Current status

- The GitHub Pages website is deployed.
- The RSS feed is collected and redeployed hourly, subject to GitHub scheduling delays.
- The first AI newsroom pilot is installed and its offline validation tests have passed.
- The AI newsroom is **not generating drafts until a Gemini API key is added**. It does not automatically publish unreviewed articles.

The site is hosted free in a public GitHub repository. Scheduled GitHub Actions checks available RSS feeds hourly, keeps a deduplicated archive, and redeploys the static website. GitHub schedules are best-effort, not exactly timed.

## Activate the AI newsroom

1. Go to https://aistudio.google.com/api-keys and create a **free-tier** Gemini API key. Select a project that has not enabled paid billing. Verify your model limits in Google AI Studio; free quotas can change.
2. Visit [Actions secrets](https://github.com/yogeshkaransharma-code/the-brief-financial-news/settings/secrets/actions), select **New repository secret**, and set the name to `GEMINI_API_KEY`. Paste the key as its **secret value**, not into source code, public issues, or chat.
3. Visit [AI newsroom workflow](https://github.com/yogeshkaransharma-code/the-brief-financial-news/actions/workflows/ai-newsroom.yml) and select **Run workflow**, branch `main`.
4. Open the completed run. Its `the-brief-ai-drafts` artifact contains up to two full article drafts and an audit report. If the source material is insufficient or the evidence checks fail, the article is held back.

The pilot checks official FCA and Bank of England web pages. It generates original plain-English reporting in British English from primary-source material and checks several verbatim evidence excerpts. **Those checks are not a substitute for editorial fact-checking.** Drafts are not displayed on the public site. The scheduled pilot runs once a day; the original hourly RSS feed continues independently.

The site is already wired to load fully written, approved articles from `data/articles.json`. After real draft quality has been tested, controlled publication can be enabled without changing the page layout. That second release should include a human-reviewed pilot, stronger independent source checks and a correction process.

**Free-tier note:** Gemini free-tier inputs and outputs may be used by Google to improve its products. This pipeline should receive only public material, not confidential client information. No billing is enabled by our GitHub code, but verify your Google project's billing settings independently.

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
- `scripts/ai_newsroom.py`: official-page reader, AI drafting and evidence checks
- `.github/workflows/ai-newsroom.yml`: daily draft workflow and action artifacts
- `.github/workflows/hourly-news.yml`: news collection and GitHub Pages deployment

## Editorial limits

Check publisher reuse conditions before expanding feeds. New feed headlines and short snippets are attributed to their sources, but have not been independently verified as original reporting. Review curated articles, the correction procedure and source permissions before promoting the site widely.
