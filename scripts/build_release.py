"""Build a GitHub-uploadable source ZIP from an explicit file allowlist."""
import argparse
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = (
    'README.md', 'DEPLOY.md', 'pyproject.toml', 'requirements.txt',
    'requirements-local.txt', 'requirements-dev.txt', 'python_app.py',
    'agent_app.py', 'cloud_agent_app.py', 'task.example.json', 'Dockerfile',
    '.gitignore', '.dockerignore', '.env.example',
    '.streamlit/config.toml', '.streamlit/secrets.example.toml',
    'model_compare/data/aa_snapshot.json', 'model_compare/data/demo_snapshot.json',
    'model_compare/data/snapshot_template.csv',
)


def release_files(root=ROOT):
    files = [root / name for name in ROOT_FILES]
    for pattern in ('model_compare/*.py', 'tests/*.py', 'scripts/*.py', '.github/workflows/*.yml'):
        files.extend(root.glob(pattern))
    missing = [str(p.relative_to(root)) for p in files if not p.is_file()]
    if missing:
        raise ValueError('Missing release files: '+', '.join(missing))
    return sorted(set(files))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT.parent/'model-comparison-apps.zip')
    args = parser.parse_args()
    files = release_files()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(args.output, 'w', ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, Path('model-comparison-apps') / path.relative_to(ROOT))
    print(f'Created {args.output} ({len(files)} files). Private settings, runtime downloads, and environments are excluded.')


if __name__ == '__main__':
    main()
