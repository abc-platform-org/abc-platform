# ABC Gate & stacked PR merge plan — NO MERGE AUTHORIZED

| Order | PR | Source branch | Target | Original head SHA |
|---|---|---|---|---|
| 0 | Gate reconciliation PR (this dossier) | governance/gates-00-02-disposition-20261029 | docs/engineering-baseline-20261028 | to be captured at PR creation |
| 1 | #1 | docs/engineering-baseline-20261028 | main | 9d7a8ed1d079059ce99d6165664cf49b64579fa6 |
| 2 | #10 | docs/phase-01-product-definition-20261029 | main after retarget | 7f940efdfeebd373825179abe3f94a11299e2749 |
| 3 | #12 | contracts/phase-02-interface-baseline-20261029 | main after retarget | 164c512a944faf186144fdbb0d88dcabee871ade |

## Preflight warning: stacked branches and asynchronous verification

- Always re-read all 4 PR head SHAs and target branches immediately before any merge; prior SHA records are **historical evidence**, not a branch lease.
- Do not treat successful CI from an older commit as current; require successful checks on the exact last SHA being merged.
- If the governance PR and Phase-02 head change during review, reset the owner approval packet with the *new* HEAD and require review again.
- Formal design-only Gate PASS requires explicit owner authorization on exact source exceptions and ADR decisions, not merely assignment or a CI pass.
- Hard service/pilot gates remain blocked independently of design-only merge.

## Preconditions

1. **Owner explicitly reviews** source exception details (3), ADR directions (10), product MVP stages (64) and contract draft (19 engines / 34 schemas / 41 API ops) with exact SHA and recorded decision.
2. Required independent evidence is either obtained at design stage or **explicitly, boundedly and acceptably reclassified to later no-live-release gates**. No unreviewed auto-waiver.
3. Source authority lookup caveat is acknowledged. No invented DOC-001 1.2, DOC-005 1.1, CCR-001 1.1.
4. Review every relevant PR diff for unintended files, validate CI at current head, check branch protection and mergeability, review blocking threads, and ensure no pending high-risk contradiction.
5. Current GitHub account owner self-review may not satisfy an independent branch-protection rule: obtain independent review or auditable owner attestation plus independently validated release gates as required by policy. Never claim an unsubmitted GitHub review occurred.
6. Obtain **separate explicit merge authorization** once formal Gate status is actually signed.

## Ordered actions

A. After Gate dossier review, merge the small governance PR **into PR #1 branch**, not directly main, only with authorization; keep evidence of new branch head.  
B. Resolve Gate-00, then merge #1 to main after all required checks.  
C. Retarget #10 to main, re-check its **18 intended file** diff; avoid duplicating inherited base files; review and merge after G-01 authorization.  
D. Retarget #12 to main, re-check its **75 intended file** diff (72 original files plus three additional audit/event-fixture artifacts; 12 contract-level findings corrected) and contract CI; review and merge after G-02 authorization.  
E. Read back final main tree, file hashes/count and results; retain source branches if needed; never force-push or claim runtime build.

Any failed condition → STOP at safe point. No PR must auto-merge merely because docs CI passed or user earlier asked to build the project.

## Delegated design-only merge mandate — superseding the prior unapproved proposal

ABC-DDR-20261029-001 conditionally authorizes merging these **documentation/design-only branches** when all current head SHAs and CI/permissions/mergeability are checked. The owner explicitly requested completing the design phases and then delegated engineering decisions to the assistant. Do **not** use this to merge executable production releases, bypass independent protection rules or claim an authenticated human PR signature. The original runbook order and stop conditions remain in force.

- PR #15 → PR #1 documentation branch; inspect CI and diff.
- PR #1 → main; avoid deleting files, preserve original baseline.
- PR #10 → main after P00; re-evaluate last SHA and requirements file diff.
- PR #12 → main after P01; re-evaluate last SHA and all 75 contract files, including 12-defect fix and 174 synthetic case CI.
- Runtime Gates G03+ and [Issue #18](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/18) remain blocking for any real customer/service release.

If repository branch protection requires a separate human review or checks fail on the **current** candidate, STOP. The delegated decision is not a fabricated GitHub review.
