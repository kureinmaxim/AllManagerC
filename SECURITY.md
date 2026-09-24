# Security policy

Language: **English** · [Русский](SECURITY_ru.md)

AllManagerC is a local desktop application for a trusted computer. This policy
describes the current `main` implementation; it does not claim independent security
certification or support for a public multi-user service.

## Report a vulnerability

Do not include credentials, real databases, exports or exploitation details in a
public issue. Check the repository's [Security page](https://github.com/kureinmaxim/AllManagerC/security).
If **Report a vulnerability** is available, use that private channel. Its availability
is not assumed here. Otherwise, open an issue requesting a private contact method
without disclosing sensitive details.

A private report should include the commit hash, OS, reproduction steps with synthetic
records, expected behavior and likely impact. No dedicated security email, PGP key,
response-time commitment or bounty program has been established.

## Versions and verification

Development takes place on `main`. There is no defined maintenance schedule for older
releases. Configuration still reports `5.6.0` despite subsequent changes; include the
commit hash in reports.

```bash
python -m unittest discover -s tests -v
```

The regression suite uses temporary profiles and synthetic records. It checks selected
data-handling and authentication behaviors, not every vulnerability or dependency.
Physical YubiKey testing and an independent security audit have not been performed
as part of the consolidation.

## Encryption and profile access

Fernet encrypts the database file and selected sensitive fields. Display-only
decrypted account fields are removed before normal persistence. Key rotation
re-encrypts nested credentials, including additional accounts.

- `SECRET_KEY` in `.env` encrypts the database.
- `FLASK_SECRET_KEY` signs Flask sessions and has a different purpose.
- YubiKey configuration and PIN values are stored outside the encrypted database.
- Uploads, including icons and receipts, are ordinary files.
- YubiKey is used for sign-in; it does not store or unlock the Fernet key.

Anyone who can read both the profile and its key can decrypt the records. Logs and
clipboard contents may also contain sensitive information; comprehensive redaction
and automatic clipboard clearing are not guaranteed.

**Full ZIP exports contain the encrypted database, its plaintext key in
`SECRET_KEY.env`, and uploads. The ZIP itself is not password-protected.**

## Known authentication limitations

- If the authentication module fails to initialize or protection is disabled, the
  dynamic request guard permits requests. Some exception paths also continue processing.
- A fallback PIN of `1234` remains in the code. PIN values are stored as plaintext.
- `/secret/login` blocks for 30 seconds after three incorrect attempts. Counters
  are held in memory and reset when the process restarts.
- `/dev_login` has separate PIN lookup logic and no dedicated attempt limit.
  Its reachability depends on the general authentication guard. Changing the
  Secret PIN does not necessarily change the developer-route PIN.
- `DEV_PIN` or `DEVELOPER_PIN` in the environment takes precedence over the configured
  Secret PIN. Changing a PIN in the UI does not change those variables.
- Without `FLASK_SECRET_KEY`, sessions use a known default secret. Exported key files
  also contain a fixed session-secret value; replace it for a new installation.

Online OTP verification uses Yubico. Allowed public IDs restrict which devices may
authenticate. With an empty allowlist, the first successfully verified public ID is
automatically enrolled. Offline static passwords are reusable secrets, not one-time
codes. Network detection determines which validation mode is used.

## Local HTTP boundary

The server listens on `127.0.0.1` with an automatically allocated port and checks the
client address. This does not isolate it from other local processes or replace
protection against web pages interacting with a local service.

There is no shared CSRF-token protection for forms. Responses include
`Access-Control-Allow-Origin: *`. Clipboard and shutdown endpoints are excluded from
the dynamic authentication requirement; shutdown is a GET route.

Do not expose the current application through a public interface, reverse proxy or
tunnel as a secured service. A random port is not an authentication secret.

## Configuration and recovery

1. Restrict operating-system access to the application profile.
2. Set your own fallback PIN and review `DEV_PIN` / `DEVELOPER_PIN`, including the
   separate developer-login behavior.
3. Set a random `FLASK_SECRET_KEY` in the correct profile's `.env`. Generate a value
   with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
4. Configure allowed public IDs and verify sign-in with your own YubiKey.
5. Back up the matching database, key, configuration and uploads. Test restoration
   on a copy and protect full exports as you would plaintext credentials.
6. Use the application's key-rotation workflow after taking a backup. Replacing
   `SECRET_KEY` directly does not re-encrypt an existing database.

These settings do not resolve all code-level limitations described above.

## Builds and Git

The macOS builder packages clean defaults without user databases, `.env` or YubiKey
configuration. The Windows builder still includes the working `config.json`; inspect
it for PINs, absolute paths and private settings before distribution.

Ignored files are not automatically removed from Git history. `config.json` and
`yubikey_config.json` are tracked: review them before committing. Deleting published
credentials in a new commit does not remove earlier copies. Replace exposed secrets;
preserve and re-encrypt data before replacing an encryption key.

The current local macOS build has an ad-hoc signature. Developer ID signing, Apple
notarization and independent security auditing have not been performed. A valid
signature or checksum does not prove the absence of application vulnerabilities.

## Improvements already made

The consolidation protected management of enrolled YubiKey keys when authentication
is enabled, preserved unchanged additional passwords, restored key-management routes,
included nested accounts in key rotation, and retained the packaged macOS profile's
encryption key across restarts.

The environment loader no longer prints `.env` contents or environment secrets.
These are specific fixes, not a claim that all vulnerabilities are resolved.
Historical guides in `docs/legacy/` are not the current security policy.
