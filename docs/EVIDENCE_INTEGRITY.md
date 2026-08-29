# NEXUS Evidence Integrity Architecture

This document explains the cryptographic evidence integrity architecture implemented in NEXUS. It details how the platform ensures that the source records underpinning analytical graphs remain untampered and mathematically verifiable.

## 1. Why NEXUS Uses Hashing

In a law enforcement and intelligence context, any graph edge (e.g., an "ACCUSED_IN" or "CALLED" relationship) must be traceable back to a source of truth, such as an FIR or CDR. By hashing these source records upon ingestion and storing the hashes, NEXUS ensures:
- **Tamper-Evidence:** Any unauthorized modification of the source record will result in a mismatched hash.
- **Auditability:** Investigators can independently verify that the data they are viewing matches the exact bytes ingested by the platform.
- **Trust in Intelligence:** Downstream insights, clustering, and AI-generated Copilot answers are grounded in cryptographically verified records, avoiding black-box hallucination.

## 2. What is Hashed

Currently, the hashing layer focuses on the **SourceRecord**. A `SourceRecord` represents a single row of an ingested dataset (e.g., one FIR case, one CDR call, one Bank Transaction).

When a CSV is ingested:
- The parser extracts the raw row as a dictionary.
- The dictionary is canonicalized.
- The canonicalized string is hashed using SHA-256.
- The `SourceRecord` is persisted with its `content_hash`, `hash_algorithm`, `hash_version`, and `hashed_at` timestamp.

## 3. Canonicalization

To ensure that hashing is deterministic regardless of Python dictionary ordering or whitespace variations, NEXUS uses a strict canonicalization process before hashing.

The `canonicalize_csv_row` function:
1. Sorts the dictionary keys alphabetically.
2. Serializes the dictionary to a JSON string using `ensure_ascii=False` to preserve raw UTF-8 characters.
3. Uses strict separators `(",", ":")` without spaces.
4. Coerces non-string values to strings before serialization.

This canonical representation is also stored as the `raw_excerpt` on the `SourceRecord`, ensuring that the exact bytes hashed are the exact bytes stored.

## 4. SHA-256 Process

NEXUS exclusively uses `SHA-256` for cryptographic integrity.
- It is a standard, collision-resistant algorithm.
- MD5 and SHA-1 are explicitly banned due to known vulnerabilities.
- The hash is generated from the UTF-8 encoded canonical string of the source record.

## 5. Verification Flow

Verification does not rely on simply reading the `content_hash` field from the database (which could theoretically be tampered with alongside the record).

Instead, the verification flow is an active process:
1. An investigator clicks **[Verify Integrity]** in the Evidence Drawer.
2. The frontend calls the backend endpoint: `POST /api/v1/nexus/sources/{source_id}/verify`.
3. The backend retrieves the `SourceRecord` from the database.
4. It extracts the `raw_excerpt` (the canonicalized source data) and **re-computes** the SHA-256 hash.
5. It compares the newly computed hash against the stored `content_hash`.
6. If they match, the record is `VERIFIED`.
7. If they differ, an `INTEGRITY MISMATCH` is triggered.
8. The result is returned to the frontend and logged to the `AuditService`.

## 6. Evidence vs. Audit Hashes

It is important to distinguish between the two layers of hashing in NEXUS:
- **Evidence Hash (`content_hash`):** The hash of a single source record (e.g., an FIR row). It ensures the integrity of the data itself.
- **Audit Chain Hash / Hop Hash:** When verifying an evidence dossier (a collection of records) or a graph path, the individual evidence hashes are concatenated and hashed again (`compute_path_chain_hash`) to create a tamper-evident audit chain. This proves that the specific collection of records existed together in that state.

## 7. What Hashing Does NOT Guarantee

- **Truthfulness of Source:** Hashing proves that the record in NEXUS is exactly what was ingested. It does *not* prove that the original police officer typed the FIR correctly.
- **Encryption/Privacy:** Hashing is for integrity, not confidentiality. The `SourceRecord` data remains readable in the database.
- **Immutability without External Anchoring:** A highly privileged attacker with direct database access could theoretically alter both the `raw_excerpt` and the `content_hash`. This is why audit logs and future blockchain anchoring are necessary.

## 8. Why Blockchain is Not Required for Every Record

NEXUS does not write every source record or hash directly to a blockchain. This is an intentional architectural decision:
- **Scalability:** Law enforcement datasets contain tens of millions of CDR and transaction rows. Public blockchains cannot handle this throughput efficiently.
- **Cost:** Transaction fees for millions of records would be prohibitive.
- **Privacy:** Even hashed PII should not be placed on public ledgers unnecessarily if local integrity checks suffice for the prototype phase.

## 9. Future Architecture: Merkle-Tree Anchoring

To achieve true immutability in the future without the scalability issues of putting every record on-chain, NEXUS is designed to support Merkle-Tree batch anchoring:

1. **Local Hashes:** Millions of evidence records receive individual SHA-256 hashes locally.
2. **Merkle Tree:** These hashes are structured into a daily or batch-based Merkle Tree.
3. **Merkle Root:** A single Merkle Root is generated representing the entire batch.
4. **Anchor:** Only the Merkle Root is anchored to a trusted ledger or blockchain.
5. **Verification:** Any individual record's integrity can be proven by providing its local hash and the Merkle proof connecting it to the anchored root.

This future architecture ensures mathematical immutability while maintaining high throughput and low cost.
