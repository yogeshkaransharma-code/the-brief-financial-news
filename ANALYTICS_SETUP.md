# The Brief — Private readership analytics

## Purpose

Track real readership rather than confusing article counts or GitHub Actions runs with traffic. No public vanity counter, tracking cookies, chargeable service, or fabricated historical data.

The website has **optional Cloudflare Web Analytics support**. The deployment injects Cloudflare's official beacon into every real HTML page only when the site owner supplies a token. A blank token means tracking is **OFF** and no figures will appear.

## Connect it (owner's free Cloudflare account)

1. Sign in to [Cloudflare](https://dash.cloudflare.com/) and open **Web Analytics**.
2. Choose **Add a site**. For this GitHub Pages publication, the hostname is `yogeshkaransharma-code.github.io`. You do **not** need to move DNS or migrate hosting.
3. In **Manage site**, copy the `data-cf-beacon` **token** from Cloudflare's JavaScript snippet. It is a public 32-character hexadecimal site identifier, *not* your Cloudflare API key.
4. In the GitHub repository, open **Settings → Secrets and variables → Actions → Variables**. Add a repository variable named `BRIEF_CF_ANALYTICS_TOKEN` with just the token.
5. Run **The Brief — hourly newsroom and site maintenance** once (or use the next normal deployment). The build inserts the Cloudflare beacon into the homepage, article pages, About, archive and section pages.
6. Check the public page source for `static.cloudflareinsights.com/beacon.min.js`, then open Cloudflare **Web Analytics** for the visitor dashboard. Data begins after the tracking beacon is live; earlier traffic cannot be reconstructed.

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

The static build fails for malformed tokens and checks that every page has exactly one beacon when configured. When unconfigured, tests assert no beacon appears anywhere. The HTML output is rebuilt on each newsroom deployment, so new articles automatically inherit measurement after connection.

No Cloudflare token has been added by ChatGPT and no traffic has been measured by this change alone.
