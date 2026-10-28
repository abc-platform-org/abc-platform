# WP-000-01 — Architecture Defect, Conflict & Risk Register

**No executable production code was inspected for actual defects.** These entries are *document conflicts*, *design gaps*, *unverified implementation claims* or *risks*. None represents a reproduced live code bug.

| ID | Class | Priority | Evidence type | Finding | Source | Responsible role | Migration | Close evidence | State |
|---|---|---|---|---|---|---|---|---|---|
| P00-001 | BASELINE | CRITICAL | CONFIRMED_DOC_CONFLICT | Legacy V1 mandates one Custom GPT vs user-approved independent platform; no formally adopted supersession | DOC-000/001/005/006/900; ADR-001 | Product architect / authority | MIG-01/02 | Formal ADR and approved authority precedence | OPEN |
| P00-002 | SOURCE | HIGH | UNVERIFIED_REFERENCE | Library v1.1 DOC-007 points to DOC-001 v1.2, DOC-005 v1.1 and CCR-001 v1.1; unavailable in recovered records | Library DOC-007 header | Source librarian | MIG-18 | Recover files or source exception approved | OPEN |
| P00-003 | DEPLOYMENT | HIGH | CONFIRMED_DOC_CONFLICT | DOC-013 says one GPT instance per salon vs multi-tenant backend design | DOC-013; ABC-F17 | Platform/security owner | MIG-11 | Tenant/role ADR and isolation contracts | OPEN |
| P00-004 | UX | HIGH | CONFIRMED_DOC_CONFLICT | Client remote consultation/output from DOC-001/014 contradicts shared in-salon-only rule | DOC-001/014; user decision | Product/UX owner | MIG-09/13 | Approved shared-screen role and output rules | OPEN |
| P00-005 | VISUAL | CRITICAL | CONFIRMED_DOC_CONFLICT | Deterministic segmentation and compositor explicitly deferred for GPT V1; platform requires new implementation proof | DOC-009/010/016A | Vision lead | MIG-06/07 | Visual runtime contract and experiments | OPEN |
| P00-006 | VISUAL | CRITICAL | ARCHITECTURE_GAP | Pixel lock outside mask does not prove inside-mask identity, realism, or haircut geometry consistency | DOC-009/010, AIS-009..020 | Visual QA lead | MIG-06/07 | Human benchmark and per-service QA | OPEN |
| P00-007 | SESSION | HIGH | ARCHITECTURE_GAP | GPT context recovery does not equal durable server-side session/job handling | DOC-005/008 | Runtime lead | MIG-08 | Persisted state, stale-result rejection tests | OPEN |
| P00-008 | QUESTIONING | HIGH | ARCHITECTURE_GAP | No executable service-specific QuestionProfileRegistry / stop/impact evaluation | DOC-001/008, AIS-004 | Consultation lead | MIG-03 | Question profiles and PQ test cases | OPEN |
| P00-009 | TECHNICAL | CRITICAL | NEW_SCOPE_DEPENDENCY | Technical plan SOP graph, mandatory evidence, material instructions and human sign-off not present in legacy output contracts | User instruction; KB-010/011 | Professional planning lead | MIG-12 | Expert SOP owners and draft/approval controls | OPEN |
| P00-010 | APPROVAL | CRITICAL | ARCHITECTURE_GAP | Look selection and professional validation may be conflated without typed approval/version invalidation | Library DOC-007; AIS-022..024 | Validation/security lead | MIG-12 | Signed version-bounded review API | OPEN |
| P00-011 | SAFETY | CRITICAL | ARCHITECTURE_GAP | Prompt-only S0–S3 policy cannot enforce runtime transactions or nonbypassable service decisions | DOC-012, KB-011 | Safety lead | MIG-10 | Backend policy evaluator and negative tests | OPEN |
| P00-012 | TENANT | CRITICAL | UNVERIFIED_RUNTIME | No backend code or test evidence of tenant/branch isolation and image access controls | ABC-F17; DOC-013 | Security lead | MIG-11 | Authorization integration test evidence | OPEN |
| P00-013 | PRIVACY | CRITICAL | OPEN_POLICY | Photo retention, opt-out, deletion, processing jurisdiction and specialist-screen confidentiality not fixed | DOC-001/012; new shared screen | Privacy lead | MIG-13 | Approved data lifecycle and consent model | OPEN |
| P00-014 | KNOWLEDGE | HIGH | SOURCE_GAP | 16 derived KB source bytes/hashes were not individually retrieved despite KB-900 freeze | KB-900 | Knowledge lead | MIG-04 | Rehash full frozen derivatives and ID mapping | OPEN |
| P00-015 | QA | CRITICAL | UNVERIFIED_RUNTIME | 120 golden cases authored; no evidence of execution, human reviews or empirical thresholds | DOC-015/018; Library DOC-018 1.2 | QA lead | MIG-15 | Runnable harness, run IDs and calibrated gates | OPEN |
| P00-016 | BUSINESS | HIGH | NEW_SCOPE_DEPENDENCY | Dashboard revenue/occupancy and Ask ABC have no verified business data source/transaction ledger | User UI; ABC-F01/F15 | Business systems lead | MIG-14 | Data lineage / action permission tests | OPEN |
| P00-017 | ENGINEERING | HIGH | UNVERIFIED_RUNTIME | ENG-01..19 are design-level responsibilities and do not establish implemented code/services | GitHub engine registry | Engineering lead | MIG-02/20 | API schema, owner, code, contract tests | OPEN |
| P00-018 | IDENTITY | HIGH | OPEN_POLICY | Specialist authentication on shared screen and visibility of private professional records not specified sufficiently | AIS-024, shared UX | Security/UX lead | MIG-13 | Shared screen privacy & signoff tests | OPEN |
| P00-019 | SOURCE | MEDIUM | HISTORICAL_SCOPE | DOC-016A/017/019 are deferred/not started, not production-evidence sources | Notion registry placeholders | Release owner | MIG-17 | Replacement readiness contract for platform | OPEN |
| P00-020 | PRODUCT | HIGH | NEW_SCOPE_DEPENDENCY | Advanced services in target feature inventory lack completed per-service professional validation and stage gates | User scope, Service Coverage | Service domain lead | MIG-19 | Service capability matrix + expert gate | OPEN |
| P00-021 | REPOSITORY | MEDIUM | CONFIRMED_DOC_GAP | PR#1 documentation passes only docs CI; no architecture approval or code tests | GitHub PR#1 and workflow | Release/program owner | MIG-20 | Reviewer record, ADR dispositions and issue links | OPEN |
| P00-022 | VERSION | MEDIUM | CONFIRMED_DOC_GAP | PACKAGE_MANIFEST says NOT_PUSHED_ACCESS_UNAVAILABLE from archive time despite actual PR upload | Manifest retained byte-identical | Program owner | MIG-20 | New audit state separate from immutable archive manifest | OPEN |
| P00-023 | INTEGRATION | HIGH | NEW_SCOPE_DEPENDENCY | No transaction/compensation contract for calendar/POS/inventory handoff from specialist plan | ABC-F03/09/10, AIS-025 | Operations integration lead | MIG-14 | Idempotent business command and state tests | OPEN |
| P00-024 | SEARCH | MEDIUM | NEW_SCOPE_DEPENDENCY | Global search/notifications lack explicit permission scope and operational event contract | ABC-F02/16 | Backend domain lead | MIG-14 | Data schema, access filters, notification policies | OPEN |
| P00-025 | EVIDENCE | MEDIUM | AUDIT_LIMITATION | Notion fetch responses expose Aug 2026 snapshots, not verified latest live edit/version state | Notion connector response headers | Source librarian | MIG-18 | Fresh metadata export and source approval | OPEN |

## Gate-00 blocking issues

- **Critical review blockers**: P00-001, 002, 003, 004, 005, 009, 015, 021, 025. They block **final authority/contract freeze**, not the creation of a proposed GitHub branch.
- Other engineering gaps become explicit downstream phase risks only after product authority accepts ownership and test obligations.
- Severity is prospective delivery risk, not runtime incidence or observed exploit.

## Evidence rule

Closing an item requires artifact URL, reviewer role and dated decision; labels like `Fixed` or `Passed` require a concrete code/test run.
