import { FileQuestion } from 'lucide-react'

interface EmptyStateProps {
  message: string
  actionLabel?: string
  onAction?: () => void
}

export function EmptyState({ message, actionLabel, onAction }: EmptyStateProps) {
  return (
    <div 
      className="flex flex-col items-center justify-center rounded-radius-md border border-dashed border-neutral-300 bg-neutral-50 px-6 py-12 text-center"
      role="status"
    >
      <FileQuestion className="h-10 w-10 text-neutral-400 mb-4" aria-hidden="true" />
      <p className="text-body text-neutral-600 max-w-sm mb-6">{message}</p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="inline-flex items-center justify-center rounded-radius-sm bg-status-info px-4 py-2 text-small font-semibold text-neutral-50 hover:bg-status-info/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-status-info transition-colors duration-fast"
        >
          {actionLabel}
        </button>
      )}
    </div>
  )
}
