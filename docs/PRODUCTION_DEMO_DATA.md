# NEXUS Production Demo Dataset & Seed Protocol

> **Target:** Smart India Hackathon 2026 (PS 26189) — AI-Powered Criminal Network Analysis System  
> **Client:** Ministry of Home Affairs (MHA) / National Crime Records Bureau (NCRB)  
> **Dataset Classification:** 100% Synthetic Ground-Truth Intelligence Fixture (Zero Real Citizen PII)  

---

## 1. What Data is Required

For an end-to-end evaluation by judges, NEXUS requires an integrated multi-relational intelligence graph comprising:
- **Case Records:** 50 multi-jurisdictional FIRs across Bengaluru, Mysuru, Hubballi, and Mangaluru.
- **Accused & Suspect Entities:** 120 resolved persons with phonetic aliases, Aadhaar tokens, and case associations.
- **Telecom Intelligence:** 150 phones with Call Detail Record (CDR) frequency weights, tower locations, and IMEI linkages.
- **Financial Accounts:** 60 bank accounts with transaction flows, IFSC codes, and transaction velocity logs.
- **Intelligence Reports:** 15 multi-agency informant notes with Section 63 BSA evidence provenance hashes.
- **Cross-Case Identity Candidates:** Explicit resolution pairs spanning independent case files (e.g. Rafiq Khan [CASE-141] ↔ Rafiq Ahmed [CASE-207]).

---

## 2. Where the Data Comes From

The ground-truth synthetic data is generated deterministically by [`synthetic_data/nexus_generator.py`](file:///d:/Projects/CaseClock/synthetic_data/nexus_generator.py) and serialized to:
- [`artifacts/nexus_graph/nexus_graph.json`](file:///d:/Projects/CaseClock/artifacts/nexus_graph/nexus_graph.json) (Checksum: `cc523c3c26bab78e...`)

---

## 3. How to Seed the Production Database

NEXUS does **not** rely on the developer's laptop. On deployment or reset, run:

```bash
python scripts/seed_production_demo.py
```

### Dry-run validation only:
```bash
python scripts/seed_production_demo.py --dry-run
```

---

## 4. How to Reset Demo State During Live Demonstration

In the NEXUS UI:
1. Navigate to **Settings** (`/settings`).
2. Click **Reset Demo Fixture**.
3. The in-memory graph, candidate decisions, and lead triage state immediately revert to the clean evaluation state without server restart.

Alternatively, via API:
```bash
curl -X POST https://<your-nexus-backend-url>/api/v1/nexus/reset
```

---

## 5. Non-PII & Ethical Compliance Verification

- All Aadhaar numbers use dummy sequences (e.g., `XXXX-XXXX-1234`).
- All names and phone numbers are generated using synthetic name distributions.
- Zero judicial guilt predictions are computed or stored.
