import { useEffect, useRef } from 'react'
import { X, Keyboard } from 'lucide-react'

interface KeyboardShortcutsDialogProps {
  open: boolean
  onClose: () => void
}

const SHORTCUTS = [
  { key: '?', description: 'Open keyboard shortcuts help' },
  { key: '↑ / ↓', description: 'Navigate rows in a table' },
  { key: 'Enter', description: 'Open the selected case' },
  { key: 'Esc', description: 'Close dialogs and drawers' },
  { key: 'Tab', description: 'Move focus to the next interactive element' },
  { key: 'Shift + Tab', description: 'Move focus to the previous element' },
  { key: 'Space / Enter', description: 'Activate the focused button or link' },
] as const

/**
 * Accessible keyboard shortcuts reference dialog.
 *
 * - role="dialog" with aria-modal and aria-labelledby
 * - Focus trapped inside while open
 * - Closes on Escape or clicking the backdrop
 */
export function KeyboardShortcutsDialog({ open, onClose }: KeyboardShortcutsDialogProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null)

  // Trap focus and handle Escape when open
  useEffect(() => {
    if (!open) return

    // Move focus to close button when dialog opens
    closeButtonRef.current?.focus()

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      }

      // Focus trap: keep Tab cycling within this dialog
      if (e.key === 'Tab') {
        const focusable = document.querySelectorAll<HTMLElement>(
          '[data-keyboard-dialog] button, [data-keyboard-dialog] [tabindex]:not([tabindex="-1"])'
        )
        if (focusable.length === 0) return

        const first = focusable[0]
        const last = focusable[focusable.length - 1]

        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault()
            last.focus()
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault()
            first.focus()
          }
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, onClose])

  if (!open) return null

  return (
    // Backdrop
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/60 p-4"
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      {/* Dialog */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="keyboard-shortcuts-title"
        data-keyboard-dialog
        className="relative w-full max-w-md rounded-radius-md border border-neutral-200 bg-neutral-50 p-6 shadow-lg"
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Keyboard className="h-5 w-5 text-status-info" aria-hidden="true" />
            <h2 id="keyboard-shortcuts-title" className="text-h2 font-semibold text-neutral-900">
              Keyboard Shortcuts
            </h2>
          </div>
          <button
            ref={closeButtonRef}
            onClick={onClose}
            className="min-h-11 min-w-11 inline-flex items-center justify-center rounded-radius-sm text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700 focus-visible:ring-2 focus-visible:ring-status-info transition-colors duration-fast"
            aria-label="Close keyboard shortcuts dialog"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        {/* Shortcuts Table */}
        <table className="w-full text-small" aria-label="Keyboard shortcuts reference">
          <thead className="sr-only">
            <tr>
              <th scope="col">Key</th>
              <th scope="col">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-200">
            {SHORTCUTS.map(({ key, description }) => (
              <tr key={key}>
                <td className="py-2 pr-4 w-32">
                  <kbd className="inline-block rounded-radius-sm border border-neutral-300 bg-neutral-100 px-2 py-0.5 font-mono text-caption text-neutral-700">
                    {key}
                  </kbd>
                </td>
                <td className="py-2 text-neutral-700">{description}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <p className="mt-4 text-caption text-neutral-400">
          Press <kbd className="rounded-radius-sm border border-neutral-200 bg-neutral-100 px-1 py-0.5 font-mono text-[10px]">Esc</kbd> to close
        </p>
      </div>
    </div>
  )
}
