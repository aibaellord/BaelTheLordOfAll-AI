import { useState, useEffect, useRef } from 'react'
import { useStore, TerminalSession } from '../store'
import {
  Plus,
  X,
  Maximize2,
  Minimize2,
  Terminal as TerminalIcon,
  Copy,
  Trash2,
  Split,
  Settings2
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import clsx from 'clsx'

// Terminal component using xterm.js
function TerminalPane({
  session,
  onClose,
  isActive,
  onClick
}: {
  session: TerminalSession
  onClose: () => void
  isActive: boolean
  onClick: () => void
}) {
  const terminalRef = useRef<HTMLDivElement>(null)
  const xtermRef = useRef<any>(null)
  const [output, setOutput] = useState<string[]>([
    `\x1b[32mBAEL Terminal v2.0.0\x1b[0m`,
    `Session: ${session.id}`,
    `Type 'help' for available commands.`,
    '',
    '$ '
  ])
  const [inputLine, setInputLine] = useState('')

  // Initialize xterm when available
  useEffect(() => {
    const initXterm = async () => {
      try {
        // Dynamic import for xterm
        const { Terminal } = await import('xterm')
        const { FitAddon } = await import('xterm-addon-fit')

        if (terminalRef.current && !xtermRef.current) {
          const term = new Terminal({
            theme: {
              background: '#0a0a0f',
              foreground: '#e0e0e0',
              cursor: '#6366f1',
              cursorAccent: '#0a0a0f',
              selection: '#6366f133',
              black: '#1e1e2e',
              red: '#f87171',
              green: '#4ade80',
              yellow: '#facc15',
              blue: '#60a5fa',
              magenta: '#c084fc',
              cyan: '#22d3ee',
              white: '#e0e0e0',
            },
            fontFamily: '"JetBrains Mono", "Fira Code", monospace',
            fontSize: 14,
            cursorBlink: true,
            cursorStyle: 'bar',
          })

          const fitAddon = new FitAddon()
          term.loadAddon(fitAddon)

          term.open(terminalRef.current)
          fitAddon.fit()

          // Write initial content
          term.writeln('\x1b[32mBAEL Terminal v2.0.0\x1b[0m')
          term.writeln(`Session: ${session.id}`)
          term.writeln("Type 'help' for available commands.")
          term.write('\r\n$ ')

          // Handle input
          let currentLine = ''
          term.onKey(({ key, domEvent }) => {
            if (domEvent.keyCode === 13) { // Enter
              term.write('\r\n')
              handleCommand(term, currentLine)
              currentLine = ''
              term.write('$ ')
            } else if (domEvent.keyCode === 8) { // Backspace
              if (currentLine.length > 0) {
                currentLine = currentLine.slice(0, -1)
                term.write('\b \b')
              }
            } else if (key.length === 1) {
              currentLine += key
              term.write(key)
            }
          })

          xtermRef.current = { term, fitAddon }

          // Handle resize
          const resizeObserver = new ResizeObserver(() => {
            fitAddon.fit()
          })
          resizeObserver.observe(terminalRef.current)

          return () => {
            resizeObserver.disconnect()
            term.dispose()
          }
        }
      } catch (error) {
        console.error('Failed to initialize xterm:', error)
      }
    }

    initXterm()
  }, [session.id])

  const handleCommand = async (term: any, command: string) => {
    const cmd = command.trim().toLowerCase()

    if (cmd === 'help') {
      term.writeln('Available commands:')
      term.writeln('  help     - Show this help')
      term.writeln('  clear    - Clear terminal')
      term.writeln('  status   - Show BAEL status')
      term.writeln('  council  - List council members')
      term.writeln('  tools    - List available tools')
      term.writeln('  exec     - Execute Python code')
    } else if (cmd === 'clear') {
      term.clear()
    } else if (cmd === 'status') {
      term.writeln('\x1b[32m● Connected\x1b[0m')
      term.writeln('Model: claude-3.5-sonnet')
      term.writeln('Memory: 42 working, 1,234 long-term')
      term.writeln('Tools: 156 registered')
    } else if (cmd === 'council') {
      term.writeln('Council Members:')
      term.writeln('  \x1b[34m◉\x1b[0m Sage - Strategic Advisor')
      term.writeln('  \x1b[31m◉\x1b[0m Guardian - Safety Monitor')
      term.writeln('  \x1b[33m◉\x1b[0m Innovator - Creative Solutions')
      term.writeln('  \x1b[32m◉\x1b[0m Analyst - Data & Logic')
    } else if (cmd === 'tools') {
      term.writeln('Available tool categories:')
      term.writeln('  • file_operations (12 tools)')
      term.writeln('  • code_execution (8 tools)')
      term.writeln('  • web_interaction (15 tools)')
      term.writeln('  • data_processing (23 tools)')
    } else if (cmd.startsWith('exec ')) {
      const code = command.slice(5)
      try {
        // Send to backend for execution
        const res = await fetch('/api/v1/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code, language: 'python' })
        })
        const result = await res.json()
        term.writeln(result.output || result.error || 'No output')
      } catch (e) {
        term.writeln(`\x1b[31mExecution error: ${e}\x1b[0m`)
      }
    } else if (cmd) {
      term.writeln(`Unknown command: ${cmd}`)
      term.writeln("Type 'help' for available commands.")
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className={clsx(
        'flex flex-col bg-bael-bg rounded-xl border overflow-hidden h-full',
        isActive ? 'border-bael-primary' : 'border-bael-border'
      )}
      onClick={onClick}
    >
      {/* Terminal Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-bael-surface border-b border-bael-border">
        <div className="flex items-center gap-2">
          <TerminalIcon size={14} className="text-bael-primary" />
          <span className="text-sm font-medium text-bael-text">{session.name}</span>
          <span className={clsx(
            'text-xs px-1.5 py-0.5 rounded',
            session.status === 'active' ? 'bg-bael-success/20 text-bael-success' : 'bg-bael-border text-bael-muted'
          )}>
            {session.status}
          </span>
        </div>

        <div className="flex items-center gap-1">
          <button
            className="p-1 hover:bg-bael-border rounded transition-colors text-bael-muted hover:text-bael-text"
            title="Copy"
          >
            <Copy size={14} />
          </button>
          <button
            className="p-1 hover:bg-bael-border rounded transition-colors text-bael-muted hover:text-bael-text"
            onClick={onClose}
            title="Close"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Terminal Content */}
      <div
        ref={terminalRef}
        className="flex-1 p-2"
        style={{ minHeight: '200px' }}
      />
    </motion.div>
  )
}

export function Terminals() {
  const { terminals, addTerminal, removeTerminal } = useStore()
  const [activeTerminal, setActiveTerminal] = useState<string | null>(null)
  const [layout, setLayout] = useState<'single' | 'split-h' | 'split-v' | 'grid'>('single')

  useEffect(() => {
    if (terminals.length > 0 && !activeTerminal) {
      setActiveTerminal(terminals[0].id)
    }
  }, [terminals, activeTerminal])

  const handleNewTerminal = () => {
    const newTerminal: TerminalSession = {
      id: `term-${Date.now()}`,
      name: `Terminal ${terminals.length + 1}`,
      status: 'active',
      createdAt: Date.now()
    }
    addTerminal(newTerminal)
    setActiveTerminal(newTerminal.id)
  }

  const handleCloseTerminal = (id: string) => {
    removeTerminal(id)
    if (activeTerminal === id) {
      const remaining = terminals.filter(t => t.id !== id)
      setActiveTerminal(remaining.length > 0 ? remaining[0].id : null)
    }
  }

  const getGridClass = () => {
    switch (layout) {
      case 'split-h':
        return 'grid-cols-2 grid-rows-1'
      case 'split-v':
        return 'grid-cols-1 grid-rows-2'
      case 'grid':
        return 'grid-cols-2 grid-rows-2'
      default:
        return 'grid-cols-1 grid-rows-1'
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-bael-border bg-bael-surface">
        <div className="flex items-center gap-2">
          <button
            onClick={handleNewTerminal}
            className="flex items-center gap-2 px-3 py-1.5 bg-bael-primary text-white rounded-lg hover:bg-bael-primary/80 transition-colors"
          >
            <Plus size={16} />
            <span className="text-sm">New Terminal</span>
          </button>

          {/* Terminal tabs */}
          <div className="flex items-center gap-1 ml-4">
            {terminals.map((term) => (
              <button
                key={term.id}
                onClick={() => setActiveTerminal(term.id)}
                className={clsx(
                  'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors',
                  activeTerminal === term.id
                    ? 'bg-bael-border text-bael-text'
                    : 'text-bael-muted hover:text-bael-text hover:bg-bael-border/50'
                )}
              >
                <TerminalIcon size={14} />
                {term.name}
              </button>
            ))}
          </div>
        </div>

        {/* Layout controls */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-bael-muted">Layout:</span>
          <div className="flex items-center gap-1 bg-bael-border rounded-lg p-1">
            <button
              onClick={() => setLayout('single')}
              className={clsx(
                'p-1.5 rounded transition-colors',
                layout === 'single' ? 'bg-bael-surface text-bael-text' : 'text-bael-muted hover:text-bael-text'
              )}
              title="Single"
            >
              <Maximize2 size={14} />
            </button>
            <button
              onClick={() => setLayout('split-h')}
              className={clsx(
                'p-1.5 rounded transition-colors',
                layout === 'split-h' ? 'bg-bael-surface text-bael-text' : 'text-bael-muted hover:text-bael-text'
              )}
              title="Split Horizontal"
            >
              <Split size={14} />
            </button>
            <button
              onClick={() => setLayout('split-v')}
              className={clsx(
                'p-1.5 rounded transition-colors rotate-90',
                layout === 'split-v' ? 'bg-bael-surface text-bael-text' : 'text-bael-muted hover:text-bael-text'
              )}
              title="Split Vertical"
            >
              <Split size={14} />
            </button>
            <button
              onClick={() => setLayout('grid')}
              className={clsx(
                'p-1.5 rounded transition-colors',
                layout === 'grid' ? 'bg-bael-surface text-bael-text' : 'text-bael-muted hover:text-bael-text'
              )}
              title="Grid"
            >
              <Settings2 size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Terminals Grid */}
      <div className={clsx('flex-1 p-4 grid gap-4', getGridClass())}>
        <AnimatePresence>
          {terminals.length === 0 ? (
            <EmptyState onNew={handleNewTerminal} />
          ) : layout === 'single' ? (
            // Single terminal mode - show only active
            terminals
              .filter(t => t.id === activeTerminal)
              .map((term) => (
                <TerminalPane
                  key={term.id}
                  session={term}
                  onClose={() => handleCloseTerminal(term.id)}
                  isActive={true}
                  onClick={() => setActiveTerminal(term.id)}
                />
              ))
          ) : (
            // Multi-terminal mode
            terminals.slice(0, layout === 'grid' ? 4 : 2).map((term) => (
              <TerminalPane
                key={term.id}
                session={term}
                onClose={() => handleCloseTerminal(term.id)}
                isActive={activeTerminal === term.id}
                onClick={() => setActiveTerminal(term.id)}
              />
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

function EmptyState({ onNew }: { onNew: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center justify-center h-full text-center"
    >
      <div className="w-16 h-16 rounded-full bg-bael-surface border border-bael-border flex items-center justify-center mb-4">
        <TerminalIcon size={32} className="text-bael-muted" />
      </div>

      <h2 className="text-xl font-semibold text-bael-text mb-2">No Terminals Open</h2>
      <p className="text-bael-muted mb-6 max-w-md">
        Open a terminal to execute commands, run scripts, and interact with BAEL's backend.
      </p>

      <button
        onClick={onNew}
        className="flex items-center gap-2 px-4 py-2 bg-bael-primary text-white rounded-lg hover:bg-bael-primary/80 transition-colors"
      >
        <Plus size={18} />
        <span>New Terminal</span>
      </button>
    </motion.div>
  )
}
