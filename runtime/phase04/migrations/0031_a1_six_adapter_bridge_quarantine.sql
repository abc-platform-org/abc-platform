-- A1 versioned six-adapter bridge. Additive and disabled for operational dispatch.
-- No existing ENG19/ENG06 tables are renamed, dropped, or rewritten.
CREATE TABLE IF NOT EXISTS abc.a1_bridge_registry (
 adapter_id text PRIMARY KEY CHECK (adapter_id IN (
 'A04_TO_06_DECISION_INPUT','A04_TO_07_LOOK_SPEC_INPUT',
 'A05_TO_06_DECISION_EVIDENCE','A06_TO_15_PLAN_CANDIDATE',
 'A04_PIXEL_TO_11_QA_EVIDENCE','A06_SOURCE_TO_16_REVIEW_EVIDENCE')),
 source_protocol text NOT NULL DEFAULT 'abc.internal.engine.v2.draft'
   CHECK (source_protocol='abc.internal.engine.v2.draft'),
 target_protocol text NOT NULL DEFAULT 'abc.internal.capability.v3.review'
   CHECK (target_protocol='abc.internal.capability.v3.review'),
 enabled boolean NOT NULL DEFAULT false CHECK (enabled=false),
 customer_release_approved boolean NOT NULL DEFAULT false CHECK (customer_release_approved=false)
);
INSERT INTO abc.a1_bridge_registry(adapter_id) VALUES
 ('A04_TO_06_DECISION_INPUT'),('A04_TO_07_LOOK_SPEC_INPUT'),
 ('A05_TO_06_DECISION_EVIDENCE'),('A06_TO_15_PLAN_CANDIDATE'),
 ('A04_PIXEL_TO_11_QA_EVIDENCE'),('A06_SOURCE_TO_16_REVIEW_EVIDENCE')
ON CONFLICT (adapter_id) DO NOTHING;
CREATE TABLE IF NOT EXISTS abc.a1_bridge_legacy (
 adapter_id text NOT NULL REFERENCES abc.a1_bridge_registry(adapter_id),
 tenant_id text NOT NULL CHECK (length(tenant_id)>0),
 branch_id text NOT NULL CHECK (length(branch_id)>0),
 session_id text NOT NULL CHECK (length(session_id)>0),
 artifact_id text NOT NULL,
 source_sha256 text NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
 consent_decision_id text NOT NULL CHECK (length(consent_decision_id)>0),
 policy_decision_id text NOT NULL CHECK (length(policy_decision_id)>0),
 source_version text NOT NULL CHECK (source_version='abc.internal.engine.v2.draft'),
 payload jsonb NOT NULL,
 PRIMARY KEY(adapter_id,tenant_id,branch_id,session_id,artifact_id)
);
CREATE TABLE IF NOT EXISTS abc.a1_bridge_shadow (
 adapter_id text NOT NULL REFERENCES abc.a1_bridge_registry(adapter_id),
 tenant_id text NOT NULL,
 branch_id text NOT NULL,
 session_id text NOT NULL,
 artifact_id text NOT NULL,
 source_sha256 text NOT NULL,
 consent_decision_id text NOT NULL,
 policy_decision_id text NOT NULL,
 source_version text NOT NULL CHECK(source_version='abc.internal.engine.v2.draft'),
 target_version text NOT NULL CHECK(target_version='abc.internal.capability.v3.review'),
 payload jsonb NOT NULL,
 dispatch_authorized boolean NOT NULL DEFAULT false CHECK(dispatch_authorized=false),
 customer_release_approved boolean NOT NULL DEFAULT false CHECK(customer_release_approved=false),
 PRIMARY KEY(adapter_id,tenant_id,branch_id,session_id,artifact_id),
 FOREIGN KEY(adapter_id,tenant_id,branch_id,session_id,artifact_id)
 REFERENCES abc.a1_bridge_legacy(adapter_id,tenant_id,branch_id,session_id,artifact_id)
);
ALTER TABLE abc.a1_bridge_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.a1_bridge_registry FORCE ROW LEVEL SECURITY;
ALTER TABLE abc.a1_bridge_legacy ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.a1_bridge_legacy FORCE ROW LEVEL SECURITY;
ALTER TABLE abc.a1_bridge_shadow ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.a1_bridge_shadow FORCE ROW LEVEL SECURITY;
REVOKE ALL ON abc.a1_bridge_registry,abc.a1_bridge_legacy,abc.a1_bridge_shadow FROM PUBLIC;
-- No runtime role is granted access. Migration test runs with ephemeral admin.
