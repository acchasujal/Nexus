interface LoadingSkeletonProps {
  layout?: 'table' | 'detail' | 'card'
  rows?: number
}

export function LoadingSkeleton({ layout = 'table', rows = 6 }: LoadingSkeletonProps) {
  if (layout === 'table') {
    return (
      <div className="w-full space-y-4" aria-busy="true">
        {/* Table header skeleton */}
        <div className="h-10 w-full rounded-radius-sm bg-neutral-200 animate-shimmer" />
        
        {/* Table row skeletons */}
        <div className="space-y-2">
          {Array.from({ length: rows }).map((_, i) => (
            <div key={i} className="flex space-x-4 items-center h-12 w-full border-b border-neutral-200 px-4">
              <div className="h-4 w-1/4 rounded-radius-sm bg-neutral-100 animate-shimmer" />
              <div className="h-4 w-1/3 rounded-radius-sm bg-neutral-100 animate-shimmer" />
              <div className="h-4 w-1/6 rounded-radius-sm bg-neutral-100 animate-shimmer" />
              <div className="h-4 w-1/8 rounded-radius-sm bg-neutral-100 animate-shimmer" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (layout === 'detail') {
    return (
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3" aria-busy="true">
        {/* Left 2 columns */}
        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-radius-md border border-neutral-200 p-6 space-y-4 bg-neutral-50">
            <div className="h-6 w-1/3 rounded-radius-sm bg-neutral-200 animate-shimmer" />
            <div className="h-24 w-full rounded-radius-sm bg-neutral-100 animate-shimmer" />
          </div>
          <div className="rounded-radius-md border border-neutral-200 p-6 space-y-4 bg-neutral-50">
            <div className="h-6 w-1/4 rounded-radius-sm bg-neutral-200 animate-shimmer" />
            <div className="space-y-2">
              <div className="h-10 w-full rounded-radius-sm bg-neutral-100 animate-shimmer" />
              <div className="h-10 w-full rounded-radius-sm bg-neutral-100 animate-shimmer" />
            </div>
          </div>
        </div>
        {/* Right column */}
        <div className="rounded-radius-md border border-neutral-200 p-6 bg-neutral-50 space-y-4">
          <div className="h-6 w-1/2 rounded-radius-sm bg-neutral-200 animate-shimmer" />
          <div className="h-96 w-full rounded-radius-sm bg-neutral-100 animate-shimmer" />
        </div>
      </div>
    )
  }

  // Card grid layout
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4" aria-busy="true">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="rounded-radius-md border border-neutral-200 p-4 bg-neutral-50 space-y-3">
          <div className="h-4 w-1/2 rounded-radius-sm bg-neutral-200 animate-shimmer" />
          <div className="h-8 w-2/3 rounded-radius-sm bg-neutral-300 animate-shimmer" />
        </div>
      ))}
    </div>
  )
}
