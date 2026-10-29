# ABC Phase 03 — UI/UX design candidate

Owner: saleheebrahimi2029-hub. Base: `1b479453c155b5744ec95e136733cce16a34ae88`.
Work packages: WP-003-01 shared AI Studio; WP-003-02 specialist Technical Plan.
Issue: [#20](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/20).

## Deliverables

- [Design system](DESIGN_SYSTEM.md): layout, tokens, components and interaction rules.
- [Screen/role/contract map](SCREEN_CONTRACT_MAP.json): exact accepted API operation IDs and session states.
- [Requirement coverage](REQUIREMENT_COVERAGE.csv): all 64 baseline requirements, with explicit prototype vs specification-only scope.
- [UX test protocol](UX_TEST_PROTOCOL.md): scenarios, pass evidence and remaining human/device checks.
- [Architecture findings](CONTRACT_FINDINGS.md): downstream inconsistencies surfaced by UI design.
- [Gate disposition](GATE_03.md): evidence-based status; not a product release.
- Executable prototype: `prototypes/phase03/index.html`, `app.mjs`, `model.mjs`, `style.css`.
- Automated tests: `node --test tests/phase03/model.test.mjs`; traceability check: `python scripts/validate_phase03.py`.

## Run
Serve `prototypes/phase03` over HTTP using your normal local development environment. The ES modules require HTTP; opening index.html with file:// is not supported. No installation, API keys, external fonts, network images, live AI, storage of customer data, camera access, upload, payment, booking or messaging are involved. Reload starts a new synthetic session; pause/resume is memory-only and is not durable backend recovery.

## Authority
The authoritative state-machine source is `contracts/v1/state-machines.json`, not older prose aliases. Shared-screen is a display projection, not a separate customer account or trusted API actor. The production backend must authorize the specialist and return a safe projection. The prototype simulates decisions using explicit fixture controls; it cannot establish real authentication, qualification, safety or image quality.

## Visual references
The accepted roadmap refers to six historical reference images but does not provide resolvable image IDs. A targeted Library search returned textual references, not the six images. This candidate uses the specified three-zone layout and a new restrained ivory/forest design; it does not claim pixel fidelity to unseen images. Reference comparison remains an explicit design-review item, not an invented completed check.
