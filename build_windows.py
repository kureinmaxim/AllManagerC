import os
import json
import subprocess
from pathlib import Path
import sys
import platform
import argparse
from datetime import datetime
import shutil

# Для корректной работы с кириллицей в Windows
if platform.system() == 'Windows':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

PROJECT_ROOT = Path(__file__).parent.resolve()
DIST_DIR = PROJECT_ROOT / 'dist'
BUILD_DIR = PROJECT_ROOT / 'build'
CONFIG_FILE = PROJECT_ROOT / 'config.json'
ICON_DIR = PROJECT_ROOT / 'static' / 'images'
ICON_ICO = ICON_DIR / 'icon.ico'
ICON_PNG = ICON_DIR / 'ALLc.png'
ICON_ICO_PREFERRED = ICON_DIR / 'icon.ico'

def read_project_version():
    # Version and release dates are managed by scripts/version.py.
    return json.loads(CONFIG_FILE.read_text(encoding='utf-8'))['app_info']['version']

def ensure_icon_ico():
    """Готовит icon.ico: если уже есть static/images/icon.ico — используем; иначе пробуем сгенерировать из ALLc.png."""
    try:
        # Если icon.ico уже существует — ничего не трогаем
        if ICON_ICO.exists():
            print(f"[icons] Найден icon.ico: {ICON_ICO}")
            return True
        # Если рядом лежит предпочтительный файл (тот же путь) — вернёт True выше
        # Иначе генерируем из PNG
        if not ICON_PNG.exists():
            print(f"[icons] PNG иконка не найдена и icon.ico отсутствует: {ICON_PNG}")
            return False
        try:
            from PIL import Image
        except Exception:
            print("[icons] Pillow не установлен. Установите: pip install pillow — чтобы сгенерировать .ico")
            return False
        img = Image.open(ICON_PNG).convert('RGBA')
        sizes = [(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]
        ICON_DIR.mkdir(parents=True, exist_ok=True)
        img.save(ICON_ICO, sizes=sizes)
        print(f"[icons] Создана иконка: {ICON_ICO}")
        return True
    except Exception as e:
        print(f"[icons] Ошибка создания icon.ico: {e}")
        return False

def find_iscc():
    candidates = [os.environ.get('ISCC'), r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe', r'C:\Program Files\Inno Setup 6\ISCC.exe']
    return next((Path(v) for v in candidates if v and Path(v).exists()), None)

def build(args):
    subprocess.run([sys.executable, str(PROJECT_ROOT / 'scripts/version.py'), 'check'], check=True)
    version = read_project_version()
    DIST_DIR.mkdir(exist_ok=True)
    if args.clean_all:
        for item in DIST_DIR.iterdir():
            shutil.rmtree(item) if item.is_dir() and not item.is_symlink() else item.unlink()
        print(f'Cleaned all generated builds from {DIST_DIR}')
        return
    if args.clean:
        keep = (DIST_DIR / 'latest').resolve() if (DIST_DIR / 'latest').is_symlink() else None
        for item in DIST_DIR.iterdir():
            if item.name not in ('latest',) and item.resolve() != keep:
                shutil.rmtree(item) if item.is_dir() and not item.is_symlink() else item.unlink()
        print(f'Cleaned old Windows builds from {DIST_DIR}; latest preserved')
        return
    BUILD_DIR.mkdir(exist_ok=True)
    output = DIST_DIR / f'AllManagerC-{version}-windows-{datetime.now():%Y%m%d-%H%M%S}'
    app_dist = output / 'app'
    app_dist.mkdir(parents=True)

    # Готовим иконку
    # Готовим иконку
    icon_ok = ensure_icon_ico()

    datas = [
        "templates;templates",
        "static;static",
        "translations;translations",
        "config.json;.",
        "ai_services_schema.json;.",
    ]

    hidden = [
        "--hidden-import=flask",
        "--hidden-import=werkzeug",
        "--hidden-import=jinja2",
        "--hidden-import=cryptography",
        "--hidden-import=requests",
        "--hidden-import=webview",
        "--hidden-import=webview.platforms.cef",
        "--hidden-import=webview.platforms.winforms",
        "--hidden-import=webview.platforms.edgechromium",
        "--hidden-import=webview.platforms.edgehtml",
        "--hidden-import=webview.platforms.mshtml",
        "--hidden-import=webview.platforms.qt",
        "--hidden-import=yubico_client",
        "--hidden-import=yubico_client.yubico_exceptions",
        "--exclude-module=PyQt6",
        "--exclude-module=PyQt5",
        "--exclude-module=PySide6",
        "--exclude-module=PySide2",
        "--exclude-module=_tkinter",
        "--exclude-module=tkinter",
        "--exclude-module=tcl",
        "--exclude-module=tk",
    ]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",
        "--windowed",
        "--name=AllManagerC",
        "--noconfirm",
        "--clean",
        f"--distpath={app_dist}",
        f"--workpath={BUILD_DIR / version}",
        "--noupx",
        "--debug=all",
        *[f"--add-data={d}" for d in datas],
        *hidden,
        "app.py"
    ]

    if ICON_ICO.exists() and icon_ok:
        cmd.insert(-1, f"--icon={ICON_ICO}")

    print("Running:", " ".join(map(str, cmd)))
    rc = subprocess.call(cmd)
    if rc != 0:
        raise SystemExit(rc)
    iscc = find_iscc()
    if not iscc:
        raise RuntimeError('Inno Setup 6 not found. Install it or set ISCC to ISCC.exe.')
    subprocess.run([str(iscc), str(PROJECT_ROOT / 'AllManagerC.iss'), f'/DMyAppVersion={version}', f'/DBuildDir={app_dist}', f'/DInstallerDir={output}'], check=True)
    installer = output / f'AllManagerC_Installer_v{version}.exe'
    latest = DIST_DIR / 'latest'
    if latest.exists() or latest.is_symlink():
        latest.unlink() if latest.is_symlink() or latest.is_file() else shutil.rmtree(latest)
    shutil.copytree(output, latest)
    (output / 'build-info.json').write_text(json.dumps({'version': version, 'installer': installer.name, 'built_at': datetime.now().astimezone().isoformat()}, indent=2) + '\n', encoding='utf-8')
    print(f'✅ Build complete. Version: {version}. Output: {output}')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Build AllManagerC for Windows with automatic versioned output.')
    parser.add_argument('--clean', action='store_true')
    parser.add_argument('--clean-all', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        subprocess.run([sys.executable, str(PROJECT_ROOT / 'scripts/version.py'), 'check'], check=True)
        print('Ready for Windows build:', read_project_version())
    else:
        build(args)
