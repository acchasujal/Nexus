# Judge walkthrough

This is a suggested three-minute presentation, not a promise that a sleeping backend wakes within three minutes. Use only the repository's synthetic dataset. Check [current status](../progress.md) and [deployment readiness](DEPLOYMENT.md) before presenting.

## Before the session

- Open the [evaluation deployment](https://nexus-eight-weld-33.vercel.app/login) in a fresh browser.
- Confirm the synthetic demo label, selected officer and snapshot version.
- Check the API health and readiness separately. Neo4j can be degraded while core data remains available.
- Prepare a local native setup using [development instructions](DEVELOPMENT.md) if hosted services are unavailable.
- Do not reset shared deployment data or depend on unverified external integrations during judging.

## 0:00–0:30 — Enter a useful workspace

Choose one of the four officer profiles. With explicit demo mode enabled, selection enters the read-only local demo workspace without waiting for backend login. Show the initial metrics and ten generated worklist rows.

Explain the connection label: **Demo snapshot · Connecting**, **Live data connected**, or **Offline demo**. A local demo role is not server authentication. The versioned snapshot comes from the canonical synthetic artifact; it is not a live queue count.

## 0:30–1:10 — Follow a lead to its evidence

When the server session is available, use the workspace link to enter the full interface. Open an investigation from Worklist and inspect its supporting records. Use the displayed identifiers rather than a memorized case number that may belong to an older fixture.

Show provenance and integrity verification. Explain that a matching digest establishes consistency with the recorded artifact, not the truth of an allegation or automatic legal admissibility.

## 1:10–1:50 — Explain a network change

Open Network Explorer and compare the available before/after snapshots. In Intelligence Center, inspect a Network Pulse and its contributing changes. Distinguish an observed connection, a derived signal and an investigator hypothesis.

**CURRENT / EXTENSION:** graph exploration, deterministic snapshot comparison and pulse review. **NEW PROTOTYPE:** constrained operational early-warning suggestions. No guilt or criminality score is produced.

## 1:50–2:30 — Review evidence gaps and verification

Open the pulse's evidence assessment. Explain supporting, conflicting and missing evidence, then inspect suggested verification actions. Show an abstention example when supported by the active fixture.

An example forecast window or support value is a synthetic rule output, not a calibrated prediction. A suggested verification step is not a completed task or an automatic graph mutation.

## 2:30–3:00 — Demonstrate accountable assistance

Use Grounded Copilot to ask a factual question about the case currently open. Inspect citations and explain the limits of the answer. A request to decide guilt should be refused.

If demonstrating a backend-dependent decision, use an authorized session and verify the actual server response. Never describe an optimistic UI state as a persisted success.

## If connectivity fails

Stay in the usable read-only snapshot and show the truthful offline state. Explain automatic bounded recovery; do not refresh repeatedly or promise a wake-up time. Graph-specific failures should be presented as degraded functionality, not fabricated results.

The local demo snapshot and the full server workspace have different capabilities. See [security](SECURITY.md), [API](API.md) and the [project report](PROJECT_REPORT.md) for boundaries and future work.
