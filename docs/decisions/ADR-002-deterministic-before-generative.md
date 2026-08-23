# ADR-002: Deterministic-Before-Generative & Ethical Refusal Gate

## Status
**Accepted & Implemented**

## Context
Deploying Artificial Intelligence in criminal justice carries immense ethical, constitutional, and legal risks. Generative LLMs are prone to hallucinations, confirmation bias, and false assertions of criminality. Furthermore, Indian criminal procedure reserves determination of guilt, innocence, and culpability strictly for the judiciary.

## Decision
1. **Deterministic Processing First:** All entity resolution, similarity scoring, community clustering, and centrality computations are executed through pure deterministic algorithms (Double Metaphone, Jaccard, Louvain, Betweenness Centrality) with mathematical confidence breakdowns.
2. **Strict Architectural Refusal Gate:** The `CopilotService` evaluates user queries against prohibited legal and ethical concepts. Any prompt requesting predictions of guilt, innocence, dangerousness, or recidivism is refused before retrieval or model generation occurs.
3. **Evidence-Grounded Citations:** LLMs are restricted to formatting and summarizing verified graph facts and must attach clickable, structured `GroundedCitation` objects referencing source records.

## Consequences
- **Positive:** Guarantees constitutional alignment, prevents biased automated labeling, and establishes evidentiary trust with law enforcement supervisors.
- **Trade-off:** The system will refuse speculative or open-ended legal advice queries by design.
