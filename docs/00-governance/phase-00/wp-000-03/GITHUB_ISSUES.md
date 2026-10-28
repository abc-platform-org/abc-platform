# WP-000-03 — Real GitHub Issue Register

**Issue existence ≠ review/approval.** All issues were created without assigning a fictional person.

| Workstream | Issue | Responsible *role* | Required outcome | Gate |
|---|---|---|---|---|
| GOV-01 | [#2](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/2) | Source / Product / Architecture | Three parent sources or signed exceptions | G-00 |
| GOV-02 | [#3](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/3) | Product + Architecture | Formal ADR-001..010 decisions | G-00 |
| GOV-03 | [#4](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/4) | Program | Named owner assignment and RACI acceptance | G-00 |
| GOV-04 | [#5](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/5) | Security + Privacy | Consent, photo lifecycle, shared display, tenancy | G-00 |
| GOV-05 | [#6](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/6) | Specialist + Safety | SOP authority and professional validation | G-00 |
| GOV-06 | [#7](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/7) | QA + Vision QA | Authored vs executed tests / calibration plan | G-00 and later release |
| GOV-07 | [#8](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/8) | Knowledge Lead | 16 derivative KB exact bytes and ID crosswalk | G-01 |
| GOV-08 | [#9](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/9) | Program + all authorities | Signed Gate-00 decision and PR governance | G-00 |

**Policy:** Every issue can close only with linked versioned evidence, reviewer identity and explicit outcome. No issue is closed by a passing Markdown-only CI check.

## Closure order / dependencies

- First: #4 appoint real individuals, accept authority boundaries.
- Then in parallel: #2 sources/exception; #3 ADR; #5 privacy; #6 safety/SOP; #7 QA.
- #8 downstream knowledge export remains open at G-01; G-00 must have explicit *reviewed risk treatment* to defer it.
- Last: #9 Gate-00 formal decision after verified evidence and PR review; merging PR is separate.
