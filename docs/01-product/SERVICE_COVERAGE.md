# Service Coverage & Service-Pack Contracts

Every service receives a `ServicePack` with fields: `service_id`, `ontology_version`, `question_profile`, `analysis_attributes`, `decision_rules`, `visual_capability`, `mask_policy`, `qa_suite`, `safety_tier`, `required_evidence`, `sop_reference`, `professional_validator_role`, `salon_capability`, `release_state`.

## Canonical families in target product

| Family | Scope | Notes |
|---|---|---|
| Haircut / Hair Styling | women's cuts, men's cuts, layers, fringe, texture, blowdry, formal styling | Geometry changes; multiple views may be needed |
| Hair Color | base, roots, grey coverage, highlights/lowlights, balayage, ombre/sombre, toning | Chemical history must not be inferred from image |
| Corrective Color | color correction and multi-stage planning | Controlled; validated SOP and specialized safety gate |
| Makeup | natural, glam, corrective visual styling, bridal | No allergy/skin diagnosis |
| Nails | color, length, shape, art, extensions/build | Material suitability requires real checks |
| Men's Grooming | haircut, beard, moustache, fade/taper, styling, grey blending | Hair/beard region masks separate |
| Extensions | hair extension, length/volume objectives | Technical and safety conditions |
| Keratin / Smoothing | chemical treatments and aftercare advisory | SOP, chemical product documentation required |
| Bridal / Complete Look | composite hair/makeup/nails/style | Per-region versioning and QA |
| Skin / Facial Beauty Advisory | cosmetic appearance and makeup preparation | NO medical diagnosis or clinical clearance |
| Service Bundles | coherent multi-service combinations | Independent approval for each component |

## Release state

`SPECIFIED → CONTRACTED → IMPLEMENTED → TESTED → PROFESSIONALLY_REVIEWED → RELEASED`. Each family may progress at a different speed. MVP release is limited to families with evidence and gate PASS. Other services must remain visible as planned or advisory-only, never as executable without approval.

## Minimum gate per pack

Question coverage, visual mask + QA coverage, recommendation acceptance, feasibility and safety scenarios, expert review, SOP integrity, shared-screen UX, operational service mapping, regression result.
