/**
 * frontend/src/lib/mocks/nexusFixture.ts
 *
 * Golden demo fixture for the NEXUS prototype (M4 frozen contract).
 *
 * Story: two apparently separate cases — FIR 141/2026 (Mysuru South, human
 * trafficking) and FIR 207/2026 (Bengaluru CEN, financial fraud) — become one
 * connected network after the investigator confirms a single entity-resolution
 * candidate (planted alias "Rafiq Khan" / "Rafiq Ahmed" sharing one phone).
 *
 * All data is synthetic. No real citizen PII.
 */
import type {
  NexusEdgeEvidenceResponse,
  NexusGraphEdge,
  NexusGraphNode,
  NexusLead,
  NexusSourceRecord,
  ResolutionCandidate,
  SnapshotDiffResponse,
} from '@shared/contracts/api'

// ─── Source records (raw evidence with locators) ─────────────────────────────

const SRC: Record<string, NexusSourceRecord> = {
  'SRC-FIR-141': {
    id: 'SRC-FIR-141', batch_id: 'BATCH-2026-08-24', source_type: 'FIR',
    locator: 'fir_141_2026.pdf — page 2, row 4 (accused list)',
    raw_excerpt: 'Accused: Rafiq Khan, s/o Iqbal Khan, age 35, res. Hootagalli, Mysuru. Mobile disclosed: +91 98450 11223.',
    occurred_at: '2026-02-11T09:30:00Z',
  },
  'SRC-FIR-207': {
    id: 'SRC-FIR-207', batch_id: 'BATCH-2026-08-24', source_type: 'FIR',
    locator: 'fir_207_2026.pdf — page 1, row 7 (accused list)',
    raw_excerpt: 'Accused: Rafiq Ahmed, s/o Iqbal Khan, age 35, res. Hootagalli Colony, Mysuru. Mobile: +91 98450 11223.',
    occurred_at: '2026-03-02T14:15:00Z',
  },
  'SRC-CDR-A12': {
    id: 'SRC-CDR-A12', batch_id: 'BATCH-2026-08-24', source_type: 'CDR',
    locator: 'cdr_mysuru_feb.csv — row 1287 (A-party +91 98450 11223)',
    raw_excerpt: '2026-02-14T22:41:05Z, +91 98450 11223 → +91 99801 55210, duration 412s, cell 4701-Hootagalli.',
    occurred_at: '2026-02-14T22:41:05Z',
  },
  'SRC-CDR-B31': {
    id: 'SRC-CDR-B31', batch_id: 'BATCH-2026-08-24', source_type: 'CDR',
    locator: 'cdr_bengaluru_mar.csv — row 4402 (A-party +91 98450 11223)',
    raw_excerpt: '2026-03-05T02:12:44Z, +91 98450 11223 → +91 98450 77310, duration 96s, cell 6112-Whitefield.',
    occurred_at: '2026-03-05T02:12:44Z',
  },
  'SRC-TXN-55': {
    id: 'SRC-TXN-55', batch_id: 'BATCH-2026-08-24', source_type: 'BANK_TXN',
    locator: 'txns_axis_9914.csv — row 55',
    raw_excerpt: '2026-03-09T11:03:00Z, ACC-9914 → ACC-7731, ₹4,80,000, ref NIFT/20260309/5521.',
    occurred_at: '2026-03-09T11:03:00Z',
  },
  'SRC-TXN-71': {
    id: 'SRC-TXN-71', batch_id: 'BATCH-2026-08-24', source_type: 'BANK_TXN',
    locator: 'txns_axis_9914.csv — row 71',
    raw_excerpt: '2026-03-11T16:47:00Z, ACC-9914 → ACC-7731, ₹2,15,000, ref NIFT/20260311/8830.',
    occurred_at: '2026-03-11T16:47:00Z',
  },
}

// ─── Resolution candidate (the planted alias) ────────────────────────────────

export const CANDIDATE_RC1: ResolutionCandidate = {
  id: 'RC-1',
  score: 0.86,
  status: 'PENDING',
  left: {
    node_id: 'P-RAFIQ-K', entity_type: 'Person', label: 'Rafiq Khan',
    case_ids: ['CASE-141'],
    properties: {
      full_name: 'Rafiq Khan', father_name: 'Iqbal Khan', age: 35,
      dob: '1991-03-14', address: 'Hootagalli, Mysuru',
      phone: '+91 98450 11223', role: 'Accused (FIR 141/2026)',
    },
    source_records: [SRC['SRC-FIR-141'], SRC['SRC-CDR-A12']],
  },
  right: {
    node_id: 'P-RAFIQ-A', entity_type: 'Person', label: 'Rafiq Ahmed',
    case_ids: ['CASE-207'],
    properties: {
      full_name: 'Rafiq Ahmed', father_name: 'Iqbal Khan', age: 35,
      dob: '1991-04-13', address: 'Hootagalli Colony, Mysuru',
      phone: '+91 98450 11223', role: 'Accused (FIR 207/2026)',
    },
    source_records: [SRC['SRC-FIR-207'], SRC['SRC-CDR-B31']],
  },
  reasons: [
    { field: 'phone', detail: 'Identical primary mobile +91 98450 11223 appears in both CDR pulls', weight: 0.40 },
    { field: 'father_name', detail: 'Father\'s name "Iqbal Khan" matches exactly in both FIRs', weight: 0.25 },
    { field: 'address', detail: 'Address locality "Hootagalli, Mysuru" matches with granularity difference', weight: 0.21 },
  ],
  conflicts: [
    { field: 'name', left_value: 'Rafiq Khan', right_value: 'Rafiq Ahmed' },
    { field: 'dob', left_value: '1991-03-14', right_value: '1991-04-13 (day/month transposition)' },
    { field: 'age', left_value: '35', right_value: '35 (consistent)' },
  ],
}

// ─── Graph snapshots ─────────────────────────────────────────────────────────

const CASE_141: NexusGraphNode = {
  id: 'CASE-141', entity_type: 'Case', label: 'FIR 141/2026 — Trafficking',
  case_ids: ['CASE-141'],
  properties: { fir_number: '141/2026', station: 'Mysuru South WS PS', district: 'Mysuru', offence: 'Human Trafficking (BNS 143)' },
}
const CASE_207: NexusGraphNode = {
  id: 'CASE-207', entity_type: 'Case', label: 'FIR 207/2026 — Fraud',
  case_ids: ['CASE-207'],
  properties: { fir_number: '207/2026', station: 'Bengaluru CEN PS', district: 'Bengaluru', offence: 'Financial Fraud (BNS 318)' },
}
const P_MEENA: NexusGraphNode = {
  id: 'P-MEENA', entity_type: 'Person', label: 'Meena Devi (Victim)',
  case_ids: ['CASE-141'], properties: { role: 'Victim', statement: 'dated 2026-02-13' },
}
const P_DEEPAK: NexusGraphNode = {
  id: 'P-DEEPAK', entity_type: 'Person', label: 'Deepak Rao (Associate)',
  case_ids: ['CASE-207'], properties: { role: 'Co-accused', phone: '+91 99801 55210' },
}
const ACC_7731: NexusGraphNode = {
  id: 'ACC-7731', entity_type: 'Account', label: 'ACC-7731 (Axis)',
  case_ids: ['CASE-141'], properties: { bank: 'Axis Bank', holder: 'Rafiq Khan' },
}
const ACC_9914: NexusGraphNode = {
  id: 'ACC-9914', entity_type: 'Account', label: 'ACC-9914 (Axis)',
  case_ids: ['CASE-207'], properties: { bank: 'Axis Bank', holder: 'Deepak Rao' },
}
const PH_A: NexusGraphNode = {
  id: 'PH-A', entity_type: 'Phone', label: '+91 98450 11223 (CDR: Mysuru)',
  case_ids: ['CASE-141'], properties: { number: '+91 98450 11223', seen_in: 'cdr_mysuru_feb.csv' },
}
const PH_B: NexusGraphNode = {
  id: 'PH-B', entity_type: 'Phone', label: '+91 98450 11223 (CDR: Bengaluru)',
  case_ids: ['CASE-207'], properties: { number: '+91 98450 11223', seen_in: 'cdr_bengaluru_mar.csv' },
}

const E = (
  id: string, source_id: string, target_id: string, edge_type: string,
  derivation_class: NexusGraphEdge['derivation_class'], confidence: number,
  recorded_at: string, case_ids: string[], evidence: string[],
): NexusGraphEdge => ({
  id, source_id, target_id, edge_type, weight: 1, confidence,
  derivation_class, recorded_at, case_ids,
  properties: { evidence_ids: evidence },
})

export const BEFORE_NODES: NexusGraphNode[] = [
  CASE_141, CASE_207, P_MEENA, P_DEEPAK, ACC_7731, ACC_9914, PH_A, PH_B,
  { id: 'P-RAFIQ-K', entity_type: 'Person', label: 'Rafiq Khan (Accused)', case_ids: ['CASE-141'],
    properties: { role: 'Accused', phone: '+91 98450 11223' } },
  { id: 'P-RAFIQ-A', entity_type: 'Person', label: 'Rafiq Ahmed (Accused)', case_ids: ['CASE-207'],
    properties: { role: 'Accused', phone: '+91 98450 11223' } },
]

export const BEFORE_EDGES: NexusGraphEdge[] = [
  E('E-ACCUSE-141', 'P-RAFIQ-K', 'CASE-141', 'ACCUSED_IN', 'FACT', 1.0, '2026-02-11T09:30:00Z', ['CASE-141'], ['SRC-FIR-141']),
  E('E-VICTIM-141', 'P-MEENA', 'CASE-141', 'VICTIM_IN', 'FACT', 1.0, '2026-02-11T09:30:00Z', ['CASE-141'], ['SRC-FIR-141']),
  E('E-USEPH-A', 'P-RAFIQ-K', 'PH-A', 'USES_PHONE', 'FACT', 0.98, '2026-02-14T22:41:05Z', ['CASE-141'], ['SRC-CDR-A12']),
  E('E-OWN-7731', 'P-RAFIQ-K', 'ACC-7731', 'OWNS_ACCOUNT', 'FACT', 0.95, '2026-02-12T10:00:00Z', ['CASE-141'], ['SRC-FIR-141']),
  E('E-ACCUSE-207', 'P-RAFIQ-A', 'CASE-207', 'ACCUSED_IN', 'FACT', 1.0, '2026-03-02T14:15:00Z', ['CASE-207'], ['SRC-FIR-207']),
  E('E-COACC-207', 'P-DEEPAK', 'CASE-207', 'CO_ACCUSED_IN', 'FACT', 1.0, '2026-03-02T14:15:00Z', ['CASE-207'], ['SRC-FIR-207']),
  E('E-USEPH-B', 'P-RAFIQ-A', 'PH-B', 'USES_PHONE', 'FACT', 0.98, '2026-03-05T02:12:44Z', ['CASE-207'], ['SRC-CDR-B31']),
  E('E-OWN-9914', 'P-DEEPAK', 'ACC-9914', 'OWNS_ACCOUNT', 'FACT', 0.95, '2026-03-02T14:15:00Z', ['CASE-207'], ['SRC-FIR-207']),
  E('E-TXN-55', 'ACC-9914', 'ACC-7731', 'TRANSFERRED_TO', 'FACT', 1.0, '2026-03-09T11:03:00Z', ['CASE-207', 'CASE-141'], ['SRC-TXN-55']),
  E('E-TXN-71', 'ACC-9914', 'ACC-7731', 'TRANSFERRED_TO', 'FACT', 1.0, '2026-03-11T16:47:00Z', ['CASE-207', 'CASE-141'], ['SRC-TXN-71']),
]

export const AFTER_NODES: NexusGraphNode[] = [
  CASE_141, CASE_207, P_MEENA, P_DEEPAK, ACC_7731, ACC_9914,
  { id: 'P-RAFIQ', entity_type: 'Person', label: 'Rafiq Khan / Rafiq Ahmed',
    case_ids: ['CASE-141', 'CASE-207'], badges: ['CROSS_CASE_BRIDGE', 'COMMUNITY-C1'],
    properties: { role: 'Accused in both FIRs', phone: '+91 98450 11223', aliases: ['Rafiq Khan', 'Rafiq Ahmed'] } },
  { id: 'PH-UNIFIED', entity_type: 'Phone', label: '+91 98450 11223 (shared)',
    case_ids: ['CASE-141', 'CASE-207'],
    properties: { number: '+91 98450 11223', seen_in: 'cdr_mysuru_feb.csv, cdr_bengaluru_mar.csv' } },
]

export const AFTER_EDGES: NexusGraphEdge[] = [
  E('E-ACCUSE-141', 'P-RAFIQ', 'CASE-141', 'ACCUSED_IN', 'FACT', 1.0, '2026-02-11T09:30:00Z', ['CASE-141'], ['SRC-FIR-141']),
  E('E-VICTIM-141', 'P-MEENA', 'CASE-141', 'VICTIM_IN', 'FACT', 1.0, '2026-02-11T09:30:00Z', ['CASE-141'], ['SRC-FIR-141']),
  E('E-USEPH-1', 'P-RAFIQ', 'PH-UNIFIED', 'USES_PHONE', 'FACT', 0.98, '2026-02-14T22:41:05Z', ['CASE-141'], ['SRC-CDR-A12']),
  E('E-USEPH-2', 'P-RAFIQ', 'PH-UNIFIED', 'USES_PHONE', 'FACT', 0.98, '2026-03-05T02:12:44Z', ['CASE-207'], ['SRC-CDR-B31']),
  E('E-OWN-7731', 'P-RAFIQ', 'ACC-7731', 'OWNS_ACCOUNT', 'FACT', 0.95, '2026-02-12T10:00:00Z', ['CASE-141'], ['SRC-FIR-141']),
  E('E-ACCUSE-207', 'P-RAFIQ', 'CASE-207', 'ACCUSED_IN', 'FACT', 1.0, '2026-03-02T14:15:00Z', ['CASE-207'], ['SRC-FIR-207']),
  E('E-COACC-207', 'P-DEEPAK', 'CASE-207', 'CO_ACCUSED_IN', 'FACT', 1.0, '2026-03-02T14:15:00Z', ['CASE-207'], ['SRC-FIR-207']),
  E('E-OWN-9914', 'P-DEEPAK', 'ACC-9914', 'OWNS_ACCOUNT', 'FACT', 0.95, '2026-03-02T14:15:00Z', ['CASE-207'], ['SRC-FIR-207']),
  E('E-COMM-DK', 'P-RAFIQ', 'P-DEEPAK', 'COMMUNICATED_WITH', 'DERIVED', 0.91, '2026-03-05T02:12:44Z', ['CASE-141', 'CASE-207'], ['SRC-CDR-B31']),
  E('E-TXN-55', 'ACC-9914', 'ACC-7731', 'TRANSFERRED_TO', 'FACT', 1.0, '2026-03-09T11:03:00Z', ['CASE-207', 'CASE-141'], ['SRC-TXN-55']),
  E('E-TXN-71', 'ACC-9914', 'ACC-7731', 'TRANSFERRED_TO', 'FACT', 1.0, '2026-03-11T16:47:00Z', ['CASE-207', 'CASE-141'], ['SRC-TXN-71']),
  E('E-BRIDGE', 'CASE-141', 'CASE-207', 'CONNECTS_CASES', 'DERIVED', 0.86, '2026-08-24T18:00:00Z', ['CASE-141', 'CASE-207'],
    ['SRC-FIR-141', 'SRC-FIR-207', 'SRC-CDR-A12', 'SRC-CDR-B31']),
]

export const SNAPSHOT_DIFF: SnapshotDiffResponse = {
  before_snapshot_id: 'SNAP-BEFORE-001',
  after_snapshot_id: 'SNAP-AFTER-001',
  added_node_ids: ['P-RAFIQ', 'PH-UNIFIED'],
  removed_node_ids: ['P-RAFIQ-K', 'P-RAFIQ-A', 'PH-A', 'PH-B'],
  changed_node_ids: [],
  added_edge_ids: ['E-USEPH-1', 'E-USEPH-2', 'E-COMM-DK', 'E-BRIDGE'],
  removed_edge_ids: ['E-ACCUSE-141', 'E-USEPH-A', 'E-ACCUSE-207', 'E-USEPH-B'],
  changed_edge_ids: [],
}

// ─── Evidence per relationship ───────────────────────────────────────────────

const edgeEvidenceBase = (edge?: NexusGraphEdge): NexusEdgeEvidenceResponse | null => {
  if (!edge) return null
  const recordIds = edge.properties.evidence_ids as string[]
  const records = recordIds.map((id) => SRC[id]).filter(Boolean)
  return {
    relationship_id: edge.id,
    edge_type: edge.edge_type,
    source_label: edge.source_id,
    target_label: edge.target_id,
    derivation_class: edge.derivation_class,
    confidence: edge.confidence,
    recorded_at: edge.recorded_at,
    source_records: records,
    derivation_chain: edge.derivation_class === 'FACT'
      ? [{ step: 1, rule: 'direct_import', inputs: recordIds }]
      : [
          { step: 1, rule: 'entity_resolution.confirm', inputs: ['RC-1'] },
          { step: 2, rule: 'projection.link_entities', inputs: recordIds },
        ],
  }
}

const AFTER_BY_ID = new Map(AFTER_EDGES.map((e) => [e.id, e]))
const BEFORE_BY_ID = new Map(BEFORE_EDGES.map((e) => [e.id, e]))
const NODE_LABEL = new Map(
  [...BEFORE_NODES, ...AFTER_NODES].map((n) => [n.id, n.label]),
)

export function evidenceFor(edgeId: string): NexusEdgeEvidenceResponse | null {
  const base = edgeEvidenceBase(AFTER_BY_ID.get(edgeId) ?? BEFORE_BY_ID.get(edgeId))
  if (!base) return null
  return {
    ...base,
    source_label: NODE_LABEL.get(base.source_label) ?? base.source_label,
    target_label: NODE_LABEL.get(base.target_label) ?? base.target_label,
  }
}

// ─── Leads ───────────────────────────────────────────────────────────────────

export const BRIDGE_LEAD: NexusLead = {
  id: 'LEAD-1',
  title: 'Cross-case bridge: Rafiq connects FIR 141/2026 with FIR 207/2026',
  rule_id: 'CROSS_CASE_BRIDGE',
  explanation:
    'After the confirmed alias (RC-1), one person ("Rafiq Khan / Rafiq Ahmed") is accused in both cases, ' +
    'uses the same phone +91 98450 11223 in both CDR pulls, and receives repeated transfers from ACC-9914 ' +
    '(co-accused Deepak Rao) into ACC-7731. This is an investigative lead, not a determination of guilt.',
  severity: 'HIGH',
  derivation_class: 'HYPOTHESIS',
  case_ids: ['CASE-141', 'CASE-207'],
  status: 'NEW',
  path: {
    node_ids: ['CASE-141', 'P-RAFIQ', 'PH-UNIFIED', 'P-DEEPAK', 'CASE-207'],
    edge_ids: ['E-ACCUSE-141', 'E-USEPH-1', 'E-USEPH-2', 'E-COMM-DK', 'E-COACC-207'],
  },
  evidence_ids: ['SRC-FIR-141', 'SRC-FIR-207', 'SRC-CDR-A12', 'SRC-CDR-B31', 'SRC-TXN-55'],
  created_at: '2026-08-24T18:00:05Z',
}

export const allSourceRecords = SRC
