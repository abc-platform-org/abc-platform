# Phase-02 Security and Authority Interfaces

## Context model (trusted)
`AuthContext = { actor_user_id, tenant_id, branch_membership_ids, roles, qualified_service_ids, session_auth_level, request_id }`, injected by authentication/middleware, NOT accepted from ordinary client body. Engine calls convey signed or otherwise authenticated principal context, not prompt text.

## Permissions by surface
- `SHARED`: only active session client image, user-facing question and look compare; never show hidden professional notes, unrelated clients or management finance.
- `SPECIALIST_PRIVILEGED`: authenticated specialist, case assignment, service-specific qualification. Step-up or protected presentation on same physical screen before private information.
- `MANAGEMENT`: reception/salon manager/owner operational roles. Distinct from consultant and from actual service qualification.
- `PLATFORM`: narrowly scoped infrastructure; cannot validate a beauty service.
- Client participation in shared UI **does not mint authenticated client permissions**.

## API guard sequence
1. Authenticate actor / derive tenant & allowed branch.
2. Fetch current session row with tenant+branch access policy and optimistic version.
3. Validate purpose-scoped active image consent where media is touched.
4. Validate engine/module policy, service readiness and qualification.
5. Validate JSON Schema and semantic invariants.
6. Authorize transition with expected state version; append outbox event atomically.
7. Enforce result field projection for shared/privileged view and signed media URLs.
8. Audit sanitized outcome without raw client images/secrets.

## Forbidden shortcuts
No tenant from JSON body; no shared professional view switched by frontend-only flag; no business action from model language; no technical plan validation from client preference; no direct CORS/public CDN access to unconsented media; no raw private data in tracing.

## Security contract test families
`SEC-TEN` cross-tenant/session/asset denial; `SEC-ROLE` unauthorized validation/finance action; `SEC-CONSENT` no-media-without-consent and withdrawal; `SEC-SHARED` private note projection / reauth; `SEC-EVENT` forgery/idempotent retry; `SEC-PROVIDER` prompt injection cannot trigger tool action.
