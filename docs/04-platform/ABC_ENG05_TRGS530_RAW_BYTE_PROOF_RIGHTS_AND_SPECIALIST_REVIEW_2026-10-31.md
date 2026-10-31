# ABC W1 / ENG05 — TRGS 530 Byte-Level Evidence and Independent Approval Protocol

**Status:** Review-only implementation candidate. No authentic PDF was transferred to this execution environment, and there is **no verified full-file SHA256**. Legal/commercial licence, actual specialist credentials and original human signatures are absent. **ENG05→ENG06 remains blocked.**

**Base:** Draft PR #72 first real source case; this stacked change never changes 0001–0028 or the professional Knowledge Worker.

## 1. What was independently checked against official material

- BAuA live register `https://www.baua.de/DE/Angebote/Regelwerk/TRGS/TRGS` (observed 2026-10-31) lists **TRGS 530 | April 2023 | Friseurhandwerk**, GMBl 2023 S. 627–634 Nr. 30 (20 April 2023), without a later amendment shown on that row. This is a timestamped **web register observation**, not an authoritative archive hash. Recheck immediately prior to final use.
- The BGW official 15-page TRGS 530 PDF was read through a web PDF viewer; pages 1, 3 and 6 were visually reviewed. The text shows staff hazard-assessment responsibility and employee chemical/skin safety scope.
- The BGW and BAuA full PDF downloads **did not reach the execution filesystem**; both direct access attempts failed due tool/network restrictions. The PDF full-file hash, publisher checksum, redirect chain, HTTP response, byte-level proof and content redistribution remain **PENDING**.
- Recorded machine-readable evidence: `governance/abc_eng05_trgs530_official_version_rights_and_specialist_precheck.v1.review.json`. This file does not grant professional or legal acceptance.

## 2. How to obtain a truthful raw-file receipt

An authorized operator retrieves the original unchanged PDF directly from the BAuA or BGW official URL on an approved computer, documents retrieval time/source, preserves the original PDF without reprinting, cropping or editing it, and runs the local-only tool with no cloud upload:

```bash
cd runtime/phase04
python -m abc_foundation.eng05_trgs530_byte_observation \
  --file /secure/intake/TRGS-530-original.pdf \
  --source-url 'https://www.bgw-online.de/resource/blob/20628/29cbf999ca5c2d91e741fa6964c6c619/trgs530-gefahrstoffe-friseurhandwerk-data.pdf' \
  --retrieved-at '2026-10-31T15:00:00+00:00'
```

Use the **actual** retrieval timestamp, not the placeholder above. The script checks a fixed origin allowlist, a time-zone-aware capture time and a bounded local regular file; it hashes the supplied **raw bytes** with SHA-256. It checks PDF header/EOF **markers only**; it expressly does **not** assert that every PDF object, digital signature or page was parsed, or that the URL/byte provenance was independently authenticated. A successful hash is not evidence of an authorized copyright licence or content correctness.

The `abc.eng05.pdf-byte-observation.v1.review` output contains no original copyrighted PDF bytes and explicitly sets publisher checksum, independent origin, professional approval, commercial rights, ingestion and ENG06 release to false. A separate reviewer must independently re-retrieve and compare hashes and current register evidence to move any source to a future approval process. **Do not edit the historical case or change the existing NULL PDF SHA in Migration 0028.**

## 3. Versioned PostgreSQL record

Append-only Migration **0029** adds `abc.eng05_trgs530_byte_observations`, which can persist an observed SHA and metadata digest once real raw bytes exist. It preserves immutable historic records, FORCE RLS and direct grant denial to `abc_app`, ENG04, ENG05, ENG06 and legacy workers. Unlike source rights, a SHA is technically recordable without a human professional decision; its corresponding flags are fixed false and never grant downstream execution. The initial review case stays `CANDIDATE_ONLY_NOT_PROFESSIONALLY_APPROVED`.

## 4. German legal issue spotting — NOT a signed licence opinion

Potentially relevant statutory rules:

- [UrhG § 5 — Amtliche Werke](https://www.gesetze-im-internet.de/urhg/__5.html): excludes certain official instruments and official works from copyright protection under defined conditions. Whether the **exact** technical rule/publication and intended downstream use qualify is a question for independent qualified counsel.
- [UrhG § 62 — Änderungsverbot](https://www.gesetze-im-internet.de/urhg/__62.html): potential non-modification constraints.
- [UrhG § 63 — Quellenangabe](https://www.gesetze-im-internet.de/urhg/__63.html): potential source-attribution obligations.
- Check BAuA/BGW website terms, publisher layouts and possible embedded third-party materials separately. Do not automatically equate public accessibility with commercial full-text ingestion, redistribution or model training rights.

Independent rights counsel must issue a dated signed opinion identifying `TRGS 530`, the exact PDF/version, the planned ABC internal retrieval and/or training use, jurisdiction, statutory exception/licence, restrictions, mandatory attribution, and review of any embedded external works. **No such opinion has been received.**

## 5. Practitioner competency and independent qualified review

TRGS 530 § 3.1 identifies employer responsibility for occupational hazard assessment and emphasizes competent experts. Depending on the claim, reviewers should include a qualified **Fachkraft für Arbeitssicherheit** familiar with salon chemical exposure and/or a **Betriebsarzt** for occupational medical risks. A **Friseurmeister** credential by itself is not proof of every safety-critical chemical/occupational medical qualification. A competent German authority and the qualified reviewers must confirm the relevant licensing/scope and revocation status.

Before registering a signed specialist attestation, require (a) verified identity and relevant independent qualifications, (b) issuer key pinned outside the repository, (c) exact PDF byte digest, (d) page/paragraph-level evidence and narrow *employee protection* applicability, (e) per-claim uncertainty/contraindications, (f) conflicts of interest, and (g) two distinct qualified people **with two distinct verified signing keys** for safety-critical claims. A technical self-signed CI key is *not* proof of real qualification.

## 6. Blocking disposition

- BAuA register match: **OBSERVED**, recheck before real approval.
- Original PDF raw bytes and independently verified hash: **NOT AVAILABLE**.
- Copyright/commercial reuse clearance: **NOT PROVIDED**.
- Actual independent specialist/occupational safety signatures: **NOT PROVIDED**.
- Signed safety/chemical conflict adjudication: **NOT PROVIDED**.
- ENG05 production knowledge ingestion and ENG05→ENG06 decision edge: **BLOCKED**.
- Original source and licensed content are **not** stored in GitHub.

Formal external dependencies remain [Issue #70](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/70). GitHub CI passing proves only the synthetic/offline engineering controls. W0/ADR and managed identity staging gates also remain open.
