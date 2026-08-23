"""Command-line entrypoint for generating synthetic graph data."""

from __future__ import annotations

import argparse
from pathlib import Path

from synthetic_data.configs import SyntheticDataConfig
from synthetic_data.export import export_csv, export_json
from synthetic_data.generator import generate_synthetic_graph


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic Case Clock graph data")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/synthetic_graph"))
    parser.add_argument("--json-name", type=str, default="synthetic_graph.json")
    parser.add_argument("--nodes-csv-name", type=str, default="nodes.csv")
    parser.add_argument("--edges-csv-name", type=str, default="edges.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = SyntheticDataConfig(
        seed=args.seed,
        output_dir=args.output_dir,
        json_filename=args.json_name,
        nodes_csv_filename=args.nodes_csv_name,
        edges_csv_filename=args.edges_csv_name,
    )
    assembly = generate_synthetic_graph(config)
    json_path = args.output_dir / args.json_name
    export_json(assembly.dataset, json_path)
    export_csv(assembly.dataset, args.output_dir)
    print(f"Generated {len(assembly.dataset.nodes)} nodes and {len(assembly.dataset.edges)} edges")
    print(f"JSON: {json_path}")
    print(f"CSV: {args.output_dir / args.nodes_csv_name}")
    print(f"CSV: {args.output_dir / args.edges_csv_name}")


if __name__ == "__main__":
    main()