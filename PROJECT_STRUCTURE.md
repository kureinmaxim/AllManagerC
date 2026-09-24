# AllManagerC Project Structure

AllManagerC is a local desktop application for managing AI service accounts and provider credentials. The repository contains the application, packaging workflows, tests, and focused documentation.

## Repository layout

```text
AllManagerC/
├── app.py, run_app.py              # Flask routes and desktop launcher
├── config.json                     # Canonical metadata and non-secret defaults
├── app_version.py                  # Generated version constant
├── ai_services_schema.json         # Data validation schema
├── templates/                      # HTML templates
├── static/                         # CSS, JavaScript, images, icons
├── translations/                   # English and Simplified Chinese catalogs
├── tests/                          # Automated tests
├── scripts/version.py              # Version status, bump, and synchronization
├── build_macos.sh                  # macOS command-line build
├── build_macos.command             # macOS Finder launcher
├── tools/build_macos.py            # macOS app and DMG workflow
├── build_windows.py                # Windows app and installer workflow
├── AllManagerC.iss                 # Inno Setup configuration
├── BUILD_MACOS.md                  # macOS build instructions
├── BUILD_WINDOWS.md                # Windows build instructions
├── DEPLOYMENT.md                   # Installation and runtime notes
├── VERSION_MANAGEMENT.md           # Version and release rules
├── SECURITY.md                     # English security policy
├── SECURITY_ru.md                  # Russian security policy
├── docs/
│   ├── guides/                     # Current YubiKey and security checklists
│   ├── lessons/                    # Historical development lessons
│   └── images/                     # Documentation images
├── build/                          # Temporary build work files
└── dist/                           # Generated installers and latest pointers
```

`data/`, `uploads/`, `.env`, `yubikey_config.json`, and `logs/` may exist during local development. They contain user data or secrets and must never be committed or packaged.

## Runtime data

Packaged builds store data outside the repository:

- macOS: `~/Library/Application Support/AllManagerC`
- Windows: `%APPDATA%\AllManagerC`
- Linux: `~/.local/share/AllManagerC`

The profile contains encrypted service data, its matching Fernet key, YubiKey settings, uploads, and security logs. Keep the encrypted file and its key together when making backups.

## Build outputs

Both platform builders read the version from `config.json` and create a new versioned directory under `dist`.

- macOS exposes the latest successful result as `dist/latest` and the latest app-only result as `dist/latest-app`.
- Windows keeps a copy of the latest successful result in `dist/latest`.
- `--clean` removes old generated results while preserving the latest result.
- `--clean-all` removes every generated result.

Builds include application code and static resources only. Personal profiles, databases, keys, and environment files are excluded. macOS uses a local ad-hoc signature; Windows uses Inno Setup and does not use a commercial certificate by default.

## Version source

`config.json` is the canonical version source. Use the version tool from the repository root:

```bash
python3 scripts/version.py status
python3 scripts/version.py bump patch
python3 scripts/version.py check
```

It synchronizes `app_version.py`, `AllManagerC.iss`, and README version badges. See [VERSION_MANAGEMENT.md](VERSION_MANAGEMENT.md) for release tags and CI checks.

## Documentation map

- [README](README.md): product overview and user quick start.
- [BUILD_MACOS](BUILD_MACOS.md) and [BUILD_WINDOWS](BUILD_WINDOWS.md): packaging.
- [DEPLOYMENT](DEPLOYMENT.md): installation and platform data locations.
- [SECURITY](SECURITY.md): threat model, limitations, and reporting.
- [Authentication](АУТЕНТИФИКАЦИЯ.md): authentication behavior and recovery.
- [YubiKey guide](docs/guides/YUBIKEY_QUICK_START.md): practical YubiKey setup.
- `docs/lessons/`: historical development material; it is not a runtime dependency.

Keep documentation free of real credentials, personal paths, database contents, and machine-specific secrets.
