# NEXUS AI Development Guidelines

This document guides AI coding assistants (GitHub Copilot, Cursor, Claude Code, Gemini, Windsurf) working within the NEXUS repository.

---

## 1. Quick Orientation

When starting a coding session, always inspect:
- [**`AGENTS.md`**](file:///d:/Projects/CaseClock/AGENTS.md) — High-level project constraints and ethical boundaries.
- [**`PROGRESS.md`**](file:///d:/Projects/CaseClock/PROGRESS.md) — Current task board, active feature branches, and integration status.
- [**`NEXUS.md`**](file:///d:/Projects/CaseClock/NEXUS.md) — Ground-truth product domain, data model, and problem statement details.

---

## 2. Core Operational Rules for AI Assistants

1. **Surgical Changes Only:** Modify only the files and functions directly related to the assigned task. Never perform unrelated mass refactoring or unsolicited file reformatting.
2. **Deterministic Processing First:** Prefer deterministic algorithms (Bigram Jaccard, Double Metaphone, Louvain Modularity, Betweenness Centrality) over probabilistic LLM prompts for analytical logic.
3. **Evidence Attribution:** Ensure all newly created relationships in the graph ontology attach an `EvidenceProvenance` object.
4. **Preserve Shared Contracts:** Never modify types in [`shared/contracts/`](file:///d:/Projects/CaseClock/shared/contracts/) without explicit coordination with all dependent lanes.
5. **Mandatory Local Verification:** Always verify code by running:
   - `pytest` for backend changes
   - `python scripts/evaluate_ground_truth.py` for entity resolution changes
   - `npm test -- --run` and `npm run build` in `frontend` for UI changes
6. **Task Board Maintenance:** Update the relevant task row in [`PROGRESS.md`](file:///d:/Projects/CaseClock/PROGRESS.md) upon starting, completing, or encountering blockers on a task.
