# Adaptive Consultation & Questioning — Phase-01 Product Contract

**Owner:** saleheebrahimi2029-hub organizationally; `ENG-02` delivery and `ENG-03/04/05/06/14` dependencies. **Status:** scope defined; runtime and question accuracy not proven.

## Behavior

On each step: `Intent → known/observed/user-reported/inferred/unknown evidence → service QuestionProfile → hard safety/capability check → value-ranked next question → normalized answer → conflict detection → readiness to recommend`. ABC should ask a *targeted single next question* when required and stop once evidence sufficient for current decision. Missing required safety/chemical history means conditional analysis or professional check, never fabricated facts or false confidence.

Question selection principles: high `DecisionImpact`, `SafetyNecessity`, `UnknownGap`; low `Burden`, `RepeatPenalty`; respect evidence provenance. Rank is qualitative/traceable, not an invented scientific prediction probability. A candidate question skipped because evidence already known stays skipped unless contradiction/confirmation arises.

## Concrete in-salon example: men's haircut

- Style habit: classic tidy / natural texture / styled modern / no fixed style.
- Daily styling budget: 0–5 / 5–10 / 10+ minutes (self-reported, do not infer from image).
- Blow-dry willingness: never / sometimes / regularly.
- Product routine: none / light / frequent.
- Fade/shaved-side tolerance; desired length and change magnitude.
- Return frequency and maintenance preference.
- Specialist observation: current density, growth pattern and condition (human validation where needed).

**Conditional follow-up:** customer says `natural, 5 min, no blow-dry` → avoid default high-upkeep blow-dry-intensive recommendation, ask if gentle sides vs skin-close transition matters. A request for hard skin fade after "avoid scalp visibility" prompts contradiction clarification.

## Service-specific QuestionProfile prototypes

| Family | Decision-critical customer questions | Professional-only/evidence |
|---|---|---|
| Men's haircut and beard | daily style, upkeep time, tools, length/fade preference, beard maintenance | growth pattern, scalp/skin and haircut feasibility |
| Women's haircut/style | usual styling, blow-dry, length, volume/fringe, event, maintenance | density, growth, condition and multi-view |
| Hair color | desired depth/tone, maintenance, desired change, history of dyes and lightening | chemical process history, hair integrity, product suitability |
| Corrective color | current-vs-target conflict, past procedures, staging tolerance | professional technical evaluation and SOP |
| Makeup/bridal | occasion, preferred intensity, finish, durability and product reactions disclosed | hygiene/skin safety, trial and service workflow |
| Nails | length/shape tolerance, hand use, design and material sensitivity history | nail condition, sanitation, material compatibility |
| Keratin/smoothing | target texture, upkeep, prior procedures, product risks | qualified suitability and manufacturer protocol |
| Extensions | target length/volume, maintenance and expected duration | attachment method, existing hair integrity |
| Skin cosmetic advisory | appearance/comfort concerns, desired cosmetic result, daily product use | no diagnosis of skin disease; medical symptoms require referral |
| Complete look | occasion and priority across hair/makeup/nails/style | independent per-service feasibility and combined dependencies |

## State, consent and audit

`QUESTION_PROPOSED → ASKED → ANSWERED | SKIPPED_KNOWN | SKIPPED_IRRELEVANT | NEEDS_PROFESSIONAL_CHECK`. Every response records question ID/version, reason, client/specialist attributed responder, `evidence_class`, answer, relevant service and timestamp. Client's answer isn't OBSERVED hair condition. Contradictions create an explicit targeted follow-up rather than overwriting facts silently.

## Acceptance objectives

- PQ-01: known answer not asked again; changing service refreshes only relevant unknowns.
- PQ-02: realistic contradictory answers lead to a clarification or conservative branch.
- PQ-03: stop when sufficient for *recommendation*, not necessarily for technical *execution*; label unknown requirements.
- PQ-04: no hallucination of hair chemistry, skin condition, medical clearance or guaranteed outcome.
- PQ-05: UI remains readable and participatory on shared screen; specialist can inspect/edit provenance with audit, client cannot access privileged notes.
- PQ-06: six service archetypes at minimum in Golden scenarios, then per-family specialist review.

Test implementation in Phase-05. Question ontology and hard required evidence validated in Phase-02 and by qualified service experts before any risky service release.
