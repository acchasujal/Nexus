import React from 'react'
import { LucideIcon } from 'lucide-react'

interface MetricCardProps {
  label: string
  value: React.ReactNode
  subtext?: React.ReactNode
  icon?: LucideIcon
  badge?: {
    text: string
    variant?: 'neutral' | 'success' | 'warning' | 'danger' | 'info'
  }
  onClick?: () => void
}

const BADGE_STYLES = {
  neutral: 'bg-neutral-100 text-neutral-700 border-neutral-200',
  success: 'bg-emerald-50 text-emerald-800 border-emerald-200',
  warning: 'bg-amber-50 text-amber-900 border-amber-200',
  danger: 'bg-rose-50 text-rose-800 border-rose-200',
  info: 'bg-blue-50 text-blue-800 border-blue-200',
}

export function MetricCard({
  label,
  value,
  subtext,
  icon: Icon,
  badge,
  onClick,
}: MetricCardProps) {
  const Component = onClick ? 'button' : 'div'
  return (
    <Component
      onClick={onClick}
      className={`relative flex flex-col justify-between rounded-xl border border-neutral-200/90 bg-white p-4 sm:p-5 shadow-xs transition-all text-left ${
        onClick ? 'hover:border-neutral-300 hover:shadow-sm cursor-pointer' : ''
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-neutral-500">
          {label}
        </span>
        {Icon && (
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-neutral-50 text-neutral-500 border border-neutral-200/60">
            <Icon className="h-3.5 w-3.5" aria-hidden="true" />
          </div>
        )}
      </div>

      <div className="mt-3 space-y-1">
        <div className="text-2xl sm:text-3xl font-extrabold tracking-tight text-neutral-900 tabular-nums">
          {value}
        </div>
        {(subtext || badge) && (
          <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-neutral-500">
            {badge && (
              <span
                className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-bold border ${
                  BADGE_STYLES[badge.variant || 'neutral']
                }`}
              >
                {badge.text}
              </span>
            )}
            {subtext && <span>{subtext}</span>}
          </div>
        )}
      </div>
    </Component>
  )
}
