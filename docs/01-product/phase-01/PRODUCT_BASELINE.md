# ABC Product Baseline — P01-1.0

## Vision
ABC is a `Professional Beauty Design & Decision Workspace` embedded in a `Salon Business OS`. A real salon specialist and a client work **together on the same screen**. The salon specialist controls the session, evaluates feasibility and validates any technical service plan. AI handles evidence-aware consultation, model recommendations, visual design, controlled refinement and conditional planning.

## Four product domains
1. **Core Intelligence:** adaptive questions, evidence provenance, service analysis, grounded knowledge and decision/recommendation.
2. **AI Studio:** Transform, Try On, Compare, Inspiration, LookSpec, Before/After, mask locking, region-aware controls, visual QA, revisions/history, selected look.
3. **Technical Planning:** service feasibility, versioned SOPs/materials, checkpoints, professional validation, conditional stop and handoff.
4. **Salon Business OS:** Home, Global Search, Calendar, Clients, Team, Services, POS, Inventory, Marketing, Analytics, Automations, Reviews, Ask ABC, Notifications, Branches, Settings.

## Primary persona / control
Specialist = salon operator; Client = onsite participant without a remote login or portal; Salon Manager / Reception / Organization Owner / Platform Operator = separately authorized internal roles. Sensitive notes and personal records must not be disclosed to the customer on the shared display. Backend RBAC protects all views.

## Release scope
- **MVP:** limited, qualified service packs (candidate: haircut/styling and men's haircut/beard) with consultation → recommendation → selected look → conditional technical roadmap → specialist validation and minimal Client/Calendar/Team/Service operations. Initial hair-color visual advisory only if visual and safety tests PASS; never infer chemical readiness.
- **V2:** advanced hair color/correction, nails, makeup, skin beauty advisory, keratin/smoothing, extensions, bridal and bundled looks, richer multi-view and business OS. Service activation gated individually by validated SOP/professional review.
- **V3:** scaled multi-branch/multi-tenant international SaaS, billing, operations and localization. Tenant isolation design is MVP infrastructure, not a V3 deferral.

Every service begins `NOT_RELEASED` and each `SPECIFIED → CONTRACTED → IMPLEMENTED → TESTED → PROFESSIONALLY_REVIEWED → RELEASED` transition needs evidence.

## Non-goals
No at-home self-service; no automatic sending looks to customers; no medical diagnosis; no unconditional fidelity/physical execution guarantee; no autonomous chemical recipe or unsupported numbers; no direct AI financial action; no fabricated demo KPIs as real live data.

## Definition of evidence
`SPECIFIED` means written and traceable. `CONTRACTED` means schemas/interaction approved. `IMPLEMENTED` means executable code exists. `TESTED` means run evidence exists. `RELEASED` requires a service-specific qualified Gate. Do not collapse these states.
