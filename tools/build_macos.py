#!/usr/bin/env python3
"""Build a native macOS app and DMG without deleting earlier builds or bundling user data."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(*args, **kwargs):
    subprocess.run([str(arg) for arg in args], check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=['app', 'dmg', 'all'], default='all')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('Run on macOS.')
    output = (args.output or ROOT / 'dist' / f'macos-{platform.machine()}-{datetime.now():%Y%m%d-%H%M%S}').resolve()
    output.mkdir(parents=True, exist_ok=True)
    app = output / 'AllManagerC.app'
    version = json.loads((ROOT / 'config.json').read_text())['app_info']['version']
    if args.stage in ('app', 'all'):
        if app.exists():
            parser.error('App already exists here. Choose a new output directory.')
        resources = output / 'build-resources'
        resources.mkdir(exist_ok=True)
        # Explicit defaults: never copy user configuration, secrets or data to the app.
        (resources / 'config.json').write_text(json.dumps({
            'app_info': {'version': version, 'developer': 'AI Manager Team'},
            'service_urls': {},
        }, indent=2))
        from PIL import Image
        with Image.open(ROOT / 'static/images/ALLc.png') as icon:
            icon.save(resources / 'AllManagerC.icns', format='ICNS')
        run(sys.executable, '-m', 'PyInstaller', '--windowed', '--onedir',
            '--name=AllManagerC', '--target-arch=arm64',
            '--osx-bundle-identifier=com.allmanagerc.app',
            f'--icon={resources / "AllManagerC.icns"}',
            f'--distpath={output}', f'--workpath={output / "work"}', f'--specpath={resources}',
            f'--add-data={ROOT / "templates"}:templates',
            f'--add-data={ROOT / "static"}:static',
            f'--add-data={ROOT / "translations"}:translations',
            f'--add-data={resources / "config.json"}:.',
            f'--add-data={ROOT / "ai_services_schema.json"}:.',
            '--hidden-import=webview.platforms.cocoa', '--hidden-import=yubico_client',
            '--exclude-module=PyQt5', '--exclude-module=PyQt6',
            '--exclude-module=PySide2', '--exclude-module=PySide6', ROOT / 'app.py', cwd=ROOT)
        run('codesign', '--verify', '--deep', '--strict', app)
        print(f'APP: {app}', flush=True)
    if args.stage in ('dmg', 'all'):
        if not app.is_dir():
            parser.error('Build the app first, using the same --output directory.')
        stage = output / 'dmg-content'
        if stage.exists():
            parser.error('DMG staging directory already exists. Choose a fresh output directory.')
        stage.mkdir()
        run('ditto', app, stage / app.name)
        (stage / 'Applications').symlink_to('/Applications', target_is_directory=True)
        dmg = output / f'AllManagerC_Installer_v{version}_arm64.dmg'
        run('hdiutil', 'create', '-volname', f'AllManagerC {version}', '-srcfolder', stage,
            '-format', 'UDZO', '-fs', 'HFS+', dmg)
        run('hdiutil', 'verify', dmg)
        with dmg.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        dmg.with_suffix('.dmg.sha256').write_text(f'{digest}  {dmg.name}\n')
        print(f'DMG: {dmg}\nSHA256: {digest}', flush=True)


if __name__ == '__main__':
    main()
