# WP-000-02 — Evidence-led Source Recovery Log

**Review date:** 2026-10-29. **Evidence scope:** Notion search/fetch, Library content search, existing GitHub PR #1 and its Phase-00 source inventory. The Notion fetch responses surface historical August 2026 snapshots; a search miss is not proof that a document never existed or cannot exist elsewhere.

## Exact upstream documents required by later productization artifacts

| Missing ID/version | Downstream cited source | Observed independently retrievable baseline | Recovery disposition |
|---|---|---|---|
| `ABC-DOC-001 v1.2.0` | Library `ABC_DOC_007...v1.1.0_PRODUCTIZATION.md` parent metadata | [DOC-001 v1.1.0](https://app.notion.com/p/3b76f520f93e814b89b6d2b4b250361d), Notion entrypoint and registry | `UNRECOVERED`; do not infer v1.2 document bytes |
| `ABC-DOC-005 v1.1.0` | Same Library DOC-007 parent metadata | [DOC-005 v1.0.2](https://app.notion.com/p/3be6f520f93e8145be7bf3cc9f836c4b); registry row explicitly says version 1.0.2 | `UNRECOVERED`; v1.0.2 is NOT equivalent to 1.1 |
| `ABC-CCR-001 v1.1.0` | Same Library DOC-007 migration-basis metadata | Search hits to documents **mentioning** CCR-001; no independent CCR document verified | `UNRECOVERED`; citation/mention is not source recovery |

## Executed search categories

- Notion internal full-title/keyword queries: `ABC-CCR-001`, `Product Specification v1.2.0`, `Intelligence Architecture v1.1.0`, `ABC-DOC-005 v1.1`, `Salon-Controlled Productization Baseline`, `Productization Rebaseline`.
- Examined the separate Notion `ABC-DOC-005 — Intelligence Architecture` registry row (URL: https://app.notion.com/p/3be6f520f93e81cd8dd7c89e939b3760): metadata confirms **v1.0.2**, blank content; the detailed Notion source also declares **v1.0.2**.
- Library searches included exact terms for all three missing versions plus titles of newer DOC-007 and DOC-018 Productization files. **Two standalone Productization documents found:** DOC-007 v1.1.0 and DOC-018 v1.2.0. Their existence does not authenticate missing parents.
- GitHub base/PR evidence: `main` initially at `62951aa6ac85e1d8a331cc7c5e14e1ac843b6e11`; documentation PR #1 head checked before WP-000-02; no platform runtime is asserted.

## Positive evidence retained

- [Legacy Charter DOC-000](https://app.notion.com/p/3b76f520f93e81e5a7b0e7b4062991ea): dated GPT-only rebaseline.
- [DOC-005](https://app.notion.com/p/3be6f520f93e8145be7bf3cc9f836c4b) + [DOC-006](https://app.notion.com/p/3be6f520f93e810fb8a0eaef1ce03856): ten *logical* agents under Custom GPT, NOT 10 deployed services.
- [DOC-009](https://app.notion.com/p/3be6f520f93e81e28b93e3b181a4ded6) and [DOC-010](https://app.notion.com/p/3be6f520f93e816ea629e6ae901f51aa): external CV/mask/compositing was explicitly deferred for historical GPT-only V1.
- [DOC-013](https://app.notion.com/p/3be6f520f93e8124b988c7f9d64cf068): one-GPT-per-salon historical model.
- [DOC-014](https://app.notion.com/p/3be6f520f93e8173954dd509eead549f): OUT-01..OUT-17 contracts are historical and transferable only through explicit mapping.
- [DOC-018](https://app.notion.com/p/3be6f520f93e8165bb8ddaf27a19e415) and Library Productization DOC-018 v1.2.0: 120 authored test cases, **no test run**; numeric calibration open.
- [ABC-KB-900](https://app.notion.com/p/3bf6f520f93e81dba5dce61e7b2a6eca): freezes 16 GPT-runtime derivative knowledge files, 39 service IDs, 45 attributes; hashes/bytes of 16 files not independently recovered in this work.
- [BUILD-005](https://app.notion.com/p/3bf6f520f93e818c8fe1efcb79cb492a): build checklist, historical state BUILD_READY; no evidence a platform was built.

## Confidence, limits and next retrieval

`CONFIRMED`: directly read a named source. `CORROBORATED`: two or more independent records agree on a bounded assertion. `REFERENCED_ONLY`: a downstream citation or title mention. `NOT_FOUND_IN_SEARCH`: search returned no matching independently usable artifact; do **not** rewrite as nonexistent. `NOT_TESTED`: runtime claim without execution evidence.

Recovery may be completed only with a file/page that includes the actual versioned contents and verified metadata, or an explicitly authorized signed missing-source exception. Otherwise parent-dependent new provisions remain provisional.
