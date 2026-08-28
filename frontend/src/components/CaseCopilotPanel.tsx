import { useState, useEffect } from 'react'
import { Sparkles, Send, ShieldCheck, AlertTriangle } from 'lucide-react'
import { apiClient } from '@/lib/apiClient'
import type { CopilotQueryResponse } from '@shared/contracts/api'

interface CaseCopilotPanelProps {
  caseId: string
  caseLabel?: string
}

export function CaseCopilotPanel({ caseId, caseLabel }: CaseCopilotPanelProps) {
  const storageKey = `nexus_case_copilot_${caseId}`
  const [question, setQuestion] = useState(() => {
    if (typeof window === 'undefined') return ''
    try {
      const saved = sessionStorage.getItem(storageKey)
      if (saved) {
        const parsed = JSON.parse(saved)
        return parsed.question || ''
      }
    } catch {
      // ignore
    }
    return ''
  })
  const [response, setResponse] = useState<CopilotQueryResponse | null>(() => {
    if (typeof window === 'undefined') return null
    try {
      const saved = sessionStorage.getItem(storageKey)
      if (saved) {
        const parsed = JSON.parse(saved)
        return parsed.response || null
      }
    } catch {
      // ignore
    }
    return null
  })
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    try {
      if (response || question) {
        sessionStorage.setItem(storageKey, JSON.stringify({ question, response }))
      }
    } catch {
      // ignore
    }
  }, [question, response, storageKey])

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
    <div className="rounded-xl border border-neutral-200 bg-white p-5 space-y-4 shadow-sm">
      <div className="flex items-center gap-2.5 border-b border-neutral-200 pb-3">
        <Sparkles className="h-5 w-5 text-blue-600" />
        <div>
          <h3 className="text-base font-bold text-neutral-900">Investigation Copilot</h3>
          <p className="text-xs text-neutral-600">Scoped to this case • Grounded in graph evidence</p>
        </div>
      </div>

      {response && (
        <div
          className={`rounded-xl p-4 space-y-3 ${
            response.is_refusal
              ? 'bg-red-50 border border-red-200 text-red-950'
              : 'bg-neutral-50 border border-neutral-200 text-neutral-900'
          }`}
        >
          {response.is_refusal && (
            <div className="flex items-center gap-2 text-xs font-bold text-red-800">
              <AlertTriangle className="h-4 w-4 text-red-600" />
              Guardrail Triggered: Autonomous guilt or predictive inference prohibited.
            </div>
          )}
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{response.answer}</p>

          {response.reasoning_path && response.reasoning_path.length > 0 && (
            <div className="rounded-lg bg-white p-2.5 text-xs border border-neutral-200 space-y-1 shadow-xs">
              <div className="font-bold text-neutral-700 text-[11px] uppercase tracking-wider">
                Reasoning Lineage:
              </div>
              <ul className="space-y-1 pl-3 list-disc text-neutral-700 text-[11px]">
                {response.reasoning_path.map((step, sIdx) => (
                  <li key={sIdx}>{step}</li>
                ))}
              </ul>
            </div>
          )}

          {response.grounded_citations && response.grounded_citations.length > 0 && (
            <div className="rounded-lg bg-white p-2.5 text-xs border border-neutral-200 space-y-1.5 shadow-xs">
              <div className="font-bold text-neutral-800 flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                Citations:
              </div>
              {response.grounded_citations.map((c, idx) => (
                <div key={idx} className="text-neutral-700 text-[11px]">
                  <strong className="text-neutral-900">[{c.source_type} {c.source_id}]</strong> {c.fact}
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
          className="flex-1 rounded-lg border border-neutral-300 bg-neutral-50 px-3 py-2 text-sm text-neutral-900 placeholder-neutral-500 focus:bg-white focus:border-blue-600 focus:outline-none"
        />
        <button
          type="submit"
          disabled={!question.trim() || isLoading}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-bold text-white hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-sm"
        >
          <Send className="h-4 w-4" />
          {isLoading ? 'Querying...' : 'Ask'}
        </button>
      </form>
    </div>
  )
}
