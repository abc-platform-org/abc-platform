# ABC — AI Studio Three-Column Design + Controlled Evidence Gate

**Status:** offline interactive UX prototype; not an AI implementation, real user service or customer image uploader.  
**Location:** `prototypes/abc-ai-studio-v2/index.html` (open locally with its style.css and app.js). No build tooling, cloud account or API key required.  
**Product mode:** specialist and customer **in person on one shared desktop/TV screen**.

## Layout and components

| Column | Contract responsibility | Required components / AIS traceability |
| --- | --- | --- |
| 01 Input & Controls | Session ID, client consent/quality indicators, service type, allowed edit regions, reference controls | AIS session/image intake & QA, consultation, service-aware controls, reference isolation, edit masks; Evidence & Uncertainty |
| 02 Visual Canvas | Before/After, Compare, zoom and identity/region protection | AIS Transform, Try-On, version history, visual QA, current/accepted states, compare with explicit unverified quality |
| 03 Look Workspace | Generated looks, shortlist, look locking, technical-plan status | AIS recommendation, look spec, shortlist, specialist review, selected look, draft plan handoff, recovery |

The current demo contains three synthetic looks with CSS-drawn schematic head shapes; these are **not** AI-generated visuals. Choosing a look only updates ephemeral prototype UI state. Every purported image/identity fidelity indicator remains **NOT VERIFIED**. ENG06 never exposes a treatment plan, parameters, professional recommendation or operational execution from this UI.

## Concrete state design

```
SESSION_DRAFT → IMAGE_QA_REQUIRED → CONSULTATION_REQUIRED
             → ENG04_RECOMMENDATIONS_PENDING → LOOKS_DRAFT
             → LOOK_SHORTLISTED → LOOK_SELECTED_NOT_SIGNED
             → ENG05_DECISION_PENDING
             → ENG06_AWAITING_EVIDENCE
             → ENG06_DRAFT_REQUIRES_SPECIALIST
             → EXTERNAL_PROFESSIONAL_VALIDATION
             → ENG14_HANDOFF_GATE → OPERATIONAL_HANDOFF
```

These are **future UI design states**, not authorized transitions in the frozen ENG01 canonical v1 graph. Keep an explicit state mapping and prevent UI-local clicks from invoking a backend transition or treating fake consent/SOP as proof.

## Non-negotiable VQ constraints

- **VQ-01 Identity:** no face/identity changes without approved explicit scope; preserve immutable baseline.
- **VQ-02 Region fidelity:** only specifically selected regions can be transformed. Editable/locked mask is versioned with Look.
- **VQ-03 Accepted state preservation:** V0 original immutable; branches V1/V2/V3 have independent diff and rollback.
- **VQ-04 Reference isolation:** a reference never becomes the customer photo or identity.
- **VQ-05 Multi-region control:** region masks and edit intent validated separately from image output.
- **VQ-06 Failure transparency:** expose unreliable/unverified visual areas, missing evidence and regeneration failures.
- **VQ-07 Image-vs-reality gap:** a plausible preview cannot certify salon feasibility or professional service results.

## Integration contracts and safe migration

1. UI starts co-present session; ENG02 authenticates specialist membership, consent purpose and client record. No client-facing remote workflow is assumed.
2. ENG03 validates evidence provenance and produces immutable scoped ledger events. It never implicitly invokes a paid LLM/image API.
3. ENG04 v2 consumes typed scoped evidence and reference pointers, returns **draft** candidate Look specs only.
4. ENG05 v2 consumes ENG04 candidate ref + independent knowledge and ENG14 policy, and must hard-stop on unknowns/contraindications.
5. The user and specialist shortlist and lock a look in a trusted, versioned server-side operation; UI-local selection is not an authorization.
6. ENG06 v2 consumes genuine selected-look lock, current state, decision, consent and SOP evidence. Missing or revoked prerequisites block validated plans and handoff.
7. An independently qualified specialist verifies the procedure/parameters and stop conditions. ENG14 still requires a separate governed handoff.

## Security/engineering parallelism: ENG01/02/03/14

Keep building and testing the trusted core in parallel: ENG01 OIDC/authenticated versioned transitions; ENG02 per-purpose consent and in-salon specialist scope; ENG03 Claim/Lease/ACK + transactional evidence lineage; ENG14 deny-first service policy and independent professional approval. The new v2 validator does **not** treat claimed tenant/session fields as an authenticated principal. Production identity requires real provider PKI/JWKS, physical PostgreSQL client certificate, and private service deployment. These resources are still unavailable and tracked by [issue #43](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/43).

## MVP acceptance with no paid model API

Prototype acceptance: open three columns on desktop and mobile, choose controlled service/region/look, verify version changes are isolated, press technical plan and observe BLOCKED, and inspect code for no network/persistent storage. The real product will later require qualified salon testing, actual image transformations with identity-preservation benchmarks, scoped consent and independently signed S1–S3 SOP reviews before G08/G10 completion.

**No claim:** ENG04/05/06 smart engines are complete, v2 is externally deployed, AI Studio performs visual synthesis, or release is authorized.
