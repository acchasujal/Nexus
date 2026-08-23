import { CheckCircle2, AlertCircle, Clock, ChevronUp } from 'lucide-react'

export type ChipStatus = 'healthy' | 'approaching' | 'stale' | 'pending' | 'resolved' | 'escalated'

interface StatusChipProps {
  status: ChipStatus
  label?: string
}

export function StatusChip({ status, label }: StatusChipProps) {
  const configs = {
    healthy: {
      colorClass: 'text-status-success bg-status-success/10 border-status-success/20',
      icon: CheckCircle2,
      defaultLabel: 'Healthy'
    },
    resolved: {
      colorClass: 'text-status-success bg-status-success/10 border-status-success/20',
      icon: CheckCircle2,
      defaultLabel: 'Resolved'
    },
    approaching: {
      colorClass: 'text-status-warning bg-status-warning/10 border-status-warning/20',
      icon: Clock,
      defaultLabel: 'Approaching'
    },
    pending: {
      colorClass: 'text-neutral-600 bg-neutral-100 border-neutral-200',
      icon: Clock,
      defaultLabel: 'Pending'
    },
    stale: {
      colorClass: 'text-status-danger bg-status-danger/10 border-status-danger/20',
      icon: AlertCircle,
      defaultLabel: 'Stale'
    },
    escalated: {
      colorClass: 'text-neutral-50 bg-status-danger border-status-danger animate-pulse',
      icon: ChevronUp,
      defaultLabel: 'Escalated'
    }
  }

  const { colorClass, icon: Icon, defaultLabel } = configs[status]
  const displayLabel = label || defaultLabel

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-radius-sm border text-caption font-semibold ${colorClass}`}
    >
      <Icon className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
      {displayLabel}
    </span>
  )
}
