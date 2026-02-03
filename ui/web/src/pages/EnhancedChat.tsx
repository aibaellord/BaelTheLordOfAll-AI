import { useState, useRef, useEffect, useCallback } from 'react'
import { useStore } from '../store'
import { showToast } from '../hooks/useToast'
import {
  Send,
  Paperclip,
  Mic,
  MicOff,
  Settings2,
  Copy,
  Check,
  RotateCcw,
  Loader2,
  Bot,
  User,
  Sparkles,
  Code,
  FileText,
  Image as ImageIcon,
  X,
  Download,
  Trash2,
  ChevronDown,
  MessageSquare,
  Plus,
  History,
  Star,
  Share2,
  MoreHorizontal,
  Zap,
  Brain,
  Crown,
  AlertTriangle,
  Key
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import clsx from 'clsx'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'

// Types
interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  persona?: string
  attachments?: Attachment[]
  metadata?: {
    model?: string
    tokens?: number
    reasoning?: string
    capabilities?: string[]
  }
  isStreaming?: boolean
}

interface Attachment {
  id: string
  name: string
  type: 'file' | 'image' | 'code'
  size: number
  content?: string
  url?: string
}

interface Conversation {
  id: string
  title: string
  messages: Message[]
  createdAt: number
  updatedAt: number
  starred?: boolean
}

// IndexedDB for persistence
const DB_NAME = 'bael-chat'
const DB_VERSION = 1
const STORE_NAME = 'conversations'

const openDB = (): Promise<IDBDatabase> => {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)
    request.onerror = () => reject(request.error)
    request.onsuccess = () => resolve(request.result)
    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id' })
      }
    }
  })
}

const saveConversation = async (conversation: Conversation) => {
  const db = await openDB()
  const tx = db.transaction(STORE_NAME, 'readwrite')
  tx.objectStore(STORE_NAME).put(conversation)
  return new Promise((resolve) => { tx.oncomplete = resolve })
}

const loadConversations = async (): Promise<Conversation[]> => {
  const db = await openDB()
  const tx = db.transaction(STORE_NAME, 'readonly')
  const request = tx.objectStore(STORE_NAME).getAll()
  return new Promise((resolve) => {
    request.onsuccess = () => resolve(request.result || [])
  })
}

const deleteConversation = async (id: string) => {
  const db = await openDB()
  const tx = db.transaction(STORE_NAME, 'readwrite')
  tx.objectStore(STORE_NAME).delete(id)
}

// Markdown components
const MarkdownComponents = {
  code({ node, inline, className, children, ...props }: any) {
    const match = /language-(\w+)/.exec(className || '')
    const [copied, setCopied] = useState(false)

    const handleCopy = () => {
      navigator.clipboard.writeText(String(children))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }

    return !inline && match ? (
      <div className="relative group">
        <button
          onClick={handleCopy}
          className="absolute right-2 top-2 p-1.5 rounded bg-bael-border/50 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
        </button>
        <SyntaxHighlighter
          style={oneDark}
          language={match[1]}
          PreTag="div"
          className="rounded-lg !bg-bael-bg !mt-2 !mb-2"
          {...props}
        >
          {String(children).replace(/\n$/, '')}
        </SyntaxHighlighter>
      </div>
    ) : (
      <code className="bg-bael-border px-1.5 py-0.5 rounded text-sm" {...props}>
        {children}
      </code>
    )
  }
}

// Message Bubble Component
function MessageBubble({
  message,
  onCopy,
  onRegenerate
}: {
  message: Message
  onCopy: () => void
  onRegenerate?: () => void
}) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)
  const [showActions, setShowActions] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
    onCopy()
  }

  // Persona icons
  const getPersonaIcon = () => {
    switch (message.persona) {
      case 'supreme': return <Crown size={16} className="text-amber-400" />
      case 'architect': return <Code size={16} className="text-blue-400" />
      case 'researcher': return <Brain size={16} className="text-purple-400" />
      default: return <Bot size={16} />
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx(
        'group flex gap-3',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* Avatar */}
      <div className={clsx(
        'w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg',
        isUser
          ? 'bg-gradient-to-br from-bael-primary to-bael-secondary'
          : 'bg-gradient-to-br from-amber-500 to-orange-600'
      )}>
        {isUser ? <User size={16} className="text-white" /> : getPersonaIcon()}
      </div>

      {/* Message Content */}
      <div className={clsx(
        'max-w-[75%] rounded-2xl px-4 py-3 shadow-lg',
        isUser
          ? 'bg-gradient-to-br from-bael-primary to-bael-secondary text-white rounded-tr-sm'
          : 'bg-bael-surface border border-bael-border text-bael-text rounded-tl-sm'
      )}>
        {/* Attachments */}
        {message.attachments && message.attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {message.attachments.map((att) => (
              <div key={att.id} className="flex items-center gap-2 bg-bael-bg/50 rounded-lg px-3 py-2">
                {att.type === 'image' ? <ImageIcon size={14} /> : <FileText size={14} />}
                <span className="text-xs">{att.name}</span>
                <span className="text-xs text-bael-muted">({(att.size / 1024).toFixed(1)}KB)</span>
              </div>
            ))}
          </div>
        )}

        {/* Content with Markdown */}
        <div className="prose prose-invert prose-sm max-w-none">
          {message.isStreaming ? (
            <span>{message.content}<span className="animate-pulse">▊</span></span>
          ) : (
            <ReactMarkdown components={MarkdownComponents}>
              {message.content}
            </ReactMarkdown>
          )}
        </div>

        {/* Metadata */}
        {message.metadata?.capabilities && message.metadata.capabilities.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {message.metadata.capabilities.map((cap, i) => (
              <span key={i} className="text-xs bg-bael-primary/20 text-bael-primary px-2 py-0.5 rounded">
                {cap}
              </span>
            ))}
          </div>
        )}

        {/* Footer */}
        <div className={clsx(
          'flex items-center gap-2 mt-2 pt-2 border-t text-xs',
          isUser ? 'border-white/20 text-white/60' : 'border-bael-border text-bael-muted'
        )}>
          <span>{new Date(message.timestamp).toLocaleTimeString()}</span>
          {message.metadata?.model && (
            <span className="opacity-60">• {message.metadata.model}</span>
          )}
          {message.metadata?.tokens && (
            <span className="opacity-60">• {message.metadata.tokens} tokens</span>
          )}

          {/* Actions */}
          <div className="flex-1" />
          <AnimatePresence>
            {showActions && (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="flex items-center gap-1"
              >
                <button
                  onClick={handleCopy}
                  className="p-1 hover:bg-white/10 rounded transition-colors"
                  title="Copy message"
                >
                  {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
                </button>
                {!isUser && onRegenerate && (
                  <button
                    onClick={onRegenerate}
                    className="p-1 hover:bg-white/10 rounded transition-colors"
                    title="Regenerate"
                  >
                    <RotateCcw size={12} />
                  </button>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  )
}

// Thinking Indicator
function ThinkingIndicator({ persona }: { persona?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex items-center gap-3"
    >
      <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg">
        <Loader2 size={16} className="animate-spin text-white" />
      </div>
      <div className="bg-bael-surface border border-bael-border rounded-2xl rounded-tl-sm px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            <span className="w-2 h-2 bg-bael-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-2 h-2 bg-bael-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-2 h-2 bg-bael-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
          <span className="text-sm text-bael-muted ml-2">
            {persona ? `${persona} is thinking...` : 'BAEL is thinking...'}
          </span>
        </div>
      </div>
    </motion.div>
  )
}

// Empty State
function EmptyState({ onQuickStart }: { onQuickStart: (prompt: string) => void }) {
  const suggestions = [
    { icon: Code, text: "Write a Python script to analyze data", category: "Code" },
    { icon: Brain, text: "Explain quantum computing simply", category: "Learn" },
    { icon: Zap, text: "Create a workflow for automated testing", category: "Automate" },
    { icon: Sparkles, text: "Generate creative ideas for my project", category: "Create" },
  ]

  return (
    <div className="flex flex-col items-center justify-center h-full p-8">
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="text-center mb-8"
      >
        <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-amber-500/20 to-orange-600/20 flex items-center justify-center">
          <Crown size={40} className="text-amber-400" />
        </div>
        <h2 className="text-2xl font-bold text-bael-text mb-2">Welcome to BAEL</h2>
        <p className="text-bael-muted">The Lord of All AI Agents awaits your command</p>
      </motion.div>

      <div className="grid grid-cols-2 gap-3 max-w-lg w-full">
        {suggestions.map((suggestion, i) => (
          <motion.button
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            onClick={() => onQuickStart(suggestion.text)}
            className="flex items-start gap-3 p-4 bg-bael-surface border border-bael-border rounded-xl hover:border-bael-primary/50 transition-all text-left group"
          >
            <div className="p-2 rounded-lg bg-bael-primary/10 text-bael-primary group-hover:bg-bael-primary/20 transition-colors">
              <suggestion.icon size={18} />
            </div>
            <div>
              <p className="text-xs text-bael-muted mb-1">{suggestion.category}</p>
              <p className="text-sm text-bael-text">{suggestion.text}</p>
            </div>
          </motion.button>
        ))}
      </div>
    </div>
  )
}

// Conversation Sidebar
function ConversationSidebar({
  conversations,
  currentId,
  onSelect,
  onNew,
  onDelete,
  isOpen,
  onClose
}: {
  conversations: Conversation[]
  currentId: string | null
  onSelect: (id: string) => void
  onNew: () => void
  onDelete: (id: string) => void
  isOpen: boolean
  onClose: () => void
}) {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ x: -280, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: -280, opacity: 0 }}
          className="absolute left-0 top-0 bottom-0 w-72 bg-bael-surface border-r border-bael-border z-20 flex flex-col"
        >
          <div className="p-4 border-b border-bael-border flex items-center justify-between">
            <h3 className="font-semibold text-bael-text flex items-center gap-2">
              <History size={18} /> Chat History
            </h3>
            <button onClick={onClose} className="p-1 hover:bg-bael-border rounded">
              <X size={18} />
            </button>
          </div>

          <button
            onClick={onNew}
            className="m-4 flex items-center justify-center gap-2 py-2.5 bg-bael-primary/20 text-bael-primary rounded-lg hover:bg-bael-primary/30 transition-colors"
          >
            <Plus size={18} /> New Conversation
          </button>

          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {conversations.length === 0 ? (
              <p className="text-center text-bael-muted text-sm py-8">No conversations yet</p>
            ) : (
              conversations
                .sort((a, b) => b.updatedAt - a.updatedAt)
                .map((conv) => (
                  <div
                    key={conv.id}
                    className={clsx(
                      'group flex items-center gap-2 p-3 rounded-lg cursor-pointer transition-colors',
                      currentId === conv.id
                        ? 'bg-bael-primary/20 text-bael-primary'
                        : 'hover:bg-bael-border/50 text-bael-text'
                    )}
                    onClick={() => onSelect(conv.id)}
                  >
                    {conv.starred ? (
                      <Star size={14} className="text-amber-400 fill-amber-400" />
                    ) : (
                      <MessageSquare size={14} className="text-bael-muted" />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm truncate">{conv.title}</p>
                      <p className="text-xs text-bael-muted">
                        {new Date(conv.updatedAt).toLocaleDateString()}
                      </p>
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); onDelete(conv.id) }}
                      className="p-1 opacity-0 group-hover:opacity-100 hover:bg-bael-error/20 rounded transition-all"
                    >
                      <Trash2 size={12} className="text-bael-error" />
                    </button>
                  </div>
                ))
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

// Main Chat Component
export function EnhancedChat() {
  const { status, settings } = useStore()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [currentConvId, setCurrentConvId] = useState<string | null>(null)
  const [showHistory, setShowHistory] = useState(false)
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null)
  const [apiKeyStatus, setApiKeyStatus] = useState<'checking' | 'configured' | 'missing'>('checking')

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Check API key configuration
  useEffect(() => {
    const checkApiKeys = async () => {
      try {
        const res = await fetch('/api/v1/settings/keys')
        if (res.ok) {
          const data = await res.json()
          const hasConfigured = data.keys?.some((k: any) => k.configured)
          setApiKeyStatus(hasConfigured ? 'configured' : 'missing')
        } else {
          // Check localStorage fallback
          const cached = localStorage.getItem('bael_secrets_status')
          if (cached) {
            const parsed = JSON.parse(cached)
            setApiKeyStatus(Object.values(parsed).some(Boolean) ? 'configured' : 'missing')
          } else {
            setApiKeyStatus('missing')
          }
        }
      } catch {
        setApiKeyStatus('missing')
      }
    }
    checkApiKeys()
  }, [])

  // Load conversations on mount
  useEffect(() => {
    loadConversations().then(setConversations)
  }, [])

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 200)}px`
    }
  }, [input])

  // Save conversation when messages change
  useEffect(() => {
    if (messages.length > 0 && currentConvId) {
      const conv: Conversation = {
        id: currentConvId,
        title: messages[0]?.content.slice(0, 50) || 'New Conversation',
        messages,
        createdAt: conversations.find(c => c.id === currentConvId)?.createdAt || Date.now(),
        updatedAt: Date.now()
      }
      saveConversation(conv)
      setConversations(prev => {
        const existing = prev.findIndex(c => c.id === currentConvId)
        if (existing >= 0) {
          const updated = [...prev]
          updated[existing] = conv
          return updated
        }
        return [...prev, conv]
      })
    }
  }, [messages, currentConvId])

  // Send message with streaming
  const sendMessage = async (content: string) => {
    if (!content.trim()) return

    // Create conversation if needed
    if (!currentConvId) {
      setCurrentConvId(`conv-${Date.now()}`)
    }

    // Add user message
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: content.trim(),
      timestamp: Date.now(),
      attachments: attachments.length > 0 ? [...attachments] : undefined
    }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setAttachments([])
    setIsThinking(true)

    try {
      // Use SSE streaming endpoint
      const response = await fetch('/api/v1/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: content,
          context: messages.slice(-10),
          persona: selectedPersona,
          attachments: attachments.map(a => ({ name: a.name, content: a.content })),
          settings: {
            model: settings.llm.model,
            temperature: settings.llm.temperature,
            maxTokens: settings.llm.maxTokens,
          }
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      // Check if it's a streaming response
      const contentType = response.headers.get('content-type')

      if (contentType?.includes('text/event-stream')) {
        // Handle SSE streaming
        setIsThinking(false)
        setIsStreaming(true)

        const reader = response.body?.getReader()
        const decoder = new TextDecoder()

        const assistantMessage: Message = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: '',
          timestamp: Date.now(),
          persona: selectedPersona || undefined,
          isStreaming: true
        }
        setMessages(prev => [...prev, assistantMessage])

        while (reader) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                if (data.content) {
                  setMessages(prev => {
                    const updated = [...prev]
                    const lastMsg = updated[updated.length - 1]
                    if (lastMsg && lastMsg.role === 'assistant') {
                      lastMsg.content += data.content
                    }
                    return updated
                  })
                }
                if (data.done) {
                  setMessages(prev => {
                    const updated = [...prev]
                    const lastMsg = updated[updated.length - 1]
                    if (lastMsg) {
                      lastMsg.isStreaming = false
                      lastMsg.metadata = data.metadata
                    }
                    return updated
                  })
                }
              } catch (e) {
                // Skip invalid JSON
              }
            }
          }
        }
        setIsStreaming(false)
      } else {
        // Handle regular JSON response
        const data = await response.json()
        setIsThinking(false)

        const assistantMessage: Message = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: data.response || data.message || 'I apologize, but I encountered an issue.',
          timestamp: Date.now(),
          persona: selectedPersona || undefined,
          metadata: data.metadata
        }
        setMessages(prev => [...prev, assistantMessage])
      }
    } catch (error: any) {
      setIsThinking(false)
      setIsStreaming(false)

      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: `Error: ${error.message}. Please check your API configuration.`,
        timestamp: Date.now()
      }
      setMessages(prev => [...prev, errorMessage])
    }
  }

  // Handle file upload
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files) return

    Array.from(files).forEach(file => {
      const reader = new FileReader()
      reader.onload = (e) => {
        const content = e.target?.result as string
        const attachment: Attachment = {
          id: `att-${Date.now()}-${Math.random()}`,
          name: file.name,
          type: file.type.startsWith('image/') ? 'image' : 'file',
          size: file.size,
          content
        }
        setAttachments(prev => [...prev, attachment])
      }
      reader.readAsText(file)
    })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    sendMessage(input)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const startNewConversation = () => {
    setMessages([])
    setCurrentConvId(null)
    setShowHistory(false)
  }

  const selectConversation = (id: string) => {
    const conv = conversations.find(c => c.id === id)
    if (conv) {
      setMessages(conv.messages)
      setCurrentConvId(id)
      setShowHistory(false)
    }
  }

  const handleDeleteConversation = async (id: string) => {
    await deleteConversation(id)
    setConversations(prev => prev.filter(c => c.id !== id))
    if (currentConvId === id) {
      startNewConversation()
    }
  }

  const regenerateLastResponse = () => {
    if (messages.length < 2) return
    const lastUserMsg = [...messages].reverse().find(m => m.role === 'user')
    if (lastUserMsg) {
      setMessages(prev => prev.slice(0, -1))
      sendMessage(lastUserMsg.content)
    }
  }

  return (
    <div className="relative flex flex-col h-full bg-bael-bg">
      {/* API Key Warning Banner */}
      {apiKeyStatus === 'missing' && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          className="bg-yellow-500/10 border-b border-yellow-500/30 px-4 py-3"
        >
          <div className="flex items-center justify-between max-w-4xl mx-auto">
            <div className="flex items-center gap-3">
              <div className="p-1.5 bg-yellow-500/20 rounded-lg">
                <Key size={16} className="text-yellow-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-yellow-400">No API keys configured</p>
                <p className="text-xs text-yellow-400/70">Configure at least one LLM provider to start chatting</p>
              </div>
            </div>
            <a
              href="/settings"
              className="px-3 py-1.5 bg-yellow-500/20 text-yellow-400 text-sm rounded-lg hover:bg-yellow-500/30 transition-colors"
            >
              Configure API Keys
            </a>
          </div>
        </motion.div>
      )}

      {/* Conversation Sidebar */}
      <ConversationSidebar
        conversations={conversations}
        currentId={currentConvId}
        onSelect={selectConversation}
        onNew={startNewConversation}
        onDelete={handleDeleteConversation}
        isOpen={showHistory}
        onClose={() => setShowHistory(false)}
      />

      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-bael-border bg-bael-surface/80 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="p-2 hover:bg-bael-border rounded-lg transition-colors"
            title="View chat history"
          >
            <History size={20} className="text-bael-muted" />
          </button>

          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg">
            <Crown size={20} className="text-white" />
          </div>
          <div>
            <h2 className="font-semibold text-bael-text">BAEL Assistant</h2>
            <p className="text-xs text-bael-muted">
              {status.activeModel || 'Claude 3.5 Sonnet'} • {status.connected ? 'Connected' : 'Connecting...'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Persona Selector */}
          <select
            value={selectedPersona || ''}
            onChange={(e) => setSelectedPersona(e.target.value || null)}
            className="bg-bael-border text-bael-text text-sm rounded-lg px-3 py-1.5 border-none outline-none"
          >
            <option value="">Default</option>
            <option value="supreme">🔥 Supreme</option>
            <option value="architect">🏗️ Architect</option>
            <option value="researcher">🔬 Researcher</option>
            <option value="creative">🎨 Creative</option>
          </select>

          <button
            onClick={startNewConversation}
            className="p-2 hover:bg-bael-border rounded-lg transition-colors text-bael-muted hover:text-bael-text"
            title="New conversation"
          >
            <Plus size={18} />
          </button>
          <button className="p-2 hover:bg-bael-border rounded-lg transition-colors text-bael-muted hover:text-bael-text">
            <Settings2 size={18} />
          </button>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <EmptyState onQuickStart={sendMessage} />
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                onCopy={() => {}}
                onRegenerate={message.role === 'assistant' ? regenerateLastResponse : undefined}
              />
            ))}

            <AnimatePresence>
              {isThinking && <ThinkingIndicator persona={selectedPersona || undefined} />}
            </AnimatePresence>

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Attachments Preview */}
      <AnimatePresence>
        {attachments.length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="px-6 py-3 border-t border-bael-border bg-bael-surface/50"
          >
            <div className="flex flex-wrap gap-2">
              {attachments.map((att) => (
                <div key={att.id} className="flex items-center gap-2 bg-bael-bg rounded-lg px-3 py-2 border border-bael-border">
                  {att.type === 'image' ? <ImageIcon size={14} /> : <FileText size={14} />}
                  <span className="text-sm">{att.name}</span>
                  <button
                    onClick={() => setAttachments(prev => prev.filter(a => a.id !== att.id))}
                    className="p-0.5 hover:bg-bael-error/20 rounded"
                  >
                    <X size={12} className="text-bael-error" />
                  </button>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input Area */}
      <div className="px-6 py-4 border-t border-bael-border bg-bael-surface/80 backdrop-blur-sm">
        <form onSubmit={handleSubmit} className="flex items-end gap-3">
          {/* File Upload */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileUpload}
            className="hidden"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="p-2.5 hover:bg-bael-border rounded-xl transition-colors text-bael-muted hover:text-bael-text"
          >
            <Paperclip size={20} />
          </button>

          {/* Text Input */}
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask BAEL anything..."
              rows={1}
              className="w-full bg-bael-bg border border-bael-border rounded-xl px-4 py-3 pr-12 text-bael-text placeholder:text-bael-muted resize-none focus:outline-none focus:border-bael-primary/50 transition-colors"
            />
            <div className="absolute right-3 bottom-3 text-xs text-bael-muted">
              {input.length > 0 && `${input.length}`}
            </div>
          </div>

          {/* Send Button */}
          <button
            type="submit"
            disabled={!input.trim() || isThinking || isStreaming}
            className={clsx(
              'p-3 rounded-xl transition-all',
              input.trim() && !isThinking && !isStreaming
                ? 'bg-gradient-to-br from-bael-primary to-bael-secondary text-white shadow-lg hover:shadow-bael-primary/20'
                : 'bg-bael-border text-bael-muted cursor-not-allowed'
            )}
          >
            {isThinking || isStreaming ? (
              <Loader2 size={20} className="animate-spin" />
            ) : (
              <Send size={20} />
            )}
          </button>
        </form>

        <p className="text-xs text-bael-muted mt-2 text-center">
          Press Enter to send, Shift+Enter for new line • {conversations.length} conversation{conversations.length !== 1 ? 's' : ''} saved
        </p>
      </div>
    </div>
  )
}

export { EnhancedChat as Chat }
