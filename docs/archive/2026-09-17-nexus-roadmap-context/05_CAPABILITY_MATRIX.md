# Capability Matrix — Current → Target

| Capability | Current | Target change | Status model |
|---|---|---|---|
| Multi-source ingestion | FIR/CDR/Bank/Intel synthetic ingestion | Add controlled digital/SOCMINT source class | EXTEND / VISION |
| Entity resolution | deterministic multi-attribute ER | add temporal/context corroboration + human decision state | EXTEND |
| Graph | GraphStore + Neo4j | living temporal graph + snapshots | EXTEND |
| Communities | Louvain | use as supporting signal | KEEP |
| Centrality | betweenness/bridge | use as supporting signal, not USP | KEEP |
| Timeline | chronological events | temporal snapshots + diff | EXTEND |
| Hotspots | current hotspot/offender intelligence | change-aware Network Pulse | EXTEND |
| Cross-case links | current cross-case bridge | affected-investigation routing | EXTEND |
| Similar Cases | current similarity | Case DNA explainable structural retrieval | EXTEND |
| Evidence provenance | edge-level provenance | support/conflict/missing evidence state | EXTEND |
| SHA-256 | implemented verification | expose in trust UX and audit | EXTEND |
| Copilot | grounded/refusal-gated | explain new signals, never create unsupported facts | EXTEND |
| Audit | immutable audit | log signal generation, verification, propagation | EXTEND |
| RBAC | implemented | apply to alerts and cross-branch exchange | EXTEND |
| Network Diff | absent as first-class object | snapshot comparison | NEW P0 |
| Network Pulse | absent as first-class object | meaningful change detection | NEW P0 |
| Early Warning | absent | constrained forecast object + abstention | NEW P0 |
| Evidence Gap | partial concepts | formal support/conflict/missing engine | NEW/EXTEND P0 |
| Next Best Verification | absent | verification planner | NEW P0 |
| Intelligence Pulse | absent | structured affected-investigation packet | NEW P1 |
| Identity Drift | absent | temporal identifier transition radar | NEW P1 |
| Network Adaptation | absent | structural adaptation detection | NEW P1 |
| Digital Shadow | absent as source class | controlled SOCMINT/digital graph fusion | NEW P1 |
| Trust anchoring | SHA-256 current | selective Merkle/permissioned target | FUTURE P2 |
| PSI/MPC | absent | privacy-preserving deconfliction | FUTURE P2 |
