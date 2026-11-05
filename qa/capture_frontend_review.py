"""Read-only exports of Agent 2's two reviewed frontend commits.

Writes only inside ignored QA scratch space. No Git index/branch operations on
the source worktree, package installation, env-file copy or source build.
"""
import hashlib
import io
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

QA = Path(__file__).resolve().parents[1]
SOURCE = Path('C:/Users/dvir3/storyforge-frontend')
BASE = '1647d71d7fa83ceec9aace4c72d5b822adc435f5'
CURRENT = 'bd40358aa88c090d012dc0a47c067d5b3bd616de'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=SOURCE)


def capture():
    root = QA / 'qa/.local'
    current, baseline = root / 'frontend-ux-current', root / 'frontend-ux-base'
    if current.exists() or baseline.exists():
        raise SystemExit('Review snapshots already exist; refusing overwrite')
    for ref, destination in ((CURRENT, current), (BASE, baseline)):
        archive = git('archive', '--format=zip', ref, 'frontend')
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            for member in bundle.namelist():
                if Path(member).name.startswith('.env'):
                    raise ValueError('Environment file in archive; refusing capture')
                if not (destination / member).resolve().is_relative_to(destination.resolve()):
                    raise ValueError('Archive path escapes QA snapshot')
            bundle.extractall(destination)
    copied = {str(p.relative_to(current)).replace('\\', '/'):
              hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted((current / 'frontend').rglob('*')) if p.is_file()}
    manifest = {'source': str(SOURCE), 'head': CURRENT, 'status': '', 'files_sha256': copied}
    (current / 'capture.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    for snapshot in (current, baseline):
        shutil.copytree(SOURCE / 'frontend/node_modules', snapshot / 'frontend/node_modules')
    print(json.dumps({'committed_baseline': BASE, 'current_source_head': CURRENT,
                      'current_files': len(copied), 'wip_status': '',
                      'manifest': str(current / 'capture.json')}, indent=2))


if __name__ == '__main__':
    capture()
