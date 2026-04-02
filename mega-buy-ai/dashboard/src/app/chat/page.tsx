'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import {
  MessageSquare, Plus, Send, Loader2, Trash2, ChevronLeft,
  Bot, User, Clock, Lightbulb, X, Coins, Zap
} from 'lucide-react'

const API = 'http://localhost:8002'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

interface Conversation {
  id: string
  title: string
  created_at: string
  updated_at: string
  messages?: Message[]
}

interface Insight {
  id: string
  insight: string
  category: string
  priority: number
  created_at: string
}

interface TokenUsage {
  budget: { initial_usd: number; spent_usd: number; remaining_usd: number; pct_used: number }
  today: { input_tokens: number; output_tokens: number; cost_usd: number; requests: number }
  this_month: { input_tokens: number; output_tokens: number; cost_usd: number; requests: number }
  all_time: { input_tokens: number; output_tokens: number; cost_usd: number; requests: number }
}

export default function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConv, setActiveConv] = useState<Conversation | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [loading, setLoading] = useState(true)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [showInsights, setShowInsights] = useState(false)
  const [showUsage, setShowUsage] = useState(false)
  const [insights, setInsights] = useState<Insight[]>([])
  const [usage, setUsage] = useState<TokenUsage | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Load conversations
  const loadConversations = useCallback(async () => {
    try {
      const res = await fetch(`${API}/chat/conversations`)
      const data = await res.json()
      setConversations(data.conversations || [])
    } catch (e) {
      console.error('Failed to load conversations:', e)
    }
    setLoading(false)
  }, [])

  useEffect(() => { loadConversations() }, [loadConversations])

  // Load insights
  const loadInsights = useCallback(async () => {
    try {
      const res = await fetch(`${API}/insights`)
      const data = await res.json()
      setInsights(data.insights || [])
    } catch (e) { console.error('Failed to load insights:', e) }
  }, [])

  useEffect(() => { loadInsights() }, [loadInsights])

  // Load token usage
  const loadUsage = useCallback(async () => {
    try {
      const res = await fetch(`${API}/usage`)
      const data = await res.json()
      setUsage(data)
    } catch (e) { console.error('Failed to load usage:', e) }
  }, [])

  useEffect(() => { loadUsage() }, [loadUsage])

  const deleteInsight = async (id: string) => {
    await fetch(`${API}/insights/${id}`, { method: 'DELETE' })
    setInsights(prev => prev.filter(i => i.id !== id))
  }

  // Load a conversation's messages
  const openConversation = async (conv: Conversation) => {
    try {
      const res = await fetch(`${API}/chat/conversations/${conv.id}`)
      const data = await res.json()
      setActiveConv(data)
      setMessages(data.messages || [])
    } catch (e) {
      console.error('Failed to load conversation:', e)
    }
  }

  // Create new conversation
  const newConversation = async () => {
    try {
      const res = await fetch(`${API}/chat/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'Nouvelle conversation' }),
      })
      const data = await res.json()
      if (data.id) {
        const conv = { id: data.id, title: data.title, created_at: new Date().toISOString(), updated_at: new Date().toISOString(), messages: [] }
        setConversations(prev => [conv, ...prev])
        setActiveConv(conv)
        setMessages([])
        inputRef.current?.focus()
      }
    } catch (e) {
      console.error('Failed to create conversation:', e)
    }
  }

  // Send message
  const sendMessage = async () => {
    if (!input.trim() || !activeConv || sending) return

    const userMsg: Message = { role: 'user', content: input.trim(), timestamp: new Date().toISOString() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setSending(true)

    try {
      const res = await fetch(`${API}/chat/conversations/${activeConv.id}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg.content }),
      })
      const data = await res.json()

      const assistantMsg: Message = {
        role: 'assistant',
        content: data.response || data.error || 'Erreur',
        timestamp: new Date().toISOString(),
      }
      setMessages(prev => [...prev, assistantMsg])

      // Update conversation title + insights + usage in sidebar
      loadConversations()
      loadInsights()
      loadUsage()
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Erreur de connexion: ${e}`, timestamp: new Date().toISOString() }])
    }
    setSending(false)
  }

  // Delete conversation
  const deleteConversation = async (id: string) => {
    try {
      await fetch(`${API}/chat/conversations/${id}`, { method: 'DELETE' })
      setConversations(prev => prev.filter(c => c.id !== id))
      if (activeConv?.id === id) {
        setActiveConv(null)
        setMessages([])
      }
    } catch (e) {
      console.error('Failed to delete:', e)
    }
  }

  // Auto scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Enter to send
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex h-[calc(100vh-3rem)] -m-6">
      {/* Sidebar */}
      {sidebarOpen && (
        <div className="w-72 bg-gray-900 border-r border-gray-800 flex flex-col">
          <div className="p-3 border-b border-gray-800">
            <button
              onClick={newConversation}
              className="w-full flex items-center gap-2 px-4 py-2.5 bg-green-600 hover:bg-green-500 text-white rounded-lg text-sm font-medium transition-colors"
            >
              <Plus className="w-4 h-4" /> Nouvelle conversation
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="p-4 text-center text-gray-500">Chargement...</div>
            ) : conversations.length === 0 ? (
              <div className="p-4 text-center text-gray-500 text-sm">Aucune conversation</div>
            ) : (
              conversations.map(conv => (
                <div
                  key={conv.id}
                  className={`flex items-center gap-2 px-3 py-2.5 cursor-pointer border-b border-gray-800/50 transition-colors group ${
                    activeConv?.id === conv.id ? 'bg-gray-800' : 'hover:bg-gray-800/50'
                  }`}
                  onClick={() => openConversation(conv)}
                >
                  <MessageSquare className="w-4 h-4 text-gray-500 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-white truncate">{conv.title}</div>
                    <div className="text-xs text-gray-500">
                      {new Date(conv.updated_at).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Paris' })}
                    </div>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteConversation(conv.id) }}
                    className="opacity-0 group-hover:opacity-100 p-1 text-gray-500 hover:text-red-400 transition-all"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Chat area */}
      <div className="flex-1 flex flex-col bg-gray-950">
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-3">
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-1 text-gray-400 hover:text-white">
            <ChevronLeft className={`w-5 h-5 transition-transform ${sidebarOpen ? '' : 'rotate-180'}`} />
          </button>
          <Bot className="w-5 h-5 text-green-400" />
          <div>
            <h1 className="text-sm font-semibold text-white">
              {activeConv ? activeConv.title : 'OpenClaw Chat'}
            </h1>
            <p className="text-xs text-gray-500">Assistant IA Trading</p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={() => { setShowUsage(!showUsage); if (!showUsage) loadUsage() }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors ${
                showUsage ? 'bg-blue-500/20 text-blue-400' : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              <Coins className="w-3.5 h-3.5" />
              {usage?.budget ? `$${usage.budget.remaining_usd.toFixed(2)} left` : '$0'}
            </button>
            <button
              onClick={() => { setShowInsights(!showInsights); if (!showInsights) loadInsights() }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors ${
                showInsights ? 'bg-yellow-500/20 text-yellow-400' : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              <Lightbulb className="w-3.5 h-3.5" />
              Insights ({insights.length})
            </button>
          </div>
        </div>

        {/* Token Usage panel */}
        {showUsage && usage && (
          <div className="px-4 py-3 border-b border-gray-800 bg-blue-500/5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-semibold text-blue-400 flex items-center gap-1">
                <Coins className="w-3.5 h-3.5" /> Budget OpenAI GPT-4o-mini
              </h3>
              <span className="text-[10px] text-gray-500">~$0.002/alerte</span>
            </div>

            {/* Budget bar */}
            {usage.budget && (
              <div className="mb-3">
                <div className="flex items-center justify-between mb-1">
                  <span className={`text-lg font-bold ${usage.budget.remaining_usd > 5 ? 'text-green-400' : usage.budget.remaining_usd > 1 ? 'text-yellow-400' : 'text-red-400'}`}>
                    ${usage.budget.remaining_usd.toFixed(2)} restant
                  </span>
                  <span className="text-xs text-gray-500">/ ${usage.budget.initial_usd.toFixed(0)} initial</span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full transition-all ${usage.budget.pct_used > 80 ? 'bg-red-500' : usage.budget.pct_used > 50 ? 'bg-yellow-500' : 'bg-green-500'}`}
                    style={{ width: `${Math.min(100, usage.budget.pct_used)}%` }}
                  />
                </div>
                <div className="flex justify-between text-[10px] text-gray-600 mt-1">
                  <span>Depense: ${usage.budget.spent_usd.toFixed(4)}</span>
                  <span>{usage.budget.pct_used.toFixed(1)}% utilise</span>
                </div>
              </div>
            )}

            <div className="grid grid-cols-3 gap-3">
              {[
                { label: "Aujourd'hui", data: usage.today, color: 'blue' },
                { label: "Ce mois", data: usage.this_month, color: 'green' },
                { label: "Total", data: usage.all_time, color: 'purple' },
              ].map(({ label, data, color }) => (
                <div key={label} className="bg-gray-800/50 rounded-lg p-2.5">
                  <div className="text-[10px] text-gray-500 mb-1">{label}</div>
                  <div className={`text-sm font-bold text-${color}-400`}>${data.cost_usd.toFixed(4)}</div>
                  <div className="text-[10px] text-gray-500 mt-1 space-y-0.5">
                    <div className="flex justify-between">
                      <span>Tokens</span>
                      <span className="font-mono">{((data.input_tokens + data.output_tokens) / 1000).toFixed(1)}K</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Requetes</span>
                      <span className="font-mono">{data.requests}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-2 flex items-center gap-2 text-[10px] text-gray-500">
              <Zap className="w-3 h-3" />
              <span>GPT-4o-mini: $0.15/M input, $0.60/M output | ~$0.002/alerte | Budget $25 = ~12,500 alertes</span>
            </div>
          </div>
        )}

        {/* Insights panel */}
        {showInsights && (
          <div className="px-4 py-3 border-b border-gray-800 bg-yellow-500/5 max-h-60 overflow-y-auto">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-semibold text-yellow-400 flex items-center gap-1">
                <Lightbulb className="w-3.5 h-3.5" /> Regles apprises ({insights.length})
              </h3>
              <span className="text-[10px] text-gray-500">Ces regles sont injectees dans chaque analyse</span>
            </div>
            {insights.length === 0 ? (
              <p className="text-xs text-gray-500">Aucun insight pour l'instant. Discutez de strategies et OpenClaw apprendra!</p>
            ) : (
              <div className="space-y-1.5">
                {insights.map(ins => (
                  <div key={ins.id} className="flex items-start gap-2 bg-gray-800/50 rounded-lg px-3 py-2">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded flex-shrink-0 mt-0.5 ${
                      ins.category === 'risk' ? 'bg-red-500/20 text-red-400' :
                      ins.category === 'filter' ? 'bg-blue-500/20 text-blue-400' :
                      ins.category === 'pattern' ? 'bg-purple-500/20 text-purple-400' :
                      ins.category === 'preference' ? 'bg-green-500/20 text-green-400' :
                      'bg-yellow-500/20 text-yellow-400'
                    }`}>{ins.category}</span>
                    <span className="text-xs text-gray-300 flex-1">{ins.insight}</span>
                    <span className="text-[10px] text-gray-600 flex-shrink-0">P{ins.priority}</span>
                    <button onClick={() => deleteInsight(ins.id)} className="text-gray-600 hover:text-red-400 flex-shrink-0">
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {!activeConv ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500 space-y-4">
              <Bot className="w-16 h-16 text-green-500/30" />
              <div className="text-center">
                <h2 className="text-xl font-bold text-white mb-2">OpenClaw</h2>
                <p className="text-sm max-w-md">
                  Discutez avec votre assistant IA trading. Analysez des trades,
                  explorez des strategies, et ameliorez les decisions ensemble.
                </p>
              </div>
              <button
                onClick={newConversation}
                className="px-6 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg text-sm transition-colors"
              >
                Commencer une discussion
              </button>
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500 space-y-3">
              <Bot className="w-12 h-12 text-green-500/20" />
              <p className="text-sm">Posez votre question...</p>
              <div className="flex flex-wrap gap-2 max-w-lg justify-center">
                {[
                  "Analyse BTCUSDT en detail",
                  "Quel est le contexte marche actuel?",
                  "Quels trades ont le mieux performe ce mois?",
                  "Comment ameliorer le win rate?",
                  "Montre moi le portfolio simulation",
                ].map(q => (
                  <button
                    key={q}
                    onClick={() => { setInput(q); inputRef.current?.focus() }}
                    className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs rounded-lg border border-gray-700 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg, i) => (
                <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                  {msg.role === 'assistant' && (
                    <div className="w-8 h-8 rounded-lg bg-green-600/20 flex items-center justify-center flex-shrink-0">
                      <Bot className="w-4 h-4 text-green-400" />
                    </div>
                  )}
                  <div className={`max-w-[75%] rounded-xl px-4 py-3 ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-800 text-gray-200'
                  }`}>
                    <div className="text-sm whitespace-pre-wrap break-words">{msg.content}</div>
                    <div className={`text-[10px] mt-1 ${msg.role === 'user' ? 'text-blue-200' : 'text-gray-500'}`}>
                      {new Date(msg.timestamp).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Paris' })}
                    </div>
                  </div>
                  {msg.role === 'user' && (
                    <div className="w-8 h-8 rounded-lg bg-blue-600/20 flex items-center justify-center flex-shrink-0">
                      <User className="w-4 h-4 text-blue-400" />
                    </div>
                  )}
                </div>
              ))}
              {sending && (
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-lg bg-green-600/20 flex items-center justify-center">
                    <Bot className="w-4 h-4 text-green-400" />
                  </div>
                  <div className="bg-gray-800 rounded-xl px-4 py-3 flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin text-green-400" />
                    <span className="text-sm text-gray-400">Analyse en cours...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input */}
        {activeConv && (
          <div className="p-4 border-t border-gray-800">
            <div className="flex gap-2 items-end">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Posez votre question a OpenClaw..."
                rows={1}
                className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-sm text-white placeholder-gray-500 focus:border-green-500 focus:outline-none resize-none"
                style={{ minHeight: '44px', maxHeight: '120px' }}
                onInput={(e) => {
                  const t = e.target as HTMLTextAreaElement
                  t.style.height = 'auto'
                  t.style.height = Math.min(t.scrollHeight, 120) + 'px'
                }}
              />
              <button
                onClick={sendMessage}
                disabled={!input.trim() || sending}
                className="p-3 bg-green-600 hover:bg-green-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-xl transition-colors"
              >
                {sending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
              </button>
            </div>
            <p className="text-xs text-gray-600 mt-2 text-center">
              OpenClaw utilise Claude + vos donnees MEGA BUY pour repondre. Enter pour envoyer, Shift+Enter pour nouvelle ligne.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
