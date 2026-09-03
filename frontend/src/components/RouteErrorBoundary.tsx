import { useRouteError, isRouteErrorResponse, Link } from 'react-router-dom'
import { AlertOctagon, RotateCcw, Home } from 'lucide-react'

export function RouteErrorBoundary() {
  const error = useRouteError()
  let errorMessage = 'An unexpected error occurred in this intelligence workspace.'
  let errorStatus: number | string = '500'

  if (isRouteErrorResponse(error)) {
    errorStatus = error.status
    errorMessage = error.data?.message || error.statusText || errorMessage
  } else if (error instanceof Error) {
    errorMessage = error.message
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-50 px-4 py-12 sm:px-6 lg:px-8">
      <div className="max-w-md w-full rounded-2xl border border-neutral-200/90 bg-white p-6 sm:p-8 text-center space-y-6 shadow-sm">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-rose-50 text-rose-600 border border-rose-200/80 shadow-2xs">
          <AlertOctagon className="h-7 w-7" />
        </div>

        <div className="space-y-2">
          <span className="text-[11px] font-bold font-mono uppercase tracking-wider text-rose-700 bg-rose-50 px-2.5 py-0.5 rounded-full border border-rose-200">
            Error {errorStatus}
          </span>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-neutral-900">
            Workspace Error
          </h1>
          <p className="text-xs sm:text-sm text-neutral-600 leading-relaxed max-w-sm mx-auto">
            {errorMessage}
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
          <button
            onClick={() => window.location.reload()}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-lg bg-neutral-900 px-4 py-2.5 text-xs font-bold text-white hover:bg-neutral-800 transition-colors shadow-xs cursor-pointer"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Reload Page
          </button>
          <Link
            to="/worklist"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-lg border border-neutral-200 bg-white px-4 py-2.5 text-xs font-bold text-neutral-800 hover:bg-neutral-50 transition-colors shadow-2xs"
          >
            <Home className="h-3.5 w-3.5 text-neutral-500" />
            Return to Worklist
          </Link>
        </div>

        <div className="pt-3 border-t border-neutral-100 text-[11px] text-neutral-400">
          NEXUS Criminal Network Intelligence · SIH 2026 PS 26189
        </div>
      </div>
    </div>
  )
}
