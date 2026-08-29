import React from 'react'
import { LucideIcon } from 'lucide-react'

interface PageHeaderProps {
  icon?: LucideIcon
  title: string
  subtitle?: React.ReactNode
  badge?: React.ReactNode
  actions?: React.ReactNode
  breadcrumbs?: Array<{ label: string; href?: string }>
}

export function PageHeader({
  icon: Icon,
  title,
  subtitle,
  badge,
  actions,
  breadcrumbs,
}: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-4 border-b border-neutral-200/80 pb-5">
      {/* Optional Breadcrumbs */}
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs text-neutral-500 font-medium">
          {breadcrumbs.map((crumb, idx) => {
            const isLast = idx === breadcrumbs.length - 1
            return (
              <React.Fragment key={crumb.label}>
                {idx > 0 && <span className="text-neutral-300">/</span>}
                {crumb.href && !isLast ? (
                  <a href={crumb.href} className="hover:text-neutral-800 transition-colors">
                    {crumb.label}
                  </a>
                ) : (
                  <span className={isLast ? 'text-neutral-900 font-semibold' : ''}>{crumb.label}</span>
                )}
              </React.Fragment>
            )
          })}
        </nav>
      )}

      {/* Main Title & Actions Bar */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1 min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2.5">
            {Icon && (
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600 border border-blue-200/60 shadow-2xs">
                <Icon className="h-5 w-5" aria-hidden="true" />
              </div>
            )}
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-neutral-900 truncate">
              {title}
            </h1>
            {badge && <div className="flex items-center">{badge}</div>}
          </div>
          {subtitle && (
            <div className="text-xs sm:text-sm text-neutral-600 leading-relaxed max-w-3xl">
              {subtitle}
            </div>
          )}
        </div>

        {actions && (
          <div className="flex flex-wrap items-center gap-2 sm:gap-3 shrink-0">
            {actions}
          </div>
        )}
      </div>
    </div>
  )
}
