# ADR-004: Synthetic Multi-Modal Intelligence Corpus Strategy

## Status
**Accepted & Implemented**

## Context
Real police First Information Reports, Call Detail Records, and bank ledgers are legally protected classified materials under Indian privacy statutes (including the Digital Personal Data Protection Act, 2023). Deploying real citizen records in a hackathon prototype or public repository is legally and ethically unacceptable. However, benchmarking Entity Resolution and graph algorithms requires realistic complexity (misspellings, aliases, burner phones, layering transactions, planted communities).

## Decision
NEXUS implements a deterministic synthetic dataset generator ([`synthetic_data/nexus_generator.py`](file:///d:/Projects/CaseClock/synthetic_data/nexus_generator.py)):
1. **Realistic Structure:** Generates 50 cases, 120 persons, 150 phone numbers, 60 bank accounts, 445 nodes, and 530 relationships mimicking Indian CCTNS and CDR patterns.
2. **Planted Ground Truth:** Embeds known target alias pairs, community rings, bridge brokers, and transaction chains in [`artifacts/nexus_graph/ground_truth.json`](file:///d:/Projects/CaseClock/artifacts/nexus_graph/ground_truth.json).
3. **Empirical Evaluation:** Powers reproducible precision, recall, F1, and latency benchmarking scripts without touching live citizen data.

## Consequences
- **Positive:** Zero privacy violations; 100% reproducible testing and evaluation.
- **Trade-off:** Synthetic data distribution must be continuously refined against real-world police statistical parameters.
