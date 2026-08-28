import { useState, useEffect, useRef } from 'react'
import { RotateCcw, Sparkles, Send, ShieldCheck, AlertTriangle } from 'lucide-react'
import { apiClient } from '@/lib/apiClient'
import { MarkdownContent } from '@/components/nexus/MarkdownContent'
import type { CopilotQueryResponse } from '@shared/contracts/api'

interface CaseCopilotPanelProps {
  caseId: string
  caseLabel?: string
}

interface CaseCopilotMessage {
  id: string
  role: 'user' | 'assistant'
  text: string
  timestamp: string
  response?: CopilotQueryResponse
}

function loadMessages(storageKey: string): CaseCopilotMessage[] {
  if (typeof window === 'undefined') return []
  try {
    const saved = sessionStorage.getItem(storageKey)
    if (!saved) return []
    const parsed = JSON.parse(saved) as { messages?: CaseCopilotMessage[]; question?: string; response?: CopilotQueryResponse }
    if (Array.isArray(parsed.messages)) return parsed.messages
    if (parsed.question && parsed.response) {
      return [
        { id: `user-${Date.now()}`, role: 'user', text: parsed.question, timestamp: parsed.response.query || new Date().toISOString() },
        { id: `assistant-${Date.now()}`, role: 'assistant', text: parsed.response.answer, timestamp: new Date().toISOString(), response: parsed.response },
      ]
    }
  } catch {
    // Ignore malformed session data and start a clean case transcript.
  }
  return []
}

export function CaseCopilotPanel({ caseId, caseLabel }: CaseCopilotPanelProps) {
  const storageKey = `nexus_case_copilot_${caseId}`
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<CaseCopilotMessage[]>(() => loadMessages(storageKey))
  const [isLoading, setIsLoading] = useState(false)
  const skipPersistRef = useRef(false)

  useEffect(() => {
    if (skipPersistRef.current) {
      skipPersistRef.current = false
      return
    }
    try {
      sessionStorage.setItem(storageKey, JSON.stringify({ messages }))
    } catch {
      // ignore
    }
  }, [messages, storageKey])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim() || isLoading) return

    setIsLoading(true)
    const text = question.trim()
    setQuestion('')
    setMessages((previous) => [...previous, {
      id: `user-${Date.now()}`,
      role: 'user',
      text,
      timestamp: new Date().toISOString(),
    }])
    try {
      const res = await apiClient.queryCopilot({
        query: text,
        case_id: caseId,
      })
      setMessages((previous) => [...previous, {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        text: res.answer,
        timestamp: new Date().toISOString(),
        response: res,
      }])
    } catch (err) {
      console.error('Case copilot query failed:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const resetChat = () => {
    skipPersistRef.current = true
    setMessages([])
    setQuestion('')
    try {
      sessionStorage.removeItem(storageKey)
    } catch {
      // ignore
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
          <button type="button" onClick={resetChat} className="ml-auto inline-flex items-center gap-1 rounded border border-neutral-300 px-2 py-1 text-xs font-semibold text-neutral-700 hover:bg-neutral-50">
            <RotateCcw className="h-3.5 w-3.5" /> Reset Chat
          </button>
      </div>

        {messages.map((message) => message.role === 'user' ? (
          <div key={message.id} className="rounded-xl bg-blue-50 border border-blue-200 p-3 text-sm text-blue-950">
            {message.text}
          </div>
        ) : (
          <div
            key={message.id}
            className={`rounded-xl p-4 space-y-3 ${
              message.response?.is_refusal
              ? 'bg-red-50 border border-red-200 text-red-950'
              : 'bg-neutral-50 border border-neutral-200 text-neutral-900'
          }`}
        >
            {message.response?.is_refusal && (
            <div className="flex items-center gap-2 text-xs font-bold text-red-800">
              <AlertTriangle className="h-4 w-4 text-red-600" />
              Guardrail Triggered: Autonomous guilt or predictive inference prohibited.
            </div>
          )}
          <MarkdownContent content={message.text} />

          {message.response?.reasoning_path && message.response.reasoning_path.length > 0 && (
            <div className="rounded-lg bg-white p-2.5 text-xs border border-neutral-200 space-y-1 shadow-xs">
              <div className="font-bold text-neutral-700 text-[11px] uppercase tracking-wider">
                Reasoning Lineage:
              </div>
              <ul className="space-y-1 pl-3 list-disc text-neutral-700 text-[11px]">
                {message.response.reasoning_path.map((step, sIdx) => (
                  <li key={sIdx}>{step}</li>
                ))}
              </ul>
            </div>
          )}

          {message.response?.grounded_citations && message.response.grounded_citations.length > 0 && (
            <div className="rounded-lg bg-white p-2.5 text-xs border border-neutral-200 space-y-1.5 shadow-xs">
              <div className="font-bold text-neutral-800 flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                Citations:
              </div>
              {message.response.grounded_citations.map((c, idx) => (
                <div key={idx} className="text-neutral-700 text-[11px]">
                  <strong className="text-neutral-900">[{c.source_type} {c.source_id}]</strong> {c.fact}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}

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
