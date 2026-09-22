/**
 * frontend/src/tests/investigationContext.test.ts
 *
 * Phase 6 Verification: Typed InvestigationContext Encoding & Decoding.
 */

import { describe, it, expect } from 'vitest'
import {
  encodeInvestigationContext,
  decodeInvestigationContext,
  buildInvestigativeUrl,
  type InvestigationContext,
} from '@/lib/investigationContext'

describe('InvestigationContext Serialization & Routing', () => {
  it('encodes a complete InvestigationContext deterministically', () => {
    const ctx: InvestigationContext = {
      case_id: 'CASE-141',
      target_case_id: 'CASE-207',
      entity_id: 'P-RAFIQ',
      evidence_id: 'SRC-FIR-141',
      change_id: 'E-BRIDGE',
      relationship_id: 'E-BRIDGE',
      snapshot_id: 'snap-current',
      feature_type: 'PULSE',
      focus: '1hop',
      drawer: 'entity',
    }

    const qs = encodeInvestigationContext(ctx)
    expect(qs).toContain('case_id=CASE-141')
    expect(qs).toContain('target_case_id=CASE-207')
    expect(qs).toContain('entity_id=P-RAFIQ')
    expect(qs).toContain('evidence_id=SRC-FIR-141')
    expect(qs).toContain('change_id=E-BRIDGE')
    expect(qs).toContain('relationship_id=E-BRIDGE')
    expect(qs).toContain('snapshot_id=snap-current')
    expect(qs).toContain('feature_type=PULSE')
    expect(qs).toContain('focus=1hop')
    expect(qs).toContain('drawer=entity')
  })

  it('decodes a query string into a typed InvestigationContext correctly', () => {
    const qs =
      'case_id=CASE-141&target_case_id=CASE-207&entity_id=P-RAFIQ&change_id=E-BRIDGE&focus=2hop&drawer=relationship'
    const decoded = decodeInvestigationContext(qs)

    expect(decoded.case_id).toBe('CASE-141')
    expect(decoded.target_case_id).toBe('CASE-207')
    expect(decoded.entity_id).toBe('P-RAFIQ')
    expect(decoded.change_id).toBe('E-BRIDGE')
    expect(decoded.focus).toBe('2hop')
    expect(decoded.drawer).toBe('relationship')
  })

  it('guarantees roundtrip lossless context preservation', () => {
    const original: InvestigationContext = {
      case_id: 'CASE-501',
      target_case_id: 'CASE-502',
      entity_id: 'VEH-1001',
      evidence_id: 'SRC-FIR-501',
      change_id: 'E-BRIDGE-3',
      snapshot_id: 'snap-current',
      feature_type: 'ADAPTATION',
      focus: 'crosscase',
      drawer: 'evidence',
    }

    const encoded = encodeInvestigationContext(original)
    const restored = decodeInvestigationContext(encoded)

    expect(restored.case_id).toBe(original.case_id)
    expect(restored.target_case_id).toBe(original.target_case_id)
    expect(restored.entity_id).toBe(original.entity_id)
    expect(restored.evidence_id).toBe(original.evidence_id)
    expect(restored.change_id).toBe(original.change_id)
    expect(restored.snapshot_id).toBe(original.snapshot_id)
    expect(restored.feature_type).toBe(original.feature_type)
    expect(restored.focus).toBe(original.focus)
    expect(restored.drawer).toBe(original.drawer)
  })

  it('handles backward-compatibility fallbacks gracefully', () => {
    // URL with legacy node_id and edge_id
    const legacyQs = 'node_id=P-RAFIQ-K&edge_id=E-ACCUSE-141&snapshot=after'
    const decoded = decodeInvestigationContext(legacyQs)

    expect(decoded.entity_id).toBe('P-RAFIQ-K')
    expect(decoded.relationship_id).toBe('E-ACCUSE-141')
    expect(decoded.snapshot_id).toBe('after')
  })

  it('builds full URL preserving base path and query parameters', () => {
    const url = buildInvestigativeUrl('/network', {
      case_id: 'CASE-141',
      focus: '1hop',
    })
    expect(url).toBe('/network?case_id=CASE-141&focus=1hop')
  })
})
