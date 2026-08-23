import { AlertCircle } from 'lucide-react'

interface ErrorStateProps {
  message: string
  onRetry?: () => void
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div 
      className="flex flex-col items-center justify-center rounded-radius-md border border-status-danger/20 bg-status-danger/5 px-6 py-10 text-center"
      role="alert"
    >
      <AlertCircle className="h-10 w-10 text-status-danger mb-3" aria-hidden="true" />
      <h3 className="text-h2 font-semibold text-status-danger mb-2">Operation Failed</h3>
      <p className="text-body text-neutral-700 max-w-md mb-6">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center justify-center rounded-radius-sm bg-status-danger px-4 py-2 text-small font-semibold text-neutral-50 hover:bg-status-danger/90 transition-colors duration-fast"
        >
          Retry Action
        </button>
      )}
    </div>
  )
}
