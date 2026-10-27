# LinkedIn integration: access blocked, not production coverage

Observed on 27 October 2026 UTC. No LinkedIn-origin articles were published.

A prepared integration on `repair/linkedin-public-discovery` resolves indexed public LinkedIn leads to registered accessible sources, preserves discovery provenance, reads each complete source once and sends it through the existing single-pass writer. Indexed snippets/dates never become article evidence. Source failures and discovery outages do not halt unrelated publishing. The registry contains six editable Insurance/Banking search definitions, disabled pending usable access.

Validation: [32 offline checks, public build and live probe](https://github.com/yogeshkaransharma-code/the-brief-financial-news/actions/runs/40423842133) passed mechanically. Fixture tests cover durable cooldown, old-source dates, one source read/one writing request, real publisher output in a temporary directory and outage isolation. These fixtures are not live news.

The actual initial live probe made four public Bing RSS queries, received 40 rows, found zero LinkedIn post URLs and resolved zero source candidates. Three simpler diagnostic queries also returned unrelated results. DuckDuckGo returned HTTP 202 with no result links (challenge response). No challenge bypass was attempted. No Gemini calls, API subscriptions or billing changes were used for these probes.

The currently connected LinkedIn tool supports people search only, not post/feed reading. LinkedIn's [Posts API permissions](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api?view=li-lms-2026-06) restrict organization-post access to authorized organization roles; member-post access is restricted. It is not a general feed of all insurers and banks.

Scheduled LinkedIn polling remains disabled to avoid repeated unproductive requests. No direct LinkedIn HTTP scraping, login, private feed access, mirror or cache is implemented. An authorized, usable post-discovery API/feed is the remaining external dependency. Do not enable this integration or claim LinkedIn coverage solely because its tests pass. Revalidate live retrieval, freshness and downstream publication after providing access.

The ordinary RSS/newsroom production workflow is separate. A quota regression fixture discovered during this work mixed simulated noon with the real Pacific quota clock after UTC midnight; its clock injection is corrected independently.
