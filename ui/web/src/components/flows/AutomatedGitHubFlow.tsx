/**
 * BAEL - Automated GitHub Flow Component
 * 
 * This React component provides an automated flow when a user provides a GitHub link:
 * 1. Analyzes the repository automatically
 * 2. Shows quality assessment
 * 3. Displays better alternatives if they exist
 * 4. Offers one-click integration options
 * 5. Can auto-generate MCP tools
 * 6. Shows improvement suggestions
 * 
 * This is the ultimate comfort feature for discovering and integrating tools.
 */

import React, { useState, useEffect, useCallback } from 'react';

// Types
interface RepoAnalysis {
  url: string;
  name: string;
  owner: string;
  description: string;
  qualityScore: number;
  stars: number;
  forks: number;
  languages: string[];
  frameworks: string[];
  capabilities: string[];
  lastUpdated: string;
  mcpPossible: boolean;
  autoSetupPossible: boolean;
}

interface AlternativeRepo {
  name: string;
  url: string;
  score: number;
  reason: string;
  improvement: string;
}

interface ImprovementSuggestion {
  id: string;
  title: string;
  description: string;
  impact: 'low' | 'medium' | 'high';
  automated: boolean;
}

interface SetupAction {
  id: string;
  title: string;
  command: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  priority: number;
}

interface GitHubFlowState {
  inputUrl: string;
  isAnalyzing: boolean;
  analysis: RepoAnalysis | null;
  alternatives: AlternativeRepo[];
  improvements: ImprovementSuggestion[];
  setupActions: SetupAction[];
  isSettingUp: boolean;
  error: string | null;
}

// Mock API functions (would connect to backend in production)
const analyzeGitHubRepo = async (url: string): Promise<{
  analysis: RepoAnalysis;
  alternatives: AlternativeRepo[];
  improvements: ImprovementSuggestion[];
  setupActions: SetupAction[];
}> => {
  // Simulate API call
  await new Promise(resolve => setTimeout(resolve, 1500));
  
  const repoName = url.split('/').pop()?.replace('.git', '') || 'unknown';
  const owner = url.split('/').slice(-2, -1)[0] || 'unknown';
  
  // Mock analysis
  const analysis: RepoAnalysis = {
    url,
    name: repoName,
    owner,
    description: `Repository ${repoName} by ${owner}`,
    qualityScore: Math.random() * 30 + 60, // 60-90
    stars: Math.floor(Math.random() * 10000),
    forks: Math.floor(Math.random() * 1000),
    languages: ['Python', 'TypeScript'],
    frameworks: ['FastAPI', 'React'],
    capabilities: ['AI Agents', 'Automation', 'API Integration'],
    lastUpdated: new Date().toISOString(),
    mcpPossible: true,
    autoSetupPossible: true
  };
  
  // Mock alternatives
  const alternatives: AlternativeRepo[] = [
    {
      name: 'bael-enhanced',
      url: 'https://github.com/bael/enhanced-version',
      score: analysis.qualityScore + 15,
      reason: 'Includes psychological amplification',
      improvement: '+15 quality score'
    },
    {
      name: 'superior-alternative',
      url: 'https://github.com/example/superior',
      score: analysis.qualityScore + 10,
      reason: 'Better architecture',
      improvement: '+10 quality score'
    }
  ];
  
  // Mock improvements
  const improvements: ImprovementSuggestion[] = [
    {
      id: 'imp_1',
      title: 'Add Bael Integration',
      description: 'Integrate with Bael orchestration for enhanced capabilities',
      impact: 'high',
      automated: true
    },
    {
      id: 'imp_2',
      title: 'Enable Parallel Universe Execution',
      description: 'Use OmniscientTaskWeaver for multi-path exploration',
      impact: 'high',
      automated: true
    },
    {
      id: 'imp_3',
      title: 'Add Sacred Geometry Optimization',
      description: 'Apply golden ratio to decision weights',
      impact: 'medium',
      automated: true
    },
    {
      id: 'imp_4',
      title: 'Generate MCP Tools',
      description: 'Auto-generate MCP server for this repository',
      impact: 'high',
      automated: true
    }
  ];
  
  // Mock setup actions
  const setupActions: SetupAction[] = [
    {
      id: 'setup_1',
      title: `Clone ${repoName}`,
      command: `git clone ${url}`,
      status: 'pending',
      priority: 10
    },
    {
      id: 'setup_2',
      title: 'Install Dependencies',
      command: `cd ${repoName} && pip install -r requirements.txt`,
      status: 'pending',
      priority: 9
    },
    {
      id: 'setup_3',
      title: 'Configure for Bael',
      command: 'bael integrate',
      status: 'pending',
      priority: 8
    },
    {
      id: 'setup_4',
      title: 'Generate MCP Server',
      command: 'bael mcp generate',
      status: 'pending',
      priority: 7
    }
  ];
  
  return { analysis, alternatives, improvements, setupActions };
};

const executeSetup = async (
  actions: SetupAction[],
  onProgress: (actionId: string, status: SetupAction['status']) => void
): Promise<void> => {
  for (const action of actions.sort((a, b) => b.priority - a.priority)) {
    onProgress(action.id, 'running');
    await new Promise(resolve => setTimeout(resolve, 800));
    onProgress(action.id, 'completed');
  }
};

// Utility Components
const QualityBadge: React.FC<{ score: number }> = ({ score }) => {
  const getColor = () => {
    if (score >= 85) return 'bg-green-500';
    if (score >= 70) return 'bg-yellow-500';
    if (score >= 50) return 'bg-orange-500';
    return 'bg-red-500';
  };
  
  const getLabel = () => {
    if (score >= 85) return 'Excellent';
    if (score >= 70) return 'Good';
    if (score >= 50) return 'Average';
    return 'Needs Improvement';
  };
  
  return (
    <span className={`px-2 py-1 rounded-full text-white text-sm ${getColor()}`}>
      {score.toFixed(0)} - {getLabel()}
    </span>
  );
};

const ImpactBadge: React.FC<{ impact: 'low' | 'medium' | 'high' }> = ({ impact }) => {
  const colors = {
    low: 'bg-gray-200 text-gray-700',
    medium: 'bg-blue-200 text-blue-700',
    high: 'bg-purple-200 text-purple-700'
  };
  
  return (
    <span className={`px-2 py-1 rounded text-xs ${colors[impact]}`}>
      {impact.toUpperCase()} IMPACT
    </span>
  );
};

const StatusBadge: React.FC<{ status: SetupAction['status'] }> = ({ status }) => {
  const styles = {
    pending: 'bg-gray-200 text-gray-600',
    running: 'bg-blue-200 text-blue-600 animate-pulse',
    completed: 'bg-green-200 text-green-600',
    failed: 'bg-red-200 text-red-600'
  };
  
  const icons = {
    pending: '○',
    running: '◐',
    completed: '✓',
    failed: '✗'
  };
  
  return (
    <span className={`px-2 py-1 rounded text-sm flex items-center gap-1 ${styles[status]}`}>
      <span>{icons[status]}</span>
      {status}
    </span>
  );
};

// Main Component
export const AutomatedGitHubFlow: React.FC = () => {
  const [state, setState] = useState<GitHubFlowState>({
    inputUrl: '',
    isAnalyzing: false,
    analysis: null,
    alternatives: [],
    improvements: [],
    setupActions: [],
    isSettingUp: false,
    error: null
  });
  
  // Detect GitHub URL in input
  const isValidGitHubUrl = (url: string): boolean => {
    return /^https?:\/\/(www\.)?github\.com\/[\w-]+\/[\w-]+/.test(url);
  };
  
  // Handle URL input
  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setState(prev => ({ ...prev, inputUrl: e.target.value, error: null }));
  };
  
  // Trigger analysis
  const handleAnalyze = async () => {
    if (!isValidGitHubUrl(state.inputUrl)) {
      setState(prev => ({ ...prev, error: 'Please enter a valid GitHub repository URL' }));
      return;
    }
    
    setState(prev => ({ ...prev, isAnalyzing: true, error: null }));
    
    try {
      const result = await analyzeGitHubRepo(state.inputUrl);
      setState(prev => ({
        ...prev,
        isAnalyzing: false,
        analysis: result.analysis,
        alternatives: result.alternatives,
        improvements: result.improvements,
        setupActions: result.setupActions
      }));
    } catch (err) {
      setState(prev => ({
        ...prev,
        isAnalyzing: false,
        error: 'Failed to analyze repository'
      }));
    }
  };
  
  // One-click setup
  const handleOneClickSetup = async () => {
    setState(prev => ({ ...prev, isSettingUp: true }));
    
    const updateStatus = (actionId: string, status: SetupAction['status']) => {
      setState(prev => ({
        ...prev,
        setupActions: prev.setupActions.map(a =>
          a.id === actionId ? { ...a, status } : a
        )
      }));
    };
    
    await executeSetup(state.setupActions, updateStatus);
    setState(prev => ({ ...prev, isSettingUp: false }));
  };
  
  // Auto-analyze on valid URL paste
  useEffect(() => {
    if (isValidGitHubUrl(state.inputUrl) && !state.analysis && !state.isAnalyzing) {
      const timer = setTimeout(handleAnalyze, 500);
      return () => clearTimeout(timer);
    }
  }, [state.inputUrl]);
  
  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          🔮 Automated GitHub Analysis
        </h1>
        <p className="text-gray-600">
          Paste any GitHub link - we'll analyze it, find better alternatives, and set it up for you
        </p>
      </div>
      
      {/* Input Section */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex gap-4">
          <input
            type="text"
            value={state.inputUrl}
            onChange={handleUrlChange}
            placeholder="Paste GitHub repository URL..."
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          />
          <button
            onClick={handleAnalyze}
            disabled={state.isAnalyzing || !state.inputUrl}
            className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {state.isAnalyzing ? 'Analyzing...' : 'Analyze'}
          </button>
        </div>
        
        {state.error && (
          <p className="mt-2 text-red-500 text-sm">{state.error}</p>
        )}
      </div>
      
      {/* Loading State */}
      {state.isAnalyzing && (
        <div className="bg-white rounded-lg shadow-lg p-8 text-center">
          <div className="animate-spin w-12 h-12 border-4 border-purple-600 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-gray-600">
            Analyzing repository, finding alternatives, generating setup...
          </p>
        </div>
      )}
      
      {/* Analysis Results */}
      {state.analysis && !state.isAnalyzing && (
        <>
          {/* Repository Info */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  {state.analysis.owner}/{state.analysis.name}
                </h2>
                <p className="text-gray-600">{state.analysis.description}</p>
              </div>
              <QualityBadge score={state.analysis.qualityScore} />
            </div>
            
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="text-center p-3 bg-gray-50 rounded">
                <div className="text-2xl font-bold text-gray-900">
                  {state.analysis.stars.toLocaleString()}
                </div>
                <div className="text-gray-500 text-sm">Stars</div>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded">
                <div className="text-2xl font-bold text-gray-900">
                  {state.analysis.forks.toLocaleString()}
                </div>
                <div className="text-gray-500 text-sm">Forks</div>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded">
                <div className="text-2xl font-bold text-gray-900">
                  {state.analysis.mcpPossible ? '✓' : '✗'}
                </div>
                <div className="text-gray-500 text-sm">MCP Ready</div>
              </div>
            </div>
            
            <div className="flex flex-wrap gap-2 mb-4">
              {state.analysis.languages.map(lang => (
                <span key={lang} className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-sm">
                  {lang}
                </span>
              ))}
              {state.analysis.frameworks.map(fw => (
                <span key={fw} className="px-2 py-1 bg-green-100 text-green-700 rounded text-sm">
                  {fw}
                </span>
              ))}
            </div>
            
            <div className="flex flex-wrap gap-2">
              {state.analysis.capabilities.map(cap => (
                <span key={cap} className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-sm">
                  {cap}
                </span>
              ))}
            </div>
          </div>
          
          {/* Better Alternatives */}
          {state.alternatives.length > 0 && (
            <div className="bg-gradient-to-r from-amber-50 to-orange-50 rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                ⚡ Better Alternatives Found
              </h2>
              <div className="space-y-3">
                {state.alternatives.map((alt, idx) => (
                  <div key={idx} className="bg-white rounded-lg p-4 flex justify-between items-center">
                    <div>
                      <div className="font-semibold text-gray-900">{alt.name}</div>
                      <div className="text-gray-600 text-sm">{alt.reason}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-green-600 font-bold">{alt.improvement}</div>
                      <a
                        href={alt.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-500 text-sm hover:underline"
                      >
                        View →
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Improvement Suggestions */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">
              🚀 Enhancement Opportunities
            </h2>
            <div className="space-y-3">
              {state.improvements.map(imp => (
                <div key={imp.id} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold">{imp.title}</span>
                      <ImpactBadge impact={imp.impact} />
                      {imp.automated && (
                        <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">
                          AUTO
                        </span>
                      )}
                    </div>
                    <div className="text-gray-600 text-sm">{imp.description}</div>
                  </div>
                  <button className="px-3 py-1 bg-purple-100 text-purple-700 rounded hover:bg-purple-200 transition-colors">
                    Apply
                  </button>
                </div>
              ))}
            </div>
          </div>
          
          {/* One-Click Setup */}
          <div className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-lg shadow-lg p-6 text-white">
            <div className="flex justify-between items-center mb-4">
              <div>
                <h2 className="text-xl font-bold">⚡ One-Click Setup</h2>
                <p className="opacity-90">
                  Automatically clone, install, configure, and integrate
                </p>
              </div>
              <button
                onClick={handleOneClickSetup}
                disabled={state.isSettingUp}
                className="px-6 py-3 bg-white text-purple-600 rounded-lg font-bold hover:bg-gray-100 disabled:opacity-50 transition-colors"
              >
                {state.isSettingUp ? 'Setting Up...' : 'Set Up Now'}
              </button>
            </div>
            
            <div className="space-y-2">
              {state.setupActions.map(action => (
                <div key={action.id} className="flex justify-between items-center p-2 bg-white/10 rounded">
                  <span>{action.title}</span>
                  <StatusBadge status={action.status} />
                </div>
              ))}
            </div>
          </div>
        </>
      )}
      
      {/* Empty State */}
      {!state.analysis && !state.isAnalyzing && !state.inputUrl && (
        <div className="bg-gray-50 rounded-lg p-12 text-center">
          <div className="text-6xl mb-4">🔍</div>
          <h3 className="text-xl font-bold text-gray-700 mb-2">
            Paste a GitHub Link to Get Started
          </h3>
          <p className="text-gray-500">
            We'll automatically analyze it, find better alternatives, and help you set it up
          </p>
        </div>
      )}
    </div>
  );
};

export default AutomatedGitHubFlow;
