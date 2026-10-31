# ENG05 W1 — TRGS 530 raw-byte verification and independent professional evidence

**Date:** 31 October 2026  
**Disposition:** DRAFT, local CI only; professional knowledge and ENG06 remain BLOCKED  
**Issue:** #70; **parent stack:** Draft PR #72.

## Official currentness cross-check

BAuA's official public TRGS register currently lists **TRGS 530 Friseurhandwerk, April 2023, GMBl 2023 S. 627–634, no amendment noted on the specific register entry**, as checked on 31 October 2026:

- https://www.baua.de/DE/Angebote/Regelwerk/TRGS/TRGS
- Primary file: https://www.baua.de/DE/Angebote/Rechtstexte-und-Technische-Regeln/Regelwerk/TRGS/pdf/TRGS-530.pdf?__blob=publicationFile
- BGW technical rule listing: https://www.bgw-online.de/bgw-online-de/service/medien-arbeitshilfen/medien-center/technische-regeln-fuer-gefahrstoffe-friseurhandwerk-20628
- BGW publisher mirror: https://www.bgw-online.de/resource/blob/20628/29cbf999ca5c2d91e741fa6964c6c619/trgs530-gefahrstoffe-friseurhandwerk-data.pdf
- BGW published staff operation aid based on TRGS530: https://www.bgw-online.de/bgw-online-de/service/medien-arbeitshilfen/medien-center/betriebsanweisung-fuer-friseurinnen-und-friseure-18188

The register’s absence of a displayed amendment is evidence only *as of the date checked*, not a future guarantee. Regulator and publisher versions should be rechecked before any professional approval, before each operational rollout, and upon regulatory change.

## Authentic source-byte validation protocol

`scripts/eng05_trgs530_pdf_byte_probe.py` is a standalone, ephemeral-runner verifier; it is not a source ingestion service. It attempts to fetch BGW, then BAuA through HTTPS with strict certificate validation, exact source URL allowlist and redirect denial, 6 MB maximum body and bounded timeout. Its PDF parser enforces **exactly 15 pages**, the first-page identifiers **TRGS 530**, **Friseurhandwerk** and **20.04.2023**, and computes SHA-256 *only* on received PDF bytes. The result contains timestampable CI provenance from GitHub's run/commit plus supplier URL, file size, digest, page count and explicit release-denial attributes. No publisher PDF is committed or packaged into the deployed application.

If either supplier's network blocks access, the CI report is `NO_VERIFIED_PDF_BYTES` with SHA `null`; no replacement hash of a webpage or JSON summary is permitted. A passing real-byte receipt does not assert that the PDF itself was publisher-signed, that legal reuse is allowed, or that the entire PDF text is suitable as AI model input. **Independent publisher checksum, if available, should be compared outside CI** before treating integrity as publisher-attested.

A GitHub Actions step probes the raw file as **report-only evidence**, and normal PostgreSQL/Python regression runs remain mandatory. Local input verification is supported only for PDF bytes already obtained through an approved channel; no direct ENG05 runtime reference is created.

## Legal reuse boundaries: German `UrhG §5`

Germany's Copyright Act `§ 5 UrhG` can exclude certain official works from copyright protection; `§ 5(2)` still references attribution and prohibition of changes under §§62–63, and `§ 5(3)` carves out private standards. These distinctions can materially change rights for an official technical rule compared to copyrighted brand manuals and product photographs. It would be improper to claim blanket permission for commercial AI text ingestion, republication or training **without a jurisdiction- and use-specific legal assessment**.

Official text of §5: https://www.gesetze-im-internet.de/urhg/__5.html

The source candidate therefore remains `commercial_reuse_cleared=false`, `machine_ingestion_rights_cleared=false`, `redistribution_rights_cleared=false` and has no actual professional approval. Preserve source author attribution and provenance even where legal protection does not apply. Human German-law review is required for any nontrivial commercial reuse claim.

## Professional attestation scope

TRGS530 addresses **occupational protection of employees handling chemicals** in salon settings, not customer hair-dye formulation or medical allergy diagnosis. Individual signoff should be requested from an appropriately qualified work-safety professional with competency for dangerous substances/hairdressing workplaces, with jurisdiction and occupational medicine involvement where required. A hairdresser trade registry listing alone is **not** an attestation of chemical occupational-risk competence; choose specialized reviewers based on exact section and safety claim. A second independent qualified reviewer and separate signing key are mandatory in ABC for safety-critical claims.

The needed external documents are: individual proof of competency, issuer/competent-authority verification or out-of-band identity evidence, credential expiry/revocation, accepted conflict-of-interest declaration, reviewed scope/page citations and an exact-data digital signature binding the official source digest. An additional independent legal rights reviewer is required. No qualified reviewer has yet been contacted or signed; test keys do not count.

## Release gate

Until a human-reviewed edition, actual document byte digest, appropriately supported licensing/official-work legal opinion, independent credential enrolment, signed technical claims and conflict adjudication are all verified in approved private staging, **do not mutate the 0028 source case to APPROVED**. Source acceptance remains the legally and professionally gated operation described in Issue #70. `ENG05→ENG06 = BLOCKED_PENDING_AUTHORITY`, customer release disabled, no paid API, no deployed service and no `main` merge.

The automatically collected PDF receipt **does not close #70**.
