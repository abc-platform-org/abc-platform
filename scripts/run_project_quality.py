"""Run the pinned Project Quality Engine against an ABC checkout."""

import argparse
import logging
import os
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

from pqe.config import parse_config
from pqe.orchestrator import RunOptions, run_pipeline

RUNTIME = "runtime/phase04"
STUDIO = "prototypes/abc-ai-studio-v2"
PHASE03 = "prototypes/phase03"
HISTORICAL_A2_VALIDATORS = {
    "validate_a2_closure_packet_v1": "026e1fb174919278e3c2d73442be10b4f11675a4",
    "validate_a2_rebaseline_candidate": "7a41f9bc13c0e4ffdbe33561816eae3b86db1823",
}


def audit_historical_a2(root, name):
    revision = HISTORICAL_A2_VALIDATORS[name]
    subprocess.run(["git", "merge-base", "--is-ancestor", revision, "HEAD"], cwd=root, check=True)
    with tempfile.TemporaryDirectory(prefix="abc-a2-historical-") as temp:
        checkout = Path(temp) / "snapshot"
        subprocess.run(["git", "worktree", "add", "--detach", "--quiet", str(checkout), revision],
                       cwd=root, check=True)
        try:
            print(f"Historical A2 source only: {revision}", flush=True)
            subprocess.run([sys.executable, f"scripts/{name}.py"], cwd=checkout,
                           env=dict(os.environ, GITHUB_ACTIONS="true"), check=True)
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(checkout)], cwd=root, check=True)



def command(name, argv, dimension="BUILD", **options):
    return {"id": name, "title": name.replace("_", " "), "argv": argv,
            "dimension": dimension, "timeout_s": 120, **options}


def build_contract(root):
    config = {
        "project": {"name": "ABC", "goal": "Evidence from design and synthetic runtime checks",
                    "exclude": [".qa/**"]},
        "docs_check": {"files": ["*.md", "docs/**/*.md", "contracts/**/*.md",
                                 "governance/**/*.md", "runtime/**/*.md"]},
        "architecture": {"python_roots": ["scripts"]},
        "pytest": {"enabled": False},
        "commands": [
            command(script.stem, ["python", script.relative_to(root).as_posix()], "INTEGRITY")
            for script in sorted((root / "scripts").glob("validate_*.py"))
            if script.stem not in HISTORICAL_A2_VALIDATORS
        ],
    }
    config["commands"].extend(
        command(
            f"historical_{name}",
            [sys.executable, str(Path(__file__).resolve()), str(root), "--historical-a2", name],
            "INTEGRITY",
        )
        for name in HISTORICAL_A2_VALIDATORS if (root / "scripts" / f"{name}.py").is_file()
    )
    phase03 = (root / PHASE03 / "index.html").is_file()
    if phase03:
        scripts = sorted((root / PHASE03).glob("*.mjs"))
        tests = sorted((root / "tests/phase03").glob("*.test.mjs"))
        config["commands"].extend(
            command("phase03_js_" + script.stem, ["node", "--check", script.relative_to(root).as_posix()])
            for script in scripts
        )
        config["commands"].extend([
            command("phase03_review_build", ["python", "scripts/build_phase03_review.py", "--check"]),
            command("phase03_node_tests", ["node", "--test", *(test.relative_to(root).as_posix()
                                                               for test in tests)], "FUNCTIONAL"),
        ])
    elif (root / STUDIO / "index.html").is_file():
        config["commands"].append(command("studio_js_syntax", ["node", "--check", f"{STUDIO}/app.js"]))

    prototype = PHASE03 if phase03 else STUDIO
    if (root / prototype / "index.html").is_file():
        config["ui"] = {
            "enabled": True, "cwd": prototype, "expect_dir": "rtl", "ready_timeout_s": 15,
            "pages": ["/", "/management.html"] if phase03 else ["/"],
            "start_command": ["python", "-m", "http.server", "{port}", "--bind", "127.0.0.1"],
        }
        config["web"] = {"enabled": True, "seo": False, "lighthouse": False}
    if (root / RUNTIME / "requirements.txt").is_file():
        config["architecture"]["python_roots"].append(RUNTIME)
        config["security"] = {"pip_audit_requirements": [f"{RUNTIME}/requirements.txt"]}
        config["pytest"] = {
            "cwd": RUNTIME, "argv": ["python", "-m", "pytest", "-q", "tests"],
            "env": {"ABC_ENV": "LOCAL_INTEGRATION_ONLY"}, "timeout_s": 420,
        }
        config["commands"].append(command("phase04_compile", ["python", "-m", "compileall", "-q",
                                                               f"{RUNTIME}/abc_foundation"]))
        if (root / "scripts/validate_a2_rebaseline_candidate.py").is_file():
            config["commands"].append(command(
                "a2_candidate_negative_mutations",
                ["python", "scripts/validate_a2_rebaseline_candidate.py", "--self-test"], "INTEGRITY",
            ))
        config["api"] = {
            "enabled": True, "cwd": RUNTIME, "health_path": "/healthz", "ready_timeout_s": 15,
            "start_command": ["python", "-m", "abc_foundation.server"],
            "auth_headers": {"Authorization": "Bearer ${ABC_PQE_TEST_TOKEN}"},
            "temp_dirs": ["ABC_PQE_DB_DIR"],
            "env": {"ABC_ENV": "LOCAL_INTEGRATION_ONLY", "ABC_LISTEN_HOST": "127.0.0.1",
                    "ABC_LISTEN_PORT": "${PQE_PORT}", "ABC_DB_PATH": "${ABC_PQE_DB_DIR}/audit.sqlite"},
            "endpoints": [{"path": "/healthz", "auth": False, "expect": [200], "load_safe": True}],
            "scenarios": [{
                "id": "local-auth-denial", "title": "Consultation cannot start without a valid token",
                "steps": [
                    {"name": "No token", "method": "POST", "path": "/v1/consultations",
                     "auth": False, "json": {}, "expect": [401]},
                    {"name": "Invalid token", "method": "POST", "path": "/v1/consultations",
                     "auth": False, "headers": {"Authorization": "Bearer synthetic.invalid.token"},
                     "json": {}, "expect": [401]},
                ],
            }, {
                "id": "unknown-route-auth-order", "title": "Unknown routes enforce authentication before routing",
                "steps": [
                    {"name": "No token", "path": "/pqe-route-that-does-not-exist",
                     "auth": False, "expect": [401]},
                    {"name": "Invalid token", "path": "/pqe-route-that-does-not-exist",
                     "auth": False, "headers": {"Authorization": "Bearer synthetic.invalid.token"},
                     "expect": [401]},
                    {"name": "Valid synthetic token", "path": "/pqe-route-that-does-not-exist",
                     "auth": True, "expect": [404]},
                ],
            }],
        }
    return config


def configure_local_api_identity(root):
    """Use the target's test-token issuer and a fresh loopback-only signing key."""
    env = dict(os.environ, ABC_LOCAL_TEST_SECRET=secrets.token_urlsafe(36))
    token = subprocess.check_output(
        [sys.executable, "-c",
         "import os; from abc_foundation.auth import mint_test_token; "
         "print(mint_test_token(os.environ['ABC_LOCAL_TEST_SECRET'], "
         "'pqe-specialist', 'pqe-tenant', ['pqe-branch']))"],
        cwd=root / RUNTIME, env=env, text=True,
    ).strip()
    os.environ["ABC_LOCAL_TEST_SECRET"] = env["ABC_LOCAL_TEST_SECRET"]
    os.environ["ABC_PQE_TEST_TOKEN"] = token


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("out", type=Path, nargs="?")
    parser.add_argument("--historical-a2", choices=HISTORICAL_A2_VALIDATORS)
    args = parser.parse_args()
    root = args.checkout.resolve()
    if args.historical_a2:
        audit_historical_a2(root, args.historical_a2)
        return
    if args.out is None:
        parser.error("out is required for a PQE run")
    out = args.out.resolve()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    config = build_contract(root)
    if config.get("api"):
        configure_local_api_identity(root)
    report = run_pipeline(
        parse_config(config, root),
        RunOptions(out_dir=out, extra_report={"abc_target_commit": commit}),
    )
    print(f"ABC {commit}: {report['decision']['decision']} — {out / 'report.md'}")


if __name__ == "__main__":
    main()
