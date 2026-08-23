import { useState } from 'react'
import { Sparkles, Send, ShieldCheck, AlertTriangle, FileText } from 'lucide-react'
import { apiClient } from '@/lib/apiClient'
import type { CopilotQueryResponse } from '@shared/contracts/api'

interface CaseCopilotPanelProps {
  caseId: string
  caseLabel?: string
}

export function CaseCopilotPanel({ caseId, caseLabel }: CaseCopilotPanelProps) {
  const [question, setQuestion] = useState('')
  const [response, setResponse] = useState<CopilotQueryResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim() || isLoading) return

    setIsLoading(true)
    try {
      const res = await apiClient.queryCopilot({
        query: question.trim(),
        case_id: caseId,
      })
      setResponse(res)
    } catch (err) {
      console.error('Case copilot query failed:', err)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5 space-y-4 shadow-lg">
      <div className="flex items-center gap-2.5 border-b border-neutral-800 pb-3">
        <Sparkles className="h-5 w-5 text-blue-500" />
        <div>
          <h3 className="text-base font-bold text-white">Investigation Copilot</h3>
          <p className="text-xs text-neutral-400">Scoped to this case • Grounded in graph evidence</p>
        </div>
      </div>

      {response && (
        <div
          className={`rounded-xl p-4 space-y-3 ${
            response.is_refusal
              ? 'bg-red-950/40 border border-red-800/60 text-neutral-200'
              : 'bg-neutral-950/80 border border-neutral-800 text-neutral-200'
          }`}
        >
          {response.is_refusal && (
            <div className="flex items-center gap-2 text-xs font-semibold text-red-400">
              <AlertTriangle className="h-4 w-4" />
              Guardrail Triggered: Autonomous guilt or predictive inference prohibited.
            </div>
          )}
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{response.answer}</p>

          {response.grounded_citations && response.grounded_citations.length > 0 && (
            <div className="rounded-lg bg-neutral-900/80 p-2.5 text-xs border border-neutral-800 space-y-1.5">
              <div className="font-semibold text-neutral-300 flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                Citations:
              </div>
              {response.grounded_citations.map((c, idx) => (
                <div key={idx} className="text-neutral-400 text-[11px]">
                  <strong>[{c.source_type} {c.source_id}]</strong> {c.fact}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={`Ask about ${caseLabel || caseId} (e.g. accused phone links, seized evidence)...`}
          className="flex-1 rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm text-neutral-100 placeholder-neutral-500 focus:border-blue-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={!question.trim() || isLoading}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 transition-colors disabled:opacity-50 flex items-center gap-1.5"
        >
          <Send className="h-4 w-4" />
          {isLoading ? 'Querying...' : 'Ask'}
        </button>
      </form>
    </div>
  )
}
