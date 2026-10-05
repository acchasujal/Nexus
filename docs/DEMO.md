# NEXUS — 3-Minute Live Demonstration Script

> **Scenario:** Inter-state extortion and cyber-fraud syndicate adapting its network through burner device rotation and cross-border bank layering.

---

## 1. Proactive Demonstration Flow (3 Minutes)

```mermaid
journey
    title 3-Minute Live Demonstration Journey
    section 0:00 - 0:35 Ingestion & Baseline
      Load Disparate Crime Telemetry: 5: Investigator
      Verify SHA-256 Provenance Hashes: 5: NEXUS
    section 0:35 - 1:15 Entity Resolution & Fusion
      Disambiguate 'Vikram' vs 'Bikram': 5: NEXUS
      Investigator Confirms Candidate Match: 5: Investigator
    section 1:15 - 2:00 Network Diff & Network Pulse
      Inject New Batch of CDR & Bank Logs: 5: Investigator
      O(N+E) Network Diff detects Bridge: 5: NEXUS
      Network Pulse alerts on Jurisdiction Shift: 5: Investigator
    section 2:00 - 2:30 Evidence & Early Warning
      Inspect Supports/Conflicts/Missing Badges: 5: Investigator
      Constrained Forecast with Abstention: 5: NEXUS
      Next Best Verification suggests Action: 5: Investigator
    section 2:30 - 3:00 Intelligence Pulse & Copilot
      Dispatch Intelligence Pulse to Mumbai Cell: 5: Investigator
      Copilot Explains Facts with BSA Citations: 5: NEXUS
      Ethical Refusal Gate rejects Guilt Score: 5: NEXUS
```

---

## 2. Minute-by-Minute Demonstration Script

### Minute 0:00 – 0:35: Multi-Source Ingestion & Evidence Provenance
- **Investigator Narrative:**  
  *"Organized criminal networks do not respect district boundaries. In Indian policing, intelligence arrives piecemeal: an extortion FIR in Bengaluru, a CDR dump from a cyber cell in Haryana, and a bank transaction sheet from Mumbai. NEXUS ingests these multi-modal streams and immediately locks every record into an immutable SHA-256 cryptographic chain conforming to Section 63 of the Bharatiya Sakshya Adhiniyam, 2023."*
- **Action on Screen:**  
  1. Navigate to **Investigations** (`/worklist`). Open **FIR-2026-0001**.
  2. Open the **Evidence Drawer**. Click **[Verify Integrity]** to show real-time SHA-256 validation passing with 0 mismatches.

### Minute 0:35 – 1:15: Explainable Entity Resolution & Human Decision
- **Investigator Narrative:**  
  *"Notice the primary suspects: 'Vikram Sharma' in Bengaluru and 'Bikram Sarma' in Mumbai. Traditional databases treat them as separate individuals. NEXUS applies phonetic normalization and matches a shared IMEI and vehicle, resolving them with 95% confidence. But AI does not make the final call—the officer reviews the mathematical breakdown and confirms the merge."*
- **Action on Screen:**  
  1. Open **Entity Fusion** (`/fusion`).
  2. Inspect candidate pair `Vikram Sharma` ↔ `Bikram Sarma`. Show the phonetic and identifier contribution weights.
  3. Click **[Confirm Match]**. Show that the decision is immediately logged in the immutable audit log.

### Minute 1:15 – 2:00: Network Diff & Network Pulse
- **Investigator Narrative:**  
  *"NEXUS does not stop at showing static connections. When new CDR logs or financial transactions arrive, our deterministic Network Diff engine compares graph snapshots in sub-millisecond time. Rather than flooding the officer with hundreds of trivial calls, Network Pulse isolates the emergence of an articulation bridge connecting an extortion cell to a hawala syndicate."*
- **Action on Screen:**  
  1. Navigate to **Network Explorer** (`/network`). Toggle the **Snapshot Diff Overlay**.
  2. Green highlights show newly added relationship edges; dashed borders highlight the newly emerged bridge node.
  3. Show the **Network Pulse** review card flagged with `CRITICAL_REVIEW`.

### Minute 2:00 – 2:30: Evidence Assessment, Early Warning & Abstention
- **Investigator Narrative:**  
  *"How do we know this lead is sound? Our Evidence Assessment engine classifies supporting documentation into SUPPORTS, CONFLICTS, and MISSING. Furthermore, NEXUS features a constrained Early-Warning Engine: it forecasts operational movements like JURISDICTION_SHIFT, but if evidence is contradictory or stale, it explicitly abstains. Next Best Verification immediately recommends the exact legal step required—such as obtaining a Section 94 BNSS subscriber verification."*
- **Action on Screen:**  
  1. Click the Pulse card to display the **Evidence Assessment** panel. Highlight the `SUPPORTS` and `MISSING` badges.
  2. Show the **Early Warning Card** indicating `Target State: JURISDICTION_SHIFT (Action Window: 48h)`.
  3. Demonstrate the **Next Best Verification** recommendation.

### Minute 2:30 – 3:00: Cross-Branch Intelligence Pulse & Refusal Firewall
- **Investigator Narrative:**  
  *"Finally, how do we alert the Mumbai Cyber Cell? NEXUS packages the verified lead into a structured Intelligence Pulse, routing it securely based on RBAC clearance. To interrogate the case, the officer turns to the Grounded Copilot. If an officer asks 'Is the suspect guilty?', our ethical refusal firewall intercepts the query, preserving the constitutional prerogative of the judiciary."*
- **Action on Screen:**  
  1. Click **[Dispatch Intelligence Pulse]** to send the packet to the affected investigation.
  2. Open **Copilot** (`/copilot`). Query: *"Show phone and syndicate links connected to case-0001"*. Show verifiable citations.
  3. Query: *"Is the accused guilty?"*. Show the immediate ethical refusal interceptor explanation.


### Judge first-paint state (2026-10-05)
After authentication, Intelligence Center immediately displays the existing versioned canonical synthetic read-model artifact. Its snapshot contains three pulses and six affected investigations; these are historical demo-baseline values, not confirmed current queue counts. The separate syncing label remains visible until API confirmation. Bootstrap/pulse/Worklist responses replace their own baseline independently; a confirmed API queue can differ from the historical snapshot. Temporary failures never become zero or an empty queue. After bounded retries, the baseline remains explicitly labelled with synchronization paused; a later healthy recovering read coordinates one catch-up request for active exhausted observers. Secondary analytics hydrate only when selected. Login commits its issued session and navigates before analytics requests finish.
