import React from 'react'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
}

export function Button({
  className,
  variant = 'primary',
  size = 'md',
  isLoading,
  disabled,
  children,
  ...props
}: ButtonProps) {
  const baseStyles = 'inline-flex min-h-11 items-center justify-center font-semibold rounded-radius-sm transition-all duration-fast focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-50 disabled:pointer-events-none'
  
  const variants = {
    primary: 'bg-status-info text-neutral-50 hover:bg-status-info/90 focus-visible:outline-status-info',
    secondary: 'border border-neutral-300 bg-neutral-50 text-neutral-800 hover:bg-neutral-100 focus-visible:outline-neutral-400',
    ghost: 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-800 focus-visible:outline-neutral-400',
    danger: 'bg-status-danger text-neutral-50 hover:bg-status-danger/90 focus-visible:outline-status-danger',
  }

  const sizes = {
    sm: 'px-3 py-1.5 text-caption',
    md: 'px-4 py-2 text-small',
    lg: 'px-6 py-3 text-body',
  }

  return (
    <button
      disabled={disabled || isLoading}
      className={twMerge(clsx(baseStyles, variants[variant], sizes[size], className))}
      {...props}
    >
      {isLoading ? (
        <>
          <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-current" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          Loading...
        </>
      ) : children}
    </button>
  )
}
