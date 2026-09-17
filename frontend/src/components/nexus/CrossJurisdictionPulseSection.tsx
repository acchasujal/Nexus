/**
 * frontend/src/components/nexus/CrossJurisdictionPulseSection.tsx
 *
 * P1-A: Cross-Jurisdiction Intelligence Pulse Dissemination & Routing Section.
 * Surfaces cryptographically sealed intelligence packets sent between state police
 * jurisdictions (e.g. Mysuru CASE-141 <-> Bengaluru CASE-207).
 * Compliant with:
 *   - Section 63 BSA Evidence Grounding
 *   - Zero Predictive Guilt Constraints
 *   - SHA-256 Cryptographic Payload Seal Verification
 *   - Authoritative Officer Acknowledgment & Actioning
 */

import { useState } from 'react'
import {
  Send,
  CheckCircle2,
  XCircle,
  Clock,
  Fingerprint,
  Link as LinkIcon,
  FileCheck,
  RefreshCw,
  PlusCircle,
} from 'lucide-react'
import {
  useIntelligencePulseInbox,
  useDispatchIntelligencePulse,
  useAcknowledgeIntelligencePulse,
} from '@/hooks/useNexus'
import type {
  IntelligencePulsePacket,
  PulseSecurityClassification,
} from '@shared/contracts/api'

interface CrossJurisdictionPulseSectionProps {
  currentCaseId?: string | null
}

const CLASSIFICATION_STYLE: Record<string, string> = {
  TOP_SECRET: 'border-red-300 bg-red-100 text-red-900 font-bold',
  SECRET: 'border-rose-300 bg-rose-50 text-rose-900 font-bold',
  CONFIDENTIAL: 'border-amber-300 bg-amber-50 text-amber-900 font-bold',
  RESTRICTED: 'border-blue-300 bg-blue-50 text-blue-900 font-semibold',
  UNCLASSIFIED: 'border-neutral-300 bg-neutral-100 text-neutral-800 font-normal',
}

const STATUS_STYLE: Record<string, string> = {
  DELIVERED: 'bg-amber-100 text-amber-800 border-amber-300',
  ACKNOWLEDGED: 'bg-blue-100 text-blue-800 border-blue-300',
  ACTIONED: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  REJECTED: 'bg-red-100 text-red-800 border-red-300',
}

export function CrossJurisdictionPulseSection({
  currentCaseId,
}: CrossJurisdictionPulseSectionProps) {
  const { data: pulses = [], isLoading, refetch } = useIntelligencePulseInbox(
    currentCaseId || undefined
  )
  const dispatchMutation = useDispatchIntelligencePulse()
  const acknowledgeMutation = useAcknowledgeIntelligencePulse()

  const [selectedPacket, setSelectedPacket] = useState<IntelligencePulsePacket | null>(null)
  const [showDispatchModal, setShowDispatchModal] = useState(false)
  const [ackNote, setAckNote] = useState('')
  const [ackSuccess, setAckSuccess] = useState<string | null>(null)

  // Dispatch Form State
  const [formOriginCase, setFormOriginCase] = useState(currentCaseId || 'CASE-141')
  const [formTargetCase, setFormTargetCase] = useState('CASE-207')
  const [formTargetDistrict, setFormTargetDistrict] = useState('Bengaluru Central')
  const [formHeadline, setFormHeadline] = useState('')
  const [formSummary, setFormSummary] = useState('')
  const [formEntities, setFormEntities] = useState('P-RAFIQ, PH-UNIFIED')
  const [formEvidence, setFormEvidence] = useState('SRC-FIR-141, SRC-CDR-A12')
  const [formClassification, setFormClassification] = useState<PulseSecurityClassification>('RESTRICTED')

  const activePacket = selectedPacket || pulses[0] || null

  const handleAcknowledge = async (decision: 'ACTION' | 'ACKNOWLEDGE' | 'REJECT') => {
    if (!activePacket) return
    try {
      await acknowledgeMutation.mutateAsync({
        packetId: activePacket.packet_id,
        req: {
          decision,
          note: ackNote.trim() || undefined,
        },
      })
      setAckSuccess(`Pulse ${activePacket.packet_id} marked as ${decision}ED.`)
      setAckNote('')
      setTimeout(() => setAckSuccess(null), 3000)
    } catch (e) {
      console.error('Failed to acknowledge pulse:', e)
    }
  }

  const handleDispatch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formHeadline.trim() || !formSummary.trim()) return

    const sharedEntities = formEntities
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    const evidenceRefs = formEvidence
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)

    try {
      await dispatchMutation.mutateAsync({
        origin_case_id: formOriginCase.trim(),
        target_case_id: formTargetCase.trim(),
        target_district: formTargetDistrict.trim(),
        headline: formHeadline.trim(),
        summary: formSummary.trim(),
        shared_entities: sharedEntities,
        evidence_refs: evidenceRefs,
        security_classification: formClassification,
      })
      setShowDispatchModal(false)
      setFormHeadline('')
      setFormSummary('')
      void refetch()
    } catch (err) {
      console.error('Dispatch pulse failed:', err)
    }
  }

  return (
    <div className="rounded-xl border border-neutral-200/90 bg-white p-5 shadow-xs space-y-4">
      {/* Section Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-neutral-100 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="rounded-lg bg-blue-50 p-2 text-blue-700 border border-blue-200">
            <Send className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-neutral-900 flex items-center gap-2">
              Cross-Jurisdiction Intelligence Pulse Conduit
              <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-bold text-blue-800">
                P1-A Active
              </span>
            </h3>
            <p className="text-xs text-neutral-500">
              Inter-district case linkage routing with SHA-256 tamper seal and Section 63 BSA grounding.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => void refetch()}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-neutral-200 bg-neutral-50 text-xs font-semibold text-neutral-700 hover:bg-neutral-100 transition-colors cursor-pointer"
            title="Refresh pulses"
          >
            <RefreshCw className={`h-3 w-3 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowDispatchModal(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 text-xs font-bold text-white hover:bg-blue-700 transition-colors shadow-2xs cursor-pointer"
          >
            <PlusCircle className="h-3.5 w-3.5" />
            Dispatch Intelligence Pulse
          </button>
        </div>
      </div>

      {pulses.length === 0 ? (
        <div className="rounded-lg border border-dashed border-neutral-200 bg-neutral-50/50 py-8 text-center">
          <p className="text-xs font-medium text-neutral-600">
            No cross-jurisdiction intelligence pulses found for this scope.
          </p>
          <button
            onClick={() => setShowDispatchModal(true)}
            className="mt-2 text-xs font-bold text-blue-700 underline hover:text-blue-900"
          >
            Dispatch a new pulse to link another jurisdiction
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {/* Packet List */}
          <div className="space-y-2 lg:col-span-1 border-r border-neutral-100 pr-0 lg:pr-3 max-h-[500px] overflow-y-auto">
            {pulses.map((pkt) => {
              const isSelected = activePacket?.packet_id === pkt.packet_id
              return (
                <button
                  key={pkt.packet_id}
                  onClick={() => setSelectedPacket(pkt)}
                  className={`w-full text-left p-3 rounded-lg border transition-colors cursor-pointer ${
                    isSelected
                      ? 'border-blue-500 bg-blue-50/60 shadow-2xs'
                      : 'border-neutral-200 hover:bg-neutral-50'
                  }`}
                >
                  <div className="flex items-center justify-between gap-1 mb-1">
                    <span className="font-mono text-[10px] font-bold text-neutral-600">
                      {pkt.packet_id}
                    </span>
                    <span
                      className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded border ${
                        STATUS_STYLE[pkt.delivery_status] || 'bg-neutral-100 text-neutral-700'
                      }`}
                    >
                      {pkt.delivery_status}
                    </span>
                  </div>
                  <h4 className="text-xs font-bold text-neutral-900 line-clamp-1">
                    {pkt.headline}
                  </h4>
                  <div className="mt-1 flex items-center justify-between text-[10px] text-neutral-500">
                    <span>
                      {pkt.origin_case_id} ({pkt.origin_district}) → {pkt.target_case_id}
                    </span>
                    <span className="font-mono">{pkt.dispatched_at.slice(0, 10)}</span>
                  </div>
                </button>
              )
            })}
          </div>

          {/* Packet Detail & Actioning */}
          {activePacket && (
            <div className="space-y-4 lg:col-span-2">
              <div className="rounded-lg border border-neutral-200 bg-neutral-50/60 p-4 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded px-2 py-0.5 text-[10px] uppercase border ${
                        CLASSIFICATION_STYLE[activePacket.security_classification] ||
                        'border-neutral-200 bg-neutral-100'
                      }`}
                    >
                      {activePacket.security_classification}
                    </span>
                    <span className="font-mono text-xs font-bold text-neutral-800">
                      {activePacket.packet_id}
                    </span>
                  </div>
                  <span
                    className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase border ${
                      STATUS_STYLE[activePacket.delivery_status] || 'bg-neutral-100'
                    }`}
                  >
                    {activePacket.delivery_status}
                  </span>
                </div>

                <div>
                  <h4 className="text-sm font-bold text-neutral-900">{activePacket.headline}</h4>
                  <p className="mt-1 text-xs text-neutral-700 leading-relaxed">
                    {activePacket.summary}
                  </p>
                </div>

                {/* Routing Flow Metadata */}
                <div className="grid grid-cols-2 gap-2 text-xs border-y border-neutral-200/80 py-2">
                  <div>
                    <span className="text-neutral-500 font-medium">Origin Jurisdiction:</span>
                    <p className="font-semibold text-neutral-800">
                      {activePacket.origin_case_id} · {activePacket.origin_district}
                    </p>
                    <p className="font-mono text-[10px] text-neutral-500">
                      IO: {activePacket.origin_officer_id}
                    </p>
                  </div>
                  <div>
                    <span className="text-neutral-500 font-medium">Target Jurisdiction:</span>
                    <p className="font-semibold text-neutral-800">
                      {activePacket.target_case_id} · {activePacket.target_district}
                    </p>
                    <p className="text-[10px] text-neutral-500">
                      Role: {activePacket.target_role}
                    </p>
                  </div>
                </div>

                {/* Grounded Entities & Evidence Citations */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] font-bold uppercase text-neutral-500 flex items-center gap-1">
                      <LinkIcon className="h-3 w-3" /> Shared Entities:
                    </span>
                    {activePacket.shared_entities.map((ent) => (
                      <span
                        key={ent}
                        className="rounded bg-blue-100/70 border border-blue-200 px-2 py-0.5 font-mono text-[10px] font-semibold text-blue-900"
                      >
                        {ent}
                      </span>
                    ))}
                  </div>

                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] font-bold uppercase text-neutral-500 flex items-center gap-1">
                      <FileCheck className="h-3 w-3" /> Evidence Provenance:
                    </span>
                    {activePacket.evidence_refs.map((ref) => (
                      <span
                        key={ref}
                        className="rounded bg-neutral-200/80 border border-neutral-300 px-2 py-0.5 font-mono text-[10px] font-medium text-neutral-800"
                      >
                        {ref}
                      </span>
                    ))}
                  </div>
                </div>

                {/* SHA-256 Cryptographic Seal */}
                <div className="flex items-center gap-2 rounded bg-white p-2 border border-neutral-200 text-[11px] text-neutral-600 font-mono">
                  <Fingerprint className="h-4 w-4 text-emerald-600 shrink-0" />
                  <span className="truncate">Seal: {activePacket.packet_hash}</span>
                </div>

                {/* Acknowledgment Details if present */}
                {activePacket.acknowledged_at && (
                  <div className="rounded bg-emerald-50 border border-emerald-200 p-2.5 text-xs text-emerald-900 space-y-1">
                    <div className="flex items-center gap-1.5 font-semibold">
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                      Acknowledged by {activePacket.acknowledged_by} on{' '}
                      {new Date(activePacket.acknowledged_at).toLocaleString()}
                    </div>
                    {activePacket.acknowledgment_note && (
                      <p className="text-emerald-800 text-[11px] italic pl-5">
                        &quot;{activePacket.acknowledgment_note}&quot;
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* Actioning Controls */}
              {activePacket.delivery_status === 'DELIVERED' && (
                <div className="rounded-lg border border-neutral-200 bg-white p-4 space-y-3 shadow-2xs">
                  <h5 className="text-xs font-bold uppercase tracking-wider text-neutral-800">
                    Authoritative Officer Receipt &amp; Actioning
                  </h5>

                  {ackSuccess && (
                    <div className="rounded border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-900 flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                      {ackSuccess}
                    </div>
                  )}

                  <div>
                    <label
                      htmlFor="pulse-ack-notes"
                      className="block text-[11px] font-semibold text-neutral-700 mb-1"
                    >
                      Officer Note / Next Action
                    </label>
                    <input
                      id="pulse-ack-notes"
                      type="text"
                      value={ackNote}
                      onChange={(e) => setAckNote(e.target.value)}
                      placeholder="e.g., Cross-referenced with suspect account; adding to Bangalore investigation."
                      className="w-full rounded border border-neutral-300 px-3 py-1.5 text-xs focus:border-blue-500 focus:outline-hidden"
                    />
                  </div>

                  <div className="flex flex-wrap gap-2 pt-1">
                    <button
                      onClick={() => handleAcknowledge('ACTION')}
                      disabled={acknowledgeMutation.isPending}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3.5 py-1.5 text-xs font-bold text-white hover:bg-emerald-700 shadow-2xs cursor-pointer disabled:opacity-50"
                    >
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Action &amp; Incorporate
                    </button>
                    <button
                      onClick={() => handleAcknowledge('ACKNOWLEDGE')}
                      disabled={acknowledgeMutation.isPending}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-bold text-blue-800 hover:bg-blue-100 cursor-pointer disabled:opacity-50"
                    >
                      <Clock className="h-3.5 w-3.5" />
                      Acknowledge Receipt
                    </button>
                    <button
                      onClick={() => handleAcknowledge('REJECT')}
                      disabled={acknowledgeMutation.isPending}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-bold text-red-800 hover:bg-red-100 cursor-pointer disabled:opacity-50"
                    >
                      <XCircle className="h-3.5 w-3.5" />
                      Reject Lead
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Dispatch Modal Dialog */}
      {showDispatchModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-lg rounded-xl border border-neutral-200 bg-white p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-neutral-100 pb-3">
              <h3 className="text-sm font-bold text-neutral-900 flex items-center gap-2">
                <Send className="h-4 w-4 text-blue-600" />
                Dispatch Cross-Jurisdiction Intelligence Pulse
              </h3>
              <button
                onClick={() => setShowDispatchModal(false)}
                className="text-neutral-400 hover:text-neutral-600 text-sm font-bold cursor-pointer"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleDispatch} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-neutral-700 mb-1">
                    Origin Case ID
                  </label>
                  <input
                    type="text"
                    value={formOriginCase}
                    onChange={(e) => setFormOriginCase(e.target.value)}
                    required
                    className="w-full rounded border border-neutral-300 px-2.5 py-1.5 text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-neutral-700 mb-1">
                    Target Case ID
                  </label>
                  <input
                    type="text"
                    value={formTargetCase}
                    onChange={(e) => setFormTargetCase(e.target.value)}
                    required
                    className="w-full rounded border border-neutral-300 px-2.5 py-1.5 text-xs font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-neutral-700 mb-1">
                  Target District
                </label>
                <input
                  type="text"
                  value={formTargetDistrict}
                  onChange={(e) => setFormTargetDistrict(e.target.value)}
                  required
                  placeholder="e.g., Bengaluru Central"
                  className="w-full rounded border border-neutral-300 px-2.5 py-1.5 text-xs"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-neutral-700 mb-1">
                  Intelligence Headline
                </label>
                <input
                  type="text"
                  value={formHeadline}
                  onChange={(e) => setFormHeadline(e.target.value)}
                  required
                  placeholder="e.g., Common hawala conduit linking Mysuru and Bengaluru syndicates"
                  className="w-full rounded border border-neutral-300 px-2.5 py-1.5 text-xs"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-neutral-700 mb-1">
                  Summary &amp; Grounded Rationale
                </label>
                <textarea
                  rows={3}
                  value={formSummary}
                  onChange={(e) => setFormSummary(e.target.value)}
                  required
                  placeholder="Detail the verified nexus and reason for transmission..."
                  className="w-full rounded border border-neutral-300 px-2.5 py-1.5 text-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-neutral-700 mb-1">
                    Shared Entities (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={formEntities}
                    onChange={(e) => setFormEntities(e.target.value)}
                    placeholder="P-RAFIQ, PH-UNIFIED"
                    className="w-full rounded border border-neutral-300 px-2.5 py-1.5 text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-neutral-700 mb-1">
                    Evidence Refs (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={formEvidence}
                    onChange={(e) => setFormEvidence(e.target.value)}
                    placeholder="SRC-FIR-141, SRC-TXN-55"
                    className="w-full rounded border border-neutral-300 px-2.5 py-1.5 text-xs font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-neutral-700 mb-1">
                  Security Classification
                </label>
                <select
                  value={formClassification}
                  onChange={(e) =>
                    setFormClassification(e.target.value as PulseSecurityClassification)
                  }
                  className="w-full rounded border border-neutral-300 px-2.5 py-1.5 text-xs"
                >
                  <option value="RESTRICTED">RESTRICTED</option>
                  <option value="CONFIDENTIAL">CONFIDENTIAL</option>
                  <option value="SECRET">SECRET</option>
                  <option value="TOP_SECRET">TOP_SECRET</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-neutral-100">
                <button
                  type="button"
                  onClick={() => setShowDispatchModal(false)}
                  className="rounded px-3 py-1.5 text-xs font-semibold text-neutral-600 hover:bg-neutral-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={dispatchMutation.isPending}
                  className="rounded bg-blue-600 px-4 py-1.5 text-xs font-bold text-white hover:bg-blue-700 disabled:opacity-50 cursor-pointer"
                >
                  {dispatchMutation.isPending ? 'Cryptographically Sealing...' : 'Dispatch Pulse'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
