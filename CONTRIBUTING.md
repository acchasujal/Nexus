# Contributing to NEXUS

> **SIH 2026 PS 26189** — AI-Powered Criminal Network Analysis System  
> Ministry of Home Affairs (MHA) / National Crime Records Bureau (NCRB)

---

## 1. Development Principles

1. **Deterministic Before Generative:** Always implement deterministic graph analysis, phonetic disambiguation, and structured traversals before using LLMs.
2. **Evidence Provenance:** Every derived lead or graph edge must be bound to verifiable source records (`EvidenceProvenance`).
3. **Strict Ethical Boundaries:** Never implement or deploy features that predict guilt, criminality, or recidivism risk.
4. **Search Before Write:** Inspect existing graph algorithms and utilities before creating new functions. Avoid duplicate logic.

---

## 2. Local Quality Gate

Before submitting pull requests, ensure the full quality gate passes:

```bash
# 1. Backend Tests (Pytest)
pytest

# 2. Ground-Truth Accuracy Evaluation
python scripts/evaluate_ground_truth.py

# 3. Graph Latency Benchmarks
python scripts/benchmark_nexus.py

# 4. Frontend Tests (Vitest) & Build
cd frontend
npm test -- --run
npm run build
```

---

## 3. Commit Convention

NEXUS uses conventional commit formatting:
- `feat: ...` for new capabilities or algorithms
- `fix: ...` for bug fixes
- `refactor: ...` for code structural changes
- `test: ...` for test cases and ground-truth validations
- `docs: ...` for documentation updates
- `perf: ...` for performance optimizations

---

## 4. Pull Request Checklist

- [ ] All 296 backend Pytest tests pass.
- [ ] All 35 frontend Vitest tests pass and `vite build` completes cleanly.
- [ ] No live citizen PII or hardcoded credentials are included.
- [ ] Any new API endpoint is typed in `shared/contracts/` and documented in `docs/API.md`.
