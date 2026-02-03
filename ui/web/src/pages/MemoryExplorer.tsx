import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain,
  Layers,
  Database,
  Clock,
  Search,
  Trash2,
  Plus,
  RefreshCw,
  ChevronRight,
  ChevronDown,
  Eye,
  Edit3,
  Tag,
  Calendar,
  Hash,
  Zap,
  BookOpen,
  Workflow,
  Settings,
  Filter
} from 'lucide-react';

// Types
interface MemoryEntry {
  id: string;
  type: 'working' | 'episodic' | 'semantic' | 'procedural' | 'meta';
  content: string;
  summary?: string;
  timestamp: string;
  importance: number;
  accessCount: number;
  tags: string[];
  relations: string[];
  metadata?: Record<string, any>;
}

interface MemoryStats {
  working: { count: number; size: string; utilization: number };
  episodic: { count: number; size: string; utilization: number };
  semantic: { count: number; size: string; utilization: number };
  procedural: { count: number; size: string; utilization: number };
  meta: { count: number; size: string; utilization: number };
}

// Memory type configurations
const memoryTypes = [
  {
    id: 'working',
    name: 'Working Memory',
    icon: Zap,
    color: 'yellow',
    description: 'Short-term processing buffer for current context'
  },
  {
    id: 'episodic',
    name: 'Episodic Memory',
    icon: Calendar,
    color: 'blue',
    description: 'Experiences, events, and temporal sequences'
  },
  {
    id: 'semantic',
    name: 'Semantic Memory',
    icon: BookOpen,
    color: 'purple',
    description: 'Facts, knowledge, and conceptual understanding'
  },
  {
    id: 'procedural',
    name: 'Procedural Memory',
    icon: Workflow,
    color: 'green',
    description: 'Skills, procedures, and action patterns'
  },
  {
    id: 'meta',
    name: 'Meta Memory',
    icon: Brain,
    color: 'red',
    description: 'Memory about memory - self-reflection'
  }
];

// Sample memory entries
const sampleMemories: MemoryEntry[] = [
  {
    id: 'w1',
    type: 'working',
    content: 'User is building an MCP hub with 52 servers. Currently working on APEX orchestrator integration.',
    timestamp: 'Just now',
    importance: 95,
    accessCount: 12,
    tags: ['mcp', 'current-task', 'high-priority'],
    relations: ['w2', 'e1']
  },
  {
    id: 'w2',
    type: 'working',
    content: 'The project uses Python 3.11.13 with FastAPI for the backend and React+TypeScript for the frontend.',
    timestamp: '2 min ago',
    importance: 85,
    accessCount: 8,
    tags: ['tech-stack', 'configuration'],
    relations: ['s1']
  },
  {
    id: 'e1',
    type: 'episodic',
    content: 'Session started with uvicorn server setup. Fixed multiple import errors in personas and tools modules.',
    summary: 'Server setup and debugging session',
    timestamp: '30 min ago',
    importance: 70,
    accessCount: 3,
    tags: ['session', 'debugging'],
    relations: ['w1']
  },
  {
    id: 'e2',
    type: 'episodic',
    content: 'Created comprehensive MCP Docker infrastructure with 33 initial servers, then expanded to 52 servers.',
    summary: 'MCP infrastructure creation',
    timestamp: '1 hour ago',
    importance: 88,
    accessCount: 5,
    tags: ['mcp', 'docker', 'milestone'],
    relations: ['s2', 'p1']
  },
  {
    id: 's1',
    type: 'semantic',
    content: 'BAEL is an advanced AI orchestration system with 200+ core modules including reasoning engines, swarm intelligence, and self-evolution capabilities.',
    summary: 'BAEL system overview',
    timestamp: '2 hours ago',
    importance: 95,
    accessCount: 15,
    tags: ['bael', 'architecture', 'core-knowledge'],
    relations: ['s2', 's3']
  },
  {
    id: 's2',
    type: 'semantic',
    content: 'MCP (Model Context Protocol) is a standard for AI tool integration. It supports stdio and SSE transports.',
    summary: 'MCP protocol knowledge',
    timestamp: '2 hours ago',
    importance: 85,
    accessCount: 10,
    tags: ['mcp', 'protocol', 'integration'],
    relations: ['s1', 'p1']
  },
  {
    id: 's3',
    type: 'semantic',
    content: 'The Supreme Controller integrates 25+ reasoning engines and coordinates through multi-agent councils.',
    summary: 'Supreme Controller architecture',
    timestamp: '3 hours ago',
    importance: 80,
    accessCount: 6,
    tags: ['supreme', 'reasoning', 'architecture'],
    relations: ['s1']
  },
  {
    id: 'p1',
    type: 'procedural',
    content: 'To start MCP Hub: 1) Create .env from template 2) Run make mcp-ultimate-up 3) Verify with make mcp-status',
    summary: 'MCP startup procedure',
    timestamp: '1 hour ago',
    importance: 75,
    accessCount: 4,
    tags: ['procedure', 'mcp', 'startup'],
    relations: ['e2']
  },
  {
    id: 'p2',
    type: 'procedural',
    content: 'For debugging: Check logs with docker logs, verify health at /health endpoint, check port conflicts with lsof.',
    summary: 'Debugging workflow',
    timestamp: '4 hours ago',
    importance: 70,
    accessCount: 7,
    tags: ['procedure', 'debugging'],
    relations: ['e1']
  },
  {
    id: 'm1',
    type: 'meta',
    content: 'Working memory is currently at high utilization (98%). Consider consolidating some entries to episodic memory.',
    summary: 'Memory optimization suggestion',
    timestamp: '5 min ago',
    importance: 60,
    accessCount: 2,
    tags: ['meta', 'optimization'],
    relations: []
  }
];

export default function MemoryExplorer() {
  const [memories, setMemories] = useState<MemoryEntry[]>(sampleMemories);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [selectedMemory, setSelectedMemory] = useState<MemoryEntry | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showGraph, setShowGraph] = useState(false);

  const [stats, setStats] = useState<MemoryStats>({
    working: { count: 2, size: '12 KB', utilization: 98 },
    episodic: { count: 2, size: '45 KB', utilization: 45 },
    semantic: { count: 3, size: '128 KB', utilization: 67 },
    procedural: { count: 2, size: '32 KB', utilization: 34 },
    meta: { count: 1, size: '8 KB', utilization: 15 }
  });

  const filteredMemories = memories.filter(m => {
    const matchesType = !selectedType || m.type === selectedType;
    const matchesSearch = !searchQuery ||
      m.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.tags.some(t => t.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesType && matchesSearch;
  });

  const getTypeConfig = (type: string) => {
    return memoryTypes.find(t => t.id === type) || memoryTypes[0];
  };

  const getImportanceColor = (importance: number) => {
    if (importance >= 90) return 'text-red-400';
    if (importance >= 70) return 'text-orange-400';
    if (importance >= 50) return 'text-yellow-400';
    return 'text-gray-400';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Layers className="w-8 h-8 text-blue-500" />
            5-Layer Memory System
          </h1>
          <p className="text-gray-400 mt-1">
            Cognitive memory architecture with working, episodic, semantic, procedural, and meta layers
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowGraph(!showGraph)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              showGraph
                ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            <Eye className="w-4 h-4" />
            Graph View
          </button>
          <button className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors">
            <RefreshCw className="w-5 h-5 text-gray-400" />
          </button>
          <button className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors">
            <Settings className="w-5 h-5 text-gray-400" />
          </button>
        </div>
      </div>

      {/* Memory Layer Stats */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {memoryTypes.map((type) => {
          const stat = stats[type.id as keyof MemoryStats];
          return (
            <motion.button
              key={type.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              onClick={() => setSelectedType(selectedType === type.id ? null : type.id)}
              className={`p-4 rounded-xl border transition-all text-left ${
                selectedType === type.id
                  ? `bg-${type.color}-500/20 border-${type.color}-500/50`
                  : 'bg-gray-800/50 border-gray-700 hover:border-gray-600'
              }`}
            >
              <div className="flex items-center gap-3 mb-3">
                <type.icon className={`w-5 h-5 text-${type.color}-500`} />
                <span className="text-white font-medium">{type.name}</span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-sm mb-3">
                <div>
                  <div className="text-gray-400">Entries</div>
                  <div className="text-white font-bold">{stat.count}</div>
                </div>
                <div>
                  <div className="text-gray-400">Size</div>
                  <div className="text-white font-bold">{stat.size}</div>
                </div>
              </div>

              <div className="w-full bg-gray-700 rounded-full h-2">
                <div
                  className={`bg-${type.color}-500 h-2 rounded-full transition-all`}
                  style={{ width: `${stat.utilization}%` }}
                />
              </div>
              <div className="text-xs text-gray-400 mt-1">{stat.utilization}% utilized</div>
            </motion.button>
          );
        })}
      </div>

      {/* Search & Filters */}
      <div className="flex items-center gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search memories by content or tags..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:border-blue-500 focus:outline-none"
          />
        </div>
        <button className="flex items-center gap-2 px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg hover:bg-gray-700 transition-colors">
          <Filter className="w-5 h-5 text-gray-400" />
          <span className="text-gray-400">Filters</span>
        </button>
        <button className="flex items-center gap-2 px-4 py-3 bg-blue-600 rounded-lg hover:bg-blue-500 transition-colors">
          <Plus className="w-5 h-5 text-white" />
          <span className="text-white font-medium">Add Memory</span>
        </button>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Memory List */}
        <div className="lg:col-span-2 space-y-4">
          <AnimatePresence mode="popLayout">
            {filteredMemories.map((memory) => {
              const typeConfig = getTypeConfig(memory.type);
              return (
                <motion.div
                  key={memory.id}
                  layout
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  onClick={() => setSelectedMemory(memory)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${
                    selectedMemory?.id === memory.id
                      ? `bg-${typeConfig.color}-500/10 border-${typeConfig.color}-500/50`
                      : 'bg-gray-800/50 border-gray-700 hover:border-gray-600'
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <typeConfig.icon className={`w-5 h-5 text-${typeConfig.color}-500`} />
                      <span className="text-sm text-gray-400">{typeConfig.name}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`text-sm font-medium ${getImportanceColor(memory.importance)}`}>
                        {memory.importance}%
                      </span>
                      <span className="text-xs text-gray-500">{memory.timestamp}</span>
                    </div>
                  </div>

                  <p className="text-white mb-3 line-clamp-2">{memory.content}</p>

                  <div className="flex items-center justify-between">
                    <div className="flex flex-wrap gap-2">
                      {memory.tags.slice(0, 3).map((tag) => (
                        <span
                          key={tag}
                          className="px-2 py-0.5 bg-gray-700 rounded text-xs text-gray-300"
                        >
                          {tag}
                        </span>
                      ))}
                      {memory.tags.length > 3 && (
                        <span className="text-xs text-gray-500">+{memory.tags.length - 3}</span>
                      )}
                    </div>
                    <div className="flex items-center gap-4 text-sm text-gray-400">
                      <span className="flex items-center gap-1">
                        <Hash className="w-3 h-3" />
                        {memory.accessCount}
                      </span>
                      <span className="flex items-center gap-1">
                        <Workflow className="w-3 h-3" />
                        {memory.relations.length}
                      </span>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>

        {/* Memory Detail Panel */}
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 h-fit sticky top-6">
          {selectedMemory ? (
            <>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-white">Memory Details</h3>
                <div className="flex items-center gap-2">
                  <button className="p-2 hover:bg-gray-700 rounded-lg transition-colors">
                    <Edit3 className="w-4 h-4 text-gray-400" />
                  </button>
                  <button className="p-2 hover:bg-red-500/20 rounded-lg transition-colors">
                    <Trash2 className="w-4 h-4 text-red-400" />
                  </button>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="text-sm text-gray-400">Type</label>
                  <div className="flex items-center gap-2 mt-1">
                    {(() => {
                      const config = getTypeConfig(selectedMemory.type);
                      return (
                        <>
                          <config.icon className={`w-4 h-4 text-${config.color}-500`} />
                          <span className="text-white">{config.name}</span>
                        </>
                      );
                    })()}
                  </div>
                </div>

                <div>
                  <label className="text-sm text-gray-400">Content</label>
                  <p className="text-white mt-1">{selectedMemory.content}</p>
                </div>

                {selectedMemory.summary && (
                  <div>
                    <label className="text-sm text-gray-400">Summary</label>
                    <p className="text-gray-300 mt-1">{selectedMemory.summary}</p>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm text-gray-400">Importance</label>
                    <div className={`text-xl font-bold mt-1 ${getImportanceColor(selectedMemory.importance)}`}>
                      {selectedMemory.importance}%
                    </div>
                  </div>
                  <div>
                    <label className="text-sm text-gray-400">Access Count</label>
                    <div className="text-xl font-bold text-white mt-1">
                      {selectedMemory.accessCount}
                    </div>
                  </div>
                </div>

                <div>
                  <label className="text-sm text-gray-400">Tags</label>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {selectedMemory.tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-1 bg-gray-700 rounded text-sm text-gray-300"
                      >
                        <Tag className="w-3 h-3 inline mr-1" />
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-sm text-gray-400">Relations</label>
                  <div className="space-y-2 mt-2">
                    {selectedMemory.relations.length > 0 ? (
                      selectedMemory.relations.map((relId) => {
                        const relMemory = memories.find(m => m.id === relId);
                        if (!relMemory) return null;
                        const config = getTypeConfig(relMemory.type);
                        return (
                          <button
                            key={relId}
                            onClick={() => setSelectedMemory(relMemory)}
                            className="w-full flex items-center gap-2 p-2 bg-gray-700/50 rounded-lg hover:bg-gray-700 transition-colors text-left"
                          >
                            <config.icon className={`w-4 h-4 text-${config.color}-500`} />
                            <span className="text-sm text-gray-300 truncate flex-1">
                              {relMemory.content.slice(0, 50)}...
                            </span>
                            <ChevronRight className="w-4 h-4 text-gray-500" />
                          </button>
                        );
                      })
                    ) : (
                      <p className="text-gray-500 text-sm">No relations</p>
                    )}
                  </div>
                </div>

                <div className="pt-4 border-t border-gray-700">
                  <div className="flex items-center gap-2 text-sm text-gray-400">
                    <Clock className="w-4 h-4" />
                    <span>{selectedMemory.timestamp}</span>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="text-center py-12">
              <Layers className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">Select a memory to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
