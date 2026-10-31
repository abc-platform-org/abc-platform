# ABC ENG05 W1 — Verified current register, PDF byte-acquisition, and independent approval workflow

**Research date:** 2026-10-31. **Status:** DRAFT / source professional release blocked.

## Evidence established

The German BAuA official register of Geltende TRGS lists **TRGS 530 — Friseurhandwerk, April 2023**, GMBl 2023 S. 627–634 (20.04.2023) as the current listed entry:
https://www.baua.de/DE/Angebote/Regelwerk/TRGS/TRGS

The official PDF first page shows edition 20.04.2023 and occupational exposure, with a total 15 pages:
https://www.baua.de/DE/Angebote/Regelwerk/TRGS/pdf/TRGS-530.pdf?__blob=publicationFile

The German Copyright Act **UrhG §5 (Amtliche Werke)** addresses government texts, with source attribution and no-alteration obligations for certain official works under §§62–63, and exceptions for some private technical standards:
https://www.gesetze-im-internet.de/urhg/__5.html

**There is no signed legal opinion** whether TRGS 530 specifically permits commercial AI ingestion, document storage, derived content, model training, redistribution or licensed reproduction. Do not confuse publicly accessible with a licence for every use.

## Raw PDF acquisition in dedicated GitHub Actions

A new isolated workflow, .github/workflows/eng05-trgs530-source-attestation.yml, checks official BAuA current and legacy PDF endpoints and an official BGW alternative. The script scripts/attest_eng05_trgs530_source.py allows only HTTPS to these exact two official hosts, bounded redirects/download sizes/timeouts, required PDF header and EOF, PDFINFO count of 15 pages, and PDFTOTEXT verification of first-page title and 2023 edition.

Only the **actual downloaded binary bytes** produce a SHA-256 and byte-count report. The workflow uploads a JSON-only GitHub Action artifact with the observed URL, digest, page count and status. It does NOT upload the third-party PDF, add it to the repo, store the content in customer memory, or send it to a model API.

If the download fails the report explicitly says BLOCKED_SOURCE_BYTES_UNAVAILABLE and contains no fake document hash. Even a successful byte-hash proof does not prove commercial reuse rights, professional accuracy, a current legal interpretation, specialist credential, individual client's suitability or ENG06 release. The existing review case retains its null PDF digest until a separately accepted evidence version is produced.

## Achieved actual BGW mirror download on 2026-10-31

The isolated [GitHub Actions source acquisition #2](https://github.com/saleheebrahimi2029-hub/abc-platform/actions/runs/41233421217) downloaded the official **BGW-hosted version** with HTTP 200, 741,429 actual bytes and 15 verified PDF pages. First-page checks confirmed TRGS 530, Friseurhandwerk and 20.04.2023.

**SHA-256 of BGW actual PDF bytes:** 356fc7d7ef4d4dc56ae687c72dfbf00d156b65ae494553f15f0060d7b46b5628.

The BAuA CURRENT and LEGACY URLs both returned HTTP 403 from the same runner, so BAuA's binary PDF **has not been proven byte-identical** with the BGW mirror. The source acquisition ZIP artifact (id 13054547656, held seven days) contains only JSON metadata; the durable, non-content audit copy is governance/abc_eng05_trgs530_bgw_raw_pdf_provenance_2026-10-31.v1.review.json.

Subsequent CI runs **pin this observed BGW digest** and refuse silent changes even when a future different PDF has a similar title. The earlier first-source case retains its original NULL raw-file digest, because its provenance was explicitly the BAuA original. This supplementary BGW record must be separately approved if used as a precise document reference.

**Remaining distinction:** a SHA of authentic public PDF bytes proves content integrity against this observed binary, but not redistribution/commercial AI rights, independence or expertise of a specialist, trust-root enrollment, or permission to run ENG05/ENG06. Those remain blocked in Issue #70.

## External professional/legal messages, NOT SENT

**Independent professional credential and safety reviewer request (German):**

Betreff: Unabhängige Fachprüfung TRGS 530, Friseurhandwerk — Arbeitsschutz und KI-Wissensbasis

Wir entwickeln eine KI-gestützte Software für Friseurbetriebe. Bitte prüfen Sie als unabhängige qualifizierte Fachperson ausschließlich den betrieblichen Arbeitsschutz im Rahmen der TRGS 530 (Fassung vom 20.04.2023). Benötigt werden der Nachweis Ihrer aktuellen fachlichen Qualifikation und der zuständigen Stelle, die geprüften konkreten Abschnitte, Anwendbarkeit, Vorsichtsmaßnahmen, Einschränkungen, offene Fragen und Widersprüche zu aktuellen Herstellerinformationen. Es geht nicht um Kundenallergie-Diagnosen oder um Mischungsverhältnisse für individuelle Haarfarben. Bei sicherheitskritischen Aussagen sind zwei voneinander unabhängige qualifizierte Prüfer mit eigenen Signaturschlüsseln erforderlich. Alle Angaben werden erst nach unabhängiger Prüfung akzeptiert.

**Rights counsel review request (German):**

Betreff: Urheberrechtliche Prüfung TRGS 530 (§§ 5, 62, 63 UrhG) für gewerbliche KI-Plattform

Bitte beurteilen Sie die urheberrechtliche Einordnung der aktuellen amtlichen TRGS 530 und die Voraussetzungen für kommerzielle Nutzung: Speichern der PDF, Extraktion und semantische Indexierung, begrenzte Zitate und Quellenangaben, abgeleitete Dokumentation, Ausgabe an Friseursalons, Weiterverbreitung sowie eine mögliche Modelltrainingsnutzung. Wir benötigen eine schriftliche rechtsverbindlich prüfbare Einschätzung einschließlich des Änderungsverbots, Quellenpflicht und gegebenenfalls notwendiger Rechte Dritter oder Einwilligungen. Bis zur positiven Prüfung bleiben alle produktiven Nutzungen gesperrt.

No message has been dispatched, no real specialist has signed any claims and no issuer/root has been enrolled.

## Scope and non-release conclusion

The BAuA register observation closes the *current edition discovery* research subtask as of 2026-10-31. It does not close the original PDF bytes/rights/reviewer/signature/conflict acceptance tasks. Source is staff occupational safety only; individualized salon chemistry and customer treatment require separate manufacturer data and specialist review.

- Actual PDF byte/hash gate: determined by evidence workflow, never guessed.
- Legal rights: PENDING qualified written opinion.
- Individual professional credential and signed claim approvals: PENDING verified independent reviewers.
- Conflict adjudication: PENDING human evidence.
- ENG05 executable knowledge facts: ZERO.
- ENG05→ENG06: BLOCKED_PENDING_AUTHORITY.
- Production deployment, ADR ratification and customer data: still blocked.

PR remains Draft; no protected main merge, paid AI APIs or cloud provisioning.
