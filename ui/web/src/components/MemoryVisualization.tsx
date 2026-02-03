import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Brain, Search, Filter, ZoomIn, ZoomOut, RotateCw,
  Database, Link, Clock, Star, Trash2, Eye, Download,
  ChevronRight, ChevronDown, Tag, Hash, ArrowRight, X
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Types
interface Memory {
  id: string;
  type: 'episodic' | 'semantic' | 'procedural' | 'working';
  content: string;
  summary?: string;
  importance: number;
  created_at: number;
  last_accessed: number;
  access_count: number;
  tags: string[];
  connections: string[];
  metadata: Record<string, any>;
}

interface MemoryNode {
  id: string;
  x: number;
  y: number;
  memory: Memory;
  selected: boolean;
}

interface MemoryConnection {
  source: string;
  target: string;
  strength: number;
}

const MemoryTypeColors: Record<string, string> = {
  episodic: '#60a5fa',   // blue
  semantic: '#34d399',   // green
  procedural: '#f472b6', // pink
  working: '#fbbf24'     // yellow
};

const MemoryTypeIcons: Record<string, React.ReactNode> = {
  episodic: <Clock className="w-4 h-4" />,
  semantic: <Database className="w-4 h-4" />,
  procedural: <ArrowRight className="w-4 h-4" />,
  working: <Brain className="w-4 h-4" />
};

// Mock data generator
const generateMockMemories = (count: number = 50): Memory[] => {
  const types: Memory['type'][] = ['episodic', 'semantic', 'procedural', 'working'];
  const contents = [
    'User prefers dark mode and minimal interfaces',
    'Project uses TypeScript with React and FastAPI backend',
    'Successful code review workflow: check types, run tests, review logic',
    'Database connection string format for PostgreSQL',
    'User asked about machine learning model training',
    'API rate limiting is set to 100 requests per minute',
    'The LLM model performs best with temperature 0.7',
    'User timezone is PST (Pacific Standard Time)',
    'Preferred coding style: functional over OOP',
    'Last session discussed workflow automation',
  ];

  return Array.from({ length: count }, (_, i) => ({
    id: `mem-${i}`,
    type: types[Math.floor(Math.random() * types.length)],
    content: contents[Math.floor(Math.random() * contents.length)],
    summary: contents[Math.floor(Math.random() * contents.length)].substring(0, 50) + '...',
    importance: Math.random(),
    created_at: Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000,
    last_accessed: Date.now() - Math.random() * 24 * 60 * 60 * 1000,
    access_count: Math.floor(Math.random() * 100),
    tags: ['context', 'preference', 'code', 'user'].slice(0, Math.floor(Math.random() * 4) + 1),
    connections: Array.from({ length: Math.floor(Math.random() * 5) }, () =>
      `mem-${Math.floor(Math.random() * count)}`
    ).filter(id => id !== `mem-${i}`),
    metadata: {}
  }));
};

// Force-directed layout helpers
const forceLayout = (nodes: MemoryNode[], connections: MemoryConnection[], iterations: number = 100) => {
  const k = 100; // Optimal distance
  const cooling = 0.95;
  let temperature = 1;

  for (let iter = 0; iter < iterations; iter++) {
    // Repulsion between all nodes
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[j].x - nodes[i].x;
        const dy = nodes[j].y - nodes[i].y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = (k * k) / dist * temperature;

        nodes[i].x -= (dx / dist) * force * 0.1;
        nodes[i].y -= (dy / dist) * force * 0.1;
        nodes[j].x += (dx / dist) * force * 0.1;
        nodes[j].y += (dy / dist) * force * 0.1;
      }
    }

    // Attraction along connections
    connections.forEach(conn => {
      const source = nodes.find(n => n.id === conn.source);
      const target = nodes.find(n => n.id === conn.target);
      if (source && target) {
        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = (dist - k) * 0.01 * temperature * conn.strength;

        source.x += (dx / dist) * force;
        source.y += (dy / dist) * force;
        target.x -= (dx / dist) * force;
        target.y -= (dy / dist) * force;
      }
    });

    temperature *= cooling;
  }

  return nodes;
};

// Components
const MemoryCard: React.FC<{ memory: Memory; onClose: () => void }> = ({ memory, onClose }) => (
  <motion.div
    initial={{ opacity: 0, x: 300 }}
    animate={{ opacity: 1, x: 0 }}
    exit={{ opacity: 0, x: 300 }}
    className="absolute right-4 top-4 w-80 bg-gray-800 rounded-lg border border-gray-700 shadow-xl overflow-hidden"
  >
    <div className="p-4 border-b border-gray-700 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <div
          className="p-2 rounded-lg"
          style={{ backgroundColor: MemoryTypeColors[memory.type] + '20' }}
        >
          {MemoryTypeIcons[memory.type]}
        </div>
        <div>
          <div className="font-medium text-white capitalize">{memory.type}</div>
          <div className="text-xs text-gray-400">ID: {memory.id}</div>
        </div>
      </div>
      <button onClick={onClose} className="text-gray-400 hover:text-white">
        <X className="w-5 h-5" />
      </button>
    </div>

    <div className="p-4 space-y-4">
      <div>
        <label className="text-xs text-gray-400 uppercase">Content</label>
        <p className="text-gray-200 mt-1">{memory.content}</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-xs text-gray-400 uppercase">Importance</label>
          <div className="flex items-center gap-2 mt-1">
            <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-500 rounded-full"
                style={{ width: `${memory.importance * 100}%` }}
              />
            </div>
            <span className="text-sm text-gray-300">{Math.round(memory.importance * 100)}%</span>
          </div>
        </div>
        <div>
          <label className="text-xs text-gray-400 uppercase">Accesses</label>
          <p className="text-gray-200 mt-1">{memory.access_count}</p>
        </div>
      </div>

      <div>
        <label className="text-xs text-gray-400 uppercase">Tags</label>
        <div className="flex flex-wrap gap-1 mt-1">
          {memory.tags.map(tag => (
            <span
              key={tag}
              className="px-2 py-1 bg-gray-700 text-gray-300 rounded text-xs"
            >
              #{tag}
            </span>
          ))}
        </div>
      </div>

      <div>
        <label className="text-xs text-gray-400 uppercase">Connections</label>
        <p className="text-gray-300 mt-1">{memory.connections.length} linked memories</p>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs text-gray-400">
        <div>
          <span>Created: </span>
          <span className="text-gray-300">{new Date(memory.created_at).toLocaleDateString()}</span>
        </div>
        <div>
          <span>Accessed: </span>
          <span className="text-gray-300">{new Date(memory.last_accessed).toLocaleDateString()}</span>
        </div>
      </div>
    </div>

    <div className="p-4 border-t border-gray-700 flex gap-2">
      <button className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm flex items-center justify-center gap-2">
        <Eye className="w-4 h-4" />
        View Full
      </button>
      <button className="px-4 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg">
        <Trash2 className="w-4 h-4" />
      </button>
    </div>
  </motion.div>
);

const MemoryGraph: React.FC<{
  nodes: MemoryNode[];
  connections: MemoryConnection[];
  zoom: number;
  pan: { x: number; y: number };
  onNodeClick: (memory: Memory) => void;
  selectedMemoryId: string | null;
}> = ({ nodes, connections, zoom, pan, onNodeClick, selectedMemoryId }) => {
  const svgRef = useRef<SVGSVGElement>(null);

  return (
    <svg
      ref={svgRef}
      className="w-full h-full"
      style={{ background: 'radial-gradient(circle at center, #1a1a2e 0%, #0a0a0f 100%)' }}
    >
      <defs>
        <filter id="glow">
          <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
          <feMerge>
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>

      <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
        {/* Connections */}
        {connections.map((conn, i) => {
          const source = nodes.find(n => n.id === conn.source);
          const target = nodes.find(n => n.id === conn.target);
          if (!source || !target) return null;

          const isHighlighted = selectedMemoryId &&
            (source.id === selectedMemoryId || target.id === selectedMemoryId);

          return (
            <line
              key={`${conn.source}-${conn.target}-${i}`}
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              stroke={isHighlighted ? '#6366f1' : '#374151'}
              strokeWidth={isHighlighted ? 2 : 1}
              strokeOpacity={isHighlighted ? 0.8 : 0.3}
            />
          );
        })}

        {/* Nodes */}
        {nodes.map(node => {
          const isSelected = selectedMemoryId === node.id;
          const isConnected = selectedMemoryId && node.memory.connections.includes(selectedMemoryId);
          const size = 8 + node.memory.importance * 8;

          return (
            <g
              key={node.id}
              transform={`translate(${node.x}, ${node.y})`}
              onClick={() => onNodeClick(node.memory)}
              style={{ cursor: 'pointer' }}
            >
              <circle
                r={size + (isSelected ? 4 : 0)}
                fill={MemoryTypeColors[node.memory.type]}
                fillOpacity={isSelected ? 1 : isConnected ? 0.8 : 0.6}
                filter={isSelected ? 'url(#glow)' : undefined}
              />
              {isSelected && (
                <circle
                  r={size + 8}
                  fill="none"
                  stroke={MemoryTypeColors[node.memory.type]}
                  strokeWidth={2}
                  strokeDasharray="4 4"
                  className="animate-spin"
                  style={{ animationDuration: '10s' }}
                />
              )}
              <title>{node.memory.content}</title>
            </g>
          );
        })}
      </g>
    </svg>
  );
};

const MemoryList: React.FC<{
  memories: Memory[];
  selectedId: string | null;
  onSelect: (memory: Memory) => void;
}> = ({ memories, selectedId, onSelect }) => (
  <div className="space-y-2 overflow-y-auto max-h-96">
    {memories.map(memory => (
      <div
        key={memory.id}
        onClick={() => onSelect(memory)}
        className={`p-3 rounded-lg cursor-pointer transition-colors ${
          selectedId === memory.id
            ? 'bg-indigo-600/20 border border-indigo-500/50'
            : 'bg-gray-800 hover:bg-gray-700 border border-transparent'
        }`}
      >
        <div className="flex items-center gap-2 mb-1">
          <div
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: MemoryTypeColors[memory.type] }}
          />
          <span className="text-xs text-gray-400 capitalize">{memory.type}</span>
          <span className="text-xs text-gray-500">•</span>
          <span className="text-xs text-gray-500">{memory.access_count} accesses</span>
        </div>
        <p className="text-sm text-gray-200 truncate">{memory.content}</p>
        <div className="flex gap-1 mt-2">
          {memory.tags.slice(0, 3).map(tag => (
            <span
              key={tag}
              className="px-1.5 py-0.5 bg-gray-700/50 text-gray-400 rounded text-xs"
            >
              #{tag}
            </span>
          ))}
        </div>
      </div>
    ))}
  </div>
);

const StatsPanel: React.FC<{ memories: Memory[] }> = ({ memories }) => {
  const stats = {
    total: memories.length,
    byType: {
      episodic: memories.filter(m => m.type === 'episodic').length,
      semantic: memories.filter(m => m.type === 'semantic').length,
      procedural: memories.filter(m => m.type === 'procedural').length,
      working: memories.filter(m => m.type === 'working').length,
    },
    avgImportance: memories.reduce((sum, m) => sum + m.importance, 0) / memories.length,
    totalConnections: memories.reduce((sum, m) => sum + m.connections.length, 0)
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="text-2xl font-bold text-white">{stats.total}</div>
        <div className="text-sm text-gray-400">Total Memories</div>
      </div>
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="text-2xl font-bold text-white">{stats.totalConnections}</div>
        <div className="text-sm text-gray-400">Connections</div>
      </div>
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="text-2xl font-bold text-white">{(stats.avgImportance * 100).toFixed(0)}%</div>
        <div className="text-sm text-gray-400">Avg Importance</div>
      </div>
      <div className="bg-gray-800 rounded-lg p-4 flex gap-2">
        {Object.entries(stats.byType).map(([type, count]) => (
          <div key={type} className="flex-1 text-center">
            <div
              className="w-3 h-3 rounded-full mx-auto mb-1"
              style={{ backgroundColor: MemoryTypeColors[type] }}
            />
            <div className="text-xs font-medium text-white">{count}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Main Component
export const MemoryVisualization: React.FC = () => {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [nodes, setNodes] = useState<MemoryNode[]>([]);
  const [connections, setConnections] = useState<MemoryConnection[]>([]);
  const [selectedMemory, setSelectedMemory] = useState<Memory | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 400, y: 300 });
  const [viewMode, setViewMode] = useState<'graph' | 'list'>('graph');
  const [isLoading, setIsLoading] = useState(true);

  // Load memories
  useEffect(() => {
    const fetchMemories = async () => {
      setIsLoading(true);
      try {
        // Try API first
        const response = await fetch('/api/v1/memory/all');
        if (response.ok) {
          const data = await response.json();
          setMemories(data.memories || []);
        } else {
          // Use mock data
          setMemories(generateMockMemories());
        }
      } catch {
        setMemories(generateMockMemories());
      }
      setIsLoading(false);
    };

    fetchMemories();
  }, []);

  // Generate graph layout
  useEffect(() => {
    if (memories.length === 0) return;

    // Filter memories
    let filtered = memories;
    if (searchQuery) {
      filtered = filtered.filter(m =>
        m.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
        m.tags.some(t => t.toLowerCase().includes(searchQuery.toLowerCase()))
      );
    }
    if (filterType) {
      filtered = filtered.filter(m => m.type === filterType);
    }

    // Create nodes with random initial positions
    let newNodes: MemoryNode[] = filtered.map(m => ({
      id: m.id,
      x: Math.random() * 600 - 300,
      y: Math.random() * 400 - 200,
      memory: m,
      selected: m.id === selectedMemory?.id
    }));

    // Create connections
    const newConnections: MemoryConnection[] = [];
    filtered.forEach(m => {
      m.connections.forEach(targetId => {
        if (filtered.some(f => f.id === targetId)) {
          newConnections.push({
            source: m.id,
            target: targetId,
            strength: 0.5 + Math.random() * 0.5
          });
        }
      });
    });

    // Apply force layout
    newNodes = forceLayout(newNodes, newConnections, 50);

    setNodes(newNodes);
    setConnections(newConnections);
  }, [memories, searchQuery, filterType, selectedMemory]);

  const handleNodeClick = useCallback((memory: Memory) => {
    setSelectedMemory(prev => prev?.id === memory.id ? null : memory);
  }, []);

  const handleZoom = (delta: number) => {
    setZoom(prev => Math.max(0.1, Math.min(3, prev + delta)));
  };

  const handleRefresh = async () => {
    setIsLoading(true);
    // Regenerate mock data for demo
    setMemories(generateMockMemories());
    setIsLoading(false);
  };

  return (
    <div className="h-full flex flex-col bg-bael-bg">
      {/* Header */}
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-600/20 rounded-lg">
              <Brain className="w-6 h-6 text-indigo-400" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-white">Memory Visualization</h2>
              <p className="text-sm text-gray-400">Explore and manage BAEL's memory network</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setViewMode(viewMode === 'graph' ? 'list' : 'graph')}
              className="px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm"
            >
              {viewMode === 'graph' ? 'List View' : 'Graph View'}
            </button>
            <button
              onClick={handleRefresh}
              className="p-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg"
            >
              <RotateCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Search and Filter */}
        <div className="flex gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search memories..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => setFilterType(null)}
              className={`px-3 py-2 rounded-lg text-sm ${
                filterType === null
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              All
            </button>
            {Object.keys(MemoryTypeColors).map(type => (
              <button
                key={type}
                onClick={() => setFilterType(type)}
                className={`px-3 py-2 rounded-lg text-sm capitalize flex items-center gap-2 ${
                  filterType === type
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                }`}
              >
                <div
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: MemoryTypeColors[type] }}
                />
                {type}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="p-4">
        <StatsPanel memories={memories} />
      </div>

      {/* Main Content */}
      <div className="flex-1 relative overflow-hidden">
        {viewMode === 'graph' ? (
          <>
            <MemoryGraph
              nodes={nodes}
              connections={connections}
              zoom={zoom}
              pan={pan}
              onNodeClick={handleNodeClick}
              selectedMemoryId={selectedMemory?.id || null}
            />

            {/* Zoom Controls */}
            <div className="absolute left-4 bottom-4 flex flex-col gap-2">
              <button
                onClick={() => handleZoom(0.1)}
                className="p-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg"
              >
                <ZoomIn className="w-5 h-5" />
              </button>
              <button
                onClick={() => handleZoom(-0.1)}
                className="p-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg"
              >
                <ZoomOut className="w-5 h-5" />
              </button>
              <span className="text-center text-sm text-gray-400">{Math.round(zoom * 100)}%</span>
            </div>

            {/* Legend */}
            <div className="absolute left-4 top-4 bg-gray-800/90 backdrop-blur rounded-lg p-3">
              <div className="text-xs text-gray-400 uppercase mb-2">Memory Types</div>
              {Object.entries(MemoryTypeColors).map(([type, color]) => (
                <div key={type} className="flex items-center gap-2 py-1">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                  <span className="text-sm text-gray-300 capitalize">{type}</span>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="p-4">
            <MemoryList
              memories={nodes.map(n => n.memory)}
              selectedId={selectedMemory?.id || null}
              onSelect={handleNodeClick}
            />
          </div>
        )}

        {/* Selected Memory Card */}
        <AnimatePresence>
          {selectedMemory && (
            <MemoryCard
              memory={selectedMemory}
              onClose={() => setSelectedMemory(null)}
            />
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default MemoryVisualization;
