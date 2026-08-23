import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { ShieldCheck, RotateCcw, Zap } from 'lucide-react'
import { Button } from '@/components/Button'
import { Input } from '@/components/Input'
import { apiFetch } from '@/lib/apiClient'
import type { ChatResponse, UserRole } from '@shared/contracts/api'
import { COPILOT_PROVIDER } from '@/config/copilot'
import { ConvoKraftCopilot } from '@/components/ConvoKraftCopilot'

interface CaseCopilotPanelProps {
  caseId: string
  caseLabel?: string
  role: UserRole
}

export function CaseCopilotPanel({ caseId, caseLabel, role }: CaseCopilotPanelProps) {
  if (COPILOT_PROVIDER === 'convokraft') {
    return <ConvoKraftCopilot caseLabel={caseLabel || caseId} />
  }

  return <QuickMLCaseCopilot caseId={caseId} role={role} />
}

function QuickMLCaseCopilot({ caseId, role: _role }: CaseCopilotPanelProps) {
  const [question, setQuestion] = useState('')

  const query = useMutation<ChatResponse, Error, string>({
    mutationFn: (value) =>
      apiFetch<ChatResponse>('/api/chat', {
        method: 'POST',
        body: JSON.stringify({ message: value, case_id: caseId }),
      }),
  })

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (question.trim()) {
      query.mutate(question.trim())
      // Clear the input on submit so the user can type a follow-up
      setQuestion('')
    }
  }

  const handleClear = () => {
    query.reset()
    setQuestion('')
  }

  return (
    <section aria-labelledby="case-copilot-heading" className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4">
      <div className="flex items-start gap-3">
        <ShieldCheck className="mt-0.5 h-5 w-5 text-status-info" aria-hidden="true" />
        <div>
          <h2 id="case-copilot-heading" className="text-h2 font-semibold text-neutral-900">Case Copilot</h2>
          <p className="mt-1 text-small text-neutral-600">
            Evidence-linked assistance for the current case record.
          </p>
        </div>
      </div>

      <form className="mt-4 flex flex-col gap-2 sm:flex-row" onSubmit={submit} aria-label="Case Copilot query form">
        <div className="flex-1">
          <Input
            label="Question about this case"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="What is blocking this investigation?"
          />
        </div>
        <div className="flex gap-2 self-end">
          <Button
            type="submit"
            isLoading={query.isPending}
            disabled={!question.trim()}
            aria-label="Submit question to Copilot"
          >
            Ask
          </Button>
          {(query.data ?? query.isError) && (
            <Button
              type="button"
              variant="ghost"
              onClick={handleClear}
              aria-label="Clear Copilot response and start over"
              title="Clear response"
            >
              <RotateCcw className="h-4 w-4" aria-hidden="true" />
            </Button>
          )}
        </div>
      </form>

      {/* Response area with aria-live for screen readers */}
      <div className="mt-4" role="log" aria-live="polite" aria-label="Copilot response" aria-atomic="false">
        {query.isPending && (
          <p className="text-small text-neutral-600" aria-live="polite">Running query...</p>
        )}

        {query.isError && (
          <div className="rounded-radius-sm border border-status-danger/20 bg-status-danger/5 p-3">
            <p className="text-small text-status-danger">{query.error.message}</p>
          </div>
        )}

        {query.data && (
          <div className="rounded-radius-sm border border-neutral-200 bg-neutral-50 p-3">
            <p className="text-small text-neutral-800 whitespace-pre-wrap">{query.data.message}</p>
            {query.data.intent?.confidence !== undefined && (
              <p className="mt-2 text-caption text-neutral-500 font-mono">
                Confidence: {Math.round(query.data.intent.confidence * 100)}%
              </p>
            )}
            {(query.data.metadata as Record<string, unknown>)?.provider === 'zoho_catalyst_quickml' && (
              <div className="mt-2 flex items-center gap-1 text-caption text-neutral-400">
                <Zap className="h-3 w-3" aria-hidden="true" />
                <span>Powered by Zoho Catalyst QuickML &middot; GLM-4.7-Flash</span>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  )
}

