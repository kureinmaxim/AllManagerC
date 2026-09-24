# AllManagerC Project Structure

AllManagerC is a local desktop application for securely managing AI service accounts, subscriptions, and provider credentials. The repository contains the application, packaging scripts, tests, and release documentation.

## Top-level layout

```text
AllManagerC/
├── app.py                         # Flask routes and desktop application entry point
├── run_app.py                     # Development launcher
├── config.json                    # Canonical application metadata and non-secret defaults
├── app_version.py                 # Generated version constant
├── ai_services_schema.json        # Service data validation schema
├── translations/                  # English and Simplified Chinese UI catalogs
├── templates/                     # HTML templates
├── static/                        # CSS, JavaScript, images, and the application icon
├── data/                          # Local development data (never commit real data)
├── uploads/                       # Local development uploads (never commit real files)
├── tests/                         # Unit, integration, localization, and startup tests
├── scripts/version.py             # Version status, synchronization, and bump commands
├── build_macos.sh                 # macOS build entry point
├── build_macos.command            # Finder double-click macOS build entry point
├── tools/build_macos.py           # macOS app and DMG builder
├── build_windows.py               # Windows app and installer builder
├── AllManagerC.iss                # Inno Setup configuration
├── BUILD_MACOS.md                 # macOS build instructions
├── BUILD_WINDOWS.md               # Windows build instructions
├── DEPLOYMENT.md                  # Installation and cross-platform operation
├── VERSION_MANAGEMENT.md          # Versioning and release rules
├── SECURITY.md                    # Security policy and limitations
├── SECURITY_ru.md                 # Russian security policy
├── АУТЕНТИФИКАЦИЯ.md              # Authentication details in Russian
└── dist/                          # Generated installers; do not commit
```

## Runtime boundaries

The application stores user data outside the source tree when packaged:

- macOS: `~/Library/Application Support/AllManagerC`
- Windows: `%APPDATA%\AllManagerC`
- Linux: `~/.local/share/AllManagerC`

The data directory contains encrypted service data, the encryption key in `.env`, YubiKey configuration, uploads, and security logs. These files are user-owned and must never be copied into an installer or committed to Git.

## Build boundaries

Build scripts create temporary files under `build/` and versioned output under `dist/`. The latest successful output is exposed as `dist/latest` on macOS and Windows. Old builds can be removed with the platform-specific `--clean` command while preserving the latest result.

The macOS builder creates a signed local `.app` and a DMG. The Windows builder creates a PyInstaller application directory and an Inno Setup installer. Neither build is notarized or code-signed with a commercial certificate by default.

## Version source

`config.json` is the canonical version source. Run the version tool from the repository root:

```bash
python3 scripts/version.py status
python3 scripts/version.py bump patch
python3 scripts/version.py check
```

The tool synchronizes `app_version.py`, `AllManagerC.iss`, and the version badges in both README files. Do not edit generated version markers independently.

## Documentation ownership

Use the focused document for each task:

- `README.md`: product overview and user quick start.
- `BUILD_MACOS.md`: macOS packaging and DMG workflow.
- `BUILD_WINDOWS.md`: Windows packaging and Inno Setup workflow.
- `DEPLOYMENT.md`: installation, runtime locations, and cross-platform notes.
- `SECURITY.md`: security model, limitations, and vulnerability reporting.
- `docs/guides/YUBIKEY_QUICK_START.md`: YubiKey setup reference.
- `VERSION_MANAGEMENT.md`: version synchronization and release tags.

Keep documentation in English unless a file is explicitly marked as a Russian companion. Do not put secrets, real database files, personal backups, or machine-specific paths into documentation.
