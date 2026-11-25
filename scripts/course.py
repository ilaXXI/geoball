"""Commandes locales du TP DevOps 01 : tests et qualité des deux services."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ("catalog", "quiz")


def run(command, cwd, report=None):
    print(f"\n[{cwd.name}] {' '.join(command)}", flush=True)
    if report is None:
        result = subprocess.run(command, cwd=cwd, check=False)
    else:
        result = subprocess.run(
            command, cwd=cwd, check=False, capture_output=True, text=True, encoding="utf-8"
        )
        report.write_text(result.stdout, encoding="utf-8")
        if report.suffix == ".json":
            for error in json.loads(result.stdout or "[]"):
                location = error["location"]
                print(
                    f"{error['filename']}:{location['row']}:{location['column']}: "
                    f"{error['code']} {error['message']}"
                )
        else:
            print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode:
        raise SystemExit(1)


def test(service):
    report_dir = ROOT / "reports" / service
    report_dir.mkdir(parents=True, exist_ok=True)
    run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests",
            "--import-mode=importlib",
            "-o",
            "pythonpath=.",
            f"--junitxml={report_dir / 'tests.xml'}",
        ],
        ROOT / "services" / service,
    )


def lint(service):
    report_dir = ROOT / "reports" / service
    report_dir.mkdir(parents=True, exist_ok=True)
    cwd = ROOT / "services" / service
    run(
        [sys.executable, "-m", "ruff", "check", "app", "tests", "--output-format=json"],
        cwd,
        report_dir / "ruff.json",
    )
    run(
        [sys.executable, "-m", "ruff", "format", "--check", "app", "tests"],
        cwd,
        report_dir / "format.txt",
    )


def main():
    commands = ["test", "lint", "verify"]
    commands += [f"{action}-{service}" for action in ("test", "lint") for service in SERVICES]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=commands)
    command = parser.parse_args().command
    if "-" in command:
        action, service = command.split("-", 1)
        (test if action == "test" else lint)(service)
        return
    if command in ("test", "verify"):
        for service in SERVICES:
            test(service)
    if command in ("lint", "verify"):
        for service in SERVICES:
            lint(service)


if __name__ == "__main__":
    main()
