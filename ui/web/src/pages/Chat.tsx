import { useState, useRef, useEffect } from 'react'
import { useStore } from '../store'
import { useMutation } from '@tanstack/react-query'
import {
  Send,
  Paperclip,
  Mic,
  Settings2,
  Copy,
  RotateCcw,
  Loader2,
  Bot,
  User,
  Sparkles,
  Code,
  FileText,
  Image as ImageIcon
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import clsx from 'clsx'

interface MessageBubbleProps {
  message: {
    id: string
    role: 'user' | 'assistant' | 'system'
    content: string
    timestamp: number
    metadata?: Record<string, any>
  }
}

function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx(
        'flex gap-3',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      <div className={clsx(
        'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
        isUser ? 'bg-bael-primary' : 'bg-bael-secondary'
      )}>
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>

      <div className={clsx(
        'max-w-[70%] rounded-2xl px-4 py-3',
        isUser
          ? 'bg-bael-primary text-white rounded-tr-sm'
          : 'bg-bael-surface border border-bael-border text-bael-text rounded-tl-sm'
      )}>
        <div className="prose prose-invert prose-sm max-w-none">
          {message.content.split('\n').map((line, i) => (
            <p key={i} className={i > 0 ? 'mt-2' : ''}>{line || '\u00A0'}</p>
          ))}
        </div>

        {/* Actions */}
        <div className={clsx(
          'flex items-center gap-2 mt-2 pt-2 border-t',
          isUser ? 'border-white/20' : 'border-bael-border'
        )}>
          <span className="text-xs opacity-60">
            {new Date(message.timestamp).toLocaleTimeString()}
          </span>
          <div className="flex-1" />
          <button
            className="p-1 hover:bg-white/10 rounded transition-colors"
            onClick={() => navigator.clipboard.writeText(message.content)}
          >
            <Copy size={12} />
          </button>
        </div>
      </div>
    </motion.div>
  )
}

export function Chat() {
  const { messages, addMessage, settings, status } = useStore()
  const [input, setInput] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom
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

  // Send message mutation
  const sendMessage = useMutation({
    mutationFn: async (content: string) => {
      const res = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: content,
          context: messages.slice(-10),
          settings: {
            model: settings.llm.model,
            temperature: settings.llm.temperature,
            maxTokens: settings.llm.maxTokens,
          }
        })
      })
      return res.json()
    },
    onMutate: (content) => {
      // Add user message immediately
      addMessage({
        id: `user-${Date.now()}`,
        role: 'user',
        content,
        timestamp: Date.now()
      })
      setIsThinking(true)
    },
    onSuccess: (data) => {
      // Add assistant response
      addMessage({
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: data.response || data.message || 'I apologize, but I encountered an issue processing your request.',
        timestamp: Date.now(),
        metadata: data.metadata
      })
      setIsThinking(false)
    },
    onError: (error) => {
      addMessage({
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: `Error: ${error.message}. Please check your API configuration.`,
        timestamp: Date.now()
      })
      setIsThinking(false)
    }
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || sendMessage.isPending) return

    sendMessage.mutate(input.trim())
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Chat Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-bael-border bg-bael-surface">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-bael-primary to-bael-secondary flex items-center justify-center">
            <Sparkles size={20} className="text-white" />
          </div>
          <div>
            <h2 className="font-semibold text-bael-text">BAEL Assistant</h2>
            <p className="text-xs text-bael-muted">
              {status.activeModel || 'No model selected'} • {status.connected ? 'Connected' : 'Disconnected'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button className="p-2 hover:bg-bael-border rounded-lg transition-colors text-bael-muted hover:text-bael-text">
            <RotateCcw size={18} />
          </button>
          <button className="p-2 hover:bg-bael-border rounded-lg transition-colors text-bael-muted hover:text-bael-text">
            <Settings2 size={18} />
          </button>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            <AnimatePresence>
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
            </AnimatePresence>

            {/* Thinking indicator */}
            {isThinking && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex gap-3"
              >
                <div className="w-8 h-8 rounded-full bg-bael-secondary flex items-center justify-center">
                  <Bot size={16} />
                </div>
                <div className="bg-bael-surface border border-bael-border rounded-2xl rounded-tl-sm px-4 py-3">
                  <div className="flex items-center gap-2 text-bael-muted">
                    <Loader2 size={14} className="animate-spin" />
                    <span className="text-sm">Thinking...</span>
                  </div>
                </div>
              </motion.div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-bael-border bg-bael-surface">
        <form onSubmit={handleSubmit} className="flex items-end gap-4">
          {/* Attachment buttons */}
          <div className="flex items-center gap-1">
            <button
              type="button"
              className="p-2 hover:bg-bael-border rounded-lg transition-colors text-bael-muted hover:text-bael-text"
            >
              <Paperclip size={18} />
            </button>
            <button
              type="button"
              className="p-2 hover:bg-bael-border rounded-lg transition-colors text-bael-muted hover:text-bael-text"
            >
              <Mic size={18} />
            </button>
          </div>

          {/* Text input */}
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message..."
              rows={1}
              className="w-full px-4 py-3 bg-bael-bg border border-bael-border rounded-xl text-bael-text placeholder-bael-muted resize-none focus:outline-none focus:border-bael-primary transition-colors"
            />
          </div>

          {/* Send button */}
          <button
            type="submit"
            disabled={!input.trim() || sendMessage.isPending}
            className={clsx(
              'p-3 rounded-xl transition-all',
              input.trim() && !sendMessage.isPending
                ? 'bg-bael-primary text-white hover:bg-bael-primary/80'
                : 'bg-bael-border text-bael-muted cursor-not-allowed'
            )}
          >
            {sendMessage.isPending ? (
              <Loader2 size={18} className="animate-spin" />
            ) : (
              <Send size={18} />
            )}
          </button>
        </form>

        <p className="text-xs text-bael-muted mt-2 text-center">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}

function EmptyState() {
  const suggestions = [
    { icon: Code, text: "Help me write Python code", category: "Code" },
    { icon: FileText, text: "Explain how BAEL works", category: "Learn" },
    { icon: Sparkles, text: "Start a council deliberation", category: "Council" },
    { icon: ImageIcon, text: "Analyze my project structure", category: "Analysis" },
  ]

  return (
    <div className="flex flex-col items-center justify-center h-full text-center">
      <div className="w-20 h-20 rounded-full bg-gradient-to-br from-bael-primary to-bael-secondary flex items-center justify-center mb-6">
        <Sparkles size={40} className="text-white" />
      </div>

      <h2 className="text-2xl font-bold text-bael-text mb-2">
        Welcome to BAEL
      </h2>
      <p className="text-bael-muted mb-8 max-w-md">
        Your autonomous AI agent with multi-persona councils, advanced memory, and
        self-organizing capabilities.
      </p>

      <div className="grid grid-cols-2 gap-3 max-w-lg">
        {suggestions.map(({ icon: Icon, text, category }) => (
          <button
            key={text}
            className="flex items-start gap-3 p-4 bg-bael-surface border border-bael-border rounded-xl hover:border-bael-primary/50 transition-all text-left group"
          >
            <div className="p-2 rounded-lg bg-bael-primary/10 text-bael-primary group-hover:bg-bael-primary group-hover:text-white transition-all">
              <Icon size={16} />
            </div>
            <div>
              <p className="text-xs text-bael-muted">{category}</p>
              <p className="text-sm text-bael-text">{text}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
