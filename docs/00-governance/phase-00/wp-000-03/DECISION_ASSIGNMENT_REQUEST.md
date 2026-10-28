# WP-000-03 — Human Governance Decision / Assignment Worksheet

**This worksheet is a request for real organizational governance decisions, not a signed decision.** No user identity is inferred from their linked GitHub account, and no profession/qualification is assumed.

## 1. Appoint actual people

| Authority role | Required identity/acceptance | Status |
|---|---|---|
| Product Authority (GOV-A01) | Named project decision-maker formally accepts scope authority | UNASSIGNED |
| Architecture Authority (GOV-A02) | Named senior technical lead accepts ADR/accountability | UNASSIGNED |
| Qualified Domain/Safety Authority (GOV-A03) | Appropriate licensed/qualified professional(s) per service and safety reviewer | UNASSIGNED |
| Security/Privacy Authority (GOV-A04) | Named reviewer; involve legal counsel as relevant | UNASSIGNED |
| QA/Evaluation Authority (GOV-A05) | Named QA owner and independent visual evaluator | UNASSIGNED |
| Delivery/Program Authority (GOV-A06) | Named owner for risk, PR/CI/governance and escalation | UNASSIGNED |

**Required record:** `role | person's name or GitHub account | verified authority/qualification | acceptance evidence | date/time | delegation/independence conditions | scope`.

## 2. Explicit product/technical decisions

- [ ] Confirm *target* platform is independent, specialist-operated, shared in-salon screen; historical Notion GPT-only V1 remains intact as archival semantics.
- [ ] Review all 10 ADRs with exact file SHA (see [issue #3](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/3)).
- [ ] Decide three unrecovered parent-source routes individually (recover vs exception), with documented boundaries (see [issue #2](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/2)).
- [ ] Accept or revise backend authority, privacy and legal workflow (see [issue #5](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/5)).
- [ ] Appoint qualified professional SOP approvals, service risk policy and version-bounded specialist validation (see [issue #6](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/6)).
- [ ] Approve QA evidence taxonomy and future-gate allocations; keep 120 Golden `NOT_RUN` (see [issue #7](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/7)).
- [ ] Accept specific deferral of KB bytes to G-01 and actual runtime benchmark/test gates to later phases, with owners and controls.
- [ ] Confirm architecture PR review/merge policy. A passing doc workflow is not approval.

## 3. Signoff evidence form (one record per decision)

```yaml
decision_id: "ADR-001 | SRC-EXC-001 | GOV-A01 | G-00"
reviewed_git_sha: "<exact blob/commit>"
reviewer_real_name_or_verified_handle: "<required>"
reviewer_role_and_authority: "<required>"
date_time_iso8601: "<required>"
decision: "ACCEPTED | REVISE | REJECTED | EXCEPTION_ACCEPTED"
scope_and_version: "<required>"
conditions_and_residual_risks: "<required>"
evidence_issue_or_review_url: "<required>"
delegation_or_conflict_of_interest: "<if applicable>"
```

Signoffs are auditable repository review records, not a generated Markdown file containing a claimed signature. Reviewer should not change historical signed values; create append-only supersession.

## 4. Decision control / next step

Until these records are real, keep `G-00: BLOCKED_FOR_FORMAL_APPROVAL`, Draft PR #1 unmerged and `main` unchanged. The project decision-maker can supply actual governance assignments in issue #4; specialized approval still requires qualified reviewers.
