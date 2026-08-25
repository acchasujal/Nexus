import sys
import json
from pathlib import Path
from backend.app.db.ingestion.pipeline import CsvIngestionPipeline
from backend.app.db.ingestion.resolution.evaluator import evaluate_ground_truth

def get_exact_results():
    input_path = Path("tests/data/fixtures/m2_csv")
    pipeline = CsvIngestionPipeline()
    
    original_resolve = pipeline._resolve_parsed
    record_to_person_map = {}
    
    def hooked_resolve(parsed):
        mapping, reviews = original_resolve(parsed)
        claims = pipeline._extract_claims(parsed)
        from backend.app.db.ingestion.identifiers import make_provisional_person_id
        for claim in claims:
            prov_id = make_provisional_person_id(claim.record_id, claim.source_type.value)
            canon_id = mapping.get(prov_id)
            if canon_id:
                record_to_person_map[claim.record_id] = canon_id
                
            print(f"CLAIM: {claim.record_id} -> {canon_id}")
            for r in reviews:
                if r.incoming_record_id == claim.record_id:
                    print(f"  Decision: {r.status} (auto={r.auto_link_allowed}) - {r.reason}")
                
        return mapping, reviews
        
    pipeline._resolve_parsed = hooked_resolve
    bundle = pipeline.ingest_directory(input_path)
    
    gt_file = input_path / "entity_resolution_ground_truth.csv"
    metrics = evaluate_ground_truth(gt_file, record_to_person_map, bundle.review_candidates)
    
    print(json.dumps(metrics, indent=2))

if __name__ == "__main__":
    get_exact_results()
