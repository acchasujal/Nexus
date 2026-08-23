# NEXUS — 3-Minute Live Demonstration Script

> **Scenario:** Inter-state criminal syndicate operating across extortion cells, telecom burner chains, and mule bank accounts.

---

## Live Demonstration Flow (3 Minutes)

```mermaid
journey
    title 3-Minute Live Demonstration Journey
    section 0:00 - 0:30 Ingestion
      Upload FIR, CDR, & Bank Logs: 5: Investigator
      Automatic Normalization: 5: NEXUS
    section 0:30 - 1:10 Entity Resolution
      Disambiguate 'Raju @ Munna': 5: NEXUS
      Explainable Match Breakdown: 5: Investigator
    section 1:10 - 1:50 Syndicate Centrality
      Louvain Community Detection: 5: NEXUS
      Betweenness Centrality isolates Kingpin: 5: Investigator
    section 1:50 - 2:25 Temporal & Provenance
      Scrub Chronological Timeline: 5: Investigator
      Inspect Clickable Edge Evidence: 5: Investigator
    section 2:25 - 3:00 Grounded Copilot
      Query Natural Language Copilot: 5: Investigator
      Verifiable Citations & BSA Dossier: 5: NEXUS
```

### 1. Ingestion & Normalization (0:00 – 0:30)
- **Investigator Narrative:**  
  *"Organized crime rings operate across state boundaries using burner SIMs, mule accounts, and aliases. An investigator receives three disparate data streams: an extortion FIR from Delhi, a CDR dump from a cyber cell in Haryana, and a bank statement from Mumbai."*
- **Action on Screen:**  
  Navigate to the Investigations overview. Open **FIR-2026-0001**, displaying connected accused persons, phone records, and seized physical evidence.

### 2. Multi-Factor Entity Resolution (0:30 – 1:10)
- **Investigator Narrative:**  
  *"Notice the suspect names: 'Vikram Sharma' in the FIR and 'Bikram Sarma' in the bank logs. In standard databases, they exist as disconnected people. NEXUS applies phonetic normalization and matches a shared phone/vehicle, resolving them with 95% confidence."*
- **Action on Screen:**  
  Open **Entity Resolution** tab. Execute search for `Vikram Sharma` (`9845012345`). Click on the resolved match candidate to display the mathematical evidence contribution breakdown.

### 3. Kingpin & Bridge Broker Discovery (1:10 – 1:50)
- **Investigator Narrative:**  
  *"Who coordinates the syndicate? Counting raw phone calls only catches low-level operatives. But when we execute Betweenness Centrality and Community Detection, NEXUS isolates the bridge broker who connects the extortion cell to the cyber hawala ring."*
- **Action on Screen:**  
  Open **Patterns & Communities** and **Network Explorer**. Highlight the two distinct modular communities and the bridge broker connecting them.

### 4. Temporal Intelligence & Evidence Provenance (1:50 – 2:25)
- **Investigator Narrative:**  
  *"To build an airtight legal case, we scrub our chronological timeline slider to watch the syndicate coordinate prior to the offense. Clicking any relationship edge opens the Evidence Provenance Sheet, showing the exact FIR number, CDR call log timestamp, and transaction reference."*
- **Action on Screen:**  
  Open **Timeline & Events**. Scrub across event dates. Open **Evidence Registry** to inspect chain-of-custody metadata.

### 5. Grounded Investigator Copilot (2:25 – 3:00)
- **Investigator Narrative:**  
  *"An investigator asks: 'Show phone and syndicate links connected to case-0001'. The copilot answers strictly from verified graph facts, backed by clickable citations. If an officer asks for an illegal prediction like 'Is suspect X guilty?', the safety refusal gate intercepts and politely refuses."*
- **Action on Screen:**  
  Open **Investigator Copilot**. Query analytical question to see citations. Submit prohibited query (`Is the accused guilty?`) to demonstrate the safety refusal banner.
