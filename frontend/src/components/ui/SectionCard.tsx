import React from 'react'

interface SectionCardProps {
  title?: React.ReactNode
  subtitle?: React.ReactNode
  actions?: React.ReactNode
  children: React.ReactNode
  className?: string
  noPadding?: boolean
}

export function SectionCard({
  title,
  subtitle,
  actions,
  children,
  className = '',
  noPadding = false,
}: SectionCardProps) {
  const hasHeader = Boolean(title || subtitle || actions)

  return (
    <section
      className={`rounded-xl border border-neutral-200/90 bg-white shadow-xs overflow-hidden ${className}`}
    >
      {hasHeader && (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-neutral-100 bg-neutral-50/60 px-5 py-3.5">
          <div>
            {title && (
              <h3 className="text-sm font-bold text-neutral-900 tracking-tight">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-xs text-neutral-500 mt-0.5">
                {subtitle}
              </p>
            )}
          </div>
          {actions && (
            <div className="flex items-center gap-2 shrink-0">
              {actions}
            </div>
          )}
        </div>
      )}
      <div className={noPadding ? '' : 'p-4 sm:p-5'}>
        {children}
      </div>
    </section>
  )
}
