#!/usr/bin/env python3
"""Build and verify AllManagerC for this Mac; version and output names are automatic."""
import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]


def run(*args, log=None, cwd=ROOT):
    command = [str(arg) for arg in args]
    if log:
        log.write('\n$ ' + ' '.join(command) + '\n')
        log.flush()
    subprocess.run(command, check=True, cwd=cwd, stdout=log,
                   stderr=subprocess.STDOUT if log else None)


def preflight(stage):
    if sys.platform != 'darwin':
        raise ValueError('Run this build on macOS.')
    if platform.machine() not in ('arm64', 'x86_64'):
        raise ValueError('Use a native arm64 or x86_64 Python installation.')
    missing = [tool for tool in ('codesign', 'ditto', 'hdiutil', 'xcode-select') if not shutil.which(tool)]
    if missing:
        raise ValueError('Missing system tools: ' + ', '.join(missing) + '. Run xcode-select --install.')
    subprocess.run(['xcode-select', '-p'], check=True, stdout=subprocess.DEVNULL)
    if stage != 'dmg':
        modules = ('flask', 'requests', 'dotenv', 'cryptography', 'webview', 'yubico_client',
                   'PyInstaller', 'PIL', 'AppKit', 'WebKit')
        missing = [name for name in modules if importlib.util.find_spec(name) is None]
        if missing:
            raise ValueError('Missing Python packages: ' + ', '.join(missing)
                             + '. Install requirements-build-macos.txt with this Python.')
    run(sys.executable, ROOT / 'scripts/version.py', 'check')


def create_output(dist, version, arch):
    dist.mkdir(parents=True, exist_ok=True)
    prefix = f'AllManagerC-{version}-{arch}-{datetime.now():%Y%m%d-%H%M%S}-'
    return Path(tempfile.mkdtemp(prefix=prefix, dir=dist))


def publish_latest(link, output):
    """Update a pointer only after success; never replace a user's real directory."""
    if link.exists() and not link.is_symlink():
        raise ValueError(f'{link} is a real file or directory. Rename it before building.')
    link.parent.mkdir(parents=True, exist_ok=True)
    temporary = link.with_name('.' + link.name + '-' + uuid.uuid4().hex)
    try:
        temporary.symlink_to(os.path.relpath(output, link.parent), target_is_directory=True)
        os.replace(temporary, link)
    finally:
        temporary.unlink(missing_ok=True)


def verify_app(app, version, arch, log=None):
    with (app / 'Contents/Info.plist').open('rb') as stream:
        metadata = plistlib.load(stream)
    if any(metadata.get(key) != version for key in ('CFBundleShortVersionString', 'CFBundleVersion')):
        raise ValueError('The app has a different version. Run a full build again.')
    run('lipo', app / 'Contents/MacOS/AllManagerC', '-verify_arch', arch, log=log)
    run('codesign', '--verify', '--deep', '--strict', app, log=log)


def build_app(output, work, app_info, arch, log):
    resources = work / 'resources'
    resources.mkdir()
    (resources / 'config.json').write_text(json.dumps({
        'app_info': {'version': app_info['version'], 'developer': 'AI Manager Team',
                     'release_date': app_info.get('release_date', '')},
        'service_urls': {},
    }, indent=2), encoding='utf-8')
    from PIL import Image
    with Image.open(ROOT / 'static/images/ALLc.png') as icon:
        icon.save(resources / 'AllManagerC.icns', format='ICNS')
    run(sys.executable, '-m', 'PyInstaller', '--windowed', '--onedir',
        '--name=AllManagerC', f'--target-arch={arch}',
        '--osx-bundle-identifier=com.allmanagerc.app',
        f'--icon={resources / "AllManagerC.icns"}',
        f'--distpath={work / "dist"}', f'--workpath={work / "work"}', f'--specpath={resources}',
        f'--add-data={ROOT / "templates"}:templates',
        f'--add-data={ROOT / "static"}:static',
        f'--add-data={ROOT / "translations"}:translations',
        f'--add-data={resources / "config.json"}:.',
        f'--add-data={ROOT / "ai_services_schema.json"}:.',
        '--hidden-import=webview.platforms.cocoa', '--hidden-import=yubico_client',
        '--hidden-import=localization', '--hidden-import=ui_preferences',
        '--exclude-module=PyQt5', '--exclude-module=PyQt6',
        '--exclude-module=PySide2', '--exclude-module=PySide6', ROOT / 'app.py', log=log)
    app = work / 'dist/AllManagerC.app'
    plist_path = app / 'Contents/Info.plist'
    with plist_path.open('rb') as stream:
        metadata = plistlib.load(stream)
    metadata.update(CFBundleShortVersionString=app_info['version'], CFBundleVersion=app_info['version'])
    with plist_path.open('wb') as stream:
        plistlib.dump(metadata, stream)
    run('codesign', '--force', '--deep', '--sign', '-', app, log=log)
    verify_app(app, app_info['version'], arch, log)
    shutil.move(str(app), output / app.name)


def build_dmg(output, work, version, arch, log):
    app = output / 'AllManagerC.app'
    verify_app(app, version, arch, log)
    name = f'AllManagerC_Installer_v{version}_{arch}.dmg'
    dmg = output / name
    if not dmg.exists():
        stage = work / 'dmg-content'
        stage.mkdir()
        run('ditto', app, stage / app.name, log=log)
        (stage / 'Applications').symlink_to('/Applications', target_is_directory=True)
        temporary = work / name
        run('hdiutil', 'create', '-volname', f'AllManagerC {version}', '-srcfolder', stage,
            '-format', 'UDZO', '-fs', 'HFS+', temporary, log=log)
        run('hdiutil', 'verify', temporary, log=log)
        shutil.move(str(temporary), dmg)
    else:
        run('hdiutil', 'verify', dmg, log=log)
    digest = hashlib.sha256()
    with dmg.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    dmg.with_suffix('.dmg.sha256').write_text(f'{digest.hexdigest()}  {name}\n', encoding='utf-8')
    return dmg, digest.hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=('app', 'dmg', 'all'), default='all')
    parser.add_argument('--output', type=Path, help='Optional output directory; normally chosen automatically')
    parser.add_argument('--check', action='store_true', help='Check the environment and versions without building')
    parser.add_argument('--skip-tests', action='store_true', help='Skip tests for a local diagnostic build')
    parser.add_argument('--open', action='store_true', help='Show the successful build in Finder')
    parser.add_argument('--clean', action='store_true', help='Remove old dist builds and keep the latest successful build')
    parser.add_argument('--clean-all', action='store_true', help='Remove every generated dist build, including latest')
    args = parser.parse_args(argv)
    if args.clean or args.clean_all:
        dist = ROOT / 'dist'
        keep = set()
        if not args.clean_all:
            for pointer_name in ('latest', 'latest-app'):
                pointer = dist / pointer_name
                if pointer.is_symlink() and pointer.exists():
                    keep.add(pointer.resolve())
        removed = 0
        if dist.exists():
            for item in dist.iterdir():
                if item.name == '.DS_Store':
                    item.unlink()
                    removed += 1
                elif item.is_symlink():
                    if args.clean_all or not item.name in ('latest', 'latest-app'):
                        item.unlink()
                        removed += 1
                elif item.is_dir() and item.resolve() not in keep:
                    shutil.rmtree(item)
                    removed += 1
                elif item.is_file():
                    item.unlink()
                    removed += 1
        mode = 'all generated builds' if args.clean_all else 'old builds (latest preserved)'
        print(f'Cleaned {mode} from {dist}: {removed} item(s) removed')
        return 0
    output = None
    try:
        print('[1/4] Checking environment and versions...', flush=True)
        preflight(args.stage)
        app_info = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))['app_info']
        version, arch = app_info['version'], platform.machine()
        if args.check:
            print(f'Ready: AllManagerC {version}, {arch}, Python {platform.python_version()}')
            return 0
        dist = ROOT / 'dist'
        if args.output:
            output = args.output.expanduser().resolve()
        elif args.stage == 'dmg':
            pointer = dist / 'latest-app'
            if not pointer.is_symlink() or not pointer.is_dir():
                raise ValueError('No app to package. Run ./build_macos.sh --stage app first.')
            output = pointer.resolve()
        else:
            output = create_output(dist, version, arch)
        output.mkdir(parents=True, exist_ok=True)
        for name in ('latest', 'latest-app'):
            if (dist / name).exists() and not (dist / name).is_symlink():
                raise ValueError(f'dist/{name} already exists as a real directory; rename it first.')
        if args.stage != 'dmg' and (output / 'AllManagerC.app').exists():
            raise ValueError('Output already contains an app. Omit --output to create a fresh build.')
        scratch = ROOT / 'build/macos'
        scratch.mkdir(parents=True, exist_ok=True)
        with (output / 'build.log').open('a', encoding='utf-8') as log, tempfile.TemporaryDirectory(dir=scratch) as directory:
            work = Path(directory)
            print('[2/4] Running tests...' if not args.skip_tests else '[2/4] Tests skipped by request.', flush=True)
            if not args.skip_tests:
                run(sys.executable, '-m', 'unittest', 'discover', '-s', ROOT / 'tests', '-v', log=log)
            if args.stage != 'dmg':
                print(f'[3/4] Building AllManagerC {version} ({arch})...', flush=True)
                build_app(output, work, app_info, arch, log)
                publish_latest(dist / 'latest-app', output)
            else:
                print('[3/4] Using the previously built app.', flush=True)
            dmg, digest = None, None
            if args.stage != 'app':
                print('[4/4] Packaging and verifying the installer...', flush=True)
                dmg, digest = build_dmg(output, work, version, arch, log)
            else:
                print('[4/4] App ready; DMG deferred.', flush=True)
            manifest = {'version': version, 'architecture': arch,
                        'built_at': datetime.now().astimezone().isoformat(),
                        'app': 'AllManagerC.app', 'dmg': dmg.name if dmg else None,
                        'sha256': digest, 'tests_run': not args.skip_tests}
            (output / 'build-info.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
            if dmg:
                publish_latest(dist / 'latest', output)
        print(f'\nReady: {output}\nApp: {output / "AllManagerC.app"}', flush=True)
        if dmg:
            print(f'Installer: {dmg}\nSHA256: {digest}\nLatest installer: dist/latest')
        if args.open:
            run('open', output)
        return 0
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f'\nBuild failed: {error}', file=sys.stderr)
        if output:
            print(f'Details: {output / "build.log"}', file=sys.stderr)
        print('For hdiutil "Device not configured", allow disk-image access and retry with --stage dmg.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
