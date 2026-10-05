#!/usr/bin/env python3
"""Fail if host-specific deployments, secrets, or backups enter the public fork."""
import pathlib
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parents[2]
files = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
violations = []
for name in filter(None, files):
    path = pathlib.PurePosixPath(name)
    private = name.startswith("deployments/private/") or path.name == "deployment.env"
    secret_env = path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example")
    sensitive_file = path.suffix in {".dump", ".backup", ".pem", ".key"} or name.endswith(".sql.gz")
    if private or secret_env or sensitive_file:
        violations.append(name)
for context in [root, root / "apps/api"]:
    ignored = (context / ".dockerignore").read_text()
    for pattern in [".env.*", "*.dump", "*.key"]:
        if pattern not in ignored:
            violations.append(f"{context.relative_to(root)}/.dockerignore missing {pattern}")
if violations:
    print("Public/private policy violations (paths only):", *violations, sep="\n", file=sys.stderr)
    sys.exit(1)
print("Public/private deployment boundary checks passed.")
