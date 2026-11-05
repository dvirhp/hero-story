"""Export committed components into QA scratch space; never alter their worktrees.

Dependencies are copied from the existing install, never downloaded. The source
commit is pinned; the installed dependency versions must be checked against its
lockfile before interpreting results. Scratch output is intentionally ignored.
"""
import argparse
import io
import shutil
import subprocess
import zipfile
from pathlib import Path

QA_ROOT = Path(__file__).resolve().parents[1]
COMMITS = {
    'frontend': 'c2b72c2d412b9bb7038fd8a9a746614ea5c92a73',
    'diagnostics': '7105be940c4381fcce2d74813681df6afa631474',
}
SOURCE = Path('C:/Users/dvir3/storyforge-frontend/frontend/node_modules')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('component', choices=COMMITS)
    component = parser.parse_args().component
    commit = COMMITS[component]
    destination = QA_ROOT / f'qa/.local/{component}-snapshot'
    if destination.exists():
        raise SystemExit('Snapshot already exists; use a fresh QA scratch path for another revision')
    paths = ['frontend'] if component == 'frontend' else []
    archive = subprocess.run(['git', 'archive', '--format=zip', commit, *paths],
                             cwd=QA_ROOT, capture_output=True, check=True).stdout
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        for name in bundle.namelist():
            target = (destination / name).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError('Archive path escapes snapshot')
        bundle.extractall(destination)
    if component == 'frontend':
        shutil.copytree(SOURCE, destination / 'frontend/node_modules')
    print(f'Committed {component} {commit} exported to {destination}')


if __name__ == '__main__':
    main()
