/**
 * frontend/src/components/nexus/DigitalShadowSection.tsx
 *
 * P1-D: Digital Shadow (SOCMINT Governance) Section.
 * Governs public digital identifier fusion with strict Section 63 BSA compliance:
 *   - Mandatory Non-Equivalence Rule: Digital aliases are never legal person proof without physical corroboration.
 *   - 4-Stage Section 63 BSA Lifecycle: OBSERVED -> CANDIDATE_LINK -> CORROBORATED -> INVESTIGATOR_CONFIRMED.
 *   - Verifiable Provenance: Linked physical hardware IMEI, subscriber MSISDN, or bank account.
 *   - Officer Decision Workflow: Actionable confirmation with immutable cryptographic audit trail.
 */

import { useState, useMemo } from 'react'
import {
  Globe,
  Radio,
  Send,
  MessageSquare,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Eye,
  RefreshCw,
  Clock,
  Filter,
  CreditCard,
  Hash,
  ExternalLink,
} from 'lucide-react'
import {
  useDigitalShadows,
  useDecideDigitalShadow,
  useDigitalShadowSummary,
} from '@/hooks/useNexus'
import { MetricCard } from '@/components/ui/MetricCard'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { ErrorState } from '@/components/ErrorState'
import type {
  DigitalShadowCorroboration,
  DigitalShadowLifecycle,
  DigitalShadowPlatform,
} from '@shared/contracts/api'

interface DigitalShadowSectionProps {
  personId?: string | null
}

const PLATFORM_CONFIG: Record<
  string,
  { label: string; icon: React.ComponentType<{ className?: string }>; border: string; bg: string; text: string }
> = {
  TELEGRAM: {
    label: 'Telegram Channel / Bot',
    icon: Send,
    border: 'border-sky-200',
    bg: 'bg-sky-50',
    text: 'text-sky-800',
  },
  WHATSAPP: {
    label: 'WhatsApp Account',
    icon: MessageSquare,
    border: 'border-emerald-200',
    bg: 'bg-emerald-50',
    text: 'text-emerald-800',
  },
  DARKWEB_FORUM: {
    label: 'Darknet Forum / Escrow',
    icon: Globe,
    border: 'border-purple-200',
    bg: 'bg-purple-50',
    text: 'text-purple-900',
  },
  PAYMENT_GATEWAY: {
    label: 'Payment Gateway / VPA',
    icon: CreditCard,
    border: 'border-amber-200',
    bg: 'bg-amber-50',
    text: 'text-amber-900',
  },
  SOCIAL_MEDIA: {
    label: 'Social Media Handle',
    icon: Radio,
    border: 'border-blue-200',
    bg: 'bg-blue-50',
    text: 'text-blue-800',
  },
  MARKETPLACE: {
    label: 'Digital Marketplace',
    icon: Hash,
    border: 'border-neutral-200',
    bg: 'bg-neutral-50',
    text: 'text-neutral-800',
  },
}

const LIFECYCLE_BADGE: Record<string, { label: string; bg: string; text: string; border: string }> = {
  OBSERVED: { label: 'STAGE 1: OBSERVED', bg: 'bg-neutral-50', text: 'text-neutral-700', border: 'border-neutral-200' },
  CANDIDATE_LINK: { label: 'STAGE 2: CANDIDATE LINK', bg: 'bg-amber-50', text: 'text-amber-800', border: 'border-amber-200' },
  CORROBORATED: { label: 'STAGE 3: HARD-ID CORROBORATED', bg: 'bg-blue-50', text: 'text-blue-800', border: 'border-blue-200' },
  INVESTIGATOR_CONFIRMED: { label: 'STAGE 4: IO CONFIRMED', bg: 'bg-emerald-50', text: 'text-emerald-800', border: 'border-emerald-200' },
  DISMISSED: { label: 'DISMISSED', bg: 'bg-neutral-100', text: 'text-neutral-600', border: 'border-neutral-200' },
}

export function DigitalShadowSection({ personId }: DigitalShadowSectionProps) {
  const {
    data: shadows = [],
    isLoading,
    error,
    refetch,
  } = useDigitalShadows(personId || undefined)

  const { data: summary, refetch: refetchSummary } = useDigitalShadowSummary()
  const decideMutation = useDecideDigitalShadow()

  const [platformFilter, setPlatformFilter] = useState<string>('ALL')
  const [lifecycleFilter, setLifecycleFilter] = useState<string>('ALL')
  const [decisionNote, setDecisionNote] = useState('')
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null)

  const filteredShadows = useMemo(() => {
    return shadows.filter((s) => {
      if (platformFilter !== 'ALL' && s.platform !== platformFilter) return false
      if (lifecycleFilter !== 'ALL' && s.lifecycle_state !== lifecycleFilter) return false
      return true
    })
  }, [shadows, platformFilter, lifecycleFilter])

  const handleDecide = async (corroborationId: string, lifecycleState: DigitalShadowLifecycle) => {
    setFeedbackMsg(null)
    try {
      await decideMutation.mutateAsync({
        corroborationId,
        req: {
          lifecycle_state: lifecycleState,
          note: decisionNote.trim() || undefined,
        },
      })
      setDecisionNote('')
      setFeedbackMsg(`Lifecycle state updated: Marked as ${lifecycleState}`)
      void refetchSummary()
    } catch (err) {
      console.error('Failed to decide digital shadow:', err)
      setFeedbackMsg('Failed to record digital shadow decision. Please try again.')
    }
  }

  if (isLoading) return <LoadingSkeleton layout="card" />
  if (error) return <ErrorState message="Failed to load Digital Shadow Radar." onRetry={() => void refetch()} />

  return (
    <div className="space-y-6">
      {/* Statutory Guardrail Alert */}
      <div className="rounded-xl border border-blue-200 bg-blue-50/70 p-4 text-xs text-blue-900 flex items-start gap-3">
        <ShieldCheck className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-bold text-blue-950">
            Section 63 BSA & DPDP Act 2023 Digital Evidence Governance Protocol
          </p>
          <p className="text-blue-800 leading-relaxed">
            A digital moniker or public handle is <strong>never</strong> treated as proof of suspect identity on its own.
            In compliance with statutory standards, digital shadows must be corroborated by a verified physical hard identifier
            (CDR subscriber MSISDN, seized hardware IMEI, or bank account KYC) before advancing to investigator confirmation.
          </p>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Total Digital Footprints"
          value={summary?.total_corroborations ?? shadows.length}
          icon={Globe}
          badge={{ text: `${summary?.corroborated_links ?? 0} Corroborated`, variant: 'info' }}
          subtext="Structured online identifiers"
        />
        <MetricCard
          label="Telegram / Darknet Intel"
          value={(summary?.telegram_channels ?? 0) + (summary?.darknet_forum_links ?? 0)}
          icon={Send}
          badge={{ text: 'Channel Intel', variant: 'warning' }}
          subtext="Coordinated cyber conduits"
        />
        <MetricCard
          label="Payment Gateway VPAs"
          value={summary?.payment_gateways ?? 0}
          icon={CreditCard}
          badge={{ text: 'UPI / Escrow', variant: 'neutral' }}
          subtext="Virtual payment handles"
        />
        <MetricCard
          label="Officer Confirmed"
          value={summary?.confirmed_links ?? 0}
          icon={ShieldCheck}
          badge={{ text: 'Section 63 Signed', variant: 'success' }}
          subtext="Entered into court record"
        />
      </div>

      {/* Control Bar: Filters & Refresh */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-4 rounded-xl border border-neutral-200/80 shadow-2xs">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold text-neutral-500 flex items-center gap-1 mr-1">
            <Filter className="h-3.5 w-3.5" /> Platform:
          </span>
          {['ALL', 'TELEGRAM', 'WHATSAPP', 'DARKWEB_FORUM', 'PAYMENT_GATEWAY', 'SOCIAL_MEDIA'].map((p) => (
            <button
              key={p}
              onClick={() => setPlatformFilter(p)}
              className={`px-3 py-1 text-xs font-semibold rounded-lg border transition-colors cursor-pointer ${
                platformFilter === p
                  ? 'bg-neutral-900 text-white border-neutral-900'
                  : 'bg-neutral-50 text-neutral-600 border-neutral-200 hover:bg-neutral-100'
              }`}
            >
              {p === 'ALL' ? 'All Platforms' : p.replaceAll('_', ' ')}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <select
            value={lifecycleFilter}
            onChange={(e) => setLifecycleFilter(e.target.value)}
            className="text-xs border border-neutral-200 rounded-lg px-3 py-1.5 bg-neutral-50 font-medium text-neutral-700"
          >
            <option value="ALL">All Lifecycle Stages</option>
            <option value="OBSERVED">Stage 1: Observed</option>
            <option value="CANDIDATE_LINK">Stage 2: Candidate Link</option>
            <option value="CORROBORATED">Stage 3: Corroborated</option>
            <option value="INVESTIGATOR_CONFIRMED">Stage 4: Confirmed</option>
            <option value="DISMISSED">Dismissed</option>
          </select>
          <button
            onClick={() => {
              void refetch()
              void refetchSummary()
            }}
            className="p-1.5 text-neutral-500 hover:text-neutral-900 rounded-lg border border-neutral-200 hover:bg-neutral-50 cursor-pointer"
            title="Refresh Digital Shadow Radar"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {feedbackMsg && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-2 text-xs font-semibold text-blue-900 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-blue-600 shrink-0" />
          <span>{feedbackMsg}</span>
        </div>
      )}

      {/* Corroborations Grid */}
      {filteredShadows.length === 0 ? (
        <div className="rounded-xl border border-dashed border-neutral-300 bg-white p-12 text-center text-neutral-500">
          No digital shadow corroborations match the current filter selection.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {filteredShadows.map((s) => {
            const platConf = PLATFORM_CONFIG[s.platform] || PLATFORM_CONFIG.TELEGRAM
            const stageConf = LIFECYCLE_BADGE[s.lifecycle_state] || LIFECYCLE_BADGE.OBSERVED
            const Icon = platConf.icon

            return (
              <div
                key={s.corroboration_id}
                className={`rounded-xl border ${platConf.border} bg-white shadow-xs p-5 flex flex-col justify-between space-y-4 hover:border-neutral-400 transition-all`}
              >
                <div>
                  {/* Header */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <div className={`p-2 rounded-lg ${platConf.bg} ${platConf.text}`}>
                        <Icon className="h-4 w-4" />
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-neutral-900">{s.person_name}</h3>
                        <p className="text-[11px] font-mono text-neutral-500">Subject ID: {s.person_id}</p>
                      </div>
                    </div>

                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${stageConf.bg} ${stageConf.text} ${stageConf.border}`}
                    >
                      {stageConf.label}
                    </span>
                  </div>

                  {/* Identifier Fusion Panel */}
                  <div className="mt-4 rounded-lg bg-neutral-50 border border-neutral-200/80 p-3.5 space-y-2">
                    <div className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider flex items-center justify-between">
                      <span>{platConf.label}</span>
                      <span className="text-neutral-700 font-bold flex items-center gap-1">
                        Confidence: {(s.confidence_score * 100).toFixed(0)}%
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
                      <div className="bg-white p-2.5 rounded-md border border-neutral-200 shadow-2xs">
                        <span className="block text-[10px] font-bold text-neutral-400 uppercase">Digital Identifier</span>
                        <code className="text-xs font-bold text-neutral-900 break-all">{s.digital_identifier}</code>
                        <span className="block text-[10px] text-neutral-400 truncate mt-0.5">{s.source_url_or_channel}</span>
                      </div>

                      <div className="bg-white p-2.5 rounded-md border border-blue-200 shadow-2xs">
                        <span className="block text-[10px] font-bold text-blue-800 uppercase">
                          Corroborating Hard ID ({s.corroborating_physical_type})
                        </span>
                        <code className="text-xs font-bold text-blue-900 break-all">{s.corroborating_physical_id}</code>
                        <span className="block text-[10px] text-emerald-700 font-semibold mt-0.5">Physical Hard Link Verified</span>
                      </div>
                    </div>
                  </div>

                  {/* Context */}
                  <p className="mt-3 text-xs text-neutral-700 leading-relaxed bg-neutral-50/50 p-2.5 rounded-lg border border-neutral-100">
                    {s.observation_context}
                  </p>

                  {/* Evidence Provenance Citations */}
                  {s.evidence_refs.length > 0 && (
                    <div className="mt-3 flex flex-wrap items-center gap-1.5">
                      <span className="text-[11px] font-bold text-neutral-500 mr-1">Section 63 BSA Citations:</span>
                      {s.evidence_refs.map((ref) => (
                        <span
                          key={ref}
                          className="px-2 py-0.5 rounded-md bg-blue-50 border border-blue-200 font-mono text-[10px] font-bold text-blue-800"
                        >
                          {ref}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Investigator Decision Record if decided */}
                  {s.decided_at && (
                    <div className="mt-3 p-2.5 rounded-lg bg-emerald-50/60 border border-emerald-200 text-xs text-emerald-950 space-y-1">
                      <div className="flex items-center gap-1.5 font-bold">
                        <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                        <span>Actioned by {s.decided_by} on {new Date(s.decided_at).toLocaleString()}</span>
                      </div>
                      {s.investigator_note && (
                        <p className="text-[11px] text-emerald-900 italic">"{s.investigator_note}"</p>
                      )}
                    </div>
                  )}
                </div>

                {/* Investigator Action Bar */}
                <div className="pt-3 border-t border-neutral-100 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => handleDecide(s.corroboration_id, 'INVESTIGATOR_CONFIRMED' as DigitalShadowLifecycle)}
                      disabled={decideMutation.isPending}
                      className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 hover:text-emerald-900 bg-emerald-50 hover:bg-emerald-100 px-2.5 py-1 rounded-md border border-emerald-200 transition-colors cursor-pointer"
                    >
                      <CheckCircle2 className="h-3.5 w-3.5" /> Confirm
                    </button>
                    <button
                      onClick={() => handleDecide(s.corroboration_id, 'CORROBORATED' as DigitalShadowLifecycle)}
                      disabled={decideMutation.isPending}
                      className="inline-flex items-center gap-1 text-[11px] font-bold text-blue-700 hover:text-blue-900 bg-blue-50 hover:bg-blue-100 px-2.5 py-1 rounded-md border border-blue-200 transition-colors cursor-pointer"
                    >
                      <Eye className="h-3.5 w-3.5" /> Corroborate
                    </button>
                    <button
                      onClick={() => handleDecide(s.corroboration_id, 'DISMISSED' as DigitalShadowLifecycle)}
                      disabled={decideMutation.isPending}
                      className="inline-flex items-center gap-1 text-[11px] font-bold text-neutral-600 hover:text-neutral-900 bg-neutral-100 hover:bg-neutral-200 px-2.5 py-1 rounded-md border border-neutral-200 transition-colors cursor-pointer"
                    >
                      <XCircle className="h-3.5 w-3.5" /> Dismiss
                    </button>
                  </div>

                  <span className="text-[10px] font-mono text-neutral-400">
                    {s.corroboration_id}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
