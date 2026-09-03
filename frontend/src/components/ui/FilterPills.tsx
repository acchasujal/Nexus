
export interface FilterPillOption<T extends string = string> {
  value: T
  label: string
  count?: number
  variant?: 'default' | 'danger' | 'warning' | 'info'
}

interface FilterPillsProps<T extends string = string> {
  options: FilterPillOption<T>[]
  value: T
  onChange: (value: T) => void
  label?: string
  className?: string
}

export function FilterPills<T extends string = string>({
  options,
  value,
  onChange,
  label,
  className = '',
}: FilterPillsProps<T>) {
  return (
    <div
      role="group"
      aria-label={label || 'Filter options'}
      className={`flex items-center gap-1.5 overflow-x-auto whitespace-nowrap p-1 bg-neutral-100/70 rounded-xl border border-neutral-200/80 ${className}`}
    >
      {label && (
        <span className="text-[11px] font-bold text-neutral-500 uppercase tracking-wider px-2 shrink-0">
          {label}:
        </span>
      )}
      {options.map((option) => {
        const isSelected = option.value === value
        return (
          <button
            key={option.value}
            onClick={() => onChange(option.value)}
            aria-pressed={isSelected}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all shrink-0 cursor-pointer ${
              isSelected
                ? 'bg-white text-neutral-900 shadow-xs border border-neutral-200 font-bold'
                : 'text-neutral-600 hover:text-neutral-900 hover:bg-white/50 border border-transparent'
            }`}
          >
            <span>{option.label}</span>
            {typeof option.count === 'number' && (
              <span
                className={`rounded-full px-1.5 py-0.2 text-[10px] tabular-nums font-bold ${
                  isSelected
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-neutral-200/80 text-neutral-600'
                }`}
              >
                {option.count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
