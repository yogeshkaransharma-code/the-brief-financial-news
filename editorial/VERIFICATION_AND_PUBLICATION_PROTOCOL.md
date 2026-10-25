# The Brief — Verification and Publication Protocol

> Operational update, 25 October 2026: the owner has authorised unattended Gemini publication. Current executable policy and controls are documented in README.md and AUDIT.md. Any older requirement below for routine human sign-off or rolling freshness windows is superseded: original announcement and publication must share the UK calendar date, every generated heading and sentence must pass separate evidence challenge, and uncertain/high-risk material stays held. Machine review must never be described as human approval.
**Version:** 1.0 (23 October 2026)  
**Owner:** The Brief editorial desk  
**Default publication mode:** HUMAN APPROVAL ONLY. No AI-driven auto-approval.  
**Applies to:** All original reports, AI-assisted articles, article updates, excerpts used in the 60-second briefing and any consequential summaries.

Read alongside [Editorial Standards](EDITORIAL_STANDARDS.md). A passing Python test is not a professional fact-checking certificate.

## 0. Decision policy

**Publish** only after every *material* factual claim is supported by usable, accessible evidence; numerical and regulatory checks pass; the exact article version is approved by an accountable person; and corrections/contact readiness is in place.

**Hold** for source gaps, ambiguous documents, potentially mistaken interpretation, unresolved conflicting accounts, uncertain calculations, missing context, incomplete rights clearance or missing review.

**Reject** fabricated or materially contradicted claims, impossible dates, incorrectly described legal force, altered quotations, unsupportable allegations, plagiarism, unauthorised reproduction, missing approval and attempts to circumvent validation.

A machine's confidence score **cannot** transform a 'hold' into a 'publish'. Failing safely is expected.

## 1. Intake record — before any drafting

Capture and retain:

| Field | Definition |
|---|---|
| Story ID | Stable ID derived from original source URL; also match duplicate reporting of the *same development* |
| Originator | Regulator, issuer, court, reporter, employee or account holder |
| Source title / URL | Exact primary-source title and HTTPS URL |
| Source type | Official record, company statement, authenticated social post, licensed media, commentary |
| Publication and update times | As displayed by issuer, including timezone where available |
| Retrieval time and snapshot hash | UTC timestamp and SHA-256 of the extracted source text/document |
| Document version / pages / sections | Consultation number, policy statement, PDF page, dataset sheet/row or paragraph |
| Source rights/access | Licence/terms status; whether full text is accessible and permitted to process |
| Evidence limits | Missing pages, truncated HTML, PDFs not parsed, secondary attribution, disputed details |
| Relationship | Whether multiple outlets derive from the same release; related and contradictory sources |
| Desk decision | Cover, monitor, hold or reject, with brief reason |

**Never infer a source's date from feed-refresh time.** For LinkedIn, validate account identity, representation and context; no automated scraping outside permitted platform access. A quote or screenshot without a stable original may be insufficient for a material claim.

## 2. Source retrieval quality gate

1. Use the highest-quality relevant primary source. For rule changes, prioritise operative final rules and commencement provisions over a headline/press notice. For financial results, review the accompanying accounts/notes and data definitions, not only the issuer's summary.
2. Confirm the **whole relevant document** was actually retrieved. If a linked PDF, appendix, table or consultation response is needed but our parser cannot read it, mark the relevant claims **HOLD**, not 'assumed correct'. A 19,000-character HTML cut-off is not comprehensive retrieval.
3. Preserve the source's meaningful context, exceptions, negative findings and qualifications.
4. Verify linked URLs are safe and genuine; do not equate an official hostname with correct interpretation.
5. Record the source snapshot hash and retrieval date. Note when sources change after drafting.

## 3. The evidence register — one row for every material claim

The reviewer breaks the **headline, standfirst, each body section and 60-second summary** into checkable assertions. For each, record the following (a local CSV or spreadsheet is suitable during human review):

| Field | Example |
|---|---|
| Claim ID | C-014 |
| Exact article text | 'The regulator has proposed lowering the threshold' |
| Location | Headline / standfirst / paragraph 3 / briefing |
| Classification | Fact, quote, number, comparison, regulatory status, scope, causal inference, analysis |
| Risk | Normal / High / Critical |
| Source URL + version | Exact document link, publication date and version |
| Locator | PDF page, paragraph, consultation question, dataset cell or website section |
| Specific evidence | Short attributed extract or exact source data |
| Independent calculation | Formula and inputs for rates, deltas and relative movement |
| Evidence outcome | SUPPORTED / CONTRADICTED / INSUFFICIENT / ANALYSIS |
| Reviewer notes | Qualifications, conflicting evidence and follow-up required |
| Reviewer + timestamp | Named accountable reviewer and UTC approval time |

**SUPPORTED** means the passage *actually entails the claim*, including scope and qualifications—not merely shares keywords. **ANALYSIS** must be visibly labelled and its factual premises checked. **INSUFFICIENT** or **CONTRADICTED** for a material claim blocks publication. A broad supporting quote reused across unrelated claims is not adequate.

Source excerpts generated by Gemini form **leads for human checking**, not completed evidence-register entries. AI cannot reliably attest to having identified every material claim; the reviewer must check claim coverage manually.

## 4. Dedicated verification passes

### 4.1 Mathematics and accounts

Verify each currency, sign, decimal, unit, percentage and reporting period with the primary dataset/table. Retain exact numerator/denominator and label whether an increase is a **percentage** or **percentage points**. Do not recalculate approximate values as more precise figures or omit conditions. Redress total is not necessarily redress **per complaint**. A complaints *volume* ranking is not a *rate* ranking. Claims about economic impact need distinct evidence.

### 4.2 Regulatory status and scope

Write a status sheet: regulator, jurisdiction, instrument/document number, **proposed vs decided vs currently binding**, consultation closing date, response publication, commencement date, transitional provisions, affected firm types and exclusions. An FCA speech is not an FCA rule; a PRA consultation is not automatically a rule for all regulated firms. Explain what workers may actually need to do, if supported, and whether dates are uncertain.

### 4.3 LinkedIn and company announcements

Confirm identity and authenticity of poster, exact words/time, whether it's a personal view or employer statement, any corrections and independent corroboration for consequential facts. A company claiming a product is 'first' or 'largest' needs clear evidence or precise attribution. A social-media post alone does not establish that a merger closed or that a regulator approved anything.

### 4.4 Legal, reputational and personal claims

Any allegation of misconduct, suspected fraud, blame, layoffs, insolvency, litigation or identifiable individual's conduct must go to a qualified human reviewer; check primary proceedings and opportunity to respond as appropriate. Do not quote speculation as fact. Escalate where personal data, defamation, copyright or market-abuse concerns arise.

### 4.5 Headline, summary and omissions

Re-check the headline and the **60-second brief separately** against the evidence. Inspect what's missing: eligibility, exclusions, comparison bases, proposed status, disputed information, source limitations. A perfectly sourced body cannot rescue a misleading headline.

## 5. Writer pass

A separate editorial pass checks clear British English, direct intro, readable figures, relevant context, non-repetitive paragraphs, appropriately defined jargon, careful causal language and precise dates. Avoid generic claims about all 'professionals', empty filler, publicity language and unsupported takeaways. A reader should leave knowing *what happened, what's confirmed, who is actually affected and what next*.

Article length should match complexity. Any AI model's stylistic self-rating is advisory only. Sample the final copy against real specialist source material.

## 6. Machine gates, explicitly limited

Current or proposed deterministic checks can reliably reject *some* faults:

- Missing source URL, invalid input schema, wrong category, article too short to be complete
- Duplicate story IDs/URLs and repeated evidence snippets
- Consultation/speech URLs mislabelled as final regulatory decisions (conservative signal)
- Amounts/dates in the draft absent from captured source text (necessary but not sufficient)
- Source snapshot mismatch, unsupported article version, missing reviewer sign-off
- No public AI publication unless an editor explicitly approves the selected draft
- Publisher workflow not allowed to use unreviewed/corrupt artifacts

**Important:** Matching a number in a 19,000-character source extract does not prove the claim around it. Passage matching, lexical topic ranking, simple document-path rules and source hostname checks are automated *screening*, not independent verification. Detecting omissions, incorrect causal chains and a claim taken out of context requires human assessment.

Do **not** say 'verified', 'fact checked' or 'Reuters-grade' based solely on a passing automated score.

## 7. Article state machine and approval

`DISCOVERED → RETRIEVED → DRAFT → AUTO-SCREENED → REVIEW_REQUIRED → APPROVED → PUBLISHED`

At any point: `HOLD` (remediable evidence gap) or `REJECTED` (unacceptable fact/rights/credibility).

- **DRAFT**: machine generated, unpublished; includes underlying source, snapshot hash, candidate claim extracts and warnings.
- **AUTO-SCREENED**: passed limited deterministic checks; **does not** mean facts are verified.
- **REVIEW_REQUIRED**: an accountable human must review material claims and check source evidence.
- **APPROVED**: exact content fingerprint recorded; editor confirms all material claims, numbers, statuses, implications and originality checked, records notes/identity/time.
- **PUBLISHED**: only the *approved fingerprint/version* is published. Publishing a changed draft requires re-review. Store approval metadata and the source provenance alongside the published version.
- **CORRECTED/WITHDRAWN**: visible reader notice and retained internal history.

Current workflow still requires a manually triggered GitHub Action; it must **never** infer human approval from workflow success. The typed approval phrase is a sign-off ceremony, not proof of the underlying checks. The desk remains accountable.

## 8. Public displays and edition selection

- Publish complete original explanatory articles *on site* only after approval.
- Keep RSS summaries clearly labelled **SOURCE UPDATE**, not 'The Brief reporting'.
- Feed **only the verified/approved article's text** into the priority '60-second briefing' where possible, with caveats intact. If there aren't three approved fresh stories, show fewer rather than inventing completeness; non-original updates must be explicitly labelled.
- Show source, issue date, proposal/final status and corrections clearly on the article.
- Never change original publication date to make an old story look fresh.

## 9. Corrections and record retention

An identified mistake creates a correction ticket: article ID, URL, report time, reporter, alleged error, source check, severity, decision and resolution. For a serious unverified claim, add a prominent warning or withdraw the article until fixed. Amend the copy and add a visible **Correction / Updated** note with date, what was inaccurate and what changed. Keep prior published version, correction trail, reviewer, source hash and approval record in controlled storage. Do not silently edit a material falsehood. Establish a working contact address/form before broad public promotion.

Follow source changes as new developments: don't automatically rewrite reviewed copy and pretend the original sign-off still covers it.

## 10. Benchmark, monitoring and release criteria

Maintain labelled *adversarial fixtures*: wrong amount, wrong denominator, percentage vs pp, wrong date, consultation labelled final, speech called binding, missing exemptions, misleading headline, duplicate evidence, bad domain, absent approval, source mismatch, invented scope, unsafe copyright reuse. Tests must deliberately mutate an otherwise valid record.

Record for each fixture: `fixture_id, severity, expected_hold, actual_result, error_message`. Review **false negatives** (unsafe article passed) first; a single high-severity miss blocks any expansion of auto-approval. Track false positives (valid drafts held) too and improve rules without weakening scrutiny. All new regressions run in CI on code changes; retain the results and documented known limitations.

**Milestones before considering even narrowly scoped auto-publication:** a sufficiently sized, independently reviewed sample representing real story types; no known severe missed errors in benchmark; tracked real-world error/hold rates; stable source-retrieval coverage, correction process and accountable owner; security/usage limits for AI. This protocol intentionally sets **no numeric accuracy promise** that current tests cannot justify.

## 11. Review worksheet — mandatory before sign-off

For each article answer **YES / NO / NOT APPLICABLE, with evidence**:

- Have I read the complete relevant primary documents, including linked tables/PDF sections where needed?
- Does each material headline, summary, body and 60-second claim have specific evidence?
- Are quotations, attribution and independent-source claims exact and fair?
- Are all amounts, denominators, dates, periods, definitions and calculations checked?
- Are regulatory force, affected firms and exceptions described correctly?
- Have I separated facts, attributed claims, interpretation and opinion?
- Is the article written originally, with source rights respected?
- Would a working reader understand the development without being misled?
- Are material objections/contradictions resolved and recorded?
- Have I reviewed the **exact version** being published, and can I explain later why I approved it?

If any material answer is **NO** or unsupported **N/A**, do not approve.

## References

- Reuters standards: https://reutersagency.com/about/standards-values/
- IPSO Editors' Code: https://www.ipso.co.uk/editors-code-of-practice/
- IPSO and AI editorial accountability: https://www.ipso.co.uk/news-analysis/does-ai-generated-content-change-editorial-standards/

This is The Brief's own internal policy, **not a certification of compliance with external press codes**. Formal policy cannot guarantee reliable journalism without effective people, evidence and accountability.

