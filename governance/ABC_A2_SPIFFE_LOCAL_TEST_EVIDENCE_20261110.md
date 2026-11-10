# ABC A2 — no-cost SPIFFE isolation execution evidence

**Execution date:** 2026-11-10
**Draft review branch:** `audit/a2-spiffe-boundary-isolation-20261110`; parent PR #88, original immutable evidence PR #78
**Result:** **22/22 isolated local Python tests PASS**; GitHub-hosted CI **NOT RUN**; independent acceptance **NOT RECEIVED**

## 1. Execution mode

Executed Python 3.13 `unittest` in a disposable local directory with the repository source files **reconstructed byte-for-byte from the connected GitHub repository**. Their Git blob IDs, computed locally with `git hash-object`, match those returned by GitHub:

| Source / test | Exact verified Git blob SHA |
|---|---|
| `runtime/phase04/abc_foundation/private_api_mtls.py` | `36b36ebf517e1b8ad9291d8a35ae8235118f9100` |
| `runtime/phase04/tests/test_private_api_mtls.py` | `2698d594d6191fd4b8a293e0cd14d7d3b205cf37` |
| `runtime/phase04/tests/test_private_api_network_mtls.py` | `196a7ca66fefaa8b72445e48865066a9370d4d77` |
| `runtime/phase04/abc_foundation/service_mesh_identity.py` | `b6ca5b454e0deea7a2a5e15b4edd79a913b462f7` |
| `runtime/phase04/abc_foundation/eng14_transition_policy.py` | `8ec3909ff731a943e770e35aa5b62ade594b5da2` |

The disposable local environment used a minimal `store.DomainError` substitute; to isolate ENG14 source it also used a **fake WorkflowMachine** with the correct nominal shape and a single synthetic S0 control edge. The two extra probe scripts below are independently written local tests, **not GitHub repository test files**. No actual full checkout, provider-managed CA, PostgreSQL, customer records or deployed mesh was used.

**Command:** `PYTHONPATH=. python -m unittest discover -s tests -p 'test_*.py' -v`

**Observed console:** `Ran 22 tests in 0.568s` / `OK`. **22** individual `... ok` results.
**Raw local log file:** 3113 bytes, SHA256 `1f9c963a9507aa3a35c755b10c89aa01ce2e068e7bc11b078d92cdffe31ba56c`. The raw local log is **not attached to this GitHub commit**; these reported results are an execution summary, not a third-party signed attestation.

## 2. Seven repo-native tests actually executed in isolation

`test_private_api_mtls.py` — 6/6:
1. `test_approved_gateway_socket_remains_accepted`
2. `test_client_certificate_uses_verified_uri_not_cn_or_dns`
3. `test_explicit_exact_client_uri_allowlist`
4. `test_managed_tls_material_required_before_bind`
5. `test_manual_allowlist_cannot_bypass_gateway_namespace`
6. `test_reject_unapproved_client_before_http_dispatch`

`test_private_api_network_mtls.py` — 1/1:
7. `test_real_tls13_rejects_missing_or_wrong_client_identity`

The real TLS1.3 test uses temporary, CA-signed X509 certificates. After each denied client (no cert, unapproved gateway, legacy engine, canonical engine), the server thread remained running and a new approved gateway connection succeeded. The fixture was hardened with KeyUsage, SKI and AKI to satisfy the local OpenSSL strict certificate checks without weakening verification.

## 3. Fifteen additional local-only probes over exact source

**10/10** independently written `BoundEngineIdentity.verify` probes over the exact GitHub source: canonical principal success, forged gateway certificate rejection (canonical and gateway JWT sub), legacy engine cert rejection, wrong single/multiple audiences, wrong consumer, wrong issuer, JWT lifetime >120s, certificate thumbprint mismatch.

**5/5** independently written `ENG14TransitionPolicy` source probes: bounded synthetic S0 specialist success; rejects Gateway SPIFFE URI, legacy engine URI, canonical engine URI and bare `ENG-03` as the human checkpoint actor. These use the explicitly described **mocked workflow graph**, not the production graph/SQL gate.

## 4. Security defect found and corrected

A CA-trusted but unauthorized client URI triggered an uncaught `ValueError` from the HTTP server's `get_request`, terminating `socketserver.serve_forever` in the initial **local** TLS experiment. In the corrected code, the socket closes and `OSError('private_api_peer_rejected')` is raised; `socketserver` handles it and continues accepting legitimate requests. The post-fix TLS test reproduces repeated rejection without loss of service. There is **no claim of exposure in live staging** (none has been attested).

## 5. Mandatory outstanding gates

- The **new native repository tests** in `test_private_engine_mtls.py` and `test_eng14_transition_gate.py` have **not been executed inside the full repository**. The local-only probes above do not count as their CI PASS.
- Full end-to-end JWT/mTLS transport against real engine services, PostgreSQL16 atomic replay, consent/ENG14, compatibility adapters and all existing regression tests require a full source checkout on permitted local hardware or renewed GitHub free compute.
- Architecture owner and independent Security/SRE/qualified specialist must review the exact final commit; no one has signed or ratified ADR-ENG-003/004/005. A green test outcome cannot replace these.
- The parent PR #88 and original PR #78 remain separate; A2's evidence-source allowlist and immutable SHA baseline must be reconciled before any merge.
- **No new paid GitHub Actions, cloud resource, public endpoint, deployment, customer processing or release** was initiated. `A2=OPEN`, `ENG06_RELEASE=BLOCKED`, `ENG07_DISPATCH=BLOCKED`.

**Evidence class:** `ISOLATED_LOCAL_FUNCTIONAL_VALIDATION / UNATTESTED / NOT_CI_OR_STAGING_ACCEPTANCE`.
