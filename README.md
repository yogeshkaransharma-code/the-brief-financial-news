# The Brief — UK financial services news

A free, mobile-friendly financial news hub covering insurance, banking, technology and regulation.

**Live website (once GitHub Pages is enabled):** https://yogeshkaransharma-code.github.io/the-brief-financial-news/

## Publish it (one-time setup)

1. Open **Settings → Pages** in this repository.
2. Under **Build and deployment → Source**, choose **GitHub Actions**.
3. Open **Actions → Collect and publish financial news → Run workflow** and select the main branch.
4. Once the workflow completes, open the GitHub Pages address above.

The site is hosted free in a public GitHub repository. Scheduled GitHub Actions checks available RSS feeds hourly, keeps a deduplicated archive, and redeploys the static website. GitHub schedules are best-effort, not exactly timed.

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
- `.github/workflows/hourly-news.yml`: news collection and GitHub Pages deployment

## Editorial limits

Check publisher reuse conditions before expanding feeds. New feed headlines and short snippets are attributed to their sources, but have not been independently verified as original reporting. Review curated articles, the correction procedure and source permissions before promoting the site widely.
