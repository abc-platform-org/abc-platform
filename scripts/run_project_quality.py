"""Run the pinned Project Quality Engine against an ABC checkout."""

import argparse
import logging
import subprocess
from pathlib import Path

from pqe.config import parse_config
from pqe.orchestrator import RunOptions, run_pipeline

RUNTIME = "runtime/phase04"
STUDIO = "prototypes/abc-ai-studio-v2"
PHASE03 = "prototypes/phase03"


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
        ],
    }
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
            "generate_secrets": ["ABC_LOCAL_TEST_SECRET"], "temp_dirs": ["ABC_PQE_DB_DIR"],
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
            }],
        }
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    root = args.checkout.resolve()
    out = args.out.resolve()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    report = run_pipeline(
        parse_config(build_contract(root), root),
        RunOptions(out_dir=out, extra_report={"abc_target_commit": commit}),
    )
    print(f"ABC {commit}: {report['decision']['decision']} — {out / 'report.md'}")


if __name__ == "__main__":
    main()
