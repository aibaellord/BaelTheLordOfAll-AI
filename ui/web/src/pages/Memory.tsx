import React, { useState, useEffect, useCallback } from 'react';
import {
  Database,
  Search,
  Clock,
  Brain,
  Trash2,
  RefreshCw,
  Filter,
  ChevronDown,
  ChevronRight,
  Eye,
  Tag,
  Calendar,
  FileText,
  MessageSquare,
  Zap,
  Layers
} from 'lucide-react';
import { useBaelStore } from '../store';

// =============================================================================
// TYPES
// =============================================================================

interface MemoryEntry {
  id: string;
  type: 'episodic' | 'semantic' | 'procedural' | 'working';
  content: string;
  summary?: string;
  tags: string[];
  importance: number;
  accessCount: number;
  createdAt: string;
  lastAccessed: string;
  metadata: Record<string, any>;
  embedding?: number[];
}

interface MemoryStats {
  total: number;
  byType: Record<string, number>;
  avgImportance: number;
  recentlyAccessed: number;
}

// =============================================================================
// COMPONENTS
// =============================================================================

const MemoryTypeIcon: React.FC<{ type: string }> = ({ type }) => {
  switch (type) {
    case 'episodic':
      return <MessageSquare className="w-4 h-4 text-blue-400" />;
    case 'semantic':
      return <Brain className="w-4 h-4 text-purple-400" />;
    case 'procedural':
      return <Zap className="w-4 h-4 text-green-400" />;
    case 'working':
      return <Clock className="w-4 h-4 text-yellow-400" />;
    default:
      return <Database className="w-4 h-4 text-gray-400" />;
  }
};

const ImportanceBar: React.FC<{ value: number }> = ({ value }) => {
  const width = Math.min(100, Math.max(0, value * 100));
  const color = value > 0.7 ? 'bg-red-500' : value > 0.4 ? 'bg-yellow-500' : 'bg-green-500';

  return (
    <div className="w-full h-1.5 bg-surface rounded-full overflow-hidden">
      <div
        className={`h-full ${color} transition-all duration-300`}
        style={{ width: `${width}%` }}
      />
    </div>
  );
};

const MemoryCard: React.FC<{
  memory: MemoryEntry;
  isExpanded: boolean;
  onToggle: () => void;
  onDelete: () => void;
}> = ({ memory, isExpanded, onToggle, onDelete }) => {
  const typeColors: Record<string, string> = {
    episodic: 'border-blue-500/30 bg-blue-500/5',
    semantic: 'border-purple-500/30 bg-purple-500/5',
    procedural: 'border-green-500/30 bg-green-500/5',
    working: 'border-yellow-500/30 bg-yellow-500/5',
  };

  return (
    <div
      className={`border rounded-lg p-4 transition-all duration-200 ${typeColors[memory.type] || 'border-border bg-surface'}`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3 flex-1">
          <button
            onClick={onToggle}
            className="p-1 hover:bg-white/10 rounded transition-colors mt-0.5"
          >
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-400" />
            )}
          </button>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <MemoryTypeIcon type={memory.type} />
              <span className="text-xs uppercase tracking-wider text-gray-400 font-medium">
                {memory.type}
              </span>
              <span className="text-xs text-gray-500">
                {memory.id.slice(0, 8)}...
              </span>
            </div>

            <p className="text-sm text-gray-200 line-clamp-2">
              {memory.summary || memory.content}
            </p>

            {isExpanded && (
              <div className="mt-4 space-y-4">
                <div className="bg-bg rounded p-3">
                  <h4 className="text-xs uppercase text-gray-500 mb-2">Full Content</h4>
                  <p className="text-sm text-gray-300 whitespace-pre-wrap">
                    {memory.content}
                  </p>
                </div>

                {memory.tags.length > 0 && (
                  <div>
                    <h4 className="text-xs uppercase text-gray-500 mb-2">Tags</h4>
                    <div className="flex flex-wrap gap-2">
                      {memory.tags.map((tag, i) => (
                        <span
                          key={i}
                          className="px-2 py-1 bg-primary/20 text-primary text-xs rounded-full"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4 text-xs text-gray-400">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-3 h-3" />
                    Created: {new Date(memory.createdAt).toLocaleString()}
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="w-3 h-3" />
                    Last accessed: {new Date(memory.lastAccessed).toLocaleString()}
                  </div>
                  <div className="flex items-center gap-2">
                    <Eye className="w-3 h-3" />
                    Access count: {memory.accessCount}
                  </div>
                  <div className="flex items-center gap-2">
                    <Layers className="w-3 h-3" />
                    Importance: {(memory.importance * 100).toFixed(0)}%
                  </div>
                </div>

                {Object.keys(memory.metadata).length > 0 && (
                  <div>
                    <h4 className="text-xs uppercase text-gray-500 mb-2">Metadata</h4>
                    <pre className="text-xs bg-bg rounded p-2 overflow-x-auto text-gray-400">
                      {JSON.stringify(memory.metadata, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 ml-4">
          <div className="w-20">
            <ImportanceBar value={memory.importance} />
          </div>
          <button
            onClick={onDelete}
            className="p-1.5 hover:bg-red-500/20 text-red-400 rounded transition-colors"
            title="Delete memory"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

const MemoryStats: React.FC<{ stats: MemoryStats }> = ({ stats }) => {
  return (
    <div className="grid grid-cols-4 gap-4 mb-6">
      <div className="bg-surface border border-border rounded-lg p-4">
        <div className="flex items-center gap-2 text-gray-400 mb-2">
          <Database className="w-4 h-4" />
          <span className="text-xs uppercase">Total Memories</span>
        </div>
        <div className="text-2xl font-bold text-white">{stats.total}</div>
      </div>

      <div className="bg-surface border border-border rounded-lg p-4">
        <div className="flex items-center gap-2 text-gray-400 mb-2">
          <Brain className="w-4 h-4" />
          <span className="text-xs uppercase">Semantic</span>
        </div>
        <div className="text-2xl font-bold text-purple-400">
          {stats.byType.semantic || 0}
        </div>
      </div>

      <div className="bg-surface border border-border rounded-lg p-4">
        <div className="flex items-center gap-2 text-gray-400 mb-2">
          <MessageSquare className="w-4 h-4" />
          <span className="text-xs uppercase">Episodic</span>
        </div>
        <div className="text-2xl font-bold text-blue-400">
          {stats.byType.episodic || 0}
        </div>
      </div>

      <div className="bg-surface border border-border rounded-lg p-4">
        <div className="flex items-center gap-2 text-gray-400 mb-2">
          <Clock className="w-4 h-4" />
          <span className="text-xs uppercase">Recently Accessed</span>
        </div>
        <div className="text-2xl font-bold text-green-400">
          {stats.recentlyAccessed}
        </div>
      </div>
    </div>
  );
};

// =============================================================================
// MAIN PAGE
// =============================================================================

export const Memory: React.FC = () => {
  const [memories, setMemories] = useState<MemoryEntry[]>([]);
  const [stats, setStats] = useState<MemoryStats>({
    total: 0,
    byType: {},
    avgImportance: 0,
    recentlyAccessed: 0
  });
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'recent' | 'importance' | 'accessed'>('recent');

  const fetchMemories = useCallback(async () => {
    setLoading(true);
    try {
      // Try the main memory endpoint first
      let response = await fetch('/api/v1/memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: searchQuery || undefined,
          type: filterType || undefined,
          limit: 100
        })
      });

      // If that fails, try the singularity memory search endpoint
      if (!response.ok) {
        response = await fetch('/api/singularity/memory/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: searchQuery || '*',
            limit: 100
          })
        });
      }

      if (response.ok) {
        const data = await response.json();
        // Handle both response formats
        const memoriesData = data.memories || data.data?.results || [];
        setMemories(memoriesData);
        setStats(data.stats || {
          total: memoriesData.length || 0,
          byType: {},
          avgImportance: 0,
          recentlyAccessed: 0
        });
        return; // Success, don't fall through to mock data
      }
    } catch (error) {
      console.error('Failed to fetch memories:', error);
    }

    // Mock data for development when API unavailable
    setMemories([
        {
          id: 'mem-001',
          type: 'episodic',
          content: 'User asked about setting up MCP servers. I provided detailed instructions for configuring multiple MCP integrations including filesystem, GitHub, and Brave Search.',
          summary: 'MCP server setup instructions provided',
          tags: ['mcp', 'setup', 'configuration'],
          importance: 0.8,
          accessCount: 5,
          createdAt: new Date(Date.now() - 3600000).toISOString(),
          lastAccessed: new Date().toISOString(),
          metadata: { conversationId: 'conv-123' }
        },
        {
          id: 'mem-002',
          type: 'semantic',
          content: 'BAEL is an AI agent system with multi-agent orchestration, workflow automation, and autonomous self-management capabilities.',
          summary: 'Core knowledge about BAEL system',
          tags: ['bael', 'core', 'architecture'],
          importance: 0.95,
          accessCount: 12,
          createdAt: new Date(Date.now() - 86400000).toISOString(),
          lastAccessed: new Date().toISOString(),
          metadata: { source: 'documentation' }
        },
        {
          id: 'mem-003',
          type: 'procedural',
          content: 'To deploy BAEL: 1) Run docker-compose up -d 2) Access UI at localhost:3000 3) Configure LLM API keys in settings 4) Run auto-setup for service discovery',
          summary: 'BAEL deployment procedure',
          tags: ['deployment', 'docker', 'setup'],
          importance: 0.7,
          accessCount: 3,
          createdAt: new Date(Date.now() - 172800000).toISOString(),
          lastAccessed: new Date(Date.now() - 3600000).toISOString(),
          metadata: {}
        },
        {
          id: 'mem-004',
          type: 'working',
          content: 'Currently implementing workflow execution engine and agent backend. User prefers autonomous operation with minimal manual configuration.',
          summary: 'Active working memory for current session',
          tags: ['session', 'implementation', 'workflow'],
          importance: 0.9,
          accessCount: 8,
          createdAt: new Date().toISOString(),
          lastAccessed: new Date().toISOString(),
          metadata: { session: 'current' }
        }
      ]);
      setStats({
        total: 4,
        byType: { episodic: 1, semantic: 1, procedural: 1, working: 1 },
        avgImportance: 0.84,
        recentlyAccessed: 3
      });

    setLoading(false);
  }, [searchQuery, filterType]);

  useEffect(() => {
    fetchMemories();
  }, [fetchMemories]);

  const handleDelete = async (id: string) => {
    try {
      await fetch(`/api/v1/memory/${id}`, { method: 'DELETE' });
      setMemories(prev => prev.filter(m => m.id !== id));
    } catch (error) {
      console.error('Failed to delete memory:', error);
    }
  };

  const sortedMemories = [...memories].sort((a, b) => {
    switch (sortBy) {
      case 'importance':
        return b.importance - a.importance;
      case 'accessed':
        return new Date(b.lastAccessed).getTime() - new Date(a.lastAccessed).getTime();
      case 'recent':
      default:
        return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
    }
  });

  const filteredMemories = sortedMemories.filter(m => {
    if (filterType && m.type !== filterType) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        m.content.toLowerCase().includes(query) ||
        m.summary?.toLowerCase().includes(query) ||
        m.tags.some(t => t.toLowerCase().includes(query))
      );
    }
    return true;
  });

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex-none p-6 border-b border-border">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <Database className="w-7 h-7 text-primary" />
              Memory
            </h1>
            <p className="text-gray-400 text-sm mt-1">
              Browse and manage BAEL's memory stores
            </p>
          </div>

          <button
            onClick={fetchMemories}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/80 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Stats */}
        <MemoryStats stats={stats} />

        {/* Filters */}
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search memories..."
              className="w-full pl-10 pr-4 py-2 bg-surface border border-border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-primary"
            />
          </div>

          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            {['episodic', 'semantic', 'procedural', 'working'].map((type) => (
              <button
                key={type}
                onClick={() => setFilterType(filterType === type ? null : type)}
                className={`px-3 py-1.5 text-xs rounded-full transition-colors ${
                  filterType === type
                    ? 'bg-primary text-white'
                    : 'bg-surface text-gray-400 hover:text-white'
                }`}
              >
                {type}
              </button>
            ))}
          </div>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="px-3 py-2 bg-surface border border-border rounded-lg text-white text-sm focus:outline-none focus:border-primary"
          >
            <option value="recent">Most Recent</option>
            <option value="importance">By Importance</option>
            <option value="accessed">Last Accessed</option>
          </select>
        </div>
      </div>

      {/* Memory List */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <RefreshCw className="w-8 h-8 text-primary animate-spin mx-auto mb-4" />
              <p className="text-gray-400">Loading memories...</p>
            </div>
          </div>
        ) : filteredMemories.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <Database className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">No memories found</p>
              <p className="text-gray-500 text-sm mt-1">
                {searchQuery ? 'Try a different search query' : 'Memories will appear here as BAEL learns'}
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredMemories.map((memory) => (
              <MemoryCard
                key={memory.id}
                memory={memory}
                isExpanded={expandedId === memory.id}
                onToggle={() => setExpandedId(expandedId === memory.id ? null : memory.id)}
                onDelete={() => handleDelete(memory.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Memory;
