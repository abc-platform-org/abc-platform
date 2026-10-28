# Explicit governance separation instruction — 2026-10-29

**Status:** `USER_DIRECTIVE_ADOPTED_AS_PRODUCT_GOVERNANCE_POLICY`; **not** `G-00_PASS`.

## Decision trace

In this ABC project conversation the user directly approved separating **architecture and contract design decisions** from **product deployment approval**, with the same individual as accountable engineering/product owner, while preserving real execution tests, service-specific professional safety review, and privacy compliance as **mandatory before activation**.

This is direct user direction, not an AI-invented preference and not a retrospective approval of every file. There is no authenticated GitHub PR review attached to the user's chat utterance, so **formal version-specific GitHub attestations still have to be recorded**.

### Adopted immediately for project governance

1. Project owner makes all product and design coordination decisions.
2. G-00, G-01 and G-02 can refer to **DESIGN_ONLY** artifact readiness; such a Gate cannot be called operational release readiness.
3. G-03/G-04/G-05/G-06/G-07/G-08/G-09 real-world safety, data privacy/security, visual QA and production work are distinct **hard release gates**.
4. Any client, chemical service, live POS, inventory, marketing, or operational data action remains **DISABLED_UNTIL_ITS_SPECIFIC_GATE**. No tests or professional credentials are inferred.
5. Original source/ADR/contract signoff records must not be forged or silently amended as if already independently approved.

### Unresolved before exact SHA design freeze

- `SRC-EXC-001..003`: three bounded source exceptions awaiting itemized version-specific decision.
- `ADR-001..010`: ten draft technical decisions awaiting itemized review of content/blob SHA.
- `G-01`: 64 feature matrix, service staging and owner-reviewed exact contract SHA.
- `G-02`: now includes a hardened new head after contract-level defect remediation; owner must review that new SHA, not the superseded initial one.
- The nine `RELEASE_SAFETY_DEFERRALS.csv` entries define **hard release blockers**, but individual professional evidence and precise risk terms still need recorded owner/reviewer acceptance.

This file is only evidence that the owner adopted the **policy principle** in chat. It is intentionally not a declaration that the owner personally reviewed individual files or submitted a GitHub signature.
