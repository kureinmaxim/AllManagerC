#!/usr/bin/env python3
"""Keep AllManagerC versions consistent. Uses only the Python standard library."""
from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)')
TARGETS = {
    'app_version.py': re.compile(r'^(VERSION\s*=\s*")([^"]+)(")', re.M),
    'AllManagerC.iss': re.compile(r'^(#define MyAppVersion\s+")([^"]+)(")', re.M),
    'README.md': re.compile(r'(https://img\.shields\.io/badge/version-)([^/?]+)(-blue)'),
    'README_ru.md': re.compile(r'(https://img\.shields\.io/badge/version-)([^/?]+)(-blue)'),
}


def validate(version: str) -> str:
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        raise ValueError(f'Invalid version {version!r}; use MAJOR.MINOR.PATCH, e.g. 6.0.2')
    return version


def bumped(version: str, level: str) -> str:
    parts = list(map(int, validate(version).split('.')))
    index = ('major', 'minor', 'patch').index(level)
    parts[index] += 1
    parts[index + 1:] = [0] * (2 - index)
    return '.'.join(map(str, parts))


def read_text(path: Path) -> str:
    with path.open(encoding='utf-8', newline='') as stream:
        return stream.read()


def load_config(root: Path) -> dict:
    config = json.loads(read_text(root / 'config.json'))
    validate(config['app_info']['version'])
    return config


def target_version(name: str, text: str) -> str:
    matches = list(TARGETS[name].finditer(text))
    if len(matches) != 1:
        raise ValueError(f'{name}: expected exactly one version marker, found {len(matches)}')
    return validate(matches[0].group(2))


def status(root: Path) -> bool:
    canonical = load_config(root)['app_info']['version']
    print(f'config.json (source): {canonical}')
    valid = True
    for name in TARGETS:
        try:
            value = target_version(name, read_text(root / name))
            matches = value == canonical
            print(f'{name}: {value} [{"OK" if matches else "MISMATCH"}]')
            valid = valid and matches
        except (OSError, ValueError) as error:
            print(f'{name}: ERROR: {error}')
            valid = False
    return valid


def atomic_write(path: Path, text: str) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='') as stream:
            stream.write(text)
        os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def synchronize(root: Path, version: str | None = None) -> None:
    config = load_config(root)
    old = config['app_info']['version']
    version = validate(version if version is not None else old)
    # Validate every target before changing any file. Never touch databases or .env.
    updates = {}
    for name, pattern in TARGETS.items():
        original = read_text(root / name)
        target_version(name, original)
        changed = pattern.sub(lambda m: m.group(1) + version + m.group(3), original)
        if changed != original:
            updates[root / name] = changed
    if version != old:
        config['app_info'].update(version=version, release_date=date.today().strftime('%d.%m.%Y'),
                                  last_updated=date.today().isoformat())
        updates[root / 'config.json'] = json.dumps(config, ensure_ascii=False, indent=2) + '\n'
    for path, text in updates.items():
        atomic_write(path, text)
        print(f'Updated {path.name}')
    print(f'Version: {version}' + (' (already synchronized)' if not updates else ''))


def main(argv=None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('status', help='Show versions and mismatches')
    check = commands.add_parser('check', help='Exit with status 1 if versions differ')
    check.add_argument('--tag', help='Also verify that the Git tag equals vMAJOR.MINOR.PATCH')
    sync = commands.add_parser('sync', help='Synchronize from config.json or an explicit version')
    sync.add_argument('version', nargs='?')
    bump = commands.add_parser('bump', help='Increment the version and synchronize')
    bump.add_argument('level', choices=('patch', 'minor', 'major'))
    set_version = commands.add_parser('set', help='Set an explicit version and synchronize')
    set_version.add_argument('version')
    args = parser.parse_args(argv)
    try:
        if args.command in ('status', 'check'):
            valid = status(root)
            if args.command == 'check' and args.tag:
                expected = 'v' + load_config(root)['app_info']['version']
                if args.tag != expected:
                    print(f'Tag mismatch: expected {expected}, got {args.tag}', file=sys.stderr)
                    valid = False
            return 1 if args.command == 'check' and not valid else 0
        version = (bumped(load_config(root)['app_info']['version'], args.level)
                   if args.command == 'bump' else args.version)
        synchronize(root, version)
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'Version error: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
