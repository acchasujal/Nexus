"""synthetic_data/nexus_generator.py

Multi-source synthetic data generator for NEXUS Criminal Network Intelligence Platform.
Generates:
  1. FIR case records with IPC/BNS crime heads and evidence
  2. CDR phone records and call logs
  3. Financial accounts and money flow transaction chains
  4. Intelligence reports with mentioned targets
  5. Planted ground truth (resolutions, communities, bridge brokers, bursts, transaction chains)
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend.app.core.graph.enums import GraphEntityType, GraphRelationshipType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_nexus_synthetic_dataset(
    seed: int = 42,
    num_cases: int = 50,
    num_persons: int = 120,
    num_phones: int = 150,
    num_accounts: int = 60,
) -> dict[str, Any]:
    rng = random.Random(seed)
    base_time = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    node_id_map: dict[str, str] = {}

    first_names = [
        "Vikram", "Rajesh", "Sameer", "Arjun", "Suresh", "Manoj", "Karan", "Anil", "Deepak",
        "Sunil", "Rahul", "Imran", "Farhan", "Ramesh", "Sanjay", "Amit", "Vinod", "Praveen",
        "Mahesh", "Girish", "Pradeep", "Raghu", "Vijay", "Satish", "Naveen", "Harish", "Rohit",
    ]
    last_names = [
        "Sharma", "Patel", "Gowda", "Reddy", "Singh", "Khan", "Kumar", "Shetty", "Iyer",
        "Hegde", "Deshmukh", "Chauhan", "Joshi", "Bhat", "Naik", "Verma", "Gupta", "Malhotra",
    ]
    aliases_pool = [
        "Vicky", "Bhai", "Shooter", "Doctor", "Ustaad", "Pandit", "Chhota", "Seth", "Captain",
        "Munna", "Anna", "Hawala King", "Master", "Agent", "Shadow", "Pilot", "Mama",
    ]
    districts = ["Bengaluru Urban", "Bengaluru Rural", "Mysuru", "Mangaluru", "Hubballi-Dharwad", "Belagavi"]
    stations = ["Central Crime Branch", "Indiranagar PS", "Koramangala PS", "Ulsoor PS", "Jayanagar PS", "Hebbal PS", "Cyber Crime PS"]
    crime_categories = [
        "Narcotics & Drug Trafficking",
        "Cyber Financial Fraud & Phishing",
        "Organized Extortion & Protection Racketeering",
        "Illegal Arms Trafficking",
        "Hawala & Money Laundering",
    ]

    # ── 1. Create Person Nodes ───────────────────────────────────────────────
    persons: list[dict[str, Any]] = []
    for i in range(num_persons):
        pid = f"person-{i+1:04d}"
        fn = rng.choice(first_names)
        ln = rng.choice(last_names)
        full_name = f"{fn} {ln}"
        aliases = [rng.choice(aliases_pool)] if rng.random() < 0.35 else []
        phone = f"98{rng.randint(10000000, 99999999)}"
        vehicle = f"KA-{rng.randint(1, 53):02d}-{chr(65+rng.randint(0, 25))}{chr(65+rng.randint(0, 25))}-{rng.randint(1000, 9999)}"
        address = f"#{rng.randint(10, 500)}, {rng.choice(['MG Road', '100ft Road', 'Ring Road', 'Brigade Road', 'Main Bazaar'])}, {rng.choice(districts)}"

        p_node = {
            "id": pid,
            "entity_type": GraphEntityType.PERSON.value,
            "properties": {
                "full_name": full_name,
                "first_name": fn,
                "last_name": ln,
                "aliases": aliases,
                "phone_number": phone,
                "vehicle_number": vehicle,
                "address_text": address,
                "national_id": f"ID-{rng.randint(100000, 999999)}" if rng.random() < 0.4 else None,
                "is_known_offender": rng.random() < 0.3,
            },
        }
        nodes.append(p_node)
        persons.append(p_node)
        node_id_map[pid] = full_name

    # ── 2. Create Planted Ground Truth Entities for Entity Resolution ────────
    # Planted duplicate identity: Vikram Sharma -> Bikram Sarma (Same phone, variant name, matching alias)
    p_planted_1 = persons[0]
    p_planted_1["properties"]["full_name"] = "Vikram Sharma"
    p_planted_1["properties"]["aliases"] = ["Vicky", "Doctor"]
    p_planted_1["properties"]["phone_number"] = "9845012345"
    p_planted_1["properties"]["vehicle_number"] = "KA01AB1001"

    p_planted_2 = persons[1]
    p_planted_2["properties"]["full_name"] = "Bikram Sarma"  # Phonetic variation
    p_planted_2["properties"]["aliases"] = ["Vicky"]
    p_planted_2["properties"]["phone_number"] = "9845012345"
    p_planted_2["properties"]["vehicle_number"] = "KA01AB1001"

    p_planted_3 = persons[2]
    p_planted_3["properties"]["full_name"] = "V. Sharma"
    p_planted_3["properties"]["aliases"] = ["Doctor"]
    p_planted_3["properties"]["address_text"] = p_planted_1["properties"]["address_text"]

    # Preserve test fixtures for global search and copilot isolation
    p_sanjay = persons[119]
    p_sanjay["properties"]["full_name"] = "Sanjay Patel"
    p_sanjay["properties"]["phone_number"] = "9820298660"

    p_praveen = persons[77]
    p_praveen["properties"]["full_name"] = "Praveen Malhotra"

    p_naveen = persons[73]
    p_naveen["properties"]["full_name"] = "Naveen Patel"

    p_girish = persons[83]
    p_girish["properties"]["full_name"] = "Girish Shetty"

    planted_resolved_pairs = [
        (persons[0]["id"], persons[1]["id"]),
        (persons[0]["id"], persons[2]["id"]),
    ]

    # ── Cluster Population Pools ─────────────────────────────────────────────
    comm_alpha_members = [persons[k]["id"] for k in range(10, 20)]
    alpha_core = [persons[k] for k in range(10, 20)]
    alpha_pool = [persons[k] for k in range(10, 25)]

    # Include Praveen Malhotra in alpha syndicate associates
    if p_praveen not in alpha_pool:
        alpha_pool.append(p_praveen)

    comm_beta_members = [persons[k]["id"] for k in range(25, 36)]
    beta_core = [persons[k] for k in range(25, 36)]
    beta_pool = [persons[k] for k in range(25, 41)]

    er_pool = [persons[0], persons[1], persons[2], persons[3]]
    delta_pool = [persons[k] for k in range(41, 50)]

    p_bridge = persons[50]
    p_bridge["properties"]["full_name"] = "Ramesh Hegde"
    p_bridge["properties"]["aliases"] = ["The Broker", "Connector"]
    planted_bridge_node_id = p_bridge["id"]

    isolated_pool = [persons[k] for k in range(51, num_persons) if persons[k] not in (p_sanjay, p_praveen, p_naveen, p_girish)]

    # ── 3. Create Case Nodes & FIR Evidence (Modular Scoping) ────────────────
    cases: list[dict[str, Any]] = []
    iso_idx = 0

    for i in range(num_cases):
        cid = f"case-{i+1:04d}"
        fir_no = f"FIR-{2026}-{rng.randint(100, 999)}"

        if i == 0:
            # Case 1: Coastal Narcotics Syndicate case with Praveen Malhotra
            district = "Mangaluru"
            category = "Narcotics & Drug Trafficking"
            station = "Central Crime Branch"
            accused_sample = [alpha_core[0], p_praveen]
        elif i < 8:
            district = rng.choice(["Mangaluru", "Mysuru"])
            category = "Narcotics & Drug Trafficking"
            station = rng.choice(["Central Crime Branch", "Koramangala PS", "Ulsoor PS"])
            num_acc = rng.randint(2, 3)
            accused_sample = rng.sample(alpha_pool, num_acc)
        elif i < 16:
            district = rng.choice(["Bengaluru Urban", "Bengaluru Rural"])
            category = "Cyber Financial Fraud & Phishing" if i % 2 == 0 else "Hawala & Money Laundering"
            station = "Cyber Crime PS" if i % 2 == 0 else "Indiranagar PS"
            num_acc = rng.randint(2, 3)
            accused_sample = rng.sample(beta_pool, num_acc)
        elif i < 20:
            district = "Bengaluru Urban"
            category = "Organized Extortion & Protection Racketeering"
            station = "Jayanagar PS"
            accused_sample = [er_pool[i - 16]]
        elif i < 26:
            district = rng.choice(["Hubballi-Dharwad", "Belagavi"])
            category = "Illegal Arms Trafficking"
            station = "Central Crime Branch"
            num_acc = rng.randint(2, 3)
            accused_sample = rng.sample(delta_pool, num_acc)
        elif i == 48:
            # Case 49: Specific case fixture for Copilot tests
            fir_no = "FIR-2026-984"
            district = "Hubballi-Dharwad"
            category = "Organized Extortion & Protection Racketeering"
            station = "Indiranagar PS"
            accused_sample = [p_sanjay, p_naveen, p_girish]
        else:
            district = rng.choice(districts)
            category = rng.choice(crime_categories)
            station = rng.choice(stations)
            num_acc = 1 if iso_idx + 2 >= len(isolated_pool) else rng.randint(1, 2)
            accused_sample = isolated_pool[iso_idx : iso_idx + num_acc]
            iso_idx += num_acc

        days_offset = rng.randint(5, 120)
        incident_date = (base_time - timedelta(days=days_offset)).isoformat()

        c_node = {
            "id": cid,
            "entity_type": GraphEntityType.CASE.value,
            "properties": {
                "fir_number": fir_no,
                "title": f"Investigation into {category} at {district}",
                "district": district,
                "station_name": station,
                "offence_category": category,
                "incident_date": incident_date,
                "status": rng.choice(["OPEN", "INVESTIGATION_IN_PROGRESS", "CHARGESHEET_FILED"]),
                "summary": f"Case registered regarding suspected {category.lower()} involving syndicates in {district}.",
                "sections": ["Section 303 (BNS)", "Section 318 (BNS)", "Section 61 (BNS)"],
            },
        }
        nodes.append(c_node)
        cases.append(c_node)
        node_id_map[cid] = fir_no

        for acc in accused_sample:
            edges.append({
                "id": f"edge-acc-{cid}-{acc['id']}",
                "source_id": acc["id"],
                "target_id": cid,
                "edge_type": GraphRelationshipType.ACCUSED_IN.value,
                "weight": 1.0,
                "provenance": {
                    "source_type": "FIR",
                    "source_id": fir_no,
                    "timestamp": incident_date,
                    "extracted_fact": f"Named as accused in {fir_no}",
                    "derivation_method": "DIRECT_RECORD",
                    "confidence": 1.0,
                },
            })

        ev_id = f"evidence-{i+1:04d}"
        ev_node = {
            "id": ev_id,
            "entity_type": GraphEntityType.EVIDENCE.value,
            "properties": {
                "evidence_number": f"EV-{2026}-{rng.randint(1000, 9999)}",
                "case_id": cid,
                "evidence_type": rng.choice(["CDR_RECORD", "SEIZED_DEVICE", "CCTV_FOOTAGE", "BANK_STATEMENT"]),
                "description": f"Evidentiary material seized for {fir_no}",
                "collected_at": incident_date,
            },
        }
        nodes.append(ev_node)
        edges.append({
            "id": f"edge-ev-{cid}-{ev_id}",
            "source_id": cid,
            "target_id": ev_id,
            "edge_type": GraphRelationshipType.HAS_EVIDENCE.value,
            "weight": 1.0,
            "provenance": {
                "source_type": "FIR",
                "source_id": fir_no,
                "timestamp": incident_date,
                "extracted_fact": f"Evidence indexed under {fir_no}",
                "derivation_method": "DIRECT_RECORD",
                "confidence": 1.0,
            },
        })

    # ── 4. Create Phone Nodes & Tiered CDR Connections ───────────────────────
    phones: list[dict[str, Any]] = []
    for i in range(num_phones):
        ph_id = f"phone-{i+1:04d}"
        msisdn = f"9845{rng.randint(100000, 999999)}"
        ph_node = {
            "id": ph_id,
            "entity_type": GraphEntityType.PHONE.value,
            "properties": {
                "phone_number": msisdn,
                "imei": f"86{rng.randint(1000000000000, 9999999999999)}",
                "carrier": rng.choice(["Airtel", "Jio", "Vodafone-Idea", "BSNL"]),
            },
        }
        nodes.append(ph_node)
        phones.append(ph_node)

        if i < num_persons:
            p_owner = persons[i]
        else:
            p_owner = rng.choice(alpha_pool + beta_pool)

        edges.append({
            "id": f"edge-ph-{p_owner['id']}-{ph_id}",
            "source_id": p_owner["id"],
            "target_id": ph_id,
            "edge_type": GraphRelationshipType.USED_PHONE.value,
            "weight": 1.0,
            "provenance": {
                "source_type": "CDR",
                "source_id": f"CDR-{ph_id}",
                "timestamp": base_time.isoformat(),
                "extracted_fact": f"SIM card subscription attributed to {p_owner['properties']['full_name']}",
                "derivation_method": "TELECOM_KYC",
                "confidence": 0.95,
            },
        })

    for k in range(25):
        p1, p2 = rng.sample(alpha_pool, 2)
        call_count = rng.randint(3, 45)
        edges.append({
            "id": f"edge-call-alpha-{k+1}",
            "source_id": p1["id"],
            "target_id": p2["id"],
            "edge_type": GraphRelationshipType.CONNECTED_TO.value,
            "weight": min(1.0, call_count / 10.0),
            "properties": {"call_count": call_count, "channel": "VOICE_CALL"},
            "provenance": {
                "source_type": "CDR",
                "source_id": f"CDR-SWEEP-{rng.randint(100, 999)}",
                "timestamp": base_time.isoformat(),
                "extracted_fact": f"{call_count} telecommunication interactions logged",
                "derivation_method": "CALL_RECORD",
                "confidence": 0.90,
            },
        })

    for k in range(25):
        p1, p2 = rng.sample(beta_pool, 2)
        call_count = rng.randint(3, 45)
        edges.append({
            "id": f"edge-call-beta-{k+1}",
            "source_id": p1["id"],
            "target_id": p2["id"],
            "edge_type": GraphRelationshipType.CONNECTED_TO.value,
            "weight": min(1.0, call_count / 10.0),
            "properties": {"call_count": call_count, "channel": "VOICE_CALL"},
            "provenance": {
                "source_type": "CDR",
                "source_id": f"CDR-SWEEP-{rng.randint(100, 999)}",
                "timestamp": base_time.isoformat(),
                "extracted_fact": f"{call_count} telecommunication interactions logged",
                "derivation_method": "CALL_RECORD",
                "confidence": 0.90,
            },
        })

    for k in range(10):
        p1, p2 = rng.sample(delta_pool, 2)
        call_count = rng.randint(3, 45)
        edges.append({
            "id": f"edge-call-delta-{k+1}",
            "source_id": p1["id"],
            "target_id": p2["id"],
            "edge_type": GraphRelationshipType.CONNECTED_TO.value,
            "weight": min(1.0, call_count / 10.0),
            "properties": {"call_count": call_count, "channel": "VOICE_CALL"},
            "provenance": {
                "source_type": "CDR",
                "source_id": f"CDR-SWEEP-{rng.randint(100, 999)}",
                "timestamp": base_time.isoformat(),
                "extracted_fact": f"{call_count} telecommunication interactions logged",
                "derivation_method": "CALL_RECORD",
                "confidence": 0.90,
            },
        })

    # ── 5. Bank Accounts & Financial Transaction Chains ───────────────
    accounts: list[dict[str, Any]] = []
    for i in range(num_accounts):
        acc_id = f"account-{i+1:04d}"
        acc_no = f"ACC-{rng.randint(1000000000, 9999999999)}"
        acc_node = {
            "id": acc_id,
            "entity_type": GraphEntityType.ACCOUNT.value,
            "properties": {
                "account_number": acc_no,
                "bank_name": rng.choice(["State Bank of India", "HDFC Bank", "ICICI Bank", "Axis Bank", "Canara Bank"]),
                "ifsc_code": f"SBIN{rng.randint(1000, 9999)}",
            },
        }
        nodes.append(acc_node)
        accounts.append(acc_node)

        if i < 4:
            p_acc_owner = beta_core[i]
        elif i < 25:
            p_acc_owner = alpha_pool[i % len(alpha_pool)]
        elif i < 45:
            p_acc_owner = beta_pool[(i - 25) % len(beta_pool)]
        else:
            p_acc_owner = delta_pool[(i - 45) % len(delta_pool)]

        edges.append({
            "id": f"edge-accowner-{p_acc_owner['id']}-{acc_id}",
            "source_id": p_acc_owner["id"],
            "target_id": acc_id,
            "edge_type": GraphRelationshipType.OWNS_ACCOUNT.value,
            "weight": 1.0,
            "provenance": {
                "source_type": "BANK_LEDGER",
                "source_id": f"KYC-{acc_id}",
                "timestamp": base_time.isoformat(),
                "extracted_fact": "Bank account holder registration",
                "derivation_method": "FINANCIAL_LEDGER",
                "confidence": 0.98,
            },
        })

    planted_txn_chain = [accounts[0]["id"], accounts[1]["id"], accounts[2]["id"], accounts[3]["id"]]
    for j in range(len(planted_txn_chain) - 1):
        edges.append({
            "id": f"edge-txn-{planted_txn_chain[j]}-{planted_txn_chain[j+1]}",
            "source_id": planted_txn_chain[j],
            "target_id": planted_txn_chain[j+1],
            "edge_type": GraphRelationshipType.TRANSFERRED_TO.value,
            "weight": 1.0,
            "properties": {"amount": 2500000.0, "currency": "INR", "is_suspicious": True},
            "provenance": {
                "source_type": "BANK_TXN",
                "source_id": f"TXN-PLANTED-{j+1}",
                "timestamp": (base_time - timedelta(days=j)).isoformat(),
                "extracted_fact": "High-value structured transfer of INR 25,00,000",
                "derivation_method": "FINANCIAL_LEDGER",
                "confidence": 1.0,
            },
        })

    # ── 6. Planted Communities & Bridge Brokers ──────────────────────────────
    for a in range(len(comm_alpha_members)):
        for b in range(a + 1, min(a + 3, len(comm_alpha_members))):
            edges.append({
                "id": f"edge-comm-alpha-{a}-{b}",
                "source_id": comm_alpha_members[a],
                "target_id": comm_alpha_members[b],
                "edge_type": GraphRelationshipType.CONNECTED_TO.value,
                "weight": 1.0,
                "provenance": {
                    "source_type": "INTEL_REPORT",
                    "source_id": "INTEL-ALPHA-GANG",
                    "timestamp": base_time.isoformat(),
                    "extracted_fact": "Active members of Coastal Narcotics Syndicate",
                    "derivation_method": "DIRECT_RECORD",
                    "confidence": 0.85,
                },
            })

    for a in range(len(comm_beta_members)):
        for b in range(a + 1, min(a + 3, len(comm_beta_members))):
            edges.append({
                "id": f"edge-comm-beta-{a}-{b}",
                "source_id": comm_beta_members[a],
                "target_id": comm_beta_members[b],
                "edge_type": GraphRelationshipType.CONNECTED_TO.value,
                "weight": 1.0,
                "provenance": {
                    "source_type": "INTEL_REPORT",
                    "source_id": "INTEL-BETA-CYBER",
                    "timestamp": base_time.isoformat(),
                    "extracted_fact": "Active members of Cyber Hawala Ring",
                    "derivation_method": "DIRECT_RECORD",
                    "confidence": 0.85,
                },
            })

    edges.append({
        "id": f"edge-bridge-alpha-{p_bridge['id']}",
        "source_id": p_bridge["id"],
        "target_id": comm_alpha_members[0],
        "edge_type": GraphRelationshipType.CONNECTED_TO.value,
        "weight": 1.0,
        "provenance": {
            "source_type": "CDR",
            "source_id": "CDR-BRIDGE-01",
            "timestamp": base_time.isoformat(),
            "extracted_fact": "Cross-syndicate coordination contact",
            "derivation_method": "CALL_RECORD",
            "confidence": 0.92,
        },
    })
    edges.append({
        "id": f"edge-bridge-beta-{p_bridge['id']}",
        "source_id": p_bridge["id"],
        "target_id": comm_beta_members[0],
        "edge_type": GraphRelationshipType.CONNECTED_TO.value,
        "weight": 1.0,
        "provenance": {
            "source_type": "CDR",
            "source_id": "CDR-BRIDGE-02",
            "timestamp": base_time.isoformat(),
            "extracted_fact": "Cross-syndicate coordination contact",
            "derivation_method": "CALL_RECORD",
            "confidence": 0.92,
        },
    })

    # ── 7. Intelligence Reports ──────────────────────────────────────────────
    for i in range(15):
        ir_id = f"intel-{i+1:04d}"
        ir_node = {
            "id": ir_id,
            "entity_type": GraphEntityType.INTELLIGENCE_REPORT.value,
            "properties": {
                "report_id": f"INTEL-2026-{rng.randint(100, 999)}",
                "title": f"Special Intelligence Assessment #{i+1}",
                "source_agency": "State Intelligence Bureau",
                "classification_level": "CONFIDENTIAL",
                "summary": f"Field intelligence report detailing suspicious activities in {rng.choice(districts)}.",
            },
        }
        nodes.append(ir_node)
        target_pool = alpha_pool if i < 7 else beta_pool if i < 13 else delta_pool
        target_persons = rng.sample(target_pool, 2)
        for tp in target_persons:
            edges.append({
                "id": f"edge-intel-{tp['id']}-{ir_id}",
                "source_id": tp["id"],
                "target_id": ir_id,
                "edge_type": GraphRelationshipType.MENTIONED_IN.value,
                "weight": 1.0,
                "provenance": {
                    "source_type": "INTEL_REPORT",
                    "source_id": ir_node["properties"]["report_id"],
                    "timestamp": base_time.isoformat(),
                    "extracted_fact": "Subject flagged in intelligence memo",
                    "derivation_method": "DIRECT_RECORD",
                    "confidence": 0.88,
                },
            })

    dataset = {
        "metadata": {
            "platform": "NEXUS Criminal Intelligence Platform",
            "version": "2.0",
            "seed": seed,
            "generated_at": _utcnow().isoformat(),
            "counts": {
                "nodes": len(nodes),
                "edges": len(edges),
                "cases": len(cases),
                "persons": len(persons),
                "phones": len(phones),
                "accounts": len(accounts),
            },
        },
        "nodes": nodes,
        "edges": edges,
    }

    ground_truth = {
        "planted_resolved_entities": [
            {"pair": list(pair), "reason": "Same individual with phonetic/alias variation"}
            for pair in planted_resolved_pairs
        ],
        "planted_communities": [
            {"community_id": "COMM-ALPHA", "name": "Coastal Narcotics Syndicate", "members": comm_alpha_members},
            {"community_id": "COMM-BETA", "name": "Cyber Hawala Syndicate", "members": comm_beta_members},
        ],
        "planted_bridge_nodes": [
            {
                "node_id": planted_bridge_node_id,
                "name": "Ramesh Hegde",
                "role": "Broker connecting Coastal Narcotics Syndicate and Cyber Hawala Syndicate",
            }
        ],
        "planted_transaction_chains": [
            {
                "chain_id": "TXN-CHAIN-01",
                "accounts": planted_txn_chain,
                "pattern": "4-hop layering and smurfing transfer",
            }
        ],
    }

    return {"dataset": dataset, "ground_truth": ground_truth}


def export_nexus_synthetic_dataset(output_dir: Path | None = None) -> tuple[Path, Path]:
    output_dir = output_dir or Path("artifacts/nexus_graph")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = generate_nexus_synthetic_dataset()
    dataset_path = output_dir / "nexus_graph.json"
    ground_truth_path = output_dir / "ground_truth.json"

    dataset_path.write_text(json.dumps(result["dataset"], indent=2), encoding="utf-8")
    ground_truth_path.write_text(json.dumps(result["ground_truth"], indent=2), encoding="utf-8")

    # Also write to local db fallback
    db_dir = Path("backend/app/db")
    db_dir.mkdir(parents=True, exist_ok=True)
    (db_dir / "synthetic_graph.json").write_text(json.dumps(result["dataset"], indent=2), encoding="utf-8")

    return dataset_path, ground_truth_path
