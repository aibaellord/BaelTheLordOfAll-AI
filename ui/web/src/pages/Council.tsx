import { useState, useEffect, useRef, useCallback } from 'react'
import { useStore, CouncilMember } from '../store'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Users,
  Play,
  Pause,
  RotateCcw,
  MessageCircle,
  ThumbsUp,
  ThumbsDown,
  AlertTriangle,
  CheckCircle,
  Loader2,
  Settings2,
  PlusCircle,
  ChevronRight,
  Sparkles,
  Wifi,
  WifiOff,
  Brain,
  Zap
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import clsx from 'clsx'

interface DeliberationMessage {
  id: string
  memberId: string
  memberName: string
  memberColor: string
  content: string
  type: 'opinion' | 'question' | 'vote' | 'consensus' | 'challenge' | 'synthesis'
  phase?: string
  vote?: 'approve' | 'reject' | 'abstain'
  timestamp: number
}

interface Deliberation {
  id: string
  topic: string
  status: 'pending' | 'active' | 'concluded'
  phase?: string
  messages: DeliberationMessage[]
  outcome?: {
    decision: string
    votes: { approve: number; reject: number; abstain: number }
    confidence: number
    rationale?: string
  }
}

interface APICouncilMember {
  id: string
  name: string
  role: string
  color: string
  description: string
  active: boolean
  specialties: string[]
}

const MEMBER_COLORS: Record<string, string> = {
  'Sage': '#9333EA',
  'Guardian': '#3B82F6',
  'Innovator': '#10B981',
  'Analyst': '#F59E0B',
  'Executor': '#EF4444',
  'Diplomat': '#EC4899',
  "Devil's Advocate": '#6B7280'
}

export function Council() {
  const { councilMembers: storeMembers, updateCouncilMember } = useStore()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'members' | 'deliberation' | 'history'>('members')
  const [deliberation, setDeliberation] = useState<Deliberation | null>(null)
  const [topic, setTopic] = useState('')
  const [isDeliberating, setIsDeliberating] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [currentPhase, setCurrentPhase] = useState<string>('')
  const wsRef = useRef<WebSocket | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Fetch council members from API
  const { data: apiMembers, isLoading: loadingMembers } = useQuery({
    queryKey: ['council-members'],
    queryFn: async () => {
      const res = await fetch('/api/v1/council/members')
      if (!res.ok) throw new Error('Failed to fetch council members')
      return res.json() as Promise<APICouncilMember[]>
    },
    staleTime: 30000,
    refetchOnWindowFocus: false
  })

  // Use API members if available, otherwise fall back to store members
  const councilMembers: CouncilMember[] = (apiMembers || storeMembers).map(m => ({
    ...m,
    color: m.color || MEMBER_COLORS[m.name] || '#9333EA',
    active: m.active ?? true
  }))

  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [deliberation?.messages])

  // WebSocket connection for real-time streaming
  const connectWebSocket = useCallback((sessionId: string) => {
    const wsUrl = `ws://localhost:8000/api/v1/council/stream/${sessionId}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('🔌 Council WebSocket connected')
      setIsStreaming(true)
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      console.log('📨 Council WS message:', data)

      if (data.type === 'phase') {
        setCurrentPhase(data.phase)
      } else if (data.type === 'opinion' || data.type === 'challenge' || data.type === 'synthesis') {
        const msg: DeliberationMessage = {
          id: `msg-${Date.now()}-${data.member_id}`,
          memberId: data.member_id,
          memberName: data.member_name,
          memberColor: MEMBER_COLORS[data.member_name] || '#9333EA',
          content: data.content,
          type: data.type as any,
          phase: data.phase,
          timestamp: Date.now()
        }
        setDeliberation(prev => prev ? { ...prev, messages: [...prev.messages, msg] } : null)
      } else if (data.type === 'vote') {
        const msg: DeliberationMessage = {
          id: `vote-${Date.now()}-${data.member_id}`,
          memberId: data.member_id,
          memberName: data.member_name,
          memberColor: MEMBER_COLORS[data.member_name] || '#9333EA',
          content: data.reasoning || `Voted: ${data.vote}`,
          type: 'vote',
          vote: data.vote as 'approve' | 'reject' | 'abstain',
          timestamp: Date.now()
        }
        setDeliberation(prev => prev ? { ...prev, messages: [...prev.messages, msg] } : null)
      } else if (data.type === 'decision') {
        setDeliberation(prev => prev ? {
          ...prev,
          status: 'concluded',
          outcome: {
            decision: data.decision,
            votes: data.votes || { approve: 0, reject: 0, abstain: 0 },
            confidence: data.confidence || 85,
            rationale: data.rationale
          }
        } : null)
        setIsDeliberating(false)
        setIsStreaming(false)
      } else if (data.type === 'error') {
        console.error('Council error:', data.message)
        setIsDeliberating(false)
        setIsStreaming(false)
      }
    }

    ws.onerror = (error) => {
      console.error('Council WebSocket error:', error)
      setIsStreaming(false)
    }

    ws.onclose = () => {
      console.log('🔌 Council WebSocket closed')
      setIsStreaming(false)
    }

    return ws
  }, [])

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  // Start deliberation with real API
  const startDeliberation = useMutation({
    mutationFn: async (topic: string) => {
      // First create a session
      const sessionRes = await fetch('/api/v1/council/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic,
          council_type: 'strategic',
          members: councilMembers.filter(m => m.active).map(m => m.id)
        })
      })

      if (!sessionRes.ok) {
        throw new Error('Failed to create council session')
      }

      const session = await sessionRes.json()

      // Then start deliberation
      const deliberateRes = await fetch('/api/v1/council/deliberate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic,
          session_id: session.session_id,
          members: councilMembers.filter(m => m.active).map(m => ({
            id: m.id,
            name: m.name,
            role: m.role || 'advisor'
          })),
          enable_challenges: true,
          voting_method: 'weighted'
        })
      })

      if (!deliberateRes.ok) {
        // Fall back to simulation if API fails
        console.warn('Council API unavailable, using simulation')
        return { fallback: true }
      }

      return deliberateRes.json()
    },
    onMutate: () => {
      setIsDeliberating(true)
      setDeliberation({
        id: `delib-${Date.now()}`,
        topic,
        status: 'active',
        phase: 'convocation',
        messages: []
      })
      setActiveTab('deliberation')
    },
    onSuccess: async (data) => {
      if (data.fallback) {
        // Fallback to simulation
        simulateDeliberation(topic)
      } else if (data.session_id) {
        // Connect WebSocket for streaming
        connectWebSocket(data.session_id)

        // If we got immediate results (non-streaming), process them
        if (data.opinions) {
          for (const opinion of data.opinions) {
            const msg: DeliberationMessage = {
              id: `msg-${Date.now()}-${opinion.member_id}`,
              memberId: opinion.member_id,
              memberName: opinion.member_name,
              memberColor: MEMBER_COLORS[opinion.member_name] || '#9333EA',
              content: opinion.content,
              type: 'opinion',
              phase: opinion.phase,
              timestamp: Date.now()
            }
            setDeliberation(prev => prev ? { ...prev, messages: [...prev.messages, msg] } : null)
            await new Promise(r => setTimeout(r, 500)) // Stagger display
          }
        }

        if (data.decision) {
          setDeliberation(prev => prev ? {
            ...prev,
            status: 'concluded',
            outcome: {
              decision: data.decision.decision,
              votes: data.decision.votes || { approve: 0, reject: 0, abstain: 0 },
              confidence: data.decision.confidence || 85,
              rationale: data.decision.rationale
            }
          } : null)
          setIsDeliberating(false)
        }
      }
    },
    onError: (error) => {
      console.error('Deliberation error:', error)
      // Fallback to simulation
      simulateDeliberation(topic)
    }
  })

  // Simulate deliberation for demo
  const simulateDeliberation = async (topic: string) => {
    const activeMembers = councilMembers.filter(m => m.active)
    const messages: DeliberationMessage[] = []

    // Each member gives an opinion
    for (const member of activeMembers) {
      await new Promise(resolve => setTimeout(resolve, 1500))

      const opinions = {
        'Sage': `After careful consideration, I believe we should approach "${topic}" with strategic foresight. We must consider long-term implications and stakeholder impact.`,
        'Guardian': `Security analysis complete. I've identified potential risks with this approach. We need proper safeguards and validation before proceeding.`,
        'Innovator': `Exciting opportunity! I see several creative solutions we haven't explored. Let me propose an unconventional approach that could yield better results.`,
        'Analyst': `Based on the data, the probability of success is approximately 73%. Key factors include resource availability, timeline constraints, and technical feasibility.`,
        'Executor': `From an implementation standpoint, this is achievable. I recommend breaking it into 4 phases with clear milestones.`,
        'Diplomat': `I've considered how this affects all parties involved. Communication and stakeholder alignment will be crucial for success.`
      }

      const msg: DeliberationMessage = {
        id: `msg-${Date.now()}-${member.id}`,
        memberId: member.id,
        memberName: member.name,
        memberColor: member.color,
        content: opinions[member.name as keyof typeof opinions] || `Regarding "${topic}", I have valuable insights to share.`,
        type: 'opinion',
        timestamp: Date.now()
      }

      messages.push(msg)
      setDeliberation(prev => prev ? { ...prev, messages: [...messages] } : null)
    }

    // Voting phase
    await new Promise(resolve => setTimeout(resolve, 1000))

    const votes = { approve: 0, reject: 0, abstain: 0 }
    for (const member of activeMembers) {
      await new Promise(resolve => setTimeout(resolve, 800))

      const voteType = Math.random() > 0.2 ? 'approve' : Math.random() > 0.5 ? 'abstain' : 'reject'
      votes[voteType]++

      const msg: DeliberationMessage = {
        id: `vote-${Date.now()}-${member.id}`,
        memberId: member.id,
        memberName: member.name,
        memberColor: member.color,
        content: voteType === 'approve' ? 'I support this proposal.' : voteType === 'reject' ? 'I have concerns that need addressing.' : 'I will defer to the majority.',
        type: 'vote',
        vote: voteType as 'approve' | 'reject' | 'abstain',
        timestamp: Date.now()
      }

      messages.push(msg)
      setDeliberation(prev => prev ? { ...prev, messages: [...messages] } : null)
    }

    // Consensus
    await new Promise(resolve => setTimeout(resolve, 1000))

    const outcome = {
      decision: votes.approve > votes.reject ? 'Approved with modifications' : 'Requires further discussion',
      votes,
      confidence: Math.round((votes.approve / activeMembers.length) * 100)
    }

    setDeliberation(prev => prev ? {
      ...prev,
      status: 'concluded',
      outcome
    } : null)
    setIsDeliberating(false)
  }

  return (
    <div className="flex h-full">
      {/* Sidebar - Council Members */}
      <div className="w-80 border-r border-bael-border bg-bael-surface flex flex-col">
        {/* Tabs */}
        <div className="flex border-b border-bael-border">
          {(['members', 'deliberation', 'history'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={clsx(
                'flex-1 px-4 py-3 text-sm font-medium transition-colors capitalize',
                activeTab === tab
                  ? 'text-bael-primary border-b-2 border-bael-primary'
                  : 'text-bael-muted hover:text-bael-text'
              )}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {activeTab === 'members' && (
            <div className="space-y-3">
              {councilMembers.map((member) => (
                <MemberCard
                  key={member.id}
                  member={member}
                  onToggle={() => updateCouncilMember(member.id, { active: !member.active })}
                />
              ))}

              <button className="w-full flex items-center justify-center gap-2 p-3 border border-dashed border-bael-border rounded-xl text-bael-muted hover:text-bael-text hover:border-bael-primary transition-colors">
                <PlusCircle size={16} />
                <span className="text-sm">Add Member</span>
              </button>
            </div>
          )}

          {activeTab === 'deliberation' && deliberation && (
            <div className="space-y-3">
              <div className="p-3 bg-bael-bg rounded-lg">
                <p className="text-xs text-bael-muted">Topic</p>
                <p className="text-sm text-bael-text font-medium">{deliberation.topic}</p>
              </div>

              {deliberation.outcome && (
                <div className="p-3 bg-bael-primary/10 border border-bael-primary/30 rounded-lg">
                  <p className="text-xs text-bael-primary mb-1">Decision</p>
                  <p className="text-sm text-bael-text font-medium">{deliberation.outcome.decision}</p>
                  <div className="flex items-center gap-4 mt-2 text-xs">
                    <span className="text-bael-success">✓ {deliberation.outcome.votes.approve}</span>
                    <span className="text-bael-error">✗ {deliberation.outcome.votes.reject}</span>
                    <span className="text-bael-muted">○ {deliberation.outcome.votes.abstain}</span>
                  </div>
                  <div className="mt-2 h-1.5 bg-bael-border rounded-full overflow-hidden">
                    <div
                      className="h-full bg-bael-success"
                      style={{ width: `${deliberation.outcome.confidence}%` }}
                    />
                  </div>
                  <p className="text-xs text-bael-muted mt-1">{deliberation.outcome.confidence}% confidence</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'history' && (
            <div className="text-center text-bael-muted text-sm py-8">
              No previous deliberations
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-bael-border bg-bael-surface">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-purple-600/20 flex items-center justify-center">
              <Users size={20} className="text-purple-400" />
            </div>
            <div>
              <h2 className="font-semibold text-bael-text flex items-center gap-2">
                Council Deliberation
                {isStreaming && (
                  <span className="flex items-center gap-1 text-xs px-2 py-0.5 bg-green-500/20 text-green-400 rounded-full">
                    <Wifi size={10} />
                    Live
                  </span>
                )}
              </h2>
              <p className="text-xs text-bael-muted">
                {councilMembers.filter(m => m.active).length} of {councilMembers.length} members active
                {currentPhase && ` • Phase: ${currentPhase}`}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {isDeliberating && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-bael-primary/20 text-bael-primary rounded-lg">
                <Loader2 size={14} className="animate-spin" />
                <span className="text-sm">{currentPhase || 'Deliberating'}...</span>
              </div>
            )}
            {loadingMembers && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-500/20 text-blue-400 rounded-lg">
                <Brain size={14} className="animate-pulse" />
                <span className="text-sm">Loading Council...</span>
              </div>
            )}
            <button
              className="p-2 hover:bg-bael-border rounded-lg transition-colors text-bael-muted hover:text-bael-text"
              title="Council Settings"
            >
              <Settings2 size={18} />
            </button>
          </div>
        </div>

        {/* Deliberation Area */}
        <div className="flex-1 overflow-y-auto p-6">
          {!deliberation ? (
            <NewDeliberationForm
              topic={topic}
              setTopic={setTopic}
              onStart={() => startDeliberation.mutate(topic)}
              disabled={!topic.trim() || councilMembers.filter(m => m.active).length === 0}
            />
          ) : (
            <div className="space-y-4 max-w-3xl mx-auto">
              <AnimatePresence>
                {deliberation.messages.map((msg) => (
                  <DeliberationBubble key={msg.id} message={msg} />
                ))}
              </AnimatePresence>

              {isDeliberating && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex items-center gap-3 text-bael-muted"
                >
                  <Loader2 size={16} className="animate-spin" />
                  <span className="text-sm">
                    {currentPhase ? `Phase: ${currentPhase}` : 'Council is deliberating'}...
                  </span>
                </motion.div>
              )}

              {/* Auto-scroll anchor */}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Actions */}
        {deliberation && (
          <div className="flex items-center justify-center gap-4 px-6 py-4 border-t border-bael-border bg-bael-surface">
            <button
              onClick={() => {
                setDeliberation(null)
                setTopic('')
              }}
              className="flex items-center gap-2 px-4 py-2 border border-bael-border rounded-lg text-bael-muted hover:text-bael-text transition-colors"
            >
              <RotateCcw size={16} />
              <span>New Topic</span>
            </button>

            {deliberation.status === 'concluded' && (
              <button className="flex items-center gap-2 px-4 py-2 bg-bael-primary text-white rounded-lg hover:bg-bael-primary/80 transition-colors">
                <CheckCircle size={16} />
                <span>Accept Decision</span>
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function MemberCard({
  member,
  onToggle
}: {
  member: CouncilMember
  onToggle: () => void
}) {
  return (
    <div className={clsx(
      'p-3 rounded-xl border transition-all cursor-pointer',
      member.active
        ? 'bg-bael-bg border-bael-border hover:border-bael-primary/50'
        : 'bg-bael-bg/50 border-bael-border/50 opacity-50'
    )}>
      <div className="flex items-start gap-3">
        <div
          className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0"
          style={{ backgroundColor: member.color + '33', color: member.color }}
        >
          {member.name.charAt(0)}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <h3 className="font-medium text-bael-text">{member.name}</h3>
            <button
              onClick={(e) => { e.stopPropagation(); onToggle() }}
              className={clsx(
                'w-8 h-4 rounded-full transition-colors relative',
                member.active ? 'bg-bael-primary' : 'bg-bael-border'
              )}
            >
              <div className={clsx(
                'absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform',
                member.active ? 'left-4' : 'left-0.5'
              )} />
            </button>
          </div>
          <p className="text-xs text-bael-muted">{member.role}</p>
          {member.specialties && (
            <div className="flex flex-wrap gap-1 mt-2">
              {member.specialties.slice(0, 2).map((s) => (
                <span key={s} className="text-xs px-1.5 py-0.5 bg-bael-border rounded text-bael-muted">
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function NewDeliberationForm({
  topic,
  setTopic,
  onStart,
  disabled
}: {
  topic: string
  setTopic: (t: string) => void
  onStart: () => void
  disabled: boolean
}) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center max-w-xl mx-auto">
      <div className="w-20 h-20 rounded-full bg-purple-600/20 flex items-center justify-center mb-6">
        <Sparkles size={40} className="text-purple-400" />
      </div>

      <h2 className="text-2xl font-bold text-bael-text mb-2">
        Council Deliberation
      </h2>
      <p className="text-bael-muted mb-8">
        Present a topic or decision for the council to deliberate. Each member will
        provide their perspective based on their expertise and vote on the outcome.
      </p>

      <div className="w-full space-y-4">
        <textarea
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="Enter the topic for deliberation..."
          rows={4}
          className="w-full px-4 py-3 bg-bael-surface border border-bael-border rounded-xl text-bael-text placeholder-bael-muted resize-none focus:outline-none focus:border-bael-primary transition-colors"
        />

        <button
          onClick={onStart}
          disabled={disabled}
          className={clsx(
            'w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl transition-all',
            disabled
              ? 'bg-bael-border text-bael-muted cursor-not-allowed'
              : 'bg-bael-primary text-white hover:bg-bael-primary/80'
          )}
        >
          <Play size={18} />
          <span>Start Deliberation</span>
        </button>
      </div>
    </div>
  )
}

function DeliberationBubble({ message }: { message: DeliberationMessage }) {
  const VoteIcon = message.vote === 'approve' ? ThumbsUp : message.vote === 'reject' ? ThumbsDown : AlertTriangle

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex gap-3"
    >
      <div
        className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0"
        style={{ backgroundColor: message.memberColor + '33', color: message.memberColor }}
      >
        {message.memberName.charAt(0)}
      </div>

      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-medium text-bael-text">{message.memberName}</span>
          {message.type === 'vote' && (
            <span className={clsx(
              'flex items-center gap-1 text-xs px-2 py-0.5 rounded-full',
              message.vote === 'approve' && 'bg-bael-success/20 text-bael-success',
              message.vote === 'reject' && 'bg-bael-error/20 text-bael-error',
              message.vote === 'abstain' && 'bg-bael-warning/20 text-bael-warning'
            )}>
              <VoteIcon size={10} />
              {message.vote}
            </span>
          )}
          <span className="text-xs text-bael-muted">
            {new Date(message.timestamp).toLocaleTimeString()}
          </span>
        </div>

        <div className="p-3 bg-bael-surface border border-bael-border rounded-xl rounded-tl-sm">
          <p className="text-sm text-bael-text">{message.content}</p>
        </div>
      </div>
    </motion.div>
  )
}
