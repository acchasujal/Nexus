# NEXUS Testing Guide

NEXUS enforces rigorous testing across backend algorithms, API contracts, safety refusal guardrails, and frontend UI components.

---

## 1. Running Backend Tests

```bash
# Run complete test suite (325 tests)
pytest

# Run with verbose output and timing
pytest -v --durations=10

# Run specific test modules
pytest tests/test_nexus_api.py
pytest tests/test_nexus_entity_resolution.py
pytest tests/test_copilot_refusal_gate.py
pytest tests/scale/test_scale_performance.py
```

---

## 2. Running Frontend Tests

```bash
cd frontend

# Run unit and component tests
npm test -- --run

# Run production build validation
npm run build
```

---

## 3. Ground Truth Evaluation

To measure Entity Resolution precision and recall against ground truth:
```bash
python scripts/evaluate_ground_truth.py
```
Target Criteria:
- **Precision:** $\ge 85\%$
- **Recall:** $\ge 80\%$
- **F1 Score:** $\ge 80\%$
