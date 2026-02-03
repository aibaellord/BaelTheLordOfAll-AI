/**
 * BAEL God-Mode Dashboard
 * ========================
 *
 * The ultimate unified control panel for BAEL.
 * One interface to rule all 200+ capabilities.
 */

import React, { useState, useEffect, useCallback } from 'react';

// Types
interface CapabilityStatus {
  name: string;
  domain: string;
  available: boolean;
  active: boolean;
  health: number;
  invocations: number;
}

interface SingularityStatus {
  mode: string;
  uptime_seconds: number;
  total_invocations: number;
  capabilities_loaded: number;
  capabilities_available: number;
  active_tasks: number;
  domains: Record<string, number>;
}

interface DomainCapabilities {
  [domain: string]: string[];
}

type SingularityMode = 'dormant' | 'awakened' | 'empowered' | 'transcendent' | 'autonomous' | 'godmode';

// API client
const api = {
  baseUrl: '/api/singularity',

  async awaken(mode: SingularityMode = 'transcendent') {
    const res = await fetch(`${this.baseUrl}/awaken`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode }),
    });
    return res.json();
  },

  async getStatus() {
    const res = await fetch(`${this.baseUrl}/status`);
    return res.json();
  },

  async getCapabilities() {
    const res = await fetch(`${this.baseUrl}/capabilities`);
    return res.json();
  },

  async think(query: string, depth: string = 'deep') {
    const res = await fetch(`${this.baseUrl}/think`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, depth }),
    });
    return res.json();
  },

  async collectiveSolve(problem: string, strategy: string, agents: number) {
    const res = await fetch(`${this.baseUrl}/collective`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ problem, strategy, agents }),
    });
    return res.json();
  },

  async reason(query: string, engines?: string[]) {
    const res = await fetch(`${this.baseUrl}/reason`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, engines }),
    });
    return res.json();
  },

  async create(request: string, mode: string = 'creative') {
    const res = await fetch(`${this.baseUrl}/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request, mode }),
    });
    return res.json();
  },

  async maximumPotential(goal: string) {
    const res = await fetch(`${this.baseUrl}/maximum`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ goal }),
    });
    return res.json();
  },

  async invoke(capability: string, method: string, args: Record<string, any>) {
    const res = await fetch(`${this.baseUrl}/invoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ capability, method, arguments: args }),
    });
    return res.json();
  },

  async setMode(mode: SingularityMode) {
    const res = await fetch(`${this.baseUrl}/mode?mode=${mode}`, {
      method: 'POST',
    });
    return res.json();
  },

  async evolve() {
    const res = await fetch(`${this.baseUrl}/evolve`, { method: 'POST' });
    return res.json();
  },

  async introspect() {
    const res = await fetch(`${this.baseUrl}/introspect`);
    return res.json();
  },
};

// Components
const ModeIcon: Record<string, string> = {
  dormant: '😴',
  awakened: '👁️',
  empowered: '💪',
  transcendent: '🌟',
  autonomous: '🤖',
  godmode: '⚡',
};

const DomainIcon: Record<string, string> = {
  orchestration: '🎯',
  collective: '🐝',
  reasoning: '🧠',
  memory: '💾',
  cognition: '💭',
  perception: '👁️',
  learning: '📚',
  resources: '⚡',
  knowledge: '📖',
  tools: '🔧',
};

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const colors: Record<string, string> = {
    dormant: 'bg-gray-500',
    awakened: 'bg-blue-500',
    empowered: 'bg-yellow-500',
    transcendent: 'bg-purple-500',
    autonomous: 'bg-green-500',
    godmode: 'bg-red-500',
  };

  return (
    <span className={`px-3 py-1 rounded-full text-white text-sm font-bold ${colors[status] || 'bg-gray-500'}`}>
      {ModeIcon[status]} {status.toUpperCase()}
    </span>
  );
};

const CapabilityCard: React.FC<{
  name: string;
  domain: string;
  onClick: () => void;
}> = ({ name, domain, onClick }) => (
  <button
    onClick={onClick}
    className="p-3 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors text-left"
  >
    <div className="flex items-center gap-2">
      <span>{DomainIcon[domain] || '🔮'}</span>
      <span className="text-sm font-mono text-gray-200">{name}</span>
    </div>
  </button>
);

const CommandInput: React.FC<{
  onExecute: (command: string) => void;
  loading: boolean;
}> = ({ onExecute, loading }) => {
  const [command, setCommand] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (command.trim()) {
      onExecute(command);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        type="text"
        value={command}
        onChange={(e) => setCommand(e.target.value)}
        placeholder="Enter command or query..."
        className="flex-1 px-4 py-2 bg-gray-800 rounded-lg border border-gray-700 text-white focus:outline-none focus:border-purple-500"
        disabled={loading}
      />
      <button
        type="submit"
        disabled={loading}
        className="px-6 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg text-white font-bold disabled:opacity-50"
      >
        {loading ? '⏳' : '▶️'}
      </button>
    </form>
  );
};

const ResultPanel: React.FC<{ result: any }> = ({ result }) => {
  if (!result) return null;

  return (
    <div className="bg-gray-800 rounded-lg p-4 overflow-auto max-h-96">
      <pre className="text-sm text-gray-300 whitespace-pre-wrap">
        {JSON.stringify(result, null, 2)}
      </pre>
    </div>
  );
};

// Main Dashboard Component
const GodModeDashboard: React.FC = () => {
  const [status, setStatus] = useState<SingularityStatus | null>(null);
  const [capabilities, setCapabilities] = useState<DomainCapabilities>({});
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);
  const [selectedCapability, setSelectedCapability] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<SingularityMode>('transcendent');
  const [activeTab, setActiveTab] = useState<'command' | 'capabilities' | 'invoke'>('command');
  const [invokeMethod, setInvokeMethod] = useState('process');
  const [invokeArgs, setInvokeArgs] = useState('{}');

  // Initialize
  const initialize = useCallback(async () => {
    try {
      setLoading(true);
      const awakenRes = await api.awaken(mode);
      if (awakenRes.success) {
        setStatus(awakenRes.data);
      }

      const capsRes = await api.getCapabilities();
      if (capsRes.success) {
        setCapabilities(capsRes.data);
      }

      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [mode]);

  // Refresh status
  const refreshStatus = useCallback(async () => {
    try {
      const res = await api.getStatus();
      if (res.success) {
        setStatus(res.data);
        setMode(res.mode as SingularityMode);
      }
    } catch (e) {
      console.error('Status refresh failed:', e);
    }
  }, []);

  useEffect(() => {
    initialize();
    const interval = setInterval(refreshStatus, 5000);
    return () => clearInterval(interval);
  }, [initialize, refreshStatus]);

  // Command handlers
  const executeCommand = async (command: string) => {
    setLoading(true);
    try {
      const lowerCmd = command.toLowerCase();

      // Parse command type
      if (lowerCmd.startsWith('/think ')) {
        const query = command.slice(7);
        const res = await api.think(query);
        setResult(res);
      } else if (lowerCmd.startsWith('/create ')) {
        const request = command.slice(8);
        const res = await api.create(request);
        setResult(res);
      } else if (lowerCmd.startsWith('/solve ')) {
        const problem = command.slice(7);
        const res = await api.collectiveSolve(problem, 'hybrid', 10);
        setResult(res);
      } else if (lowerCmd.startsWith('/reason ')) {
        const query = command.slice(8);
        const res = await api.reason(query);
        setResult(res);
      } else if (lowerCmd.startsWith('/maximum ')) {
        const goal = command.slice(9);
        const res = await api.maximumPotential(goal);
        setResult(res);
      } else if (lowerCmd === '/evolve') {
        const res = await api.evolve();
        setResult(res);
      } else if (lowerCmd === '/introspect') {
        const res = await api.introspect();
        setResult(res);
      } else if (lowerCmd.startsWith('/mode ')) {
        const newMode = command.slice(6) as SingularityMode;
        const res = await api.setMode(newMode);
        setResult(res);
        if (res.success) {
          setMode(newMode);
          setStatus(res.data);
        }
      } else {
        // Default to think
        const res = await api.think(command);
        setResult(res);
      }

      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const invokeCapability = async () => {
    if (!selectedCapability) return;

    setLoading(true);
    try {
      const args = JSON.parse(invokeArgs);
      const res = await api.invoke(selectedCapability, invokeMethod, args);
      setResult(res);
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gradient-to-r from-purple-900 via-red-900 to-purple-900 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold flex items-center gap-3">
                <span className="text-4xl">⚡</span>
                BAEL GOD-MODE
                <span className="text-4xl">⚡</span>
              </h1>
              <p className="text-purple-200 mt-1">Unified Control of 200+ Capabilities</p>
            </div>
            <div className="flex items-center gap-4">
              {status && <StatusBadge status={status.mode} />}
              <button
                onClick={initialize}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg"
                disabled={loading}
              >
                🔄 Refresh
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Stats Bar */}
      {status && (
        <div className="bg-gray-800 border-b border-gray-700">
          <div className="max-w-7xl mx-auto py-4 px-6 grid grid-cols-5 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-400">{status.capabilities_loaded}</div>
              <div className="text-sm text-gray-400">Loaded</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-400">{status.capabilities_available}</div>
              <div className="text-sm text-gray-400">Available</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-400">{status.total_invocations}</div>
              <div className="text-sm text-gray-400">Invocations</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-400">{Math.round(status.uptime_seconds / 60)}m</div>
              <div className="text-sm text-gray-400">Uptime</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-400">{status.active_tasks}</div>
              <div className="text-sm text-gray-400">Active Tasks</div>
            </div>
          </div>
        </div>
      )}

      {/* Mode Selector */}
      <div className="bg-gray-850 border-b border-gray-700 p-4">
        <div className="max-w-7xl mx-auto flex items-center gap-4">
          <span className="text-gray-400">Mode:</span>
          {(['dormant', 'awakened', 'empowered', 'transcendent', 'autonomous', 'godmode'] as SingularityMode[]).map((m) => (
            <button
              key={m}
              onClick={() => executeCommand(`/mode ${m}`)}
              className={`px-3 py-1 rounded-lg transition-colors ${
                mode === m
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {ModeIcon[m]} {m}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto p-6">
        {/* Tab Navigation */}
        <div className="flex gap-4 mb-6">
          {(['command', 'capabilities', 'invoke'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-6 py-2 rounded-lg font-bold ${
                activeTab === tab
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {tab === 'command' && '💬 Command'}
              {tab === 'capabilities' && '🔮 Capabilities'}
              {tab === 'invoke' && '⚙️ Direct Invoke'}
            </button>
          ))}
        </div>

        {error && (
          <div className="bg-red-900/50 border border-red-500 rounded-lg p-4 mb-6">
            <span className="text-red-400">⚠️ {error}</span>
          </div>
        )}

        {/* Command Tab */}
        {activeTab === 'command' && (
          <div className="space-y-6">
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-xl font-bold mb-4">🎮 Command Center</h2>
              <CommandInput onExecute={executeCommand} loading={loading} />

              <div className="mt-4 text-sm text-gray-400">
                <p className="mb-2">Available commands:</p>
                <ul className="grid grid-cols-2 gap-2">
                  <li><code>/think [query]</code> - Deep thinking</li>
                  <li><code>/create [request]</code> - Creative generation</li>
                  <li><code>/solve [problem]</code> - Collective solving</li>
                  <li><code>/reason [query]</code> - Multi-engine reasoning</li>
                  <li><code>/maximum [goal]</code> - Maximum potential</li>
                  <li><code>/evolve</code> - Trigger evolution</li>
                  <li><code>/introspect</code> - Deep introspection</li>
                  <li><code>/mode [mode]</code> - Change mode</li>
                </ul>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-4 gap-4">
              <button
                onClick={() => executeCommand('/maximum Build the most advanced AI system')}
                className="p-4 bg-gradient-to-br from-red-600 to-purple-600 rounded-lg hover:opacity-90"
              >
                <div className="text-2xl mb-2">🔥</div>
                <div className="font-bold">Maximum Power</div>
              </button>
              <button
                onClick={() => executeCommand('/evolve')}
                className="p-4 bg-gradient-to-br from-green-600 to-teal-600 rounded-lg hover:opacity-90"
              >
                <div className="text-2xl mb-2">🧬</div>
                <div className="font-bold">Evolve</div>
              </button>
              <button
                onClick={() => executeCommand('/introspect')}
                className="p-4 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg hover:opacity-90"
              >
                <div className="text-2xl mb-2">🔍</div>
                <div className="font-bold">Introspect</div>
              </button>
              <button
                onClick={() => executeCommand('/solve How to achieve AGI?')}
                className="p-4 bg-gradient-to-br from-yellow-600 to-orange-600 rounded-lg hover:opacity-90"
              >
                <div className="text-2xl mb-2">🐝</div>
                <div className="font-bold">Collective Solve</div>
              </button>
            </div>

            <ResultPanel result={result} />
          </div>
        )}

        {/* Capabilities Tab */}
        {activeTab === 'capabilities' && (
          <div className="grid grid-cols-4 gap-6">
            {/* Domain List */}
            <div className="bg-gray-800 rounded-lg p-4">
              <h3 className="text-lg font-bold mb-4">📁 Domains</h3>
              <div className="space-y-2">
                {Object.keys(capabilities).map((domain) => (
                  <button
                    key={domain}
                    onClick={() => setSelectedDomain(domain)}
                    className={`w-full p-3 rounded-lg text-left flex items-center justify-between ${
                      selectedDomain === domain
                        ? 'bg-purple-600'
                        : 'bg-gray-700 hover:bg-gray-600'
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <span>{DomainIcon[domain] || '🔮'}</span>
                      <span className="capitalize">{domain}</span>
                    </span>
                    <span className="text-sm text-gray-400">
                      {capabilities[domain]?.length || 0}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Capability List */}
            <div className="col-span-3 bg-gray-800 rounded-lg p-4">
              <h3 className="text-lg font-bold mb-4">
                {selectedDomain ? (
                  <span className="flex items-center gap-2">
                    {DomainIcon[selectedDomain] || '🔮'}
                    <span className="capitalize">{selectedDomain}</span> Capabilities
                  </span>
                ) : (
                  'Select a domain'
                )}
              </h3>

              {selectedDomain && capabilities[selectedDomain] && (
                <div className="grid grid-cols-3 gap-3">
                  {capabilities[selectedDomain].map((cap) => (
                    <CapabilityCard
                      key={cap}
                      name={cap}
                      domain={selectedDomain}
                      onClick={() => {
                        setSelectedCapability(cap);
                        setActiveTab('invoke');
                      }}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Invoke Tab */}
        {activeTab === 'invoke' && (
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4">⚙️ Direct Capability Invoke</h2>

            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-2">Capability</label>
                  <select
                    value={selectedCapability || ''}
                    onChange={(e) => setSelectedCapability(e.target.value)}
                    className="w-full px-4 py-2 bg-gray-700 rounded-lg text-white"
                  >
                    <option value="">Select capability...</option>
                    {Object.entries(capabilities).map(([domain, caps]) =>
                      caps.map((cap) => (
                        <option key={cap} value={cap}>
                          {DomainIcon[domain]} {cap}
                        </option>
                      ))
                    )}
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-2">Method</label>
                  <input
                    type="text"
                    value={invokeMethod}
                    onChange={(e) => setInvokeMethod(e.target.value)}
                    className="w-full px-4 py-2 bg-gray-700 rounded-lg text-white"
                    placeholder="process"
                  />
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-2">Arguments (JSON)</label>
                  <textarea
                    value={invokeArgs}
                    onChange={(e) => setInvokeArgs(e.target.value)}
                    className="w-full px-4 py-2 bg-gray-700 rounded-lg text-white font-mono text-sm h-32"
                    placeholder="{}"
                  />
                </div>

                <button
                  onClick={invokeCapability}
                  disabled={loading || !selectedCapability}
                  className="w-full px-6 py-3 bg-purple-600 hover:bg-purple-700 rounded-lg font-bold disabled:opacity-50"
                >
                  {loading ? '⏳ Executing...' : '▶️ Execute'}
                </button>
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-2">Result</label>
                <ResultPanel result={result} />
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-gray-800 border-t border-gray-700 p-4 mt-12">
        <div className="max-w-7xl mx-auto text-center text-sm text-gray-500">
          <p>🔥 BAEL - The Ultimate AI Agent Framework 🔥</p>
          <p>200+ Capabilities • Unified Control • Maximum Potential</p>
        </div>
      </footer>
    </div>
  );
};

export default GodModeDashboard;
