# ABC P04/W0 — Authenticated Producer/Consumer Handoff, Local E2E

**2026-10-30. Status:** CI-only experimental review transport; requires independent signoff of ADR-ENG-003/004. **No customer processing and no engine execution.**

## Source-controlled implementation

- `0019_eng19_review_inbox.sql`: 16 canonical artifact kind edges registered in the PostgreSQL16 database. An append-only, forced-RLS inbox stores one immutable receipt per handoff UUID and scoped content hash. Application and worker roles have **no direct table INSERT/UPDATE/DELETE/SELECT grants**. A SECURITY DEFINER database function checks transaction-scoped tenant and branch, physical workload allowance, exact edge, active unexpired purpose-specific consent, current CREATED session and state-version fencing. `FOR SHARE` locks the consent and session rows against concurrent revocation/PAUSE. Same handoff + same content returns `ALREADY_RECORDED_REVIEW_ONLY`; same UUID + different content fails.
- `eng19_review_consumer.py`: checks strict 19-edge JSON contract, caller/target and producer-scope identity; requires externally verified mTLS-bound signed JWT, exact per-target audience, independently injected live session, consent and ENG14 policy authorities. It consumes JWT JTI through the existing shared PostgreSQL replay ledger and stores a review-only durable receipt.
- `eng19_review_transport.py`: real TLS1.3 mutual-certificate loopback listener and client with exact target, framed message and sanitized denied responses. No public or hosted listener, no HTTP and no domain engine dispatch. No connection to customer media, paid inference, salon business operations or real specialist approval.
- `test_eng19_actual_mtls_handoff_pg.py`: synthetic, test-only ephemeral certificates, real signed RSA JWT, true loopback network, actual PG16 durable inbox, two separate TLS listeners and six concurrent connection attempts. Covers replay, same-handoff new-JTI retry, conflicting immutable content, revoked consent, fake policy gate, stale version, wrong tenant/engine/branch, unsupported v1/v2, missing cert, forged thumbprint and staging denial. These tests **do not** supply a real professional authority.

## Security and reliability invariants

1. Ingress rejects any untrusted certificate/token **before** scope/policy, and rejects withdrawn/missing purpose consent **before** consuming JTI. The DB independently rechecks current session and consent after replay admission.
2. Incomplete failure can consume one JTI without inserting the handoff. **Never reuse the same JWT** on retry; a fresh one-time JWT with the same handoff UUID and identical payload yields an idempotent receipt if consent remains active. Receipt is not an ACK from a domain engine and does not imply work completed.
3. Fencing: PAUSED or version-changed sessions, withdrawn/expired consent, unknown tenant, mismatched branch and wrong artifact edge cannot insert into the inbox. Row locks serialize concurrent consent withdrawal relative to receipt.
4. This is a **single inbound edge proof** using the shared 16-edge schema, not proof that all 16 handoffs or 19 engines execute. No worker claim, lease, downstream job dispatch, approval or real visual model was introduced.
5. The database workload gate currently recognizes preexisting ENG01-approved physical logins in managed tenant mode. Real per-consumer credential binding and private PKI issuance require separate audited migration; **do not deploy from this branch**.
6. Source adapter PR #54 and proposed ADR-ENG-003/004 must be independently reviewed and signed before any ABI promotion or hosted execution; this implementation does not update frozen v1/v2 ports.

## Remaining release-blocking work

- Operational managed external CA/JWKS, physical Postgres client cert and private network, true per-engine workload grants; independent actual consent/ENG14 authorization provider and non-revocable auditable evidence.
- Per-engine typed payload contracts, real producer-generated and durably persisted outbox, at-least-once delivery with fresh signed JWT retries, bounded ACK, DLQ, incident/rollback observability, cancellation propagation and end-to-end recovered production workflow.
- Domain and specialist approvals for ENG07–ENG19, 190 signed G01–G10 gates and signed architecture ADR acceptance.
- Production authorization remains **BLOCKED**, Phase04 remains **IN_PROGRESS**, exact-head CI is necessary but not sufficient.
