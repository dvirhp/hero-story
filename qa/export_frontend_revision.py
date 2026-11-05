"""Export a committed Agent 2 frontend revision into ignored QA scratch space.

Read-only with respect to Agent 2's worktree: only `git archive`, `git rev-parse`
and `git status` are run there. No checkout, reset, stash, index or branch
operation is performed. Dependencies are copied from an already-installed QA
snapshot, never downloaded from the network.

Usage:
    python qa/export_frontend_revision.py b09f54b frontend-ux-latest
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

QA_ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("C:/Users/dvir3/storyforge-frontend")
DEPENDENCY_SOURCE = QA_ROOT / "qa/.local/frontend-ux-current/frontend/node_modules"


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=SOURCE)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("ref", help="Commit-ish to export (must be a commit)")
    parser.add_argument("name", help="Directory name under qa/.local")
    args = parser.parse_args()

    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.name):
        raise SystemExit('Snapshot name must be a simple directory name within qa/.local')

    sha = git("rev-parse", "--verify", f"{args.ref}^{{commit}}").decode().strip()
    destination = QA_ROOT / "qa/.local" / args.name
    if not destination.resolve().is_relative_to((QA_ROOT / 'qa/.local').resolve()):
        raise SystemExit('Snapshot destination escapes QA scratch space')
    if destination.exists():
        raise SystemExit(f"{destination} already exists; refusing to overwrite")

    status = git("status", "--porcelain=v1").decode("utf-8", "replace")
    archive = git("archive", "--format=zip", sha, "frontend")
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        for member in bundle.namelist():
            target = (destination / member).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError("Archive path escapes QA snapshot")
            if Path(member).name.startswith(".env"):
                raise ValueError("Environment file in archive; refusing capture")
        bundle.extractall(destination)

    frontend = destination / "frontend"
    copied_files = {
        str(path.relative_to(destination)).replace("\\", "/"):
        hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(frontend.rglob("*"))
        if path.is_file()
    }
    dependency_manifest = {
        str(path.relative_to(DEPENDENCY_SOURCE)).replace("\\", "/"):
        hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(DEPENDENCY_SOURCE.rglob("package.json"))
        if path.is_file() and "node_modules" in path.parts
    }
    manifest = {
        "source": str(SOURCE),
        "ref": args.ref,
        "commit": sha,
        "snapshot_kind": "committed git archive; Agent 2 worktree not modified",
        "worktree_status_at_capture": status.splitlines(),
        "dependency_source": str(DEPENDENCY_SOURCE),
        "dependency_package_json_sha256": dependency_manifest,
        "files_sha256": copied_files,
    }
    (destination / "capture.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    if not DEPENDENCY_SOURCE.is_dir():
        raise SystemExit(f"Missing QA dependency source: {DEPENDENCY_SOURCE}")
    shutil.copytree(DEPENDENCY_SOURCE, frontend / "node_modules")
    print(
        json.dumps(
            {
                "ref": args.ref,
                "commit": sha,
                "destination": str(destination),
                "files": len(copied_files),
                "dirty_worktree_entries_recorded": len(status.splitlines()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
