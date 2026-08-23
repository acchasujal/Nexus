import { useState, useRef, useEffect, useMemo } from 'react'
import { useMutation } from '@tanstack/react-query'
import { apiFetch } from '@/lib/apiClient'
import { useAuth } from '@/contexts/AuthContext'
import { useWorklist } from '@/hooks/useWorklist'
import { useCaseDetail } from '@/hooks/useCaseDetail'
import { ClockBadge } from '@/components/ClockBadge'
import { 
  Sparkles, 
  Send, 
  RotateCcw, 
  Copy, 
  Check, 
  ShieldCheck, 
  MessageSquare, 
  AlertCircle,
  Briefcase,
  Clock,
  Layers,
  FileText
} from 'lucide-react'
import type { ChatResponse, ChatMessage as SharedChatMessage } from '@shared/contracts/api'
import { COPILOT_PROVIDER } from '@/config/copilot'
import { ConvoKraftCopilot } from '@/components/ConvoKraftCopilot'

interface Message {
  id: string
  role: 'user' | 'assistant'
  text: string
  refused?: boolean
  refusal_reason?: string | null
  confidence?: number
  reasoning_path?: string[] | null
  timestamp: string
}

const SUGGESTED_PROMPTS = [
  { text: 'Is the accused likely to reoffend if granted bail?', type: 'safety' },
  { text: 'Detail the outstanding FSL and forensic blockers for this case.', type: 'query' },
  { text: 'Explain the 60-day statutory clock remaining deadline.', type: 'query' },
]

export default function Copilot() {
  if (COPILOT_PROVIDER === 'convokraft') {
    return <ConvoKraftCopilot className="mx-auto max-w-5xl" />
  }

  return <QuickMLCopilot />
}

function QuickMLCopilot() {
  const { role } = useAuth()
  const { data: cases } = useWorklist()
  
  // Map simulated dropdown values to real database UUIDs dynamically
  const realCase847 = useMemo(() => cases?.[0] || null, [cases])
  const realCase902 = useMemo(() => cases?.[1] || null, [cases])

  const [conversationId, setConversationId] = useState<string | null>(null)
  const [caseContext, setCaseContext] = useState<string>('847') // Default to first case
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      text: 'Welcome to CaseClock Investigation Copilot. I can help summarize statutory clocks, identify evidentiary blockers, and explain case escalations using investigation graph records.',
      timestamp: new Date().toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }),
    }
  ])
  const [input, setInput] = useState('')
  const [copiedId, setCopiedId] = useState<string | null>(null)
  
  const chatEndRef = useRef<HTMLDivElement>(null)

  // Determine active real UUID to load case details for the right panel
  const activeRealCaseId = useMemo(() => {
    if (caseContext === '847') return realCase847?.id || null
    if (caseContext === '902') return realCase902?.id || null
    return null
  }, [caseContext, realCase847, realCase902])

  // Fetch case details for the right panel
  const { data: activeCaseDetails } = useCaseDetail(activeRealCaseId || undefined)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const queryMutation = useMutation<ChatResponse, Error, { text: string; caseId: string | null }>({
    mutationFn: ({ text, caseId }) => {
      const historyPayload: SharedChatMessage[] = messages
        .filter(m => m.id !== 'welcome')
        .map(m => ({
          role: m.role,
          content: m.text,
        }))

      return apiFetch<ChatResponse>('/api/chat', {
        method: 'POST',
        body: JSON.stringify({
          message: text,
          conversation_id: conversationId || undefined,
          case_id: caseId || undefined,
          history: historyPayload,
        }),
      })
    },
    onSuccess: (data) => {
      if (data.conversation_id) {
        setConversationId(data.conversation_id)
      }
      const timestamp = new Date().toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
      const botMessage: Message = {
        id: Math.random().toString(36).substring(2, 11),
        role: 'assistant',
        text: data.message || '',
        confidence: data.intent?.confidence,
        timestamp,
      }
      setMessages(prev => [...prev, botMessage])
    },
    onError: (error) => {
      const timestamp = new Date().toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
      const errorMessage: Message = {
        id: Math.random().toString(36).substring(2, 11),
        role: 'assistant',
        text: 'Case Copilot is temporarily unavailable. Please try again shortly.',
        timestamp,
      }
      setMessages(prev => [...prev, errorMessage])
    }
  })

  const handleSend = (text: string) => {
    if (!text.trim()) return
    
    // Pass the real UUID to the backend for grounded querying
    const resolvedId = caseContext === '847' 
      ? realCase847?.id 
      : caseContext === '902' 
      ? realCase902?.id 
      : null

    const timestamp = new Date().toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
    const userMessage: Message = {
      id: Math.random().toString(36).substring(2, 11),
      role: 'user',
      text,
      timestamp,
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    queryMutation.mutate({ text, caseId: resolvedId || null })
  }

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 2000)
    })
  }

  const handleClear = () => {
    setConversationId(null)
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        text: 'Welcome to CaseClock Investigation Copilot. I can help summarize statutory clocks, identify evidentiary blockers, and explain case escalations using investigation graph records.',
        timestamp: new Date().toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }),
      }
    ])
    setInput('')
  }

  // Keyboard Shortcuts (Ctrl+L -> Clear, Ctrl+C -> Copy response)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key.toLowerCase() === 'l') {
        e.preventDefault()
        handleClear()
      }
      if (e.ctrlKey && e.key.toLowerCase() === 'c' && !window.getSelection()?.toString()) {
        const lastBotMessage = [...messages].reverse().find(m => m.role === 'assistant')
        if (lastBotMessage) {
          e.preventDefault()
          handleCopy(lastBotMessage.id, lastBotMessage.text)
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [messages])

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] space-y-4">
      {/* Copilot Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-neutral-200 pb-4">
        <div>
          <h1 className="text-h1 font-bold text-neutral-900 flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-status-info" /> Copilot Command Center
          </h1>
          <p className="text-body text-neutral-500">
            Factual grounded investigation intelligence. Legally constrained under BNSS guidelines.
          </p>
        </div>

        {/* Case Context Selection */}
        <div className="flex items-center gap-2">
          <label htmlFor="context-select" className="text-small font-semibold text-neutral-700">
            Case Context:
          </label>
          <select
            id="context-select"
            value={caseContext}
            onChange={(e) => setCaseContext(e.target.value)}
            className="rounded-radius-md border border-neutral-300 bg-white px-3 py-1.5 text-small font-medium text-neutral-800 shadow-sm focus:border-status-info focus:outline-none focus:ring-1 focus:ring-status-info"
          >
            <option value="847">{realCase847 ? `${realCase847.fir_number} (FSL Blocker)` : 'Case 847 Context'}</option>
            <option value="902">{realCase902 ? `${realCase902.fir_number} (Aggravated Assault)` : 'Case 902 Context'}</option>
            <option value="none">General Investigation Context</option>
          </select>
        </div>
      </div>

      {/* Main Chat Grid (Left 70% / Right 30%) */}
      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-10 gap-6">
        
        {/* Chat Window (Left/Center - 70%) */}
        <div className="lg:col-span-7 flex flex-col border border-neutral-200 rounded-radius-md bg-neutral-50 shadow-sm min-h-0">
          
          {/* Messages Stream */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
              >
                <div className="flex items-center gap-1.5 mb-1 text-[10px] text-neutral-400">
                  <span>{msg.role === 'user' ? 'Investigating Officer' : 'CaseClock Copilot'}</span>
                  <span>•</span>
                  <span>{msg.timestamp}</span>
                </div>
                
                <div
                  className={`relative w-full max-w-[95%] rounded-radius-md p-3 text-small leading-relaxed shadow-xs border ${
                    msg.role === 'user'
                      ? 'bg-neutral-800 border-neutral-700 text-neutral-100'
                      : msg.refused
                      ? 'bg-amber-50 border-amber-200 text-amber-900'
                      : 'bg-white border-neutral-200 text-neutral-800'
                  }`}
                >
                  {/* Assistant Safety Refusal */}
                  {msg.refused && (
                    <div className="flex items-start gap-2 mb-2">
                      <ShieldCheck className="h-4.5 w-4.5 text-amber-600 shrink-0 mt-0.5" />
                      <span className="font-bold text-amber-800">Compliance Boundary Refusal</span>
                    </div>
                  )}

                  <p className="whitespace-pre-wrap">{msg.text}</p>

                  {/* Confidence Display */}
                  {msg.role === 'assistant' && msg.confidence !== undefined && (
                    <div className="mt-2 text-[10px] text-neutral-400 font-mono">
                      Safety gate confidence: {Math.round(msg.confidence * 100)}%
                    </div>
                  )}

                  {/* Citations Reasoning Path */}
                  {msg.role === 'assistant' && msg.reasoning_path && msg.reasoning_path.length > 0 && (
                    <details className="mt-3 border-t border-neutral-200/60 pt-2 text-[11px]">
                      <summary className="cursor-pointer font-semibold text-status-info hover:underline focus:outline-none">
                        Show ground truth reasoning path
                      </summary>
                      <ul className="mt-1 list-inside list-decimal text-neutral-600 space-y-0.5 pl-1 font-mono">
                        {msg.reasoning_path.map((path, idx) => (
                          <li key={idx} className="truncate">{path}</li>
                        ))}
                      </ul>
                    </details>
                  )}

                  {/* Message Action Controls */}
                  <div className="absolute right-2 top-2 opacity-0 hover:opacity-100 focus-within:opacity-100 flex gap-1 transition-opacity duration-fast">
                    <button
                      onClick={() => handleCopy(msg.id, msg.text)}
                      className="p-1 rounded-radius-sm bg-neutral-100 hover:bg-neutral-200 text-neutral-500 focus:outline-none"
                      title="Copy response"
                    >
                      {copiedId === msg.id ? <Check className="h-3 w-3 text-status-success" /> : <Copy className="h-3 w-3" />}
                    </button>
                  </div>
                </div>
              </div>
            ))}

            {/* Loading typing indicator */}
            {queryMutation.isPending && (
              <div className="flex flex-col items-start">
                <div className="text-[10px] text-neutral-400 mb-1">CaseClock Copilot is compiling facts...</div>
                <div className="bg-white border border-neutral-200 rounded-radius-md px-4 py-3 flex items-center space-x-1.5 shadow-xs">
                  <div className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Prompt Entry Form (Textarea support for Shift+Enter / shortcuts) */}
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSend(input)
            }}
            className="p-3 border-t border-neutral-200 bg-white flex gap-2 rounded-b-radius-md"
          >
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSend(input)
                }
              }}
              placeholder="Ask Copilot about clocks or dependencies (Enter to Send, Shift+Enter for new line)..."
              disabled={queryMutation.isPending}
              rows={2}
              className="flex-grow rounded-radius-md border border-neutral-300 bg-neutral-50 px-3 py-2 text-small text-neutral-800 placeholder-neutral-400 focus:border-status-info focus:outline-none focus:ring-1 focus:ring-status-info disabled:opacity-50 resize-none font-sans"
            />
            <div className="flex flex-col gap-2 justify-center">
              <button
                type="submit"
                disabled={!input.trim() || queryMutation.isPending}
                className="px-3 py-2 rounded-radius-md bg-neutral-800 text-neutral-100 hover:bg-neutral-700 transition-colors focus:outline-none disabled:opacity-50 flex items-center justify-center"
              >
                <Send className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={handleClear}
                className="p-2 border border-neutral-200 rounded-radius-md text-neutral-500 hover:bg-neutral-50 focus:outline-none"
                title="Clear conversation history (Ctrl+L)"
              >
                <RotateCcw className="h-4 w-4" />
              </button>
            </div>
          </form>
        </div>

        {/* Sidebar Information / Context Panel (Right - 30%) */}
        <div className="lg:col-span-3 space-y-4 overflow-y-auto pr-1">
          {/* Active Case Context Metadata */}
          {activeCaseDetails && (
            <div className="p-4 border border-neutral-200 rounded-radius-md bg-neutral-50 shadow-sm space-y-3">
              <h3 className="text-small font-bold text-neutral-800 uppercase flex items-center gap-2 border-b border-neutral-200 pb-2">
                <Briefcase className="h-4 w-4 text-neutral-500" /> Active Case File
              </h3>
              <div className="text-small space-y-2">
                <div>
                  <span className="text-caption text-neutral-400 block uppercase tracking-wider">FIR NUMBER</span>
                  <span className="font-bold text-neutral-900">{activeCaseDetails.fir_number}</span>
                </div>
                <div>
                  <span className="text-caption text-neutral-400 block uppercase tracking-wider">OFFENCE CATEGORY</span>
                  <span className="font-semibold text-neutral-700">{activeCaseDetails.offence_category}</span>
                </div>
                <div>
                  <span className="text-caption text-neutral-400 block uppercase tracking-wider">POLICE STATION</span>
                  <span className="text-neutral-600">{activeCaseDetails.station_name}</span>
                </div>
              </div>
              
              {/* Clocks */}
              <div className="pt-2">
                <span className="text-caption font-bold text-neutral-500 uppercase tracking-wider block mb-1.5 flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" /> Statutory Clocks
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {activeCaseDetails.clocks.map(c => (
                    <ClockBadge key={c.id} status={c.status} daysRemaining={c.days_remaining} />
                  ))}
                </div>
              </div>

              {/* Dependencies */}
              <div className="pt-2">
                <span className="text-caption font-bold text-neutral-500 uppercase tracking-wider block mb-1.5 flex items-center gap-1">
                  <Layers className="h-3.5 w-3.5" /> Blockers &amp; Dependencies
                </span>
                {activeCaseDetails.dependencies.length === 0 ? (
                  <span className="text-[11px] text-neutral-400 italic">No unresolved blockers.</span>
                ) : (
                  <ul className="space-y-1">
                    {activeCaseDetails.dependencies.map(d => (
                      <li key={d.id} className="text-[11px] bg-white border border-neutral-200 rounded px-2 py-1 text-neutral-700 font-medium">
                        {d.name} ({d.status})
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}

          {/* Suggested Prompts */}
          <div className="p-4 border border-neutral-200 rounded-radius-md bg-neutral-50 shadow-sm space-y-3">
            <h3 className="text-small font-bold text-neutral-800 uppercase flex items-center gap-2 border-b border-neutral-200 pb-2">
              <MessageSquare className="h-4 w-4 text-neutral-500" /> Suggested Prompts
            </h3>
            <div className="flex flex-col gap-2">
              {SUGGESTED_PROMPTS.map((prompt) => (
                <button
                  key={prompt.text}
                  type="button"
                  onClick={() => handleSend(prompt.text)}
                  disabled={queryMutation.isPending}
                  className={`text-left text-caption p-2.5 rounded-radius-sm border hover:bg-neutral-100 transition-colors ${
                    prompt.type === 'safety'
                      ? 'border-amber-200 bg-amber-50/50 hover:bg-amber-100/60'
                      : 'border-neutral-200 bg-white'
                  }`}
                >
                  <span className="font-semibold text-neutral-800 block mb-0.5">{prompt.text}</span>
                  <span className="text-[10px] text-neutral-400 block font-mono">
                    {prompt.type === 'safety' ? 'Safety Guardrail Test' : 'Grounded Case Query'}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Shortcuts Info */}
          <div className="p-4 border border-neutral-200 rounded-radius-md bg-neutral-50 shadow-sm space-y-3">
            <h3 className="text-small font-bold text-neutral-800 uppercase flex items-center gap-2 border-b border-neutral-200 pb-1.5">
              Keyboard Shortcuts
            </h3>
            <dl className="text-[11px] space-y-1 text-neutral-600 font-mono">
              <div className="flex justify-between">
                <dt>Send Prompt</dt>
                <dd className="bg-neutral-200 px-1 rounded">Enter</dd>
              </div>
              <div className="flex justify-between">
                <dt>New Line</dt>
                <dd className="bg-neutral-200 px-1 rounded">Shift + Enter</dd>
              </div>
              <div className="flex justify-between">
                <dt>Clear chat</dt>
                <dd className="bg-neutral-200 px-1 rounded">Ctrl + L</dd>
              </div>
              <div className="flex justify-between">
                <dt>Copy latest response</dt>
                <dd className="bg-neutral-200 px-1 rounded">Ctrl + C</dd>
              </div>
            </dl>
          </div>

          {/* Compliance Info */}
          <div className="p-4 border border-neutral-200 rounded-radius-md bg-neutral-50 shadow-sm flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-status-info shrink-0 mt-0.5" />
            <div className="text-caption text-neutral-600 space-y-1">
              <h4 className="font-bold text-neutral-800 flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5" /> Compliance Guardrails
              </h4>
              <p className="leading-relaxed text-[11px]">
                Copilot executes intent checks via standard NLP filters. Legally barred queries (guilt inference, reoffending likelihood, predictions) trigger a safety refusal screen.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
