import React, { useId } from 'react'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, type = 'text', ...props }, ref) => {
    const inputId = useId()
    const errorId = useId()

    return (
      <div className="w-full space-y-1.5 text-left">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-small font-semibold text-neutral-700"
          >
            {label}
          </label>
        )}
        <input
          id={inputId}
          type={type}
          ref={ref}
          className={twMerge(
            clsx(
              'block min-h-11 w-full rounded-radius-sm border border-neutral-300 bg-neutral-50 px-3 py-1.5 text-small text-neutral-900 placeholder-neutral-400 focus:border-status-info focus:ring-1 focus:ring-status-info transition-colors duration-fast disabled:opacity-50',
              error ? 'border-status-danger focus:border-status-danger focus:ring-status-danger' : ''
            ),
            className
          )}
          aria-invalid={error ? 'true' : 'false'}
          aria-describedby={error ? errorId : undefined}
          {...props}
        />
        {error && (
          <p
            id={errorId}
            className="text-caption text-status-danger font-semibold mt-1"
          >
            {error}
          </p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'
