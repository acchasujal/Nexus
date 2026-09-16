**NEXUS**

**Unified Product Strategy, Red-Team Review & Implementation Roadmap**

**SIH 2026 • PS 26189 • AI-Powered Criminal Network Analysis System**

Consolidated from current NEXUS project material, PS 26189, related PS 26184, and external law-enforcement/security research

| Decision principle: prioritize capabilities that create measurable investigator value in real-world conditions; reject features that are impressive in a demo but difficult to validate, govern, or operate safely. |
| :---- |

# **Executive Recommendation**

NEXUS should evolve from a strong retrospective criminal-network analysis prototype into a proactive, evidence-grounded intelligence layer. The priority is not more generic AI or more graph algorithms; it is a closed operational loop that detects meaningful network change, identifies evidence-supported emerging signals, explains the evidence, recommends what to verify next, and routes trusted intelligence to the investigation or jurisdiction that may need it.

The current foundation is already substantial: multi-source ingestion, entity resolution, a heterogeneous graph, network/temporal analytics, evidence provenance, SHA-256 integrity, Copilot safety/refusal controls, auditability, RBAC, Neo4j integration and a working investigator workflow. The recommended next phase should make these capabilities act as one system.

# **The Recommended NEXUS Positioning**

| NEXUS \= Proactive, evidence-grounded criminal-network intelligence: observe → connect → detect change → forecast only what is justified → alert → verify → act → learn. |
| :---- |

## **Three headline differentiators**

| USP | What it does | Why it matters | Confidence |
| :---- | :---- | :---- | :---- |
| 1\. Early-Warning Network Intelligence | Detects meaningful changes in observed networks and produces evidence-supported forecasts of the next investigation-relevant state. | Moves NEXUS from retrospective analysis toward time-sensitive investigative intelligence without predicting criminal intent. | HIGH |
| 2\. Digital Shadow \+ Identity/Network Drift | Fuses authorized SOCMINT/digital identifiers with offline evidence to detect identifier changes, emerging relationships and network adaptation. | Adds the missing cyber/digital dimension and helps investigators recognize when a network changes form. | HIGH; governance dependent |
| 3\. Trusted Intelligence Exchange | Combines provenance, SHA-256 integrity, RBAC/audit and future privacy-preserving or permissioned trust mechanisms to move verified intelligence across investigations. | Makes NEXUS useful across jurisdictional boundaries while giving Blockchain & Cybersecurity a real role. | HIGH for architecture; advanced federation is roadmap |

## **Supporting capabilities**

·        Evidence Gap & Contradiction Engine

·        Next Best Verification

·        Network Pulse / Network Change Detection

·        Cross-Branch Intelligence Pulse

·        Case DNA / Investigative Memory

·        Human-in-the-loop Entity Resolution

·        Temporal intelligence and network adaptation detection

·        Selective SHA-256 evidence integrity and optional trust anchoring

# **1\. Red-Team Conclusions**

A serious review should reject feature inflation. A proposed capability is useful only if it improves a real investigator decision, has observable data support, can be evaluated, exposes uncertainty, and can be governed safely.

| Idea | Verdict | Reason |
| :---- | :---- | :---- |
| Person-level future-crime prediction | REJECT | High bias/feedback-loop risk; difficult validation; weak evidentiary semantics. |
| Guilt / criminality probability | REJECT | Conflates analytical evidence with legal judgment. |
| Generic LLM Copilot as USP | REJECT | Chat is common; the differentiator is grounding, evidence and safety. |
| Blockchain for all crime records | REJECT | High overhead and poor fit for sensitive high-volume raw data. |
| Raw social-media scraping as intelligence | REJECT | High noise, attribution, provenance and governance risk. |
| Facial/voice recognition as core feature | DEFER | Large biometric/privacy/validation burden. |
| Generic crime heatmap | KEEP / REPOSITION | Useful but common; combine with network change and temporal intelligence. |
| More graph algorithms | DEPRIORITIZE | Current graph analytics are already strong; more algorithms do not create differentiation. |
| Privacy-preserving deconfliction / PSI | VISION | Potentially differentiated and relevant, but requires rigorous cryptographic implementation. |
| Evidence Gap / Next Best Verification | STRONGLY KEEP | Direct investigator value, explainable and much safer than speculative prediction. |

## **Red-team rule**

For every new AI capability, require answers to: what decision it improves; what data supports it; how false positives/negatives are measured; how uncertainty is shown; who may act; how outputs are independently verified; and what happens when evidence is missing or contradictory.

# **2\. What PS 26184 Teaches NEXUS**

PS 26184 should be treated as an operating-model reference, not a feature template. Its deeper pattern is proactive: predictive analytics → risk localization → real-time alerts → coordinated intervention. NEXUS should transfer that pattern from cyber-fraud withdrawal locations to criminal-network change and investigative state transitions.

| PS 26184 concept | NEXUS adaptation |
| :---- | :---- |
| Predict likely withdrawal location | Forecast an evidence-supported next network/jurisdictional state |
| Risk heatmap | Network Pulse / change map |
| LEA interface | Investigator workspace \+ affected-investigation routing |
| Real-time alerts | Structured Intelligence Pulse with evidence \+ action window |
| Feedback from new complaints/events | Continuous graph/timeline update and forecast refresh |

# **3\. Target Product Architecture**

**1\. Intelligence Fusion** — FIR • CDR • financial • intelligence reports • criminal history • authorized SOCMINT/digital signals

**2\. Identity \+ Knowledge Graph** — Entity resolution • canonical identities • cross-case relationships • communities • paths • influential/bridge positions

**3\. Change \+ Forecast** — Temporal change • network diff • mobility/jurisdiction transition • identity drift • communication/financial transition • network adaptation

**4\. Action** — Early warning • action window • next best verification • structured intelligence pulse • affected investigations

**5\. Trust** — Evidence provenance • SHA-256 integrity • RBAC • audit • selective privacy-preserving exchange • future ledger/Merkle anchoring

Recommended flow: SOURCE DATA → NORMALIZE / EXTRACT → ENTITY RESOLUTION → UNIFIED GRAPH → NETWORK \+ TEMPORAL ANALYTICS → CHANGE DETECTION → EARLY-WARNING ENGINE → EVIDENCE CHECK → INTELLIGENCE PULSE → NEXT BEST VERIFICATION → INVESTIGATOR → AUDIT

# **4\. Capability: Early-Warning Network Intelligence**

This is the hero USP. NEXUS must not predict whether a person will commit a crime. It should detect changes in an already-observed network and forecast only a narrowly defined next investigative-relevant state supported by current evidence.

·        Jurisdiction transition signal — emerging cross-district/cross-state activity supported by temporal, communication, financial or location evidence.

·        Communication-pattern shift — material change from an established communication baseline.

·        Financial-route transition — a new intermediary, recipient path or network relationship.

·        Network restructuring — new bridge, community merge/split, intermediary replacement or new cross-case connection.

·        Identifier drift — correlated changes in phone/device/account/alias/vehicle/digital identifiers.

## **Required forecast object**

| Field | Requirement |
| :---- | :---- |
| Signal | What changed |
| Time window | When it changed / how recent it is |
| Evidence | Exact source records supporting the signal |
| Forecast | Narrowly defined next investigative-relevant state |
| Support level | Interpretable support level; never criminality probability |
| Uncertainty | Conflicts, stale data, missing evidence |
| Action window | Why review may be time-sensitive |
| Suggested verification | Evidence checks; not autonomous enforcement |

| Abstention is a valid outcome. If data is sparse, stale or contradictory, NEXUS should say “Insufficient evidence / no forecast” rather than force a prediction. |
| :---- |

# **5\. Capability: Network Pulse / Network Change Detection**

Upgrade the current hotspot/bridge/pattern views into a temporal change-detection layer.

| Current capability | Target change |
| :---- | :---- |
| Crime concentration | Change in concentration plus contributing network signals |
| Cross-district bridges | New bridge formation and affected investigations |
| Network modules | Community formation/merge/split/change |
| Repeat offender radar | Repeat network presence with temporal context, not guilt scoring |
| Static graph | Before/after network diff |

Network Diff should show: added/removed entities, added/removed relationships, changed communities, new bridge candidates, new jurisdictions, new evidence and affected cases.

# **6\. Capability: Digital Shadow / Authorized SOCMINT Fusion**

PS 26189 explicitly includes social-media intelligence. Add it as a source class into the graph, not as a generic social-media dashboard. Only authorized/public sources should be used, with source, timestamp, capture context and association status preserved.

| Digital signal | Use | Control |
| :---- | :---- | :---- |
| Public username/alias | Candidate identity correlation | Username match is not identity proof |
| Public profile/post | Temporal/location/context signal | Preserve source and capture context |
| Public domain/email/phone | Digital infrastructure relationship | Corroborate independently |
| Crypto address | Financial/network relationship | Ownership remains a separate claim |
| Device/digital indicator | Connect digital and physical network | Authorization \+ provenance |

Recommended association state: Observed → Candidate Link → Corroborated → Investigator Confirmed.

# **7\. Capability: Identity Drift & Network Adaptation Radar**

Detect coordinated changes in identifiers or network infrastructure after a network event without asserting intent.

| Signal | Example | Safe interpretation |
| :---- | :---- | :---- |
| Identifier drift | Phone A disappears; Phone B becomes active in same network context | Observed identifier transition |
| Intermediary replacement | A–B disappears; A–X–B appears | Possible network reconfiguration |
| Jurisdiction shift | Network activity moves district/state | Emerging cross-jurisdiction activity |
| Community adaptation | Known bridge disappears; another bridge forms | Network adaptation signal |

# **8\. Capability: Evidence Gap & Next Best Verification**

Every important candidate or lead should separate supporting evidence, contradictions, missing corroboration and the next verification step.

| Section | Example |
| :---- | :---- |
| Supports | Shared phone • same locality • corroborating account relationship |
| Conflicts | DOB mismatch • timestamp inconsistency |
| Missing | Independent subscriber/KYC source • second location source |
| Next Best Verification | Review subscriber record • inspect transaction chain • verify cross-case timeline |

| Output is a verification plan, not an autonomous order. The investigator remains responsible for the decision. |
| :---- |

# **9\. Capability: Cross-Branch Intelligence Pulse**

Do not claim simple alerts are novel. The differentiation is the evidence-backed signal → affected investigations → structured intelligence packet workflow.

| Alert field | Example |
| :---- | :---- |
| Source branch/case | Mysuru / FIR-141 |
| Affected investigations | Bengaluru / FIR-207, FIR-358 |
| Signal | Emerging cross-district network |
| Observed change | \+3 relationships in 24h |
| Evidence | 5 source references |
| Action window | Active / requires review |
| Verification | Review linked entity \+ current CDR |

# **10\. Capability: Case DNA / Investigative Memory**

Upgrade Similar Cases into explainable structural retrieval across network shape, communication topology, financial paths, locations, temporal sequences and common entities.

·        Network structure similarity

·        Communication topology similarity

·        Financial path similarity

·        Location/jurisdiction similarity

·        Temporal sequence similarity

·        Common entities or identifiers

·        Historical investigations with analogous relationship structures

Never interpret case similarity as guilt or organizational identity. It is a retrieval/prioritization mechanism.

# **11\. Cybersecurity & Blockchain Strategy**

The Blockchain & Cybersecurity theme should be supported by an authentic trust architecture, not blockchain-for-everything.

## **Evidence integrity — current/near-term**

·        Canonicalize evidence deterministically.

·        Compute SHA-256 at or near collection/ingestion.

·        Store the digest in secure integrity storage separate from editable evidence representation.

·        Recompute and verify on demand or at integrity checkpoints.

·        Audit VERIFIED and MISMATCH outcomes.

·        Never overwrite a prior hash after detecting a mismatch.

## **Selective ledger anchoring — target architecture**

Use a permissioned ledger only when independent agencies need a shared trust anchor. Store hashes, commitments, decision/notarization events or Merkle roots—not raw FIRs, CDRs, bank records or PII.

| Use | Avoid |
| :---- | :---- |
| Batch/Merkle commitments | Raw evidence on-chain |
| Integrity/decision events | Every CDR row as a blockchain transaction |
| Permissioned identities | Public cryptocurrency chain by default |
| Sensitive data off-chain | Claiming blockchain creates legal admissibility |

## **Privacy-preserving deconfliction — advanced vision**

A strong future cyber capability is Private Set Intersection: authorized jurisdictions can determine whether private identifier sets overlap without revealing their non-overlapping elements. For production, this requires a vetted PSI/MPC protocol and threat model; never treat a naive hash of a phone number as production PSI.

# **12\. Real-Time & Large-Scale Architecture**

| Layer | Responsibility |
| :---- | :---- |
| Raw evidence/data lake | Large FIR/CDR/financial/digital artifacts, encrypted and access-controlled |
| PostgreSQL | Application state, users, roles, metadata, workflow/audit records as appropriate |
| Neo4j | Durable entity/relationship graph and traversal |
| Graph analytics | Neo4j GDS/equivalent over bounded/projected investigation subgraphs |
| Processing/streaming | Batch \+ incremental ingestion; add queue/stream only when volume requires it |
| Evidence trust | SHA-256 → integrity registry → optional Merkle/ledger anchor |
| Investigator layer | Case, graph, evidence, alerts, verification and Copilot |

Do not perform unrestricted full-graph expensive analytics on every UI request. Use candidate blocking, deterministic identifiers, bounded 2–3 hop queries, incremental graph updates and targeted graph projections.

# **13\. Real-World Evaluation Strategy**

The current synthetic benchmark is useful for regression but cannot establish field accuracy. Every proactive capability must have a temporal evaluation protocol and simple baselines.

| Capability | Recommended evaluation |
| :---- | :---- |
| Entity resolution | Precision/recall/F1, false-merge and false-split rates, data-quality stratification |
| Early warning | Precision@K, recall@K, false-alert rate, lead time, calibration, abstention rate |
| Network change | Detection precision/recall against labeled temporal events |
| SOCMINT correlation | Attribution precision, independent corroboration rate, source-quality stratification |
| Case DNA | Top-K retrieval relevance and expert validation |
| Next Best Verification | Expert-rated usefulness and whether it resolves the uncertainty |
| Integrity | Tamper-detection correctness and zero silent-overwrite rate |

·        Use temporal holdouts for forecasting.

·        Compare complex models against simple baselines.

·        Measure stale/missing/conflicting data performance.

·        Report uncertainty and abstention.

·        Separate synthetic benchmark claims from field claims.

# **14\. Current NEXUS → Recommended Change**

| Current | Change | Outcome |
| :---- | :---- | :---- |
| Static hotspots | Network Pulse \+ change signals | Emerging network view |
| Current-state graph | Network Diff | Investigators see what changed |
| Reactive leads | Early-warning layer | Time-sensitive signals |
| Entity Fusion reasons | Evidence Gap \+ Next Best Verification | Clearer next investigation step |
| FIR/CDR/finance focus | Authorized SOCMINT/digital source class | Digital Shadow |
| Identity matching | Track identifier transitions | Identity Drift / Evasion Radar |
| Cross-case links | Affected-investigation routing | Intelligence Pulse |
| Similar Cases | Explainable Case DNA | Investigative memory |
| SHA-256 | Integrate into evidence UX and audit | Trust Fabric |

# **15\. Priority Roadmap**

| Priority | Work | Reason | Target |
| :---- | :---- | :---- | :---- |
| P0 | Network Diff \+ Network Pulse | Uses existing graph/temporal foundation and makes change operational. | Prototype \+ vision |
| P0 | Evidence Gap \+ Next Best Verification | Highest practical investigator value with low overclaim risk. | Prototype |
| P0 | Early-Warning signal framework with abstention | Creates the main new USP while constraining prediction semantics. | Prototype on validated event data |
| P1 | Intelligence Pulse / affected-investigation routing | Turns signals into operational coordination. | Prototype |
| P1 | Identity Drift / Network Adaptation | Adds cyber-aware proactive intelligence. | Prototype/vision |
| P1 | Digital Shadow/SOCMINT graph schema \+ controlled ingestion | Directly addresses an explicit PS source category. | Vision \+ controlled demo |
| P1 | SHA-256 integrity UX | Strengthens cybersecurity with real implementation. | Prototype |
| P2 | Case DNA | Builds on existing Similar Cases. | Prototype |
| P2 | Selective Merkle/ledger anchoring | Adds meaningful blockchain value without storing raw evidence. | Target/vision |
| P2 | PSI federation | Major differentiation but security-heavy. | Architecture \+ research prototype |
| P3 | Temporal GNN / crypto intelligence / biometrics | High complexity and governance burden. | Future research |

# **16\. Explicitly Reject / Avoid**

·        Person-level future-crime prediction.

·        Guilt or culpability probability.

·        Generic high-risk-suspect labels.

·        Raw investigative data on public blockchains.

·        Naive SHA-256(phone) as production PSI.

·        Private-account scraping or covert social surveillance.

·        Biometric recognition as a core feature without a full governance/evaluation program.

·        Extra algorithms that do not change an investigator decision.

·        Generic chatbot-as-USP.

·        Synthetic benchmark accuracy presented as real-world accuracy.

# **17\. Governance & Safety Requirements**

·        Distinguish observed fact, derived relationship, hypothesis/forecast and investigator decision.

·        Every proactive signal must have traceable evidence.

·        Forecasts must abstain on sparse, stale or contradictory evidence.

·        RBAC must apply to data, alerts, cross-branch propagation and deconfliction.

·        Digital/SOCMINT data needs source, timestamp, authorization context and preservation metadata.

·        Forecast models require drift/false-positive monitoring.

·        No model output should become a self-fulfilling enforcement label.

·        Sensitive actions should be auditable.

# **18\. Recommended End-to-End Investigator Workflow**

| Step | Experience |
| :---- | :---- |
| 1 | Open investigation / Worklist |
| 2 | Inspect Network Pulse and current network |
| 3 | Review entity-resolution candidates |
| 4 | Inspect supporting/conflicting/missing evidence |
| 5 | Confirm/reject/defer relationship |
| 6 | See Network Diff and affected cases |
| 7 | Review Evidence-Grounded Lead / Early Warning |
| 8 | See forecast, evidence, uncertainty and action window |
| 9 | Review Next Best Verification |
| 10 | If relevant, generate Intelligence Pulse |
| 11 | Review authorized digital/SOCMINT signals |
| 12 | Ask Copilot why; trace every citation |
| 13 | Record human decision |
| 14 | Audit trail captures action |
| 15 | New evidence updates the network and refreshes intelligence |

# **19\. Recommended Judge Demo**

·        Start with two investigations that appear disconnected.

·        Show Entity Fusion and conflicting evidence.

·        Confirm identity and show Network Diff.

·        Inject a new time-stamped event and show Network Pulse.

·        Generate an Early-Warning Signal with evidence \+ uncertainty.

·        Show Action Window and Next Best Verification.

·        Send an Intelligence Pulse to the affected investigation/jurisdiction.

·        If available, show an authorized synthetic SOCMINT signal joining the same entity/network.

·        Verify evidence integrity using SHA-256.

·        Ask Copilot why the signal exists; click citations.

·        Finish with audit showing the investigator—not AI—made the decision.

# **20\. PPT Storyline**

| Slide | Message |
| :---- | :---- |
| Problem | Data exists, but relationships, change and time-sensitive intelligence are fragmented. |
| Proposed Solution | NEXUS creates a continuously updating evidence-grounded intelligence graph. |
| USP / Innovation | Early Warning \+ Digital Shadow/Identity Drift \+ Trusted Intelligence Exchange. |
| Technical Approach | Sources → Entity Resolution → Graph → Temporal/Network Analysis → Change Detection → Forecast → Evidence → Intelligence Pulse → Investigator. |
| Impact | Faster discovery, earlier signals, less duplicated analysis, better coordination, auditable decisions. |
| Prototype vs Vision | Clearly distinguish implemented capability from target vision. |

# **21\. Prototype vs Target Vision**

| Area | Current / near-term | Target vision |
| :---- | :---- | :---- |
| Graph | GraphStore \+ Neo4j path | Production Neo4j \+ scalable projections/GDS |
| Entity resolution | Deterministic explainable matching \+ human confirmation | Distributed/candidate-blocked resolution |
| Digital intelligence | Not a major implemented source | Controlled SOCMINT/digital graph fusion |
| Early warning | To be implemented as constrained change/forecast layer | Continuously evaluated operational forecasting |
| Cross-branch exchange | Leads/audit concepts | Structured Intelligence Pulse |
| Privacy federation | Architecture/vision | Vetted PSI/MPC |
| Blockchain | SHA-256 integrity | Selective Merkle/permissioned anchoring |
| Copilot | Grounded investigator interface | Broader controlled/local generative layer after validation |

# **22\. Success Metrics for the Next Version**

·        Median time from new evidence arrival to investigator-ready signal.

·        False-alert rate and precision@K for early-warning signals.

·        Lead time gained before a transition becomes retrospectively obvious.

·        Percentage of leads with at least two independent supporting sources.

·        Percentage of leads for which Next Best Verification resolves an evidence gap.

·        Cross-case discovery rate for validated new links.

·        Percentage of analytical claims with source provenance.

·        Integrity mismatch detection rate.

·        Cross-branch alert delivery/acknowledgement latency.

·        Investigator usefulness rating.

# **23\. Final Recommendation**

| Do not turn NEXUS into a collection of AI demos. Turn it into a closed intelligence loop. |
| :---- |

The winning version is not the one with the most algorithms. It is the one that makes an investigator measurably faster and more informed at the moment a case changes.

Recommended product evolution: Reactive analysis → Continuous network change detection → Evidence-grounded early warning → Trusted intelligence propagation → Human verification/action → Auditable feedback.

The system should forecast network/operational states, not criminal intent; identify verification needs, not issue autonomous orders; and use cybersecurity controls to make intelligence trustworthy rather than adding blockchain as decoration.

# **24\. External Research References**

**MHA — CCTNS / ICJS —** [https://www.mha.gov.in/en/divisionofmha/women-safety-division/cctns](https://www.mha.gov.in/en/divisionofmha/women-safety-division/cctns)

**MHA — ICJS overview —** [https://www.mha.gov.in/en/commoncontent/inter-operable-criminal-justice-system-icjs](https://www.mha.gov.in/en/commoncontent/inter-operable-criminal-justice-system-icjs)

**INTERPOL — Criminal intelligence analysis —** [https://www.interpol.int/How-we-work/Criminal-intelligence-analysis](https://www.interpol.int/How-we-work/Criminal-intelligence-analysis)

**INTERPOL — Project INSIGHT —** [https://www.interpol.int/How-we-work/Criminal-intelligence-analysis/Projects/Project-INSIGHT](https://www.interpol.int/How-we-work/Criminal-intelligence-analysis/Projects/Project-INSIGHT)

**INTERPOL — Fugitive investigative support —** [https://www.interpol.int/How-we-work/Fugitive-investigative-support](https://www.interpol.int/How-we-work/Fugitive-investigative-support)

**INTERPOL — ROXANNE —** [https://www.interpol.int/en/Who-we-are/Legal-framework/Information-communications-and-technology-ICT-law-projects/Completed-ICT-law-projects/ROXANNE-Project](https://www.interpol.int/en/Who-we-are/Legal-framework/Information-communications-and-technology-ICT-law-projects/Completed-ICT-law-projects/ROXANNE-Project)

**Europol — QUEST / operational information services —** [https://www.europol.europa.eu/how-we-work/services-support/operational-information-services](https://www.europol.europa.eu/how-we-work/services-support/operational-information-services)

**Europol — SIENA —** [https://www.europol.europa.eu/how-we-work/services-support/siena](https://www.europol.europa.eu/how-we-work/services-support/siena)

**Europol — Large File Exchange —** [https://www.europol.europa.eu/how-we-work/services-support/siena/LFE](https://www.europol.europa.eu/how-we-work/services-support/siena/LFE)

**UK ACE — Prometheus —** [https://www.gov.uk/government/case-studies/ace-delivers-prometheus-as-a-scalable-capability-for-policing](https://www.gov.uk/government/case-studies/ace-delivers-prometheus-as-a-scalable-capability-for-policing)

**NIST — AI Risk Management Framework —** [https://www.nist.gov/itl/ai-risk-management-framework](https://www.nist.gov/itl/ai-risk-management-framework)

**NIST — Digital Evidence Preservation —** [https://www.nist.gov/publications/digital-evidence-preservation-considerations-evidence-handlers](https://www.nist.gov/publications/digital-evidence-preservation-considerations-evidence-handlers)

**NIST — Private Set Intersection —** [https://csrc.nist.gov/Projects/pec/psi](https://csrc.nist.gov/Projects/pec/psi)

# **25\. Scope Boundary**

This report combines current project/source material with external official research. Items labelled target vision, future, or research direction are proposals, not claims about what the current prototype already implements. Implementation should follow the priority roadmap and evidence/evaluation rules above.
