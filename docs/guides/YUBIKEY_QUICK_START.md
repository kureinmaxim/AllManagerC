# YubiKey Quick Start

AllManagerC treats YubiKey as an optional second factor. The application remains usable with a strong local fallback only when that fallback is explicitly configured.

## Before you start

1. Keep a backup of the encrypted data file and its matching `SECRET_KEY`.
2. Connect the YubiKey and confirm that the operating system can see it.
3. Open AllManagerC and go to Settings → Authentication.

## Configuration

YubiKey settings are stored in the user data directory, not in the repository. Optional environment variables include:

```text
YUBIKEY_ALLOWED_PUBLIC_IDS=public-id-1,public-id-2
YUBIKEY_STATIC_PASSWORDS=long-random-fallback
```

Use long, unique fallback values and protect the `.env` file. Never commit it, paste it into an issue, or include it in a build artifact.

## Recovery

If the key is unavailable, use a configured fallback and immediately review the authentication settings. Do not replace `SECRET_KEY`: it must remain the key that encrypted the existing data file. Re-enrolling a key does not decrypt or repair a damaged database.

For the complete security model and known limitations, read the repository root [SECURITY.md](../../SECURITY.md).
