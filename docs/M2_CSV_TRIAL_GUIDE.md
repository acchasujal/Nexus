# M2 CSV Trial Guide

The trial runner is repository-independent and reads only caller-selected synthetic CSV files. It does not update graph artifacts, repositories, APIs, or databases.

## Run

```text
python -m backend.app.db.ingestion.cli --input-dir tests/data/fixtures/m2_csv --output-dir /tmp/nexus_m2_csv_trial
```

The input directory may contain `fir_records.csv`, `cdr_records.csv`, `bank_transactions.csv`, and optionally `intelligence_records.csv`. A missing source file is skipped. The output directory is created if needed and receives only:

- `ingestion_summary.json`
- `normalized_nodes.json`
- `normalized_relationships.json`
- `entity_review_candidates.json`
- `rejected_rows.json`
- `evaluation_metrics.json`

## Safety Boundaries

All input is synthetic. CSV cells are parsed as data and are never executed as formulas or Python. The runner does not accept filesystem paths from CSV fields, and parser diagnostics avoid exposing sensitive identifiers in messages.

Every factual relationship must reference a `SourceRecord`. Before output, node and relationship models, node endpoints, source-record references, and the M1-compatible graph adapter are validated in memory.

Evaluation metrics are reported only when a compatible ground-truth file is available. Missing or incompatible ground truth is reported as unevaluated; the runner does not claim perfect precision or recall without evidence.
