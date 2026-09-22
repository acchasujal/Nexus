/**
 * frontend/src/lib/investigationContext.ts
 *
 * Phase 6: Typed InvestigationContext Encoder, Decoder & URL Router Integration.
 * Provides unified cross-screen context preservation across:
 *   - Network Pulse
 *   - Identity Drift Radar
 *   - Network Adaptation Radar
 *   - Case DNA
 *   - Entity Fusion
 *   - Network Explorer
 *   - Timeline
 *   - Evidence
 */

import { useSearchParams } from 'react-router-dom'
import { useCallback, useMemo } from 'react'
import type { InvestigationContext } from '@shared/contracts/api'

export type { InvestigationContext }

/**
 * Encode an InvestigationContext object into a deterministic URL query string.
 */
export function encodeInvestigationContext(context: InvestigationContext): string {
  const params = new URLSearchParams()

  if (context.case_id) params.set('case_id', context.case_id)
  if (context.target_case_id) params.set('target_case_id', context.target_case_id)
  if (context.entity_id) {
    params.set('entity_id', context.entity_id)
    params.set('node_id', context.entity_id) // backward compatibility
  }
  if (context.evidence_id) params.set('evidence_id', context.evidence_id)
  if (context.change_id) params.set('change_id', context.change_id)
  if (context.relationship_id) {
    params.set('relationship_id', context.relationship_id)
    params.set('edge_id', context.relationship_id) // backward compatibility
  }
  if (context.snapshot_id) params.set('snapshot_id', context.snapshot_id)
  if (context.feature_type) params.set('feature_type', context.feature_type)
  if (context.focus) params.set('focus', context.focus)
  if (context.drawer) params.set('drawer', context.drawer)

  return params.toString()
}

/**
 * Decode a URLSearchParams instance or query string into a typed InvestigationContext.
 */
export function decodeInvestigationContext(
  searchParams: URLSearchParams | string
): InvestigationContext {
  const params = typeof searchParams === 'string' ? new URLSearchParams(searchParams) : searchParams

  const rawFocus = params.get('focus')?.toLowerCase()
  let focus: InvestigationContext['focus'] | undefined = undefined
  if (rawFocus === '1hop' || rawFocus === '2hop' || rawFocus === 'crosscase' || rawFocus === 'community') {
    focus = rawFocus
  }

  const rawDrawer = params.get('drawer')?.toLowerCase()
  let drawer: InvestigationContext['drawer'] | undefined = undefined
  if (rawDrawer === 'entity' || rawDrawer === 'relationship' || rawDrawer === 'evidence') {
    drawer = rawDrawer
  }

  return {
    case_id: params.get('case_id') || undefined,
    target_case_id: params.get('target_case_id') || undefined,
    entity_id: params.get('entity_id') || params.get('node_id') || undefined,
    evidence_id: params.get('evidence_id') || undefined,
    change_id: params.get('change_id') || undefined,
    relationship_id: params.get('relationship_id') || params.get('edge_id') || undefined,
    snapshot_id: params.get('snapshot_id') || params.get('snapshot') || undefined,
    feature_type: params.get('feature_type') || undefined,
    focus,
    drawer,
  }
}

/**
 * Build a full investigative navigation URL preserving context.
 */
export function buildInvestigativeUrl(basePath: string, context: InvestigationContext): string {
  const qs = encodeInvestigationContext(context)
  return qs ? `${basePath}?${qs}` : basePath
}

/**
 * Hook for consuming and updating typed InvestigationContext from URL search params.
 */
export function useInvestigationContext() {
  const [searchParams, setSearchParams] = useSearchParams()

  const context = useMemo(() => decodeInvestigationContext(searchParams), [searchParams])

  const setContext = useCallback(
    (updates: Partial<InvestigationContext>) => {
      const merged: InvestigationContext = { ...context, ...updates }
      const newQs = encodeInvestigationContext(merged)
      setSearchParams(new URLSearchParams(newQs))
    },
    [context, setSearchParams]
  )

  return { context, setContext }
}
