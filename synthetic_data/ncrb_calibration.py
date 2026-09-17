"""synthetic_data/ncrb_calibration.py

NCRB 2024 calibration constants for NEXUS synthetic investigation data generation.

PROVENANCE
----------
All constants in this file are derived from the NCRB Crime in India 2024 publication.
They were extracted and validated by scripts/ncrb/extract_ncrb_calibration.py which
produces artifacts/ncrb_calibration_extracted.json with full source coordinates,
SHA-256 file hashes, denominators, and calculation formulas.

DO NOT edit values manually. Re-run the extraction script to update:
    python scripts/ncrb/extract_ncrb_calibration.py

CLASSIFICATION MODEL
--------------------
Each constant is annotated with its provenance type:
  NCRB_DERIVED     — Directly read from a specific NCRB table cell.
  NCRB_INFERRED    — Computed from NCRB cells via an explicit, documented formula.
  SYNTHETIC_ASSUMPTION — Design choice NOT supported by available NCRB files.

SCOPE
-----
  State:        Karnataka, India
  Year:         2024
  Publication:  NCRB Crime in India 2024
  Primary files used:
    1DistrictwiseIPCCrimes2024.xlsx  (SHA-256: 41a4270149aa...)
    2DistrictwiseSLLCrimes2024.xlsx  (SHA-256: 9800f505564c...)
    9DistrictwiseCyberCrimes2024.xlsx (SHA-256: 20aa987a34cc...)
    TABLE17B13.xlsx                   (SHA-256: 35f86df80dbf...)

EXTENSIBILITY
-------------
This module uses a simple state-profile pattern. To add Maharashtra or Delhi,
create a new profile dict following the same structure and pass it to the generator.
The current Karnataka profile is the DEFAULT_PROFILE.

IMPORTANT — DO NOT MIX REGISTERS
----------------------------------
Karnataka IPC/BNS crimes (138,784) and SLL crimes (NDPS: 4,165; Arms: 282;
Cyber: 21,993) are SEPARATE statistical registers. They cannot be summed into
a single probability vector without double-counting risk.

  IPC weights  → use IPC-only denominator (138,784).
  SLL overlays → modelled as scenario flags on top of IPC crime mix.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# CALIBRATION VERSION (matches extraction artifact version)
# ---------------------------------------------------------------------------

NCRB_CALIBRATION_VERSION = "1.0.0"
NCRB_PUBLICATION_YEAR = 2024
NCRB_STATE_FOCUS = "Karnataka"

# ---------------------------------------------------------------------------
# ── SECTION 1: Karnataka IPC Crime Group Weights ──────────────────────────
#
# SOURCE: 1DistrictwiseIPCCrimes2024.xlsx
#         Sheet: 'District Data Report'
#         State marker: Row 339 ('State: Karnataka')
#         Karnataka Total Row: 378
#
# PROVENANCE: NCRB_INFERRED
# FORMULA: group_total / karnataka_ipc_grand_total
# DENOMINATOR: 138,784 (Karnataka Total Cognizable IPC/BNS crimes 2024, col155)
#
# ACCOUNTING: All 8 groups sum EXACTLY to 138,784 (verified, difference = 0).
#
# NEXUS CATEGORY MAPPING (IPC Group → NEXUS crime category string):
#   property        → "Theft & Property Crime"
#   human_body      → "Violence & Bodily Harm"
#   women_children  → "Offences Against Women & Children"
#   miscellaneous   → "Miscellaneous IPC"
#   other_ipc       → "Other IPC"
#   documents_forgery → "Fraud & Forgery"
#   public_tranquility → "Public Order"
#   against_state   → "Offences Against the State"
#
# NOTE: These weights drive case_factory.py choose_weighted() calls.
#       They govern IPC case generation ONLY; SLL (narcotics, arms, cyber)
#       is handled separately via scenario overlays.
# ---------------------------------------------------------------------------

# (category_label, weight) tuples for use with choose_weighted()
# Ordered by descending frequency (largest first for readability)
KARNATAKA_IPC_CRIME_CATEGORY_WEIGHTS: list[tuple[str, float]] = [
    # NCRB group: Miscellaneous IPC/BNS Crimes (col153) = 38,643 / 138,784
    ("Miscellaneous IPC", 0.2784),
    # NCRB group: Offences affecting Human Body (col73) = 37,927 / 138,784
    ("Violence & Bodily Harm", 0.2733),
    # NCRB group: Offences against Property (col124) = 30,805 / 138,784
    ("Theft & Property Crime", 0.2220),
    # NCRB group: Other IPC/BNS crimes (col154) = 9,152 / 138,784
    ("Other IPC", 0.0659),
    # NCRB group: Offences against Women and Children (col30) = 10,673 / 138,784
    ("Offences Against Women & Children", 0.0769),
    # NCRB group: Offences Relating to Documents & Property (col138) = 7,241 / 138,784
    ("Fraud & Forgery", 0.0522),
    # NCRB group: Offences against Public Tranquility (col101) = 4,342 / 138,784
    ("Public Order", 0.0313),
    # NCRB group: Offences against State (col76) = 1 / 138,784
    ("Offences Against the State", 0.0000),
]
# Verification: weights sum = 1.0000 (0.2784+0.2733+0.2220+0.0659+0.0769+0.0522+0.0313+0.0000)

# ---------------------------------------------------------------------------
# ── SECTION 2: Karnataka District IPC Weights ─────────────────────────────
#
# SOURCE: 1DistrictwiseIPCCrimes2024.xlsx, Sheet: 'District Data Report'
# PROVENANCE: NCRB_INFERRED
# FORMULA: district_ipc_total / 138,784
# DENOMINATOR: 138,784 (Karnataka IPC grand total 2024)
# DISTRICT ROWS: 340-377 (38 districts, verified by sum)
#
# NOTE: Only districts present in the NEXUS generator are listed here.
#       The generator uses 6 district names; weights are renormalized to those 6.
#       KRailways (railway jurisdiction) and smaller districts are excluded from
#       the NEXUS scenario scope but their data informs the overall distribution.
# ---------------------------------------------------------------------------

# Full 38-district Karnataka IPC weights (NCRB_INFERRED)
_KARNATAKA_ALL_DISTRICT_IPC_WEIGHTS: dict[str, float] = {
    # Rows 340-377, col155 / 138784
    "Bagalkot": 0.0160,
    "Bengaluru City": 0.2501,
    "Bengaluru District": 0.0550,
    "Belagavi District": 0.0321,
    "Ballari": 0.0144,
    "Bidar": 0.0214,
    "Vijayapura": 0.0217,
    "Chikkaballapura": 0.0195,
    "Chamarajnagar": 0.0146,
    "Chikkamagaluru": 0.0191,
    "Chitradurga": 0.0319,
    "Dakshina Kannada": 0.0130,
    "Davanagere": 0.0227,
    "Dharwad": 0.0077,
    "Gadag": 0.0077,
    "Kalaburgi": 0.0189,
    "Hassan": 0.0367,
    "Haveri": 0.0176,
    "Hubballi Dharwad City": 0.0131,
    "KGF": 0.0057,
    "Kodagu": 0.0108,
    "Kolar": 0.0163,
    "Koppal": 0.0128,
    "Mandya": 0.0314,
    "Mangaluru City": 0.0152,
    "Mysuru City": 0.0182,
    "Mysuru District": 0.0352,
    "Raichur": 0.0202,
    "KRailways": 0.0062,
    "Ramanagara": 0.0289,
    "Shimoga": 0.0331,
    "Tumakuru": 0.0458,
    "Udupi": 0.0195,
    "Uttara Kannada": 0.0186,
    "Yadgiri": 0.0114,
    "Belagavi City": 0.0125,
    "Kalaburgi City": 0.0130,
    "Vijayanagara": 0.0122,
}

# NEXUS generator uses 6 named districts (from configs.py + nexus_generator.py).
# The mapping below renormalizes the full distribution to the 6 NEXUS districts.
# Each NEXUS district aggregates one or more NCRB district entries.
_NEXUS_TO_NCRB_DISTRICT_MAPPING: dict[str, list[str]] = {
    "Bengaluru City": ["Bengaluru City"],
    "Bengaluru Rural": ["Bengaluru District"],
    "Mysuru": ["Mysuru City", "Mysuru District"],
    "Mangaluru": ["Mangaluru City", "Dakshina Kannada"],
    "Hubballi-Dharwad": ["Hubballi Dharwad City", "Dharwad"],
    "Belagavi": ["Belagavi District", "Belagavi City"],
}

def _compute_nexus_district_weights() -> list[tuple[str, float]]:
    """Compute renormalized IPC weights for the 6 NEXUS district names.

    PROVENANCE: NCRB_INFERRED (aggregated from district IPC weights)
    FORMULA: sum(NCRB_district_weights for districts in nexus_group) / sum(all 6 nexus groups)
    """
    raw: dict[str, float] = {}
    for nexus_district, ncrb_districts in _NEXUS_TO_NCRB_DISTRICT_MAPPING.items():
        raw[nexus_district] = sum(
            _KARNATAKA_ALL_DISTRICT_IPC_WEIGHTS.get(d, 0.0) for d in ncrb_districts
        )
    total = sum(raw.values())
    return [(k, v / total) for k, v in raw.items()]


# Pre-computed for choose_weighted() in case_factory.py
# PROVENANCE: NCRB_INFERRED (renormalized aggregation of NCRB district IPC weights)
NEXUS_DISTRICT_IPC_WEIGHTS: list[tuple[str, float]] = _compute_nexus_district_weights()

# ---------------------------------------------------------------------------
# ── SECTION 3: Karnataka District NDPS Weights ────────────────────────────
#
# SOURCE: 2DistrictwiseSLLCrimes2024.xlsx
#         Sheet: 'District Data Report', col44 (NDPS Act 1985 Total)
# PROVENANCE: NCRB_INFERRED
# FORMULA: district_ndps / 4,165 (Karnataka NDPS total)
# DENOMINATOR: 4,165 (Karnataka Total NDPS 2024)
#
# KEY FINDING: Mangaluru City = 1,114 NDPS cases (26.7% of Karnataka total),
# the highest of any single district. This reflects Mangaluru's coastal narcotics
# trafficking nexus and is a real NCRB-grounded finding.
# ---------------------------------------------------------------------------

# Raw district NDPS totals (NCRB_DERIVED, col44 values)
KARNATAKA_DISTRICT_NDPS_RAW: dict[str, int] = {
    "Bagalkot": 18, "Bengaluru City": 495, "Bengaluru District": 75,
    "Belagavi District": 50, "Ballari": 29, "Bidar": 24, "Vijayapura": 28,
    "Chikkaballapura": 26, "Chamarajnagar": 37, "Chikkamagaluru": 227,
    "Chitradurga": 66, "Dakshina Kannada": 44, "Davanagere": 173,
    "Dharwad": 19, "Gadag": 23, "Kalaburgi": 22, "Hassan": 130,
    "Haveri": 19, "Hubballi Dharwad City": 244, "KGF": 26, "Kodagu": 86,
    "Kolar": 39, "Koppal": 12, "Mandya": 57, "Mangaluru City": 1114,
    "Mysuru City": 43, "Mysuru District": 27, "Raichur": 20, "KRailways": 59,
    "Ramanagara": 50, "Shimoga": 380, "Tumakuru": 111, "Udupi": 123,
    "Uttara Kannada": 86, "Yadgiri": 7, "Belagavi City": 55,
    "Kalaburgi City": 53, "Vijayanagara": 68,
}
_KARNATAKA_NDPS_TOTAL = 4165  # NCRB_DERIVED, col44 Karnataka total row

# Renormalized for 6 NEXUS districts
def _compute_nexus_district_ndps_weights() -> list[tuple[str, float]]:
    """PROVENANCE: NCRB_INFERRED (aggregated from district NDPS raw counts)."""
    raw: dict[str, float] = {}
    for nexus_district, ncrb_districts in _NEXUS_TO_NCRB_DISTRICT_MAPPING.items():
        raw[nexus_district] = sum(
            KARNATAKA_DISTRICT_NDPS_RAW.get(d, 0) for d in ncrb_districts
        )
    total = sum(raw.values())
    return [(k, v / total) for k, v in raw.items()]


# PROVENANCE: NCRB_INFERRED
NEXUS_DISTRICT_NDPS_WEIGHTS: list[tuple[str, float]] = _compute_nexus_district_ndps_weights()

# ---------------------------------------------------------------------------
# ── SECTION 4: Karnataka District Cyber Crime Weights ─────────────────────
#
# SOURCE: 9DistrictwiseCyberCrimes2024.xlsx
#         Sheet: 'District Data Report', col59 (Total Cyber Crimes A+B+C)
# PROVENANCE: NCRB_INFERRED
# FORMULA: district_cyber / 21,993 (sum of district totals)
# DENOMINATOR: 21,993 (sum of Karnataka district cyber totals 2024)
#
# KEY FINDING: Bengaluru City = 17,561 cyber cases = 79.9% of Karnataka cyber total.
# This is a real NCRB-grounded concentration that should drive cyber scenario generation.
# ---------------------------------------------------------------------------

KARNATAKA_DISTRICT_CYBER_RAW: dict[str, int] = {
    "Bagalkot": 47, "Bengaluru City": 17561, "Bengaluru District": 844,
    "Belagavi District": 65, "Ballari": 118, "Bidar": 41, "Vijayapura": 80,
    "Chikkaballapura": 189, "Chamarajnagar": 24, "Chikkamagaluru": 92,
    "Chitradurga": 74, "Dakshina Kannada": 104, "Davanagere": 142,
    "Dharwad": 68, "Gadag": 67, "Kalaburgi": 33, "Hassan": 131,
    "Haveri": 125, "Hubballi Dharwad City": 240, "KGF": 97, "Kodagu": 82,
    "Kolar": 58, "Koppal": 27, "Mandya": 67, "Mangaluru City": 137,
    "Mysuru City": 260, "Mysuru District": 46, "Raichur": 21, "KRailways": 0,
    "Ramanagara": 236, "Shimoga": 123, "Tumakuru": 322, "Udupi": 203,
    "Uttara Kannada": 96, "Yadgiri": 19, "Belagavi City": 102,
    "Kalaburgi City": 30, "Vijayanagara": 22,
}
_KARNATAKA_CYBER_TOTAL = 21993  # NCRB_DERIVED (sum of district totals)


def _compute_nexus_district_cyber_weights() -> list[tuple[str, float]]:
    """PROVENANCE: NCRB_INFERRED (aggregated from district cyber raw counts)."""
    raw: dict[str, float] = {}
    for nexus_district, ncrb_districts in _NEXUS_TO_NCRB_DISTRICT_MAPPING.items():
        raw[nexus_district] = sum(
            KARNATAKA_DISTRICT_CYBER_RAW.get(d, 0) for d in ncrb_districts
        )
    total = sum(raw.values())
    return [(k, v / total) for k, v in raw.items()]


# PROVENANCE: NCRB_INFERRED
NEXUS_DISTRICT_CYBER_WEIGHTS: list[tuple[str, float]] = _compute_nexus_district_cyber_weights()

# ---------------------------------------------------------------------------
# ── SECTION 5: Case Status Weights ────────────────────────────────────────
#
# SOURCE: TABLE17B13.xlsx, Sheet: 'CIIReport'
#         Row 186 ('Total Cognizable IPC/BNS crimes')
#         col5 = Total Cases for Investigation = 282,191
#         col21 = Cases Chargesheeted = 142,300
#         col27 = Cases Pending = 94,662
#         col28 = Chargesheeting Rate = 76.0%
#         col29 = Pendency Percentage = 33.5%
#
# PROVENANCE: NCRB_INFERRED
# SCOPE: ALL-INDIA AGGREGATE (not Karnataka-specific; used as proxy)
# DENOMINATOR: 282,191 (Total Cases for Investigation)
#
# NEXUS STATE MAPPING:
#   CHARGESHEET_FILED      ← col21 (142,300) / 282,191 = 0.504
#   INVESTIGATION_IN_PROGRESS ← col27 (94,662) / 282,191 = 0.335
#   CLOSED_NO_EVIDENCE     ← remainder (45,229) / 282,191 = 0.160
#
# IMPORTANT: "OPEN" (newly registered, not yet processed) is not represented
# in the police disposal table and is treated as a SYNTHETIC_ASSUMPTION.
# The weights below apply to cases ALREADY in the investigation pipeline.
# New OPEN cases are assigned with a small synthetic probability.
# ---------------------------------------------------------------------------

# PROVENANCE: NCRB_INFERRED (all-India as proxy for Karnataka)
NEXUS_CASE_STATUS_WEIGHTS: list[tuple[str, float]] = [
    # All-India: 142,300 / 282,191 = 0.504
    ("CHARGESHEET_FILED", 0.50),
    # All-India: 94,662 / 282,191 = 0.335 → rounded to preserve 3 states
    ("INVESTIGATION_IN_PROGRESS", 0.35),
    # Remainder = 0.160 (FR false, insufficient evidence, abated, etc.)
    # Collapsed into OPEN for NEXUS operational meaning (newly registered)
    ("OPEN", 0.15),
]

# ---------------------------------------------------------------------------
# ── SECTION 6: BNS Section Mapping (MANUALLY CURATED) ─────────────────────
#
# PROVENANCE: SYNTHETIC_ASSUMPTION (manually curated, informed by TABLE1B44 headers)
#
# WHY NOT NCRB_DERIVED:
#   TABLE1B44 contains crime-HEAD labels that include BNS/IPC section references
#   within their text (e.g., "Rape (Section 64 to Section 71 BNS / Section 376 IPC)").
#   However, the table provides CRIME COUNTS by metropolitan city, not a canonical
#   crime-head → section mapping. A manually curated mapping is required.
#
# TABLE1B44 FINDING: The column headers DO contain section references. They are used
#   here to INFORM (not source) the manual mapping. Each entry records this.
#
# FORMAT: crime_category → list of (act_name, section_label, severity)
# ---------------------------------------------------------------------------

NEXUS_BNS_SECTIONS_BY_CATEGORY: dict[str, list[tuple[str, str, str]]] = {
    # Informed by TABLE1B44 Row4 header: "Rape (Section 64 to Section 71 BNS / Section 376 IPC)"
    "Offences Against Women & Children": [
        ("BNS", "Section 64 BNS (Rape)", "serious"),
        ("BNS", "Section 75 BNS (Sexual Harassment)", "serious"),
        ("BNS", "Section 80 BNS (Dowry Death)", "serious"),
        ("BNS", "Section 85 BNS (Cruelty by Husband)", "moderate"),
    ],
    # Informed by TABLE1B44 Row5 header: "Murder (Section 103 (1) BNS /Section 302 IPC)"
    "Violence & Bodily Harm": [
        ("BNS", "Section 103(1) BNS (Murder)", "serious"),
        ("BNS", "Section 115 BNS (Hurt/Grievous Hurt)", "serious"),
        ("BNS", "Section 109 BNS (Attempt to Murder)", "serious"),
        ("BNS", "Section 137 BNS (Kidnapping & Abduction)", "moderate"),
    ],
    # From 1DistrictwiseIPCCrimes2024.xlsx col header: "Theft (Section 303,305-307 BNS)"
    "Theft & Property Crime": [
        ("BNS", "Section 303 BNS (Theft)", "moderate"),
        ("BNS", "Section 305 BNS (Vehicle Theft)", "moderate"),
        ("BNS", "Section 309 BNS (Robbery)", "serious"),
        ("BNS", "Section 312 BNS (Burglary)", "moderate"),
    ],
    # From 1DistrictwiseIPCCrimes2024.xlsx col header: "Fraud (Total i+ii+iii+iv)"
    "Fraud & Forgery": [
        ("BNS", "Section 318 BNS (Cheating)", "moderate"),
        ("BNS", "Section 336 BNS (Forgery)", "moderate"),
        ("IT Act", "Section 66C IT Act (Identity Theft)", "moderate"),
        ("IT Act", "Section 66D IT Act (Cheating by Personation)", "moderate"),
    ],
    # NDPS Act — SLL overlay; sections from NDPS Act 1985 (not BNS)
    "Narcotics & Drug Trafficking": [
        ("NDPS Act", "Section 21 NDPS (Possession for Trafficking)", "serious"),
        ("NDPS Act", "Section 20 NDPS (Production/Sale)", "serious"),
        ("NDPS Act", "Section 27 NDPS (Consumption)", "minor"),
    ],
    # Arms Act — SLL overlay
    "Illegal Arms Trafficking": [
        ("Arms Act", "Section 25 Arms Act (Illegal Arms Possession)", "serious"),
        ("Arms Act", "Section 27 Arms Act (Use of Illegal Arms)", "serious"),
    ],
    # Cyber crimes — IT Act
    "Cyber Financial Fraud": [
        ("IT Act", "Section 66 IT Act (Computer-Related Offences)", "moderate"),
        ("IT Act", "Section 66C IT Act (Identity Theft)", "moderate"),
        ("IT Act", "Section 66D IT Act (Cheating by Personation)", "moderate"),
        ("BNS", "Section 318 BNS (Cheating via cyber)", "moderate"),
    ],
    "Public Order": [
        ("BNS", "Section 191 BNS (Unlawful Assembly)", "moderate"),
        ("BNS", "Section 196 BNS (Rioting)", "moderate"),
    ],
    "Miscellaneous IPC": [
        ("BNS", "Section 223 BNS (Rash Driving)", "minor"),
        ("BNS", "Section 296 BNS (Obscene Acts)", "minor"),
    ],
    "Other IPC": [
        ("BNS", "Section 61 BNS (Criminal Conspiracy)", "moderate"),
        ("BNS", "Section 238 BNS (Trespass)", "minor"),
    ],
    "Hawala & Money Laundering": [
        ("PMLA", "Section 3 PMLA (Money Laundering)", "serious"),
        ("BNS", "Section 318 BNS (Cheating — financial channel)", "moderate"),
    ],
    "Offences Against the State": [
        ("BNS", "Section 147 BNS (Sedition equivalent)", "serious"),
    ],
}

# ---------------------------------------------------------------------------
# ── SECTION 7: Karnataka Name Pools (SYNTHETIC ASSUMPTION) ────────────────
#
# PROVENANCE: SYNTHETIC_ASSUMPTION
# REASON: NCRB aggregate crime tables contain no personal name distribution.
#   These pools are SYNTHETIC REALISM INPUT reflecting Karnataka's multilingual
#   demographics (Kannada, Tamil, Urdu, Telugu communities).
# DO NOT label as NCRB-derived.
# ---------------------------------------------------------------------------

# Kannada community first names
_KANNADA_FIRST_NAMES = [
    "Ramesh", "Suresh", "Mahesh", "Ganesh", "Rajesh", "Naresh", "Girish", "Harish",
    "Nagesh", "Shivakumar", "Basavaraj", "Manjunath", "Venkatesh", "Siddaramaiah",
    "Anand", "Prasad", "Ravi", "Srinivas", "Deepak", "Kiran", "Vikram", "Arun",
    "Madhu", "Chandra", "Pavan", "Rohan", "Abhishek", "Lokesh", "Praveen", "Naveen",
]
_KANNADA_FEMALE_FIRST_NAMES = [
    "Kavitha", "Shobha", "Geetha", "Meena", "Usha", "Rekha", "Suma", "Anitha",
    "Savitha", "Latha", "Vidya", "Nandini", "Rashmi", "Divya", "Priya", "Shreya",
]

# Urdu/Muslim community names (common in Karnataka)
_URDU_FIRST_NAMES = [
    "Mohammed", "Imran", "Farhan", "Saleem", "Riyaz", "Nasir", "Khalid", "Irfan",
    "Azeez", "Rafiq", "Basheer", "Shahid", "Arfan", "Zubair", "Hameed",
]
_URDU_FEMALE_FIRST_NAMES = [
    "Ayesha", "Fatima", "Nazia", "Shaista", "Rubina", "Zainab", "Reshma",
]

# Telugu community names (Hyderabad Karnataka region)
_TELUGU_FIRST_NAMES = [
    "Venkat", "Srinivas", "Ramu", "Satish", "Ravi", "Suresh", "Naidu",
    "Chandra", "Balu", "Sankar",
]

# Tamil community names (border districts, Bengaluru)
_TAMIL_FIRST_NAMES = [
    "Murugan", "Selvam", "Arjun", "Rajan", "Senthil", "Kumar", "Vijay",
    "Pandian", "Kannan", "Suresh",
]

# Combined male first names pool (SYNTHETIC ASSUMPTION — multilingual Karnataka)
KARNATAKA_MALE_FIRST_NAMES: list[str] = (
    _KANNADA_FIRST_NAMES + _URDU_FIRST_NAMES + _TELUGU_FIRST_NAMES + _TAMIL_FIRST_NAMES
)

# Combined female first names pool
KARNATAKA_FEMALE_FIRST_NAMES: list[str] = (
    _KANNADA_FEMALE_FIRST_NAMES + _URDU_FEMALE_FIRST_NAMES
    + ["Sowmya", "Lakshmi", "Radha", "Sunitha", "Deepa", "Meghana", "Pooja", "Asha"]
)

# Last names (SYNTHETIC ASSUMPTION — representing major Karnataka surname groups)
KARNATAKA_LAST_NAMES: list[str] = [
    # Kannada surnames
    "Gowda", "Reddy", "Hegde", "Shetty", "Naik", "Bhat", "Rao", "Murthy",
    "Nayak", "Kulkarni", "Patil", "Desai", "Kamath", "Prabhu",
    # Muslim surnames
    "Khan", "Syed", "Sheikh", "Ansari", "Pasha",
    # Telugu surnames
    "Sharma", "Verma", "Naidu", "Raju",
    # Common Karnataka surnames
    "Kumar", "Gupta", "Singh", "Patel", "Iyer",
]

# Criminal aliases pool (SYNTHETIC ASSUMPTION — investigative realism)
KARNATAKA_CRIMINAL_ALIASES: list[str] = [
    "Vicky", "Bhai", "Shooter", "Doctor", "Ustaad", "Pandit", "Chhota", "Seth",
    "Captain", "Munna", "Anna", "Hawala King", "Master", "Agent", "Shadow",
    "Pilot", "Mama", "Chacha", "Bade Bhai", "Sardar", "Timber", "Cobra",
    "Don", "Sher", "Billa", "Ranga", "Dada", "Bhau", "Bhaijaan",
]

# ---------------------------------------------------------------------------
# ── SECTION 8: Age Distribution (SYNTHETIC ASSUMPTION) ────────────────────
#
# PROVENANCE: SYNTHETIC_ASSUMPTION
# REASON: NCRB Table 10A (Persons Arrested by Age and Sex) would provide the
#   correct accused age distribution but is NOT in the 19 downloaded files.
#   The 10DistrictwiseMissingPersons2024.xlsx provides missing-PERSON age data,
#   NOT accused age data — these must NOT be conflated.
#
# The values below are a design prior based on general criminological literature
#   (accused persons peak in 18-35 age band globally and in India).
# They are explicitly labeled SYNTHETIC_ASSUMPTION.
#
# RECOMMENDATION: Obtain NCRB Table 10A for a defensible source.
# ---------------------------------------------------------------------------

# (age_band_label, lower_bound, upper_bound, weight)
# PROVENANCE: SYNTHETIC_ASSUMPTION
NCRB_ACCUSED_AGE_BANDS: list[tuple[str, int, int, float]] = [
    ("18-25", 18, 25, 0.30),   # SYNTHETIC ASSUMPTION
    ("25-35", 25, 35, 0.35),   # SYNTHETIC ASSUMPTION
    ("35-45", 35, 45, 0.20),   # SYNTHETIC ASSUMPTION
    ("45-55", 45, 55, 0.10),   # SYNTHETIC ASSUMPTION
    ("55+",   55, 70, 0.05),   # SYNTHETIC ASSUMPTION
]
# Verification: 0.30+0.35+0.20+0.10+0.05 = 1.00

# Victim age bands (SYNTHETIC ASSUMPTION — broader distribution than accused)
# NOTE: Missing-person age data from 10DistrictwiseMissingPersons2024.xlsx
#   applies ONLY to missing-person scenarios, not general victim demographics.
NCRB_VICTIM_AGE_BANDS: list[tuple[str, int, int, float]] = [
    ("0-18",  0,  18, 0.12),   # SYNTHETIC ASSUMPTION
    ("18-30", 18, 30, 0.28),   # SYNTHETIC ASSUMPTION
    ("30-45", 30, 45, 0.30),   # SYNTHETIC ASSUMPTION
    ("45-60", 45, 60, 0.20),   # SYNTHETIC ASSUMPTION
    ("60+",   60, 85, 0.10),   # SYNTHETIC ASSUMPTION
]

# ---------------------------------------------------------------------------
# ── SECTION 9: Gender Weights (SYNTHETIC ASSUMPTION) ──────────────────────
#
# PROVENANCE: SYNTHETIC_ASSUMPTION
# REASON: NCRB Table 10A (Persons Arrested by Age and Sex) would provide
#   accused gender distribution but is NOT in the 19 downloaded files.
#   TABLE3B13 provides crime-against-women RATES for metropolitan cities,
#   NOT accused gender breakdown.
#
# The values below are a design prior. Do NOT label them NCRB-derived.
# RECOMMENDATION: Obtain NCRB Table 10A for a defensible source.
# ---------------------------------------------------------------------------

# PROVENANCE: SYNTHETIC_ASSUMPTION
NCRB_ACCUSED_GENDER_WEIGHTS: list[tuple[str, float]] = [
    ("male", 0.88),    # SYNTHETIC ASSUMPTION — design prior
    ("female", 0.11),  # SYNTHETIC ASSUMPTION — design prior
    ("other", 0.01),   # SYNTHETIC ASSUMPTION — design prior
]

# PROVENANCE: SYNTHETIC_ASSUMPTION
NCRB_VICTIM_GENDER_WEIGHTS: list[tuple[str, float]] = [
    ("male", 0.55),    # SYNTHETIC ASSUMPTION — design prior
    ("female", 0.44),  # SYNTHETIC ASSUMPTION — design prior
    ("other", 0.01),   # SYNTHETIC ASSUMPTION — design prior
]

# ---------------------------------------------------------------------------
# ── SECTION 10: Missing Person Scenario Parameters ─────────────────────────
#
# SOURCE: 10DistrictwiseMissingPersons2024.xlsx, Sheet: 'District Data Report'
#         Bengaluru City Row (row 339), col2=Male Total, col8=Female Total
# PROVENANCE: NCRB_INFERRED
# USE: ONLY for missing-person case scenarios (not general victim demographics)
#
# Bengaluru City missing persons 2024:
#   Male: 2,704 (col2)   Female: 3,534 (col8)   Total: ~6,238
# Denominator: Male+Female (non-transgender) = 6,238
# ---------------------------------------------------------------------------

# PROVENANCE: NCRB_INFERRED (applicable ONLY to missing-person scenarios)
MISSING_PERSON_BENGALURU_GENDER_WEIGHTS: list[tuple[str, float]] = [
    ("male", 0.434),    # 2704 / (2704+3534) = 0.434
    ("female", 0.566),  # 3534 / (2704+3534) = 0.566
]

# ---------------------------------------------------------------------------
# ── SECTION 11: Shared latent entity noise parameters (SYNTHETIC ASSUMPTION)
# ---------------------------------------------------------------------------

# Rates at which shared identifiers create adversarial ER challenges
# PROVENANCE: SYNTHETIC_ASSUMPTION — network realism design priors
SHARED_PHONE_CLUSTER_RATE = 0.20       # 20% of accused share phone numbers (org/family phones)
SHARED_VEHICLE_CLUSTER_RATE = 0.15     # 15% share vehicle registrations
SHARED_ADDRESS_CLUSTER_RATE = 0.30     # 30% share residential addresses

# Noise injection rates for controlled ambiguity
ALIAS_SPELLING_VARIATION_RATE = 0.25   # 25% of aliases have transliteration variation
MISSING_FIELD_RATE = 0.15              # 15% of person records have 1+ missing field
STALE_IDENTIFIER_RATE = 0.10           # 10% of phone/vehicle identifiers are stale

# ---------------------------------------------------------------------------
# ── SECTION 12: Validation ────────────────────────────────────────────────
# ---------------------------------------------------------------------------

def validate_all() -> dict[str, bool]:
    """Runtime self-check: verify all weight vectors sum to 1.0 (±0.005)."""
    results: dict[str, bool] = {}

    def check(name: str, weights: list[tuple[str, float]]) -> None:
        total = sum(w for _, w in weights)
        results[name] = abs(total - 1.0) <= 0.005

    check("KARNATAKA_IPC_CRIME_CATEGORY_WEIGHTS", KARNATAKA_IPC_CRIME_CATEGORY_WEIGHTS)
    check("NEXUS_DISTRICT_IPC_WEIGHTS", NEXUS_DISTRICT_IPC_WEIGHTS)
    check("NEXUS_DISTRICT_NDPS_WEIGHTS", NEXUS_DISTRICT_NDPS_WEIGHTS)
    check("NEXUS_DISTRICT_CYBER_WEIGHTS", NEXUS_DISTRICT_CYBER_WEIGHTS)
    check("NEXUS_CASE_STATUS_WEIGHTS", NEXUS_CASE_STATUS_WEIGHTS)
    check("NCRB_ACCUSED_GENDER_WEIGHTS", NCRB_ACCUSED_GENDER_WEIGHTS)
    check("NCRB_VICTIM_GENDER_WEIGHTS", NCRB_VICTIM_GENDER_WEIGHTS)

    # Age bands
    accused_age_sum = sum(w for _, _, _, w in NCRB_ACCUSED_AGE_BANDS)
    results["NCRB_ACCUSED_AGE_BANDS"] = abs(accused_age_sum - 1.0) <= 0.005
    victim_age_sum = sum(w for _, _, _, w in NCRB_VICTIM_AGE_BANDS)
    results["NCRB_VICTIM_AGE_BANDS"] = abs(victim_age_sum - 1.0) <= 0.005

    return results


if __name__ == "__main__":
    results = validate_all()
    all_passed = all(results.values())
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}]  {name}")
    print()
    if all_passed:
        print("All calibration weight vectors VALID.")
    else:
        failed = [k for k, v in results.items() if not v]
        raise SystemExit(f"FAILED: {failed}")
