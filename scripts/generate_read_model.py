"""scripts/generate_read_model.py

Build and persist the canonical intelligence read-model artifact.
Used in the precomputation pipeline to ensure deterministic read models.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.services.canonical_read_model import (
    build_canonical_read_model,
    save_canonical_read_model,
)


def main() -> None:
    print("Building canonical intelligence read model...")
    model = build_canonical_read_model()
    save_canonical_read_model(model)
    print(f"Read model generated successfully.")
    print(f"  Dataset Version: {model.get('dataset_version')}")
    print(f"  Checksum:        {model.get('checksum')}")
    print(f"  Cases:           {len(model.get('cases', []))}")
    print(f"  Pulses:          {len(model.get('pulses', []))}")
    print(f"  Active Changes:  {model.get('kpis', {}).get('total_changes')}")


if __name__ == "__main__":
    main()
