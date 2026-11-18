"""Verify the Phase 04 integration source without transferring historical approvals."""

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = "96a19c76b00e74656892fc08f6a3814a683e73d7"
HISTORICAL_PACKET_COMMIT = "7a41f9bc13c0e4ffdbe33561816eae3b86db1823"
HISTORICAL_PACKET = "governance/ABC_A2_SOURCE_BASELINE_CANDIDATE_20261110.json"
AUDIT_WORKFLOW = ".github/workflows/phase04-combined-quality.yml"
AUDIT_WORKFLOW_BLOB = "35e3f6e989c9edb09a2fa800f04e42e44df503bd"
SOURCE_PATHS = ("runtime", "contracts", "prototypes", ".github/workflows")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def verify():
    historical = json.loads(git("show", f"{HISTORICAL_PACKET_COMMIT}:{HISTORICAL_PACKET}"))
    historical_source = historical["candidate_code_commit_sha"]
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", historical_source, CANDIDATE],
        cwd=ROOT, check=True,
    )
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", CANDIDATE, "HEAD"],
        cwd=ROOT, check=True,
    )
    if git("status", "--porcelain", "--untracked-files=all", "--", *SOURCE_PATHS):
        raise SystemExit("Phase 04 source paths contain uncommitted changes")
    drift = git("diff", "--name-only", CANDIDATE, "HEAD", "--", *SOURCE_PATHS)
    if drift != AUDIT_WORKFLOW:
        raise SystemExit(f"Unexpected Phase 04 source changes relative to the candidate:\n{drift}")
    if git("rev-parse", f"HEAD:{AUDIT_WORKFLOW}") != AUDIT_WORKFLOW_BLOB:
        raise SystemExit("Combined quality workflow differs from its reviewed Git blob")

    locks = historical["locked_git_blob_shas"]
    if len(locks) != 17:
        raise SystemExit("Historical A2 packet must contain all 17 source locks")
    updated = {}
    for path, previous_blob in sorted(locks.items()):
        if git("rev-parse", f"{historical_source}:{path}") != previous_blob:
            raise SystemExit(f"Historical A2 blob does not match its original commit: {path}")
        candidate_blob = git("rev-parse", f"{CANDIDATE}:{path}")
        if candidate_blob != previous_blob:
            updated[path] = {"historical_blob": previous_blob, "candidate_blob": candidate_blob}

    return {
        "scope": "SOURCE_PROVENANCE_ONLY",
        "historical_source_commit": historical_source,
        "historical_locks_verified": len(locks),
        "candidate_commit": CANDIDATE,
        "candidate_tree": git("rev-parse", f"{CANDIDATE}^{{tree}}"),
        "checked_working_tree_paths": SOURCE_PATHS,
        "audit_workflow_blob": AUDIT_WORKFLOW_BLOB,
        "changed_historical_locks": updated,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
