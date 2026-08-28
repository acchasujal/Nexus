import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Sparkles, 
  Send, 
  RotateCcw, 
  ShieldCheck, 
  AlertTriangle, 
  FileText, 
  Bot, 
  User,
  ExternalLink,
  Briefcase,
  Network,
  Clock,
  ChevronRight,
} from 'lucide-react'
import { apiClient } from '@/lib/apiClient'
import { EvidenceDrawer } from '@/components/nexus/EvidenceDrawer'
import type { GroundedCitation } from '@shared/contracts/api'

/** Maps canonical source record IDs to the most representative graph edge
 *  that carries them in its evidence_ids. Derived from NEXUS golden fixture. */
const SOURCE_TO_EDGE: Record<string, string> = {
  'SRC-FIR-141':  'E-ACCUSE-141',
  'SRC-FIR-207':  'E-ACCUSE-207',
  'SRC-CDR-A12':  'E-USEPH-1',
  'SRC-CDR-B31':  'E-USEPH-2',
  'SRC-TXN-55':   'E-TXN-55',
  'SRC-TXN-71':   'E-TXN-71',
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  text: string
  isRefusal?: boolean
  refusalReason?: string
  citations?: GroundedCitation[]
  evidenceIds?: string[]
  reasoningPath?: string[]
  suggestedActions?: string[]
  caseId?: string
  timestamp: string
}

const INITIAL_WELCOME_MESSAGE: Message = {
  id: 'welcome-0',
  role: 'assistant',
  text: 'Hello Investigator. I am the NEXUS Intelligence Copilot. I can assist in analyzing suspect networks, phone call bursts, bank transaction chains, and corroborating evidence across intelligence files.',
  timestamp: '2026-08-23T00:00:00.000Z',
}

const SUGGESTED_PROMPTS = [
  { text: 'How are the two cases connected?', type: 'connection' },
  { text: 'Is the accused guilty of committing cyber financial fraud?', type: 'safety' },
  { text: 'Show multi-hop bank transaction layering chains across flagged accounts', type: 'financial' },
  { text: 'Find all bridge entities connecting narcotics and hawala syndicates', type: 'bridges' },
]

const STORAGE_KEY = 'nexus_copilot_chat_history'

function loadInitialMessages(): Message[] {
  if (typeof window === 'undefined') return [INITIAL_WELCOME_MESSAGE]
  try {
    const saved = sessionStorage.getItem(STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed
      }
    }
  } catch (e) {
    console.warn('Failed to load copilot chat history from sessionStorage', e)
  }
  return [INITIAL_WELCOME_MESSAGE]
}

function createMessageId(role: 'user' | 'assistant' | 'err'): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${role}-${crypto.randomUUID()}`
  }
  return `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

export default function Copilot() {
  const navigate = useNavigate()
  const [messages, setMessages] = useState<Message[]>(loadInitialMessages)
  const [inputQuery, setInputQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [selectedRelationshipId, setSelectedRelationshipId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    if (typeof messagesEndRef.current?.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Persist chat messages to sessionStorage across in-app navigation
  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages))
    } catch (e) {
      console.warn('Failed to persist copilot chat history to sessionStorage', e)
    }
  }, [messages])

  const handleResetChat = () => {
    try {
      sessionStorage.removeItem(STORAGE_KEY)
    } catch (e) {
      // ignore
    }
    setMessages([INITIAL_WELCOME_MESSAGE])
  }

  const handleActionClick = (act: string, caseId?: string) => {
    const actLower = act.toLowerCase()
    if (caseId) {
      if (actLower.includes('open case')) {
        navigate(`/cases/${caseId}`)
        return
      }
      if (actLower.includes('view case network') || actLower.includes('view network')) {
        navigate(`/network?case_id=${caseId}`)
        return
      }
      if (actLower.includes('view timeline') || actLower.includes('timeline')) {
        navigate(`/timeline?case_id=${caseId}`)
        return
      }
      if (actLower.includes('view evidence') || actLower.includes('evidence')) {
        navigate(`/evidence?case_id=${caseId}`)
        return
      }
    }
    handleSend(act)
  }

  const handleSend = async (queryText?: string) => {
    const textToSend = (queryText || inputQuery).trim()
    if (!textToSend || isLoading) return

    const nowIso = new Date().toISOString()
    const userMessage: Message = {
      id: createMessageId('user'),
      role: 'user',
      text: textToSend,
      timestamp: nowIso,
    }

    setMessages((prev) => [...prev, userMessage])
    setInputQuery('')
    setIsLoading(true)

    try {
      // Use NEXUS copilot endpoint
      const response = await apiClient.queryNexusCopilot(textToSend)

      const responseTimeIso = new Date().toISOString()
      const assistantMessage: Message = {
        id: createMessageId('assistant'),
        role: 'assistant',
        text: response.answer,
        isRefusal: response.is_refusal,
        refusalReason: response.refusal_reason || undefined,
        citations: response.grounded_citations,
        evidenceIds: response.evidence_ids,
        reasoningPath: response.reasoning_path,
        suggestedActions: response.suggested_actions,
        caseId: response.case_id,
        timestamp: responseTimeIso,
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch {
      const errorTimeIso = new Date().toISOString()
      setMessages((prev) => [
        ...prev,
        {
          id: createMessageId('err'),
          role: 'assistant',
          text: 'An error occurred while querying the NEXUS graph intelligence service.',
          timestamp: errorTimeIso,
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto h-[calc(100vh-8rem)] flex flex-col">
      {/* Header */}
      <div className="border-b border-neutral-200 pb-4 flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 flex items-center gap-2.5">
            <Sparkles className="h-6 w-6 text-blue-600" />
            NEXUS Investigator Copilot
          </h1>
          <p className="text-xs text-neutral-600 mt-0.5">
            Evidence-grounded assistant • Strict refusal gate against autonomous guilt / predictive inference
          </p>
        </div>
        <button
          onClick={handleResetChat}
          className="flex items-center gap-1.5 text-xs text-neutral-700 hover:text-neutral-900 border border-neutral-300 bg-white px-3 py-1.5 rounded-lg shadow-sm hover:bg-neutral-50 transition-colors cursor-pointer"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          Reset Chat
        </button>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-2">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {m.role === 'assistant' && (
              <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center text-white shrink-0 mt-1 shadow-md">
                <Bot className="h-4 w-4" />
              </div>
            )}

            <div
              className={`max-w-2xl rounded-2xl p-4 space-y-3 shadow-sm ${
                m.role === 'user'
                  ? 'bg-blue-600 text-white ml-12'
                  : m.isRefusal
                  ? 'bg-red-50 border border-red-200 text-red-950'
                  : 'bg-white border border-neutral-200 text-neutral-900'
              }`}
            >
              {/* Refusal Notice Header if Guardrail triggered */}
              {m.isRefusal && (
                <div className="flex items-center gap-2 text-xs font-bold text-red-900 bg-red-100 px-2.5 py-1 rounded-lg border border-red-300">
                  <AlertTriangle className="h-4 w-4 shrink-0 text-red-600" />
                  Ethical &amp; Legal Guardrail Enforced
                </div>
              )}

              <p className="text-sm leading-relaxed whitespace-pre-wrap">{m.text}</p>

              {/* Dedicated Case Context Navigation Bar */}
              {m.caseId && (
                <div className="rounded-xl bg-blue-50/80 border border-blue-200 p-3 space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-blue-950 flex items-center gap-1.5">
                      <Briefcase className="h-3.5 w-3.5 text-blue-700" />
                      Investigation Case Context: {m.caseId}
                    </span>
                    <button
                      onClick={() => navigate(`/cases/${m.caseId}`)}
                      className="inline-flex items-center gap-1 text-[11px] font-bold text-blue-700 hover:text-blue-900 hover:underline cursor-pointer"
                    >
                      Open Case File <ChevronRight className="h-3 w-3" />
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-1.5 pt-1 border-t border-blue-100">
                    <button
                      onClick={() => navigate(`/cases/${m.caseId}`)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-blue-600 text-white font-medium text-[11px] hover:bg-blue-700 shadow-2xs transition-colors cursor-pointer"
                    >
                      <Briefcase className="h-3 w-3" />
                      Open Case Details
                    </button>
                    <button
                      onClick={() => navigate(`/network?case_id=${m.caseId}`)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-white border border-blue-300 text-blue-800 font-medium text-[11px] hover:bg-blue-50 shadow-2xs transition-colors cursor-pointer"
                    >
                      <Network className="h-3 w-3" />
                      View Case Network
                    </button>
                    <button
                      onClick={() => navigate(`/timeline?case_id=${m.caseId}`)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-white border border-blue-300 text-blue-800 font-medium text-[11px] hover:bg-blue-50 shadow-2xs transition-colors cursor-pointer"
                    >
                      <Clock className="h-3 w-3" />
                      View Timeline
                    </button>
                    <button
                      onClick={() => navigate(`/evidence?case_id=${m.caseId}`)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-white border border-blue-300 text-blue-800 font-medium text-[11px] hover:bg-blue-50 shadow-2xs transition-colors cursor-pointer"
                    >
                      <FileText className="h-3 w-3" />
                      View Evidence
                    </button>
                  </div>
                </div>
              )}

              {/* Grounded Evidence Citations */}
              {m.citations && m.citations.length > 0 && (
                <div className="rounded-xl bg-neutral-50 p-3 text-xs border border-neutral-200 space-y-2">
                  <div className="font-bold text-neutral-800 flex items-center gap-1.5">
                    <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                    Grounded Graph Citations &amp; Provenance:
                  </div>
                  {m.citations.map((cite, cIdx) => {
                    const isCaseCitation = cite.source_type === 'FIR' || cite.source_type === 'CASE' || Boolean(m.caseId)
                    return (
                      <div key={cIdx} className="text-neutral-700 flex items-start justify-between gap-2 bg-white p-2 rounded border border-neutral-200">
                        <div className="flex items-start gap-2">
                          <FileText className="h-3.5 w-3.5 text-blue-600 shrink-0 mt-0.5" />
                          <div>
                            <strong className="text-neutral-900">[{cite.source_type} {cite.source_id}]</strong>: {cite.fact} (confidence: {Math.round(cite.confidence * 100)}%)
                          </div>
                        </div>
                        {isCaseCitation && m.caseId && (
                          <button
                            onClick={() => navigate(`/cases/${m.caseId}`)}
                            className="inline-flex items-center gap-0.5 text-[10px] font-bold text-blue-700 hover:text-blue-900 shrink-0 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-200 cursor-pointer"
                            title={`Navigate to Case ${m.caseId}`}
                          >
                            <span>Open</span>
                            <ChevronRight className="h-2.5 w-2.5" />
                          </button>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}

              {/* NEXUS Grounded Evidence Chips */}
              {m.evidenceIds && m.evidenceIds.length > 0 && (
                <div className="rounded-xl bg-neutral-50 p-3 text-xs border border-neutral-200 space-y-2">
                  <div className="font-bold text-neutral-800 flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                      Grounded Evidence Records:
                    </span>
                    <span className="text-[10px] text-neutral-500 font-normal">Click to inspect forensic record</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {m.evidenceIds.map((id) => {
                      const relId = SOURCE_TO_EDGE[id] ?? null
                      return (
                        <button
                          key={id}
                          onClick={() => { if (relId) setSelectedRelationshipId(relId) }}
                          disabled={!relId}
                          className={`inline-flex items-center gap-1 rounded px-2 py-0.5 font-mono text-[11px] font-semibold border transition-colors shadow-2xs ${relId ? 'bg-amber-100 hover:bg-amber-200 text-amber-900 border-amber-300 cursor-pointer' : 'bg-neutral-100 text-neutral-500 border-neutral-200 cursor-default'}`}
                          title={relId ? `Click to view provenance for ${id}` : `Source record ${id}`}
                        >
                          <FileText className="h-3 w-3 text-amber-700" />
                          <span>{id}</span>
                          <ExternalLink className="h-2.5 w-2.5 opacity-60 ml-0.5" />
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* NEXUS Reasoning Path */}
              {m.reasoningPath && m.reasoningPath.length > 0 && (
                <div className="rounded-xl bg-neutral-50 p-3 text-xs border border-neutral-200 space-y-1.5">
                  <div className="font-bold text-neutral-700 text-[11px] uppercase tracking-wider">
                    Evidence Lineage &amp; Reasoning Path:
                  </div>
                  <ol className="space-y-1 pl-4 list-decimal text-neutral-700 text-[11px] font-medium">
                    {m.reasoningPath.map((step, sIdx) => (
                      <li key={sIdx} className="leading-relaxed">
                        {step}
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {/* Suggested Actions */}
              {m.suggestedActions && m.suggestedActions.length > 0 && (
                <div className="pt-2 border-t border-neutral-200 space-y-1.5">
                  <span className="text-[11px] font-semibold text-neutral-600">Suggested Next Steps:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {m.suggestedActions.map((act, aIdx) => (
                      <button
                        key={aIdx}
                        onClick={() => handleActionClick(act, m.caseId)}
                        className="text-xs bg-neutral-100 hover:bg-blue-50 hover:text-blue-800 hover:border-blue-300 text-neutral-800 px-2.5 py-1 rounded-lg border border-neutral-200 transition-colors cursor-pointer text-left"
                      >
                        {act}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <span className="block text-[10px] text-neutral-400 text-right">
                {m.timestamp.startsWith('2026-08-23T00:00:00') ? 'Today' : new Date(m.timestamp).toLocaleTimeString()}
              </span>
            </div>

            {m.role === 'user' && (
              <div className="h-8 w-8 rounded-full bg-blue-100 border border-blue-300 flex items-center justify-center text-blue-800 shrink-0 mt-1">
                <User className="h-4 w-4" />
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Prompts */}
      <div className="shrink-0 space-y-2">
        <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
          <span className="text-neutral-500 text-[11px] shrink-0 font-medium">Quick Prompts:</span>
          {SUGGESTED_PROMPTS.map((p, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(p.text)}
              className={`shrink-0 rounded-lg px-2.5 py-1 text-xs font-medium shadow-xs transition-colors ${
                p.type === 'safety'
                  ? 'bg-red-50 text-red-800 border border-red-200 hover:bg-red-100'
                  : 'bg-white text-neutral-800 border border-neutral-300 hover:bg-neutral-50 hover:text-neutral-900'
              }`}
            >
              {p.text}
            </button>
          ))}
        </div>

        {/* Query Input Box */}
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSend()
          }}
          className="flex items-center gap-2 bg-white border border-neutral-300 rounded-xl p-2 focus-within:border-blue-600 shadow-md"
        >
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder="Ask NEXUS Copilot (e.g. Find suspect phone links, verify bank layering, explain co-accused)..."
            className="flex-1 bg-transparent px-3 py-2 text-sm text-neutral-900 placeholder-neutral-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={!inputQuery.trim() || isLoading}
            className="rounded-lg bg-blue-600 p-2.5 text-white hover:bg-blue-700 transition-colors disabled:opacity-40 shadow-sm"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>

      <EvidenceDrawer
        relationshipId={selectedRelationshipId}
        onClose={() => setSelectedRelationshipId(null)}
      />
    </div>
  )
}
