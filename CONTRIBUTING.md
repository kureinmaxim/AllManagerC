# Contributing to AllManagerC

Small, focused changes are easiest to test and review. Thank you for helping improve
the project.

## Start here

- Check [existing issues](https://github.com/kureinmaxim/AllManagerC/issues) before reporting a bug.
- For vulnerabilities, follow [SECURITY.md](SECURITY.md).
- Follow [README.md](README.md) for setup and build commands.

Use a branch in your own fork and open a pull request against `main`.

## Development

Create a virtual environment for your operating system and install dependencies
using the README instructions. Start the desktop app with `python run_app.py`, using
the Python interpreter from that environment.

Before submitting:

```bash
python -m unittest discover -s tests -v
git diff --check
```

Keep new tests isolated from real user profiles. The existing suite uses temporary
directories and generated records.

Explain the problem, resulting behavior and checks performed in your pull request.
Include screenshots for UI changes using fictional records. State the OS and
architecture tested; identify platforms that have not been checked.

## Scope and data handling

- Keep functional changes and unrelated formatting separate.
- Preserve import and encrypted-data compatibility where possible.
- Update documentation when commands or behavior change.
- Never commit `.env`, real databases, private exports, credentials or local backups.
- Review tracked `config.json` and `yubikey_config.json` before committing.
- Use synthetic data in bug reports, logs and screenshots.

The configuration still reports `5.6.0`; do not reuse an existing release tag for a
different build. Publication is separate from ordinary code review.

## Documentation

The main README and security policy are in English with Russian counterparts.
Detailed operational guides remain in Russian and are labeled accordingly.
Update both language versions where practical.

The [previous Russian contribution guide](CONTRIBUTING_ru.md) is retained as a
historical reference. This English guide describes the current workflow.

## License

Contributions are made under the project's [MIT license](LICENSE).
