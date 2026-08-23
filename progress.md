# CaseClock Progress

Last updated: 2026-07-28

## Current objective

Fix the signed Zoho Catalyst ConvoKraft production webhook while preserving secure, fail-closed signature validation and deterministic CaseClock repository responses.

## Root cause found

The AppSail staging step produced incomplete cryptography dependencies. The deployed tree contained `cryptography` metadata/native files but did not contain the actual `cryptography` package directory. The previous verification was a false positive because it imported the globally installed local package instead of the isolated AppSail staging tree.

The current 503 branch was `ConvoKraftCryptoUnavailable`, confirmed by the fresh AppSail log:

```text
ConvoKraft signature verification requested
ERROR ConvoKraft crypto runtime unavailable
POST ... 503
```

## Changes made

- `backend/predeploy.py`
  - force-reinstalls dependencies into the AppSail root;
  - verifies the complete `cryptography`, `cffi`, and native binding tree;
  - performs isolated `-S` imports and a real DSA sign/verify smoke test.
- `backend/app/appsail_server.py`
  - logs safe startup diagnostics for cryptography runtime availability;
  - does not log keys, signatures, request bodies, or secrets.
- `backend/app/api/convokraft_routes.py`
  - preserves fail-closed validation;
  - supports PEM values containing literal `\\n` sequences;
  - returns controlled responses for missing/invalid keys and unavailable crypto.
- `backend/app-config.json`
  - removed the blank repository `CONVOKRAFT_PUBLIC_KEY` value so the Catalyst Console configuration is not overwritten.
- ConvoKraft regression tests were expanded for valid signatures, invalid/missing signatures, malformed/missing keys, unavailable crypto, and response behavior.

## Security behavior

- Missing signature: `401`.
- Invalid signature: `401`.
- Missing or malformed public key: controlled `503`.
- Missing cryptographic runtime: controlled `503`.
- Valid signed request: proceeds to deterministic action dispatch.
- Secure webhook validation was not disabled.

## Verification completed

- Focused ConvoKraft tests: `10/10` passed.
- Backend suite: `603/603` passed.
- Frontend tests: `38/38` passed.
- Frontend build passed.
- AppSail deployment completed successfully.
- Live `/health`: `200`, service status `ok`.
- Live `/worklist?role=IO`: `200`.
- Live unsigned ConvoKraft request: `401` with `Invalid ConvoKraft signature`.

## Commits and deployment

- `a4e51db` — package ConvoKraft signature verification.
- `acd36ba` — handle ConvoKraft key transport safely.
- `3587e6d` — stage Python 3.11 cryptography wheels.
- `0afb5ae` — verify and force-stage crypto package tree.
- `a40a173` — log AppSail crypto runtime diagnostics.

`HEAD` and `origin/main` currently point to `a40a173`. AppSail deployment succeeded.

## Configuration status

`CONVOKRAFT_PUBLIC_KEY` is configured by the user in Catalyst Console. Its secret contents were not read or logged. The expected representation is the complete PEM public key, including:

```text
-----BEGIN PUBLIC KEY-----
...
-----END PUBLIC KEY-----
```

Multiline PEM values and environment values containing literal `\\n` are supported. A fresh runtime metadata check or real signed request is still required to independently confirm that the key reaches the running AppSail process.

## Remaining verification blocker

The real CaseAssistant request has not yet been reproduced from this environment. Therefore the final `200`, successful signature verification, `case_status_summary` dispatch, deterministic pending-case count, and visible CaseAssistant rendering remain unverified. Do not claim ConvoKraft is fully working until a real signed bot request and fresh logs confirm them.

The separate `/internal/jobs/deadline-sweep -> 401` result remains a `CRON_SECRET` configuration issue and is intentionally unrelated to the ConvoKraft fix.

## Update log

### 2026-07-28

- Created this progress file.
- Recorded the incomplete AppSail cryptography artifact root cause.
- Recorded packaging, runtime diagnostics, security, test, deployment, and live endpoint results.
