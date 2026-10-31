# ABC W1 — Private infrastructure commissioning and ADR-ENG-003/004 security review

**Engineering date:** 2026-10-31  
**Disposition:** SECURITY REVIEW PACKET / ENGINEERING CANDIDATE; NOT SIGNED OR DEPLOYED  
**Head dependency:** PR #61 `0a4bee7b32f59ce0650d4cb15a7ae07fba30900a` (CI: 469/469).  
**Scope:** W1 private staging for ENG-01/02/03/04/05/06/14; ENG05→ENG06 automatic delivery remains blocked.

## Executive decision

The connected Render workspace `tea-dbhglamc6qcc73fcjer0` was queried through the linked provider interface on 2026-10-31. It returned **no listed services** and **no PostgreSQL instances**. This is an observation of that workspace, not a universal claim about other accounts. The pre-existing provider-fit decision, `governance/phase04_infrastructure_selection.v1.json`, is still unapproved and explicitly states:

- Render private-service compute is only a **candidate**. The available connected service creation tool produces public web services rather than the required private pserv topology.
- For ABC's required physical PostgreSQL client certificate verification and `sslmode=verify-full`, the project's recorded selection requires an **externally controlled private PostgreSQL 16** provider. Creating a Render Managed PostgreSQL instance would violate the current policy.
- `billing_authorized=false`, `deployment_authorized=false`, `monthly_spend_cap_usd=null`, `approver=null`, and independent security signoff absent.

**No provider resource has been created, paid for, exposed, deployed or credentialed in this PR.** Any assertion of W1 provisioned/verified is false until external operator evidence exists. Synthetic CI credentials are not managed service identities.

## W1 concrete target topology (review candidate)

```
Salon shared display (future) ── separate authorized edge / API boundary ── ENG-01
                                      │
          private network / service discovery / default DENY
                                      │
  ENG-02 ──> ENG-03 ──> ENG-04 ──> ENG-05 ──> ENG-06
       scoped consent     evidence      knowledge    decision
          │                                          │
          └──────── ENG-14 separate deny-first policy authority
                                      │
              external private PostgreSQL 16 (no public ingress)
              external managed workload PKI/OIDC + secret custody
              immutable audit / backup / recovery / alerting
```

This diagram is a logical trust map, not a deployed route. ENG-01 is the control plane. ENG-14 decisions must be independently retrieved and validated; caller-provided policy strings cannot authorize any transition. There must be no client-photo capture, ENG-07 look output or professional operation until separately approved.

The exact candidate workload and edge inventory is machine-readable in `governance/abc_w1_workload_trust_boundaries.v0.review.json`: seven distinct target principals, seven target engine-specific DB permission groups, 11 scoped candidate communication/control edges, all DENY pending external evidence. `spiffe://abc.internal/staging/ENG-xx` is a proposed identity naming convention **not** a verified identity issued by a working PKI.

## Critical architecture/security findings to close

| ID / severity | Finding | Required independent acceptance evidence |
|---|---|---|
| W1-P0-01 / BLOCKER | Provider has no verified private compute, CA issuer, or private database; existing project decision forbids Render Managed PostgreSQL for the specified physical client-cert requirement | Real private service topology, provider resource IDs, no public listener proof, PostgreSQL certificate-based client identity under enforced hostssl, verify-full, RLS and isolation |
| W1-P0-02 / BLOCKER | No owner-approved cost ceiling/provider plan and no operator authority to create paid infrastructure; only a public Render web-service creation path is connected | Explicit cost/region/plan decision and operator authorization; security-reviewed private provisioner workflow |
| W1-P0-03 / BLOCKER | ADR-ENG-003 and ADR-ENG-004 are PROPOSED and no independent review exists on #57/#59/#61 | Named accountable architecture decision, distinct security reviewer approval, exact commit, immutable evidence and independent SRE review |
| W1-P0-04 / BLOCKER | ENG-04 and ENG-05 currently share an older `abc_pipeline_worker` permission group in synthetic paths, even though physical CI login names differ | Separate engine-specific NOLOGIN roles + per-engine LOGIN/managed identity, explicit GRANT/RLS review, revocation/cross-engine privilege tests, staged migration/rollback |
| W1-P0-05 / BLOCKER | Present ENG-05→ENG-06 path has only separate review TLS inbox and synthetic admin-seeded independent ENG06 Worker; operational outbox delivery is never authorized | Separately authorized dispatcher with actual managed identities, verified ENG-14 P2, durable inbox, consent/version CAS, exactly-once logical effect, fault injection, rollback |
| W1-P0-06 / BLOCKER | ENG-02 pre-capture guard deliberately returns 501; there is no atomic real consent+media-write, verified issuing authority or deletion/retention process | Independently verified consent authority and revocation race tests, encrypted object storage, purpose isolation, deletion and retention proof |
| W1-P1-07 / HIGH | Legacy staging migration client checks `sslmode=require`; this does not independently validate expected server identity | New operator-only signed migration path using verified CA and `verify-full`, explicit migration identity scope, tests for rogue endpoint cert; never relax to make provider fit |
| W1-P1-08 / HIGH | Service-level live PKI renewal, telemetry, audit/backup restore, patch and on-call ownership have no external evidence | Cert expiry and rotation simulations, trace provenance, backup/PITR restore, alarms, signed runbook and rollback drill |
| W1-P1-09 / HIGH | No independently qualified professional evidence issuer for ENG-05 source library or ENG-06 decision quality | Professional SOP ownership, provenance, qualification verification and safe fallback; zero recommendations on unverifiable source |

Do **not** equate newly created target group names with SQL privileges already provisioned. Current `abc_eng06_review_worker` is test-only. The target groups remain `provisioned=false`; migrations must be separately reviewed and executed only in explicitly approved private staging.

## Exact operator sequence once authority is explicitly granted

1. Record approved cloud/provider, region, 30-day spend limit, billing owner and whether a private staging resource may be created. Require separate architecture/security review for provider compatibility. No deployment otherwise.
2. Provision default-deny private network: no public engine hostnames, no public PostgreSQL ingress, restricted egress, TLS 1.3 and auditable internal DNS. Collect provider configuration export and independently verify from a second network vantage.
3. Provision external private PostgreSQL 16 with CA-validated server cert and client-certificate authentication. Confirm `hostssl` + clientcert verifier, `sslmode=verify-full` and CA pinning, isolated migration account, PITR, encrypted backups and recovery test.
4. Issue **seven separately attestable** identities for ENG01, ENG02, ENG03, ENG04, ENG05, ENG06 and ENG14; short-lived, independently revocable, with engine/audience/tenant scopes. Create **seven distinct** `NOLOGIN` database permission groups (split ENG04 and ENG05). Provision physical LOGINs under operator custody and prove each other engine's privilege is denied.
5. Issue externally managed certificate+OIDC JWT/JWKS trust metadata, validate issuer/JWKS pins, mTLS peer URI, audience, nonce/JTI, certificate binding, rotation and revocation. Never commit keys or bearer tokens in GitHub.
6. Validate ENG-14 denial without any caller-controlled allow reference; then rehearse stale lease, session-version race, revoked consent, cross-tenant replay, and policy proof substitution. Verify no event is ACKed or dispatched after denial.
7. Run isolated, **synthetic only** staged migrations and smoke tests with signed build digest, redacted logs, rollback and disaster recovery. Record immutable evidence links to exact build commit; independent security, SRE and architecture reviewers verify them.
8. Only after separate, attributable signoffs, create an *additional* PR proposing controlled ENG05 outbox dispatch to an authenticated ENG06 receiver. Do not reinterpret `BLOCKED_PENDING_AUTHORITY` as permission. Customer release is a separate approval.

## Ratification record and authority segregation

| Review authority | Required decision | Present state |
|---|---|---|
| Architecture owner — ADR-ENG-003 | Confirm 19 independent owners, protocol v1/v2 frozen, v3 adapter semantics, 17-stage graph, control planes | **PENDING** |
| Independent security reviewer — ADR-ENG-004 | Confirm PKI/mTLS, RLS, policy and consent races, threat model and negative tests | **PENDING** |
| Qualified professional reviewer | Confirm professional sources, SOP, human control and no executable unreviewed plan | **PENDING** |
| Independent platform/SRE reviewer | Confirm private network, DB, backup/restore, observability, runbooks and rollback | **PENDING** |

An AI-generated document, GitHub collaborator permission or green CI cannot constitute a real independent review. The four reviewer slots remain unsigned in `governance/abc_w0_ratification_manifest.v0.review.json`; 190 engine acceptance gates remain OPEN. No reviewer IDs, dates or signatures are fabricated.

## Evidence bundle generated in this PR

- `governance/abc_w1_workload_trust_boundaries.v0.review.json` — seven independent target principal and DB role designs, 11 candidate edges, ten missing external evidence slots.
- `scripts/validate_abc_w1_private_trust.py` — source-locked deny-first validator with 15 synthetic negative mutation tests; it cannot grant operational authorization.
- Foundation CI runs W1 validator alongside the existing 469 Python/PostgreSQL tests, W0 ratification and W1/W2 readiness guards.
- PR #61 remains the reference for independent synthetic ENG06 review-worker baseline, not a live decision worker.
- Issue #58 tracks independent architecture reviews, #60 tracks private commissioning. New review evidence must be scoped to the exact final reviewed commit.

**Final state:** W1 provisioning *not complete*, ADR-ENG-003/004 *not ratified*, ENG05→ENG06 production delivery *blocked*, no client data, no Render bill, no protected-main merge.
