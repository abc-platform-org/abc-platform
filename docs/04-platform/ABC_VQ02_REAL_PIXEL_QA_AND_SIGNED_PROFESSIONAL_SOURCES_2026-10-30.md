# ABC VQ-02 — ENG-04 Pixel QA and Professional Source Trust Boundary

**Date:** 2026-10-30. **Status:** implemented offline in draft PR #49; **no production identity verification, inference model or real professional SOP.**  
**Product:** in-salon specialist and client share one screen, with consent-driven evidence and no remote customer workflow.

## What is truly implemented

`eng04_visual_qa.py` decodes actual PNG/JPEG bytes using a pinned image decoder and performs deterministic per-pixel comparisons, masked quantification and source/reference comparisons. `eng04_scoped_visual.py` binds the report to the existing v2 tenant/branch/session/version and requires an independently supplied authenticated media/evidence authority before emitting a scoped report. There is no in-repository authority/key and no real media endpoint.

| Measurement | Implemented metric / hard gate | Exact test outcome |
| --- | --- | --- |
| Allowed edit region | Binary editable PNG (0/255); at least 1 changed pixel **inside**, no more than 85% of image editable | Missing/nonbinary/broad/overlapping masks rejected |
| Locked original pixels | **0 pixel-level RGB changes** outside editable mask | Any change is BLOCKED; even JPEG lossy re-encoding can block |
| Protected face region | Binary separately supplied protected mask; **0 changes** inside | Any protected change is BLOCKED, not an identity recognition approval |
| Reference isolation | SHA256 of normalized source/after/reference pixel arrays; candidate or source **must not exactly copy** a reference; duplicate reference prohibited | Exact copied reference image blocked; perceptual/style leakage still untested |
| Output visual differences | Real measured changed pixel counts, before/after editable mean RGB, **CIE76 delta-E on masked region means** | Quantitative image differences, *not* human realism or hair detection |
| Image quality | 8-bit mean luminance, near-white/black clipping fractions, edge-variance **proxy** | Measured only; no independently approved exposure/blur thresholds |
| Format/resource bounds | PNG/JPEG RGB/L, PNG binary grayscale masks; max 8 MiB each, 2048px per edge, max 2048×2048 pixels, no animation/alpha | Rejected mismatches, corrupt image, oversized and unsupported input |

**Every successful run still yields** `PIXEL_GUARDS_PASSED_REVIEW_REQUIRED`, `visual_qa_status=REQUIRES_REVIEW`, `identity_verified=false`, `face_region_annotation_verified=false`, `professional_approval_verified=false`, `release_approved=false`. This is intentional and non-negotiable. The mask can be forged or incomplete; image pixels alone do not verify who is in the picture. Genuine face detection, identity consistency, hair/skin segmentation, realistic transformation and optical/visual quality require trained models, independently labeled datasets, and expert scoring.

## Consumer and consent gates

Before enabling a real image upload, obtain explicit valid client consent with purpose and retention, immutable ENG03 media evidence records, verified member/tenant/branch/session ownership under ENG01/14, revocation/expiry handling and private encrypted media storage. Media bytes are only passed in-memory to the offline analyzer today; no cloud upload or image persistence is implemented.

The existing ENG04 v2 Recommendation engine still emits **synthetic style specifications**, not actual image generation. The image QA layer cannot transmute generated pixels into valid specialist advice or certify service feasibility.

## ENG05 trusted knowledge content

`professional_sources_v2.py` verifies a detached **Ed25519** signature over the exact immutable source metadata: record reference, type (KNOWLEDGE), service kind, version, **SHA256 of actual content bytes**, authorized reviewer and issuer identifiers, review scope, validity start/end and ACTIVE status. The registry also requires an independently provisioned, current specialist qualification roster, pinned trusted public key and revocation set. Reviewer identity and cryptographic issuer provenance are separate from browser-supplied strings.

`SignedKnowledgePolicyGate` requires both a genuine signed professionally reviewed source and an **independent ENG14 policy verifier** before ENG05 lists even a reviewable recommendation. A source alone cannot bypass BLOCK, critical unknowns, tenant/session restrictions or professional validation. **There are no actual onboarded, independently verified specialist credentials, approved source signatures or paid knowledge APIs in this repository.** All positive signature tests create disposable Ed25519 keys and content in CI only.

Three public **candidate** source URLs are recorded in `governance/professional_source_intake.v1.json`: FDA Hair Dyes, European Commission SCCS Opinions, and NHS Hair Dye Reactions. Identifying an authoritative publication does not mean its content is a salon-specific approved SOP, that any claim has been signed by a specialist, or that it is universally applicable to local regulations or product manufacturers. All are `REVIEW_PENDING` and deliberately excluded from live ENG05 serving.

## ENG06 professional SOP and protocol safety

`SignedSOPConsentGate` independently checks a **signed current SOP record** for the exact service, subject to reviewer qualification, source bytes SHA256, expiry and revocation, AND requires a separate ENG02/ENG05/ENG14 consent + decision + selected-look evidence gate. No valid SOP exists in repo beyond synthetic test fixtures. `eng06_technical_plan_v2.py` therefore blocks real plan creation without external evidence; controlled tests can only produce a **nonprocedural** draft template.

Professional onboarding must supply: approved product-specific current manufacturer instructions, contraindication/risk assessment, verified specialist competency, current client state, recorded consent, service-specific parameter ranges, materials, sequencing, quality checkpoints, stop rules, time/resource plans and aftercare, all versioned and signed. An unapproved AI output must never substitute a professional SOP or execute a treatment.

## Reproducibility and remaining release gates

Tests: `test_eng04_visual_qa_real_pixels.py`, `test_eng04_scoped_real_visual.py`, `test_eng05_06_signed_professional_sources.py`, `test_professional_source_intake_safety.py`; existing v2 contract and real network TLS/PG-clientcert CI remain unchanged.

**Open specialist-grade VQ roadmap:** trusted hair/face segmentation under difficult lighting/occlusion; benchmark identity precision/recall and wrong-person/face confusion; mask IoU against independently labeled truth; ΔE calibration with controlled illumination/ICC; perceptual identity and texture fidelity; reference-style contamination detection; user+specialist blinded A/B plausibility assessment; calibrated p50/p95/p99 latency, mobile/desktop performance and SLO budgets; real consent/security/privacy reviews; approved SOPs and independently signed ENG04/05/06 G01–G10 completion. Do not mark COMPLETE until these are demonstrably passed.

**Engine status:** 0/7 COMPLETE, **release BLOCKED**, protected main and v1 frozen, no paid AI API used.
