# ABC ENG05 W1 — TRGS 530: First real technical source acceptance case

**Case:** `eng05-de-hair-color-worker-safety-trgs530-20230420`  
**Recorded:** 2026-10-31  
**State:** REAL OFFICIAL REFERENCE IDENTIFIED — NOT QUALIFIED AS PROFESSIONAL ENG05 KNOWLEDGE  
**Engineering inheritance:** Draft PR #71 → this stacked Draft PR  
**Scope:** German salons, staff occupational chemical-safety; **NOT** individualized client hair-dye formulation, consumer allergy diagnosis or ENG06 decision output.

## Primary and corroborating sources

- German BAuA/AGS official technical rule: **TRGS 530 Friseurhandwerk**, 15 pages, version dated **20 April 2023**, GMBl 2023, S. 627–634, Nr. 30. Official source: https://www.baua.de/DE/Angebote/Rechtstexte-und-Technische-Regeln/Regelwerk/TRGS/pdf/TRGS-530.pdf?__blob=publicationFile
- BGW official accessible PDF: https://www.bgw-online.de/resource/blob/20628/29cbf999ca5c2d91e741fa6964c6c619/trgs530-gefahrstoffe-friseurhandwerk-data.pdf
- BGW publication metadata: https://www.bgw-online.de/bgw-online-de/service/medien-arbeitshilfen/medien-center/technische-regeln-fuer-gefahrstoffe-friseurhandwerk-20628
- BAuA TRGS register: https://www.baua.de/DE/Angebote/Regelwerk/TRGS/TRGS

The BAuA source first page was visually inspected; the BGW mirror was retrieved by a PDF text viewer, confirming **15 pages** and 20 April 2023 heading. **Retrieval of the raw PDF bytes into the engineering workspace failed**, including attempts from both BAuA and BGW. Therefore **no full-file content SHA-256 is claimed**; metadata and section references do not substitute for the source-document hash. Do not store the 15-page third-party text or print-ready PDF in a commercial repository until legal rights are resolved.

## Source-anchored review areas (not approved recommendations)

| Rule area | Printed page | Question requiring independent specialist sign-off |
|---|---|---|
| 1 Anwendungsbereich | 2 | Bound occupational employee exposure scope; exclude customer treatment inference |
| 3.1/3.2 | 3 | Check professional risk-assessment responsibilities and product-manufacturer safety information |
| 3.6 | 6 | Verify skin/occupational sensitization precautions and exposure evidence boundaries |
| 4.1–4.4 | 7–9 | Evaluate occupational controls against the salon's actual hazard assessment; prevent automated chemical-mixing ratios |
| 5–6 | 10–12 | Evaluate employee training and occupational health obligations; not client clinical advice |

These are **topics to validate**, not independently reissued technical operating instructions. This document alone does not provide a client-specific colour recipe, mixture ratio, strand-test outcome, diagnosis or medical authorization.

## External acceptance gates: six independent evidence packets

1. **SOURCE_BYTES** — Obtain the official/current PDF from BAuA or authenticated BGW link using an approved download process. Hash the **actual bytes** and record retrieval timestamp, full URL, redirect chain, file size, media type, authoritative HTTP headers and independent provenance; compare to an independent publisher-supplied checksum if available. Do not confuse a hash of a URL/JSON summary with the actual document.
2. **CURRENT_VERSION** — Review BAuA's current TRGS register and GMBl notices for TRGS 530 amendments, corrections and replacement. A 2023 PDF is a recorded edition, not a permanent guarantee of currentness.
3. **LEGAL_RIGHTS** — Obtain a written German legal opinion regarding public-sector technical publications and applicable reuse rights (including §§ 5 and 63 UrhG where pertinent) or a sufficient documented license/permission to ingest text into a commercial AI platform. Linking and making a private hash are not automatically evidence of redistribution, model training, or full-text commercial database rights. Confirm rights per media, edition, jurisdiction and intended operations.
4. **SPECIALIST_CREDENTIAL** — Identify a real, jurisdiction-qualified hairdresser/occupational safety specialist via the competent registry; require independent official/licence evidence, scope, expiry, revocation, person identity, conflicts and an SRE-pinned verified issuer root. Directory pages alone never certify an individual.
5. **INDEPENDENT_CLAIM_REVIEW** — A qualified independent reviewer must sign exactly the validated source bytes/digest and the four section-level claims, applicability, uncertainties, required product label/manual evidence, exclusions and unresolved questions. For safety-critical claims require two **different people and two different qualified signing keys**, independent of the source submitter/publisher.
6. **SAFETY_CONFLICT_ADJUDICATION** — Collect BGW guidance, current product labels/SDS and regulatory amendments where relevant, document any disagreements, have independent specialists adjudicate with signed rationale and conservative stop conditions; never auto-select a newest version or majority vote.

These are external obligations and **no signatures or licence approvals have been forged**. The real-world prerequisites are tracked in [Issue #70](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/70).

## Code and database evidence

- `governance/abc_eng05_trgs530_first_professional_source_intake.v1.review.json`: frozen real source metadata, section/page references, six external approval requirements, null source PDF digest and explicit work/care exclusions.
- `runtime/phase04/abc_foundation/eng05_first_source_acceptance.py`: strict fail-closed validation; `local_pdf_evidence_hash` computes SHA-256 **only from actual PDF bytes** and provides no content or professional release authority; `create_external_review_requests` produces six deterministic unsigned external evidence requests.
- Versioned **migration 0028**: append-only, FORCE-RLS `eng05_external_document_acceptance_cases` and `eng05_external_approval_requests`. Source digest remains NULL, rights/professional/source-ingestion/ENG06 booleans are constrained false, no engine can perform direct DML. The existing migrations 0001–0027 are untouched.
- Integration tests reject forged PDF hash, fake licensing, simulated independent specialist signoff, unauthorized client formula interpretations, ENG06 release, and direct engine DB access; also test six immutable request receipts and PostgreSQL SHA consistency.

## Approval and release disposition

- **Source-reference discovery:** established with BAuA/BGW official metadata and identifiable sections.
- **Exact content-byte acquisition and hash:** not established.
- **Commercial ingestion/republication rights:** not established; legal review required.
- **Independent qualified specialist licence and signed interpretation:** not established.
- **Professional release into ENG05 knowledge Worker:** **DISABLED**.
- **ENG05→ENG06 decision edge:** **BLOCKED_PENDING_AUTHORITY**.
- **Customer-facing recommendations:** **DISABLED**.

A green CI certifies software behavior under *synthetic testing only*. It neither signs a safety-critical professional rule nor turns an official link into a licenced model-training resource. Never close Issue #70 solely because this PR passes.

## Operational next step that requires authorized humans

A registered German salon safety professional and a German legal rights reviewer need to evaluate this exact source. A platform security owner must independently verify the external issuer and enrol the trust key; hand-signed professional reviews should then be validated in **private approved staging** with strong revocation tests. Only with those external artifacts can a new versioned, separately approved ENG05 knowledge-retrieval adapter be proposed. Current W0 ADR-ENG-003/004, private infrastructure and all 19×G01–G10 formal acceptance gates remain open.

**Nonchanges:** protected main, professional knowledge runtime, ENG06 dispatcher, paid AI APIs, customer media, live production and Notion.
