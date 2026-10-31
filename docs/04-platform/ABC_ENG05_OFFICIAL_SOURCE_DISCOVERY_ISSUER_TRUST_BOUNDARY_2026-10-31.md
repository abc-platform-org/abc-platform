# ABC ENG05 — Real official-reference discovery & independent credential issuer boundary

**Date:** 2026-10-31
**Status:** DRAFT — SOURCE_DISCOVERY_ONLY / NO PRACTITIONER CERTIFIED / NO LIVE RECOMMENDATIONS
**Inheritance:** PR #69 source governance v1 (unmerged) → this stacked PR.

## Step 1: First real, retrievable source references for a scoped service

The first service is **EU / HAIR_COLOR** because hair-colouring ingredients and professional-use warnings are subject to cosmetics product regulation. The discovery catalog `governance/abc_eng05_hair_color_eu_official_references.v1.review.json` references three genuine official published resources (without copying full copyrighted materials):

| Identifier | Source/publisher | Verification URL | Why | Exact state |
|---|---|---|---|---|
| eu-commission-hair-dye-products | European Commission hair dye topic | https://single-market-economy.ec.europa.eu/sectors/cosmetics/cosmetic-products-specific-topics/hair-dye-products_en | Classifies product types and links to relevant EU regulatory materials | REFERENCE_ONLY |
| eu-echa-annex-iii-cosmetic-restrictions | European Chemicals Agency | https://echa.europa.eu/cosmetics-restricted-substances/-/legislationlist/substance/100.023.232 | Locate Annex III substance restrictions; current entry/label must be validated | REFERENCE_ONLY |
| eu-eurlex-cosmetics-regulation | EUR-Lex | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02009R1223-20221006 | Dated EU cosmetics law consolidation requiring current-version cross-check | REFERENCE_ONLY |

The technical authenticity of an official **URL** can be checked. It is not proof that the entire document was fetched and hashed, that the cited legal conditions apply to the proposed individual service, or that full text may be redistributed. Accordingly **raw document SHA=NULL, licence=false, reviewer=false, professional facts released=0**. Latest legal updates and the signed current legal text must be rechecked by a reviewer at actual qualification time.

**Separate credential authority discovery** (not verification of any named person): the EU [regulated-professions database](https://single-market-economy.ec.europa.eu/single-market/services/free-movement-professionals/database-regulated-professions_en) and [German Handwerksordnung](https://www.gesetze-im-internet.de/hwo/BJNR014110953.html) identify how to locate competent bodies/registration requirements. Neither webpage alone verifies a particular specialist's licence.

## Step 2: External credential issuer — code cannot fabricate an authorized issuer

New frozen contract: `governance/abc_eng05_external_issuer_manifest.v1.review.schema.json` / `abc.eng05.external-credential-issuer.v1.review`. The `eng05_external_authority.py` verifier:
- Requires Ed25519 roster signature tied to a **separately provisioned root key and fingerprint**. No trust root is imported from claimant payload, a repository secret, a random ChatGPT-generated key or the public references.
- Independently provisioned **expected issuer ID** must match the signed roster; the SRE-maintained monotonic **minimum accepted roster timestamp** prevents rollback to an earlier signed but now-revoked list. Without external operator control of these values, a test signature proves only cryptographic consistency.
- Checks roster validity, jurisdiction EU, named practitioner, service-specific HAIR_COLOR scope, expiry and revocation list, distinct credential IDs, mandatory verification links, signer public keys.
- Produces ephemeral review-only key anchors for the previously implemented `eng05_professional_sources.adjudicate` signature, conflict and uncertainty evaluator.
- Keeps `professionally_released_facts=[]`, `professional_runtime_authorized=false`, `eng05_to_eng06_dispatch_authorized=false` independently of any cryptographic test result.
- Tests use **disposable, randomly generated CI issuer/specialist keys**, not an actual Handwerkskammer or professional licence issuer. A self-provided root and matching pin can prove only internal consistency, not external real-world authority. Production acceptance requires secure external trust-root enrollment, operating authority checks, approved issuer policy and human reviewers.

## Step 3: PostgreSQL provenance and no-release controls

Migration **0027** adds:

1. `abc.eng05_official_reference_discovery`: immutable metadata/URL bytes, SHA256 and fixed `REFERENCE_ONLY`, with source body not fetched, no redistribution rights, no specialist approval and no engagement authority.
2. `abc.eng05_external_issuer_review_packets`: immutable issuer packet digest, detached signature, public key fingerprint and **false-only** external authority/professional approval/ENG06 flags.

Both use **FORCE RLS, REVOKE ALL** from engine and application roles and the previously proved immutable snapshot trigger. They have no data-read or data-mutation grants to ENG05, ENG06, application gateway or legacy combined Worker. Normal test administrator may insert review snapshots but cannot promote them into authority.

The existing ENG05 review queue, consent/ENG03/ENG04 source fencing, specialist-unverified output, ENG06 `BLOCKED_PENDING_AUTHORITY` status and customer release controls remain unchanged.

## Integration and security tests

- Curated official URLs, allowed HTTPS authorities, and malicious host/user-info/port confusion rejection; rejects attempts to set `expert_verified`, `license_to_copy_verified`, non-NULL raw document hash or dispatch true.
- Valid signed issuer + separately pinned root (CI only), wrong root pin, substituted root, corrupted issuer signature, fake reviewer, revoked/expired credentials, missing credentials, duplicate IDs and unsupported scope.
- A mock issuer + a mock specialist signature may create `REVIEWED_NON_EXECUTABLE` only; it never creates a live professional fact.
- Real disposable PostgreSQL tests enforce source URL-only RLS/immutability and issuer packet no-promotion constraints; 27 versioned checksum-locked migrations, complete W1/W2 fail-closed suite and historical ENG05 local worker tests remain mandatory.

## External requirements NOT met

**There is NO actual practitioner credential or issuer signature, real copyright/redistribution clearance, original-document byte hash or independent specialist SOP acceptance.** A genuinely independently accepted document therefore cannot be claimed. The external path is [Issue #70](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/70) for sourcing, rights confirmation, regulator/competent-authority contact, credentials and specialists. Developer and CI tests do not replace professional review.

**Next acceptance evidence:** actual verified document bytes and rights; one formally scoped specialist (two for safety-critical claims) with current licence checked by a competent authority; **independent pinned issuer root** enrolled by SRE; signed reviewed claims with full citations, contradictions resolved by a professional; review-only end-to-end staging proof under real private identity. Only after independent ADR approvals and safety/quality release gating may a separately reviewed knowledge retrieval adapter be contemplated. ENG06 must remain blocked.

**Explicit non-changes:** `main`, v1/v2 historical source pipeline, ENG05 review worker execution, ENG06 dispatch, paid model APIs, customer imagery, Notion, external managed infrastructure.
