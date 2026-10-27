# The Brief — Editorial Standards

**Current working standards · 27 October 2026**

These standards describe what The Brief aims to publish and what its live automated workflow actually checks. They are not a certification of every published sentence. The current production route is a single source-based Gemini writing pass with deterministic source, UK-date, identity and duplicate controls. There is no separate AI claim-review pass or routine human editorial approval. Never describe these checks as independent fact-checking.

## 1. Our promise

**Tell people what happened. Help them understand why it matters. Do not pretend to know more than the evidence tells us.**

The Brief is a specialist UK insurance and banking publication. It should be useful to underwriters, brokers, intermediaries, claims teams, bankers, relationship managers and interested members of the public. Industry knowledge is an advantage, not an excuse for jargon. Clarity and accuracy matter more than speed, volume or a dramatic headline.

## 2. A grounded, human British voice

- Write the way a capable, thoughtful person would explain the story to another person: direct, calm, warm, confident and natural. British spelling, ordinary words and sensible sentence lengths.
- Lead with the development. No vague scene-setting, exaggerated hooks, self-conscious wit, forced excitement or generic conclusions.
- Never sound like a press release. Avoid empty phrases such as “significant milestone”, “dynamic landscape”, “game-changing”, “transformative” and “stakeholders” where a clear, specific description would work.
- Understand commercial realities. Where supported, explain who must make a decision, which firms or customers are affected, what has changed and what follows.
- Do not assume that every acquisition, partnership, personnel change or product launch transforms an industry. A routine appointment can be a brief item without a grand conclusion.
- Explain necessary jargon in context, without talking down to experts or newcomers.
- Do not invent anecdotes, interviews, first-hand experience, quotes, independent opinions, expert reactions or market impact to make prose seem more human.

These requirements are included in the live `scripts/single_pass.py` writing prompt and protected against accidental prompt removal by `scripts/test_single_pass.py`. This is prompt enforcement, **not** a demonstrated factual-accuracy guarantee.

## 3. Clear news hierarchy

The newsroom should ultimately distinguish:

- **Major story:** a genuinely consequential development, with space for context supported by the evidence.
- **Straight news report:** what happened, who is affected and necessary qualifications.
- **Short news brief:** a routine appointment, launch or limited announcement, reported cleanly and proportionately.
- **Explainer:** background material that is clearly dated and does not masquerade as new reporting.
- **Analysis or comment:** visibly identified interpretation, never passed off as established fact.

The current source-selection route is deterministic rather than a full editor's significance assessment. Visual ranking and stronger article-type separation are desired improvements, not capabilities already guaranteed in production.

## 4. Sources and attribution

- Follow reputable original material, including official regulator publications, filings, company statements and credible original journalism. A newsroom page, RSS listing or syndication item is a lead, not automatically corroboration.
- Link the underlying source and preserve publisher, original source date and publication date.
- Attribute a company's figures, forecasts and claims to that company. Do not silently elevate an attributed assertion into independently confirmed fact.
- A single publisher, however reputable, is still one source. Two outlets repeating the same announcement are not independent confirmation.
- Never claim that The Brief interviewed anyone, attended an event, saw private records or independently verified information when it did not.
- Do not copy substantial protected text from other publishers. Write original explanations and respect rights, paywalls and access controls.

## 5. Accuracy requirements for every article

- Distinguish consultations, proposals, announcements, guidance, final decisions and rules already in force. Do not turn a proposal into a legal obligation.
- Distinguish a signed acquisition agreement from a completed transaction; forecasts from actual results; management claims from external evidence.
- Preserve financial units, currency, periods, denominators and caveats. A percentage-point increase is not the same as a percentage increase.
- State a concrete consequence for a broker, insurer, bank, employer or customer only when the retrieved source supports it. Otherwise omit “why it matters”.
- Use the exact relevant date rather than manufacturing freshness. Today's edition requires the original source date to match the UK publication date.
- Do not invent what a company “will” do, or what regulators or competitors “are likely” to do, unless that statement is grounded and attributed.
- Avoid reporting unsupported serious allegations, sensitive personal information or unverified accusations. Those require qualified human judgement before consequential publication.

The live automated route uses source retrieval and deterministic publication eligibility checks. It **does not** confirm every figure or proposition in an article against an independent claim register. Human auditing or a separate robust review process would be necessary to claim that standard.

## 6. Reader experience

Write as much as the source justifies and no more. Small stories should be short. Complex regulatory changes may require greater depth and, if there is not enough reliable source material, restraint rather than filler.

A good headline states the development accurately. A standfirst adds a meaningful fact or qualification rather than merely repeating the headline. Sections should help orientation, not follow an artificial template.

The 60-second briefing should summarise published pieces faithfully. It must never introduce new claims, turn a proposal into a decision or present an earlier announcement as a fresh event.

## 7. Accountability and corrections

We aim to correct material errors visibly, explain what changed and retain relevant source and publication history. Readers can submit a correction request through the public GitHub issue tracker linked on the About page, although that is not yet an ideal reader-facing contact channel.

The Brief must not imply routine human approval, certification, independent verification or an accreditation it does not have. AI-assisted production is disclosed accurately in our methods information without making software the centre of the publication's identity. Avoid invented human bylines.

A successful workflow and a functioning webpage establish that publishing worked technically. They do **not** establish that every article is accurate, newsworthy or well written. Periodic human audits, a more accessible corrections channel, better ranking of news importance and stronger independent verification remain necessary improvements.

## 8. Publishing and costs

Retain the existing hourly discovery and publication schedule, existing Gemini provider and existing no-billing policy unless the owner explicitly changes them. Do not add a separate model call merely for stylistic polishing. The current process batches up to three source-based stories into a single writing request and checks the resulting articles for technical/source-date eligibility.

For the real workflow and its limitations, see [README](../README.md), [single-pass writer](../scripts/single_pass.py) and the [historical proposed human-review protocol](VERIFICATION_AND_PUBLICATION_PROTOCOL.md).
