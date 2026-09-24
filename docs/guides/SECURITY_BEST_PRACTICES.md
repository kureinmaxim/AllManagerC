# Security Best Practices

AllManagerC is designed for local use. Treat the machine, user account, and application data directory as trusted boundaries.

- Keep `SECRET_KEY`, `FLASK_SECRET_KEY`, `.env`, YubiKey configuration, and encrypted data private.
- Use a separate, random Flask session secret; never reuse a password.
- Keep backups of the encrypted data file and its matching key together.
- Do not commit `data/`, `uploads/`, `logs/`, `.env`, or personal backups.
- Use YubiKey where available and store recovery credentials offline.
- Review the security log after authentication or key-management changes.
- Install releases only from a trusted source and verify the published checksum.
- Keep Python, operating system, and application dependencies updated.
- Report suspected vulnerabilities privately according to [SECURITY.md](../../SECURITY.md).

The root security policy documents the threat model, limitations, and reporting process. This guide is a practical checklist, not a replacement for that policy.
