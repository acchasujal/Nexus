import { AlertOctagon, AlertTriangle, CheckCircle, HelpCircle } from 'lucide-react'

type RiskLevel = 'HIGH' | 'MEDIUM' | 'LOW' | 'UNDETERMINED'

interface RiskBadgeProps {
  level: RiskLevel
  reasonUrl?: string
}

export function RiskBadge({ level, reasonUrl }: RiskBadgeProps) {
  const configs = {
    HIGH: {
      colorClass: 'text-status-danger bg-status-danger/10 border-status-danger/20',
      icon: AlertOctagon,
      label: 'High Risk'
    },
    MEDIUM: {
      colorClass: 'text-status-warning bg-status-warning/10 border-status-warning/20',
      icon: AlertTriangle,
      label: 'Medium Risk'
    },
    LOW: {
      colorClass: 'text-status-success bg-status-success/10 border-status-success/20',
      icon: CheckCircle,
      label: 'Low Risk'
    },
    UNDETERMINED: {
      colorClass: 'text-neutral-500 bg-neutral-100 border-neutral-200',
      icon: HelpCircle,
      label: 'Undetermined'
    }
  }

  const { colorClass, icon: Icon, label } = configs[level]

  return (
    <div className="inline-flex items-center space-x-2">
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-radius-sm border text-caption font-bold ${colorClass}`}
      >
        <Icon className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
        {label}
      </span>
      {reasonUrl && (
        <a
          href={reasonUrl}
          className="text-caption text-status-info hover:underline focus-visible:ring-1 focus-visible:ring-status-info"
          aria-label={`Learn why this case is marked ${label.toLowerCase()}`}
        >
          Why?
        </a>
      )}
    </div>
  )
}
