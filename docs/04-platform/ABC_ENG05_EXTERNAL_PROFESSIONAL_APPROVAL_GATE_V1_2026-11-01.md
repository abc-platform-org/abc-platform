# ENG-05 External Professional Approval Gate — v1 (review-only)

Parent: PR #77 / commit `99d6f38ea61c0db53a3db1e3edbfd1ef7becc96f`. This document is a **requirements and evidence checklist**, not an approval, production release, or new engine.

## Mandatory independent evidence

| Gate | Required evidence | Fail-closed condition |
| --- | --- | --- |
| Source provenance | Official edition, source URL, retrieved bytes and SHA-256, independent publisher provenance/currentness assessment | SHA alone does not attest publisher identity |
| Legal | Signed jurisdiction- and use-specific commercial text ingestion and redistribution opinion, scope, expiry and reviewer identity | Unreviewed copyright/rights |
| Professional identity | Verified issuer, license/qualification registry, role/scope/jurisdiction, independent person identity | Self-attested credentials |
| Cryptographic signatures | Signed canonical claim set, trusted issuer root, key rotation, signature time, revocation/expiry and audit | Untrusted, expired, revoked or missing chain |
| Evidence-to-claim | Versioned source edition, precise page/section, applicability and uncertainty per claim | Uncited or superseded claim |
| Conflicts | Explicit conflicting sources, precedence rationale, independent reviewer resolution and abstention | Unresolved contradiction |
| Safety-critical review | Two distinct qualified independent reviewers, separation of duties and specialist sign-off | One signer, shared identity or conflicts of interest |
| Governance | Independent ADR-ENG-003/004 ratification and ENG-14 policy enforcement, managed workload identity and private staging evidence | Missing independent ratification |

## Non-bypassable state machine

`CANDIDATE` → `PROVENANCE_VERIFIED` → `RIGHTS_REVIEWED` → `CREDENTIALS_VERIFIED` → `CLAIMS_REVIEWED` → `DUAL_SIGNED` → `GOVERNANCE_RATIFIED`.

Each transition requires immutable evidence IDs, authenticated independent reviewer identity, versioned policy decision, event audit and negative/revocation tests. Revocation, new edition, source conflict, reviewer expiry or changed rights invalidates approval and requires a new review. No retroactive approval by rewriting old rows. These are **proposed review states**, not deployed transitions.

## Integration boundary

Do **not** mutate migration 0028/0029/0030. Do **not** grant read/write access from ENG-05 worker or ENG-06 to untrusted observation tables. Do **not** enable operational handoff. Use additive migrations and independently reviewed contracts only after the approval mechanism has been threat-modeled and accepted. Until external proof exists: `professionally_released_facts=[]`, `ENG05→ENG06=BLOCKED_PENDING_AUTHORITY`, `customer_release=false`.

## Acceptance tests to implement before approval

- Forged or self-issued signer, revoked/expired credential, wrong jurisdiction or service scope.
- One signer reused twice, colluding signers, same organization when independence is required.
- Changed canonical payload after signing, replay, missing citation, source-version mismatch.
- Concurrent contradictory claims, source withdrawal, lost consent, unavailable issuer registry.
- Network timeouts, partial persistence, duplicate events, idempotent replay and audit integrity.
- Direct SQL, role/tenant crossover, migration checksum drift and bypass of ENG-14.

## Evidence inventory

Existing technical proof: BGW-hosted TRGS 530 PDF, 741429 bytes, 15 pages, SHA-256 `356fc7d7ef4d4dc56ae687c72dfbf00d156b65ae494553f15f0060d7b46b5628`. This is not publisher-signed or legally approved. PR #77 CI passed 560 tests; it did **not** complete any external professional gate.

External evidence not supplied: independent legal opinion, authoritative issuer trust chain, real qualified signers, adjudicated claim set, ratified ADRs and private staging acceptance. Keep Issue #70 open.
