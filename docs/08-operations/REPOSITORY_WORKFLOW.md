# GitHub Engineering Workflow & Change Control

## Repository policy

Target: `saleheebrahimi2029-hub/abc-platform`. **Initial verification note:** Access to target private repository was NOT available through linked GitHub integration when this package was generated. This folder is prepared as a conflict-safe import baseline, not claimed pushed.

## Proposed branch flow

- `main`: protected, production-intent trunk, no direct commits and no force-push.
- `docs/abc-engineering-baseline-20261028`: isolated documentation import branch.
- `feat/<issue-id>-short-name`, `fix/<issue-id>-short-name`, `chore/<issue-id>-short-name` for future changes.
- Every PR links task, feature IDs, engine contracts, test evidence, ADR when relevant and rollback policy.

## PR checks

1. Code review from designated owner and relevant QA/professional reviewer.
2. CI lint/format/schema/contract/unit and relevant E2E tests; protected required checks configured in GitHub after repo access.
3. No high-severity secrets, user photos, personal data in PR.
4. Breaking schema changes use migration, version bump and consumer review.
5. `main` merges only after gate criteria; no automatic production deployment from an unreviewed PR.
6. Release notes, changelog, implementation status, tested commit SHA and evidence links.

## Collaboration between contributors/ChatGPT accounts

Work via nonoverlapping issues and isolated branches, explicit owner per engine. Never edit same contract without coordination. PR cross-review and sync with latest base. Context docs stored as repo files/ADRs; do not depend on one account's conversational memory. Regular `docs` updates track decisions and open questions; no silent modification of frozen specifications.

## Commit conventions

`docs: establish architecture baseline`, `feat(ai-studio): ...`, `fix(visual): ...`, `test(engine): ...`, `chore(ci): ...`. Include `ABC-F`, `AIS`, `PRD`, `WP` IDs in PR description.

## Reproducible trace

A completed task reports issue URL, branch, commit SHA, changed files, tests actually run, results, unresolved risks, next dependency, and PR state. A zip attachment or a ChatGPT response is not a Git commit.
