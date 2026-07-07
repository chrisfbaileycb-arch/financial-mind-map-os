# Security Policy

## Reporting a vulnerability

Please report suspected vulnerabilities privately by opening a
[GitHub security advisory](https://github.com/chrisfbaileycb-arch/financial-mind-map-os/security/advisories/new)
on this repository. Do not open public issues for security reports. You
should receive an acknowledgement within 7 days.

## Security posture

Financial Mind-Map OS is designed **local-first**:

- **PII hashing** — account identifiers, merchant names, and member
  identifiers are SHA-256 hashed with a local salt (`PII_SALT`) before
  storage. Transaction descriptions are tokenized to safe keywords; digit
  runs (card/account numbers) are stripped before anything is stored.
- **Local storage** — all data lives in a local SQLite file (`FMM_DB_PATH`).
  No financial data is transmitted anywhere by default.
- **Localhost binding** — the API server binds `127.0.0.1` by default and is
  not reachable from other machines unless you explicitly change
  `FMM_API_HOST`.
- **CORS allowlist** — browser origins are restricted to the local UI and
  dev server by default (`FMM_CORS_ORIGINS` to extend).
- **Security headers** — responses set `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, and `Referrer-Policy: same-origin`.
- **Parameterized SQL** — all queries use bound parameters; column names in
  dynamic updates come from fixed allowlists.
- **Input validation** — all write endpoints validate payloads (ISO dates,
  ticker-symbol format, bounded numeric ranges, a size cap on CSV imports).
- **Outbound requests** — the only outbound calls are to the market-data
  provider you explicitly configure (fixed HTTPS hosts, request timeouts);
  with no API key configured the app makes no network requests at all.

## Hard requirements before storing real data

1. **Set a unique `PII_SALT`** in `.env` — the app warns at startup if the
   built-in default is still in place:
   `python -c "import secrets; print(secrets.token_hex(32))"`
2. **Never commit `.env` or `*.db` files** — both are `.gitignore`d; keep it
   that way.
3. **Do not expose the server publicly.** There is currently **no
   authentication layer**; the app is single-user by design. If you must
   reach it remotely, put it behind a VPN or an authenticating reverse
   proxy. A hosted multi-user deployment requires an auth layer first (see
   ROADMAP.md).

## Dependency updates

Run `pip list --outdated` / `npm audit` periodically and keep FastAPI,
uvicorn, and frontend build tooling current.
