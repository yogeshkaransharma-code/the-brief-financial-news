# The Brief — Private readership analytics

## Purpose

Track real readership rather than confusing article counts or GitHub Actions runs with traffic. No public vanity counter, tracking cookies, chargeable service, or fabricated historical data.

The owner has created a free Cloudflare Web Analytics site for the hostname `yogeshkaransharma-code.github.io` and supplied its public beacon token. That 32-character site identifier has been connected to the **production GitHub Pages build** via `.github/workflows/ai-newsroom.yml`. It is an identifier embedded in public HTML, **not** a Cloudflare API key, account credential or secret.

## How to view readership

1. Open [Cloudflare Web Analytics](https://dash.cloudflare.com/) in the owner's account.
2. Select the site for `yogeshkaransharma-code.github.io`.
3. Review visits, page views, top pages, referrers and countries over the last 24 hours, 7 days or a longer period.
4. Test by opening [The Brief](https://yogeshkaransharma-code.github.io/the-brief-financial-news/) in a normal browser with no tracking blocker. Data may take a few minutes to appear.

No further GitHub variable or manual insertion is necessary for this connected site. The next successfully deployed public build contains one Cloudflare module beacon per HTML page, just before the closing `</body>` tag. New articles automatically inherit it.

**Important:** analytics only counts visits made *after* the production beacon is live. Earlier visits cannot be reconstructed. The dashboard initially showing zero or “not enough data” is expected before the site receives measured traffic.

### What the owner can monitor

- Visitors and page views, by day/week and top page.
- Referring websites and broad geographic distribution.
- Trends after sharing articles on LinkedIn or getting search traffic.
- Site performance and loading issues.

Be cautious interpreting the numbers. These are browser-measured estimates, not an audit of every human reader. Ad blockers, repeat browsing, bots and analytics sampling can affect the figures. **Readers ≠ article views ≠ GitHub Actions runs.**

### Costs and privacy

Cloudflare says Web Analytics is free, can be used without putting the site behind its network, and does not collect visitors' personal data. We have not installed GA4, advertising trackers, tracking cookies, external public counters or any billing-dependent products.

The published [Privacy page](https://yogeshkaransharma-code.github.io/the-brief-financial-news/privacy.html) explains the intended measurement. The operator should periodically check current UK privacy requirements and Cloudflare's terms, especially if the site's measurement methods change. No website owner or model should claim this constitutes legal compliance certification.

## Verification

The static build fails for malformed tokens and checks that every page has exactly one beacon when configured. The HTML output is rebuilt on each newsroom deployment, so every new article inherits measurement. This identifies the tracking code's installation, not confirmed visits or traffic totals.
