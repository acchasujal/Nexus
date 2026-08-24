import sys
from pathlib import Path
from backend.app.db.ingestion.pipeline import CsvIngestionPipeline

def check_fixtures():
    pipeline = CsvIngestionPipeline()
    bundle = pipeline.ingest_directory("tests/data/fixtures/m2_csv")
    
    print("M2 CSV Trial Fixture Validation")
    print("=" * 40)
    print(f"Total Rows Received: {bundle.summary.received_count}")
    print(f"Accepted: {bundle.summary.accepted_count}")
    print(f"Duplicates: {bundle.summary.duplicate_count}")
    print(f"Rejected: {bundle.summary.rejected_count}")
    print(f"Warnings: {bundle.summary.warning_count}")
    print(f"Nodes Created: {bundle.summary.node_created_count}")
    print(f"Relationships: {bundle.summary.relationship_created_count}")
    print(f"Auto-linked Identities: {bundle.summary.auto_linked_count if hasattr(bundle.summary, 'auto_linked_count') else 'N/A'}")
    print(f"Review Required: {bundle.summary.review_required_count}")
    
    # Ground truth validation is tested by evaluate_ground_truth? We don't have it explicitly bound here, but the evaluator handles it.
    
if __name__ == "__main__":
    check_fixtures()
