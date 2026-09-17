"""scripts/ncrb/extract_ncrb_calibration.py

Development-time NCRB calibration extraction pipeline.

PURPOSE
-------
Reads raw NCRB 2024 Excel files from data/ and produces:
  artifacts/ncrb_calibration_extracted.json  — fully annotated extraction with
      provenance, source coordinates, raw values, denominators, and formulas.

This script is NOT imported at application runtime. It exists to:
  1. Document exactly which NCRB numbers produced which calibration constants.
  2. Allow regeneration of calibration values when new NCRB data is released.
  3. Support audits of synthetic data realism.

USAGE
-----
    python scripts/ncrb/extract_ncrb_calibration.py [--data-dir data/] [--out artifacts/]

REQUIREMENTS
------------
    pip install openpyxl

PROVENANCE MODEL
----------------
Each extracted parameter is classified as one of:
  NCRB_DERIVED     — Directly read from a NCRB table cell, no transformation.
  NCRB_INFERRED    — Computed from NCRB cells via an explicit documented formula.
  SYNTHETIC_ASSUMPTION — Not supported by available NCRB files; design choice.

CALIBRATION SCOPE
-----------------
State focus: Karnataka (India) 2024
Publication: NCRB Crime in India 2024
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Requirements check
# ---------------------------------------------------------------------------
try:
    import openpyxl
except ImportError:
    sys.exit("ERROR: openpyxl not installed. Run: pip install openpyxl")


# ---------------------------------------------------------------------------
# File hash helper
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Column helpers
# ---------------------------------------------------------------------------

def _row_as_dict(ws, row_idx: int) -> list[Any]:
    return list(ws.iter_rows(min_row=row_idx, max_row=row_idx, values_only=True))[0]


def _safe_int(v: Any) -> int:
    if v is None:
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _safe_float(v: Any) -> float:
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# Source A: 1DistrictwiseIPCCrimes2024.xlsx
# ---------------------------------------------------------------------------

def extract_ipc_karnataka(data_dir: Path) -> dict[str, Any]:
    """Extract Karnataka district-wise IPC crime group totals.

    SOURCE: 1DistrictwiseIPCCrimes2024.xlsx, Sheet='District Data Report'
    STATE MARKER: Row 339 'State: Karnataka'
    DISTRICT ROWS: 340–377 (38 districts)
    KARNATAKA TOTAL ROW: 378

    GROUP AGGREGATE COLUMNS (verified: groups sum exactly to col155):
      col30  = Total Offences against Women and Children
      col73  = Total Offences affecting Human Body
      col76  = Total Offences against State
      col101 = Total Offences against Public Tranquility
      col124 = Total Offences against Property
      col138 = Total Offences Relating to Documents & Property
      col153 = Total Miscellaneous IPC/BNS Crimes
      col154 = Other IPC/BNS crimes
      col155 = Grand Total Cognizable IPC/BNS crimes
    """
    path = data_dir / "1DistrictwiseIPCCrimes2024.xlsx"
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["District Data Report"]

    # Karnataka total row 378
    total_row = _row_as_dict(ws, 378)
    grand_total = _safe_int(total_row[155])

    group_totals = {
        "women_children": _safe_int(total_row[30]),
        "human_body": _safe_int(total_row[73]),
        "against_state": _safe_int(total_row[76]),
        "public_tranquility": _safe_int(total_row[101]),
        "property": _safe_int(total_row[124]),
        "documents_forgery": _safe_int(total_row[138]),
        "miscellaneous": _safe_int(total_row[153]),
        "other_ipc": _safe_int(total_row[154]),
    }

    # Verify accounting: sum must equal grand total
    group_sum = sum(group_totals.values())
    assert group_sum == grand_total, (
        f"IPC group totals {group_sum} != grand total {grand_total}"
    )

    # District-level IPC totals (col155) for district weight computation
    districts_raw: list[dict[str, Any]] = []
    for row_idx in range(340, 378):
        row = _row_as_dict(ws, row_idx)
        district = str(row[1]).strip() if row[1] else ""
        total = _safe_int(row[155])
        if not district or total == 0:
            continue
        districts_raw.append({
            "district": district,
            "ipc_total": total,
            "women_children": _safe_int(row[30]),
            "human_body": _safe_int(row[73]),
            "property": _safe_int(row[124]),
            "miscellaneous": _safe_int(row[153]),
            "other_ipc": _safe_int(row[154]),
        })

    wb.close()

    # Compute normalized district weights (denominator = Karnataka IPC total)
    district_ipc_weights: dict[str, float] = {}
    for d in districts_raw:
        district_ipc_weights[d["district"]] = d["ipc_total"] / grand_total

    # Verify weights sum to ~1.0
    weight_sum = sum(district_ipc_weights.values())
    assert abs(weight_sum - 1.0) < 0.001, f"District IPC weights sum to {weight_sum}"

    return {
        "source": {
            "file": "1DistrictwiseIPCCrimes2024.xlsx",
            "sha256": _sha256(path),
            "sheet": "District Data Report",
            "state_marker_row": 339,
            "state": "Karnataka",
            "district_rows": "340-377",
            "total_row": 378,
            "group_columns": {
                "women_children_total": "col30",
                "human_body_total": "col73",
                "against_state_total": "col76",
                "public_tranquility_total": "col101",
                "property_total": "col124",
                "documents_forgery_total": "col138",
                "miscellaneous_total": "col153",
                "other_ipc": "col154",
                "grand_total": "col155",
            },
        },
        "karnataka_ipc_group_totals": {
            "type": "NCRB_DERIVED",
            "grand_total": grand_total,
            "groups": group_totals,
            "note": "Groups verified to sum exactly to grand_total (difference=0)",
        },
        "karnataka_ipc_group_weights": {
            "type": "NCRB_INFERRED",
            "formula": "group_total / karnataka_ipc_grand_total",
            "denominator": grand_total,
            "denominator_label": "Karnataka Total Cognizable IPC/BNS crimes 2024",
            "weights": {k: v / grand_total for k, v in group_totals.items()},
        },
        "karnataka_district_ipc_weights": {
            "type": "NCRB_INFERRED",
            "formula": "district_ipc_total / karnataka_ipc_grand_total",
            "denominator": grand_total,
            "denominator_label": "Karnataka Total Cognizable IPC/BNS crimes 2024",
            "weights": district_ipc_weights,
        },
        "districts_raw": districts_raw,
    }


# ---------------------------------------------------------------------------
# Source B: 2DistrictwiseSLLCrimes2024.xlsx
# ---------------------------------------------------------------------------

def extract_sll_karnataka(data_dir: Path) -> dict[str, Any]:
    """Extract Karnataka district-wise SLL (NDPS, Arms Act) crime totals.

    SOURCE: 2DistrictwiseSLLCrimes2024.xlsx, Sheet='District Data Report'
    STATE MARKER: Row 338 'Karnataka'
    DISTRICT ROWS: 339-377 (approximately; verified by empty check)

    KEY COLUMNS (from row 2-4 header analysis):
      col23 = Arms Act 1959 Total
      col44 = NDPS Act 1985 Total
      col94 = Total SLL (last identified column)
    """
    path = data_dir / "2DistrictwiseSLLCrimes2024.xlsx"
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["District Data Report"]

    # State marker at row 338 for Karnataka
    districts_raw: list[dict[str, Any]] = []
    karnataka_total_row: dict[str, Any] | None = None

    for row_idx in range(339, 382):
        row = _row_as_dict(ws, row_idx)
        col0 = str(row[0]).strip() if row[0] else ""
        district = str(row[1]).strip() if row[1] else ""

        if "State:" in col0 and "Karnataka" not in col0:
            break
        if not district.strip():
            continue
        if "Total" in district:
            karnataka_total_row = {
                "district": district,
                "arms_act": _safe_int(row[23]),
                "ndps": _safe_int(row[44]),
            }
            continue

        entry = {
            "district": district,
            "arms_act": _safe_int(row[23]),
            "ndps": _safe_int(row[44]),
        }
        districts_raw.append(entry)

    wb.close()

    total_ndps = sum(d["ndps"] for d in districts_raw)
    total_arms = sum(d["arms_act"] for d in districts_raw)

    # Compute district NDPS weights (denominator = Karnataka NDPS total)
    district_ndps_weights: dict[str, float] = {}
    for d in districts_raw:
        if total_ndps > 0:
            district_ndps_weights[d["district"]] = d["ndps"] / total_ndps

    return {
        "source": {
            "file": "2DistrictwiseSLLCrimes2024.xlsx",
            "sha256": _sha256(path),
            "sheet": "District Data Report",
            "state": "Karnataka",
            "key_columns": {
                "arms_act_total": "col23 (The Arms Act, 1959 Total)",
                "ndps_total": "col44 (The NDPS Act, 1985 Total)",
            },
        },
        "karnataka_sll_totals": {
            "type": "NCRB_DERIVED",
            "ndps_total": total_ndps,
            "arms_act_total": total_arms,
            "note": "SLL crimes are separate from IPC/BNS crimes; must not be mixed with IPC denominators",
        },
        "karnataka_district_ndps_weights": {
            "type": "NCRB_INFERRED",
            "formula": "district_ndps_total / karnataka_ndps_total",
            "denominator": total_ndps,
            "denominator_label": "Karnataka Total NDPS Act 2024 cases",
            "weights": district_ndps_weights,
        },
        "districts_raw": districts_raw,
    }


# ---------------------------------------------------------------------------
# Source C: 9DistrictwiseCyberCrimes2024.xlsx
# ---------------------------------------------------------------------------

def extract_cyber_karnataka(data_dir: Path) -> dict[str, Any]:
    """Extract Karnataka district-wise cyber crime totals.

    SOURCE: 9DistrictwiseCyberCrimes2024.xlsx, Sheet='District Data Report'
    STATE MARKER: Row 339 'Karnataka'
    KEY COLUMN: col59 = Total Cyber Crimes (A+B+C)
    """
    path = data_dir / "9DistrictwiseCyberCrimes2024.xlsx"
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["District Data Report"]

    districts_raw: list[dict[str, Any]] = []
    total_cyber_karnataka = 0

    for row_idx in range(340, 382):
        row = _row_as_dict(ws, row_idx)
        col0 = str(row[0]).strip() if row[0] else ""
        district = str(row[1]).strip() if row[1] else ""

        if "State:" in col0 and "Karnataka" not in col0:
            break
        if not district.strip():
            continue
        if "Total" in district:
            total_cyber_karnataka = _safe_int(row[59])
            continue

        entry = {"district": district, "total_cyber": _safe_int(row[59])}
        districts_raw.append(entry)

    wb.close()

    total_from_districts = sum(d["total_cyber"] for d in districts_raw)

    district_cyber_weights: dict[str, float] = {}
    denom = total_from_districts if total_from_districts > 0 else 1
    for d in districts_raw:
        district_cyber_weights[d["district"]] = d["total_cyber"] / denom

    return {
        "source": {
            "file": "9DistrictwiseCyberCrimes2024.xlsx",
            "sha256": _sha256(path),
            "sheet": "District Data Report",
            "state": "Karnataka",
            "key_column": "col59 = Total Cyber Crimes (A. IT Act + B. IPC Cyber + C. SLL Cyber)",
        },
        "karnataka_cyber_totals": {
            "type": "NCRB_DERIVED",
            "total_cyber_from_districts": total_from_districts,
            "total_cyber_state_row": total_cyber_karnataka,
            "note": "Cyber crimes are a SUBSET of SLL (IT Act) and IPC; they cross-cut the IPC/SLL boundary",
        },
        "karnataka_district_cyber_weights": {
            "type": "NCRB_INFERRED",
            "formula": "district_cyber_total / karnataka_cyber_total (district sum)",
            "denominator": total_from_districts,
            "denominator_label": "Sum of Karnataka district cyber crime totals 2024",
            "weights": district_cyber_weights,
        },
        "districts_raw": districts_raw,
    }


# ---------------------------------------------------------------------------
# Source D: TABLE17B13.xlsx — Case disposal rates
# ---------------------------------------------------------------------------

def extract_disposal_rates(data_dir: Path) -> dict[str, Any]:
    """Extract aggregate case disposal statistics from TABLE17B13.

    SOURCE: TABLE17B13.xlsx, Sheet='CIIReport'
    SCOPE: All-India aggregate (NOT Karnataka-specific)
    KEY ROW: Row 186 'Total Cognizable IPC/BNS crimes'

    COLUMN MAPPING (verified from header rows 3-4):
      col3  = Cases Reported during the year
      col5  = Total Cases for Investigation
      col21 = Cases Charge sheeted (Total)
      col27 = Cases Pending Investigation at end of year
      col28 = Chargesheeting Rate (col21/col5 * 100)
      col29 = Pendency Percentage (col27/col5 * 100)

    IMPORTANT: These are ALL-INDIA figures. Karnataka-specific disposal data
    is not available in the currently downloaded files. The weights derived
    here are labeled NCRB_INFERRED (all-India as proxy) not Karnataka-specific.
    """
    path = data_dir / "TABLE17B13.xlsx"
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["CIIReport"]

    # All-India total is row 186
    total_row = _row_as_dict(ws, 186)

    reported = _safe_int(total_row[3])
    total_for_investigation = _safe_int(total_row[5])
    chargesheeted = _safe_int(total_row[21])
    pending = _safe_int(total_row[27])
    chargesheeting_rate = _safe_float(total_row[28])
    pendency_pct = _safe_float(total_row[29])

    # Map to NEXUS case status categories:
    # CHARGESHEET_FILED ← chargesheeted cases fraction of total_for_investigation
    # PENDING_INVESTIGATION ← pending cases fraction
    # CLOSED_NO_EVIDENCE ← (total_for_investigation - chargesheeted - pending) fraction
    #
    # NOTE: These fractions apply to CASES IN PIPELINE, not new registrations.
    # Using fraction of total_for_investigation as approximate generation weight.
    fraction_chargesheeted = chargesheeted / total_for_investigation if total_for_investigation else 0.0
    fraction_pending = pending / total_for_investigation if total_for_investigation else 0.0
    fraction_closed_other = 1.0 - fraction_chargesheeted - fraction_pending

    wb.close()

    return {
        "source": {
            "file": "TABLE17B13.xlsx",
            "sha256": _sha256(path),
            "sheet": "CIIReport",
            "scope": "ALL-INDIA aggregate (not Karnataka-specific)",
            "total_row": 186,
            "row_label": "Total Cognizable IPC/BNS crimes",
            "column_mapping": {
                "col3": "Cases Reported during the year",
                "col5": "Total Cases for Investigation",
                "col21": "Cases Charge sheeted Total",
                "col27": "Cases Pending at year end",
                "col28": "Chargesheeting Rate",
                "col29": "Pendency Percentage",
            },
        },
        "all_india_disposal_raw": {
            "type": "NCRB_DERIVED",
            "reported": reported,
            "total_for_investigation": total_for_investigation,
            "chargesheeted": chargesheeted,
            "pending": pending,
            "chargesheeting_rate_pct": chargesheeting_rate,
            "pendency_pct": pendency_pct,
        },
        "nexus_case_status_weights": {
            "type": "NCRB_INFERRED",
            "scope_warning": "All-India proxy; Karnataka-specific disposal data not in current files",
            "formula": "fraction = category_count / total_for_investigation",
            "denominator": total_for_investigation,
            "denominator_label": "All-India Total Cases for Investigation 2024",
            "nexus_mapping": {
                "CHARGESHEET_FILED": {
                    "ncrb_source": "Cases Charge sheeted (col21)",
                    "ncrb_value": chargesheeted,
                    "weight": round(fraction_chargesheeted, 4),
                },
                "INVESTIGATION_IN_PROGRESS": {
                    "ncrb_source": "Cases Pending at year end (col27)",
                    "ncrb_value": pending,
                    "weight": round(fraction_pending, 4),
                },
                "CLOSED_NO_EVIDENCE": {
                    "ncrb_source": "Computed: total - chargesheeted - pending",
                    "ncrb_value": total_for_investigation - chargesheeted - pending,
                    "weight": round(fraction_closed_other, 4),
                },
            },
            "note": (
                "NCRB disposal states (FR False, Mistake of Fact, True-Insufficient-Evidence, Abated) "
                "are collapsed into CLOSED_NO_EVIDENCE. OPEN (newly registered, not yet processed) "
                "is not directly represented in the disposal table and is treated as a SYNTHETIC_ASSUMPTION."
            ),
        },
    }


# ---------------------------------------------------------------------------
# Synthetic assumptions (not NCRB-derived)
# ---------------------------------------------------------------------------

SYNTHETIC_ASSUMPTIONS: list[dict[str, Any]] = [
    {
        "parameter": "accused_gender_weights",
        "type": "SYNTHETIC_ASSUMPTION",
        "reason": (
            "NCRB does not provide accused/arrested-person gender distribution "
            "in the 19 downloaded files. TABLE files cover metropolitan cities "
            "(TABLE3B13 = crime against women rates, not accused gender). "
            "A design prior of ~88% male is commonly cited in literature but "
            "cannot be sourced to the current file set."
        ),
        "value_used": {"male": 0.88, "female": 0.11, "other": 0.01},
        "source_attempted": "None of the 19 NCRB files provide accused gender breakdown for Karnataka",
        "recommendation": "Obtain NCRB Table 10A (Persons Arrested by Age and Sex) for a defensible source",
    },
    {
        "parameter": "accused_age_band_weights",
        "type": "SYNTHETIC_ASSUMPTION",
        "reason": (
            "NCRB provides age-disaggregated arrest data in Table 10 (Persons Arrested) "
            "but this table is not in the 19 downloaded files. "
            "10DistrictwiseMissingPersons2024.xlsx provides MISSING PERSON age data, "
            "which cannot be used as accused age proxy."
        ),
        "value_used": {
            "18-25": 0.30, "25-35": 0.35, "35-45": 0.20, "45-55": 0.10, "55+": 0.05
        },
        "source_attempted": "Age bands sourced from general criminological literature (accused peak 18-35)",
        "recommendation": "Obtain NCRB Table 10A for defensible accused age distribution",
    },
    {
        "parameter": "victim_gender_weights",
        "type": "SYNTHETIC_ASSUMPTION",
        "reason": (
            "10DistrictwiseMissingPersons2024 provides MISSING PERSON gender breakdowns "
            "which is a specific scenario. Victim gender for general IPC crimes is not "
            "available in current files without per-crime-type disaggregation."
        ),
        "value_used": {"male": 0.55, "female": 0.44, "other": 0.01},
        "source_attempted": "TABLE3B13 covers metropolitan cities crime-against-women rate only",
        "recommendation": "Obtain NCRB Table 5A (Victims of IPC Crimes) for accurate victim gender weights",
    },
    {
        "parameter": "missing_person_victim_age_weights",
        "type": "NCRB_INFERRED",
        "source_file": "10DistrictwiseMissingPersons2024.xlsx",
        "source_scope": "Karnataka, 2024",
        "reason": (
            "Used ONLY for missing-person case scenarios. "
            "Bengaluru City total missing: Male=2704, Female=3534. "
            "Karnataka total from state row provides age-band fractions for missing-person victim profiles."
        ),
        "bengaluru_city_raw": {"male_total": 2704, "female_total": 3534},
        "applicable_scenario": "MISSING_PERSON cases only; NOT applied to general victim demographics",
    },
    {
        "parameter": "karnataka_name_pools",
        "type": "SYNTHETIC_ASSUMPTION",
        "reason": (
            "NCRB aggregate crime tables contain no personal name distribution. "
            "Karnataka is a multi-linguistic state with Kannada, Tamil, Urdu, "
            "and Telugu communities. Name pools are constructed as SYNTHETIC REALISM "
            "INPUT based on demographic knowledge, not NCRB data."
        ),
        "design_intent": "Reflect Karnataka's multilingual population for investigative realism",
    },
    {
        "parameter": "bns_section_to_crime_category_mapping",
        "type": "SYNTHETIC_ASSUMPTION",
        "reason": (
            "TABLE1B44 (IPC/BNS Crimes Crime-Head-wise) contains column headers that "
            "reference section numbers within crime-head labels (e.g., 'Rape (Section 64 to "
            "Section 71 BNS / Section 376 IPC)'). However, the table provides CRIME COUNTS "
            "by metropolitan city, not a canonical crime-head → section mapping. "
            "A manually curated mapping is required and is labeled as SYNTHETIC ASSUMPTION "
            "with explicit rationale per entry."
        ),
        "table1b44_finding": (
            "TABLE1B44 Row4 headers DO contain BNS/IPC section references within crime-head labels. "
            "These are used to INFORM the manual mapping but the mapping itself is curated."
        ),
    },
    {
        "parameter": "cross_jurisdiction_network_axes",
        "type": "SYNTHETIC_ASSUMPTION",
        "reason": (
            "NCRB aggregate crime counts cannot establish that criminal networks traverse "
            "specific geographic axes. The Bengaluru↔Mangaluru and Bengaluru↔Hubballi "
            "axes in NEXUS are SYNTHETIC SCENARIO TOPOLOGY, not NCRB-derived relationships."
        ),
    },
    {
        "parameter": "criminal_network_topology",
        "type": "SYNTHETIC_ASSUMPTION",
        "reason": (
            "Degree distribution, community sizes, bridge frequency, component sizes, "
            "clustering coefficients, temporal activity patterns, communication burst behavior, "
            "and transaction fan-out/fan-in are all synthetic network realism assumptions. "
            "NCRB does not provide criminal network topology data."
        ),
    },
]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(data_dir: str = "data", out_dir: str = "artifacts") -> None:
    data_path = Path(data_dir)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print("Extracting NCRB calibration data...")

    print("  [1/4] IPC crimes (Karnataka district-level)...")
    ipc = extract_ipc_karnataka(data_path)

    print("  [2/4] SLL crimes (NDPS, Arms Act)...")
    sll = extract_sll_karnataka(data_path)

    print("  [3/4] Cyber crimes...")
    cyber = extract_cyber_karnataka(data_path)

    print("  [4/4] Case disposal rates...")
    disposal = extract_disposal_rates(data_path)

    # Compute NEXUS crime category weights from IPC groups + SLL
    # IMPORTANT: IPC and SLL are SEPARATE registers. They share a denominator ONLY
    # if we create a combined "all crimes" denominator explicitly.
    # For NEXUS generator, we create separate weighted categories:
    #   IPC-based categories use IPC group weights (denominator = IPC total)
    #   SLL categories (NDPS, Arms) are modeled as separate scenario tags
    ipc_weights = ipc["karnataka_ipc_group_weights"]["weights"]

    # For the NEXUS generator crime_category field, we map NCRB IPC groups to
    # NEXUS crime categories. SLL (NDPS, Arms) are treated as enhancements to
    # the "miscellaneous" IPC category since they don't appear in the IPC register.
    # This mapping is explicitly a SYNTHETIC transformation:
    nexus_crime_category_mapping = {
        "type": "NCRB_INFERRED",
        "scope_warning": (
            "IPC groups → NEXUS crime categories. SLL crimes (NDPS, Arms) are mapped "
            "from a separate register and cannot be directly combined with IPC weights "
            "without double-counting risk. They are modeled as scenario-specific overlays."
        ),
        "ipc_group_to_nexus_category": {
            "property": {
                "nexus_category": "Theft & Property Crime",
                "ipc_group": "property",
                "ipc_weight": ipc_weights["property"],
            },
            "human_body": {
                "nexus_category": "Violence & Bodily Harm",
                "ipc_group": "human_body",
                "ipc_weight": ipc_weights["human_body"],
            },
            "women_children": {
                "nexus_category": "Offences Against Women & Children",
                "ipc_group": "women_children",
                "ipc_weight": ipc_weights["women_children"],
            },
            "miscellaneous": {
                "nexus_category": "Miscellaneous IPC",
                "ipc_group": "miscellaneous",
                "ipc_weight": ipc_weights["miscellaneous"],
            },
            "other_ipc": {
                "nexus_category": "Other IPC",
                "ipc_group": "other_ipc",
                "ipc_weight": ipc_weights["other_ipc"],
            },
            "documents_forgery": {
                "nexus_category": "Fraud & Forgery",
                "ipc_group": "documents_forgery",
                "ipc_weight": ipc_weights["documents_forgery"],
            },
            "public_tranquility": {
                "nexus_category": "Public Order",
                "ipc_group": "public_tranquility",
                "ipc_weight": ipc_weights["public_tranquility"],
            },
        },
        "sll_overlays": {
            "narcotics_ndps": {
                "type": "NCRB_INFERRED",
                "description": "NDPS Act cases as scenario overlay on top of IPC crime mix",
                "karnataka_ndps_total": sll["karnataka_sll_totals"]["ndps_total"],
                "note": "Applied as separate scenario dimension; not mixed into IPC weight vector",
            },
            "arms_trafficking": {
                "type": "NCRB_INFERRED",
                "description": "Arms Act cases as scenario overlay",
                "karnataka_arms_total": sll["karnataka_sll_totals"]["arms_act_total"],
            },
            "cyber_fraud": {
                "type": "NCRB_INFERRED",
                "description": "Cyber crimes (IT Act + IPC cyber + SLL cyber) as scenario overlay",
                "karnataka_cyber_total": cyber["karnataka_cyber_totals"]["total_cyber_from_districts"],
            },
        },
    }

    artifact = {
        "_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator": "scripts/ncrb/extract_ncrb_calibration.py",
            "ncrb_publication_year": 2024,
            "state_focus": "Karnataka",
            "calibration_version": "1.0.0",
            "provenance_model": {
                "NCRB_DERIVED": "Directly read from NCRB table cell",
                "NCRB_INFERRED": "Computed from NCRB cells via explicit formula",
                "SYNTHETIC_ASSUMPTION": "Design choice; not supported by available NCRB files",
            },
        },
        "source_files": {
            "1DistrictwiseIPCCrimes2024.xlsx": ipc["source"],
            "2DistrictwiseSLLCrimes2024.xlsx": sll["source"],
            "9DistrictwiseCyberCrimes2024.xlsx": cyber["source"],
            "TABLE17B13.xlsx": disposal["source"],
        },
        "extracted_parameters": {
            "karnataka_ipc": ipc,
            "karnataka_sll": sll,
            "karnataka_cyber": cyber,
            "case_disposal": disposal,
            "nexus_crime_category_mapping": nexus_crime_category_mapping,
        },
        "synthetic_assumptions": SYNTHETIC_ASSUMPTIONS,
        "validation": {
            "ipc_groups_sum_to_total": sum(ipc["karnataka_ipc_group_totals"]["groups"].values())
            == ipc["karnataka_ipc_group_totals"]["grand_total"],
            "district_ipc_weights_sum": round(
                sum(ipc["karnataka_district_ipc_weights"]["weights"].values()), 6
            ),
            "district_ndps_weights_sum": round(
                sum(sll["karnataka_district_ndps_weights"]["weights"].values()), 6
            ),
            "district_cyber_weights_sum": round(
                sum(cyber["karnataka_district_cyber_weights"]["weights"].values()), 6
            ),
        },
    }

    out_file = out_path / "ncrb_calibration_extracted.json"
    out_file.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nExtraction complete: {out_file}")
    print(f"  IPC grand total: {ipc['karnataka_ipc_group_totals']['grand_total']:,}")
    print(f"  NDPS total: {sll['karnataka_sll_totals']['ndps_total']:,}")
    print(f"  Arms total: {sll['karnataka_sll_totals']['arms_act_total']:,}")
    print(f"  Cyber total: {cyber['karnataka_cyber_totals']['total_cyber_from_districts']:,}")
    print(f"  Validation: {artifact['validation']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract NCRB calibration data")
    parser.add_argument("--data-dir", default="data", help="Directory containing NCRB Excel files")
    parser.add_argument("--out", default="artifacts", help="Output directory for JSON artifact")
    args = parser.parse_args()
    main(data_dir=args.data_dir, out_dir=args.out)
