import React, { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, X, Clock, Hash, Sparkles, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useRecentSearches } from '../hooks/useSessionPersistence';

interface SearchResult {
  id: string;
  type: 'page' | 'memory' | 'chat' | 'workflow' | 'command';
  title: string;
  description?: string;
  path?: string;
  action?: () => void;
  score: number;
}

// Simulated search function - in production, this would call the API
async function performSearch(query: string): Promise<SearchResult[]> {
  if (!query.trim()) return [];

  // Simulated results - replace with actual API call
  const allItems: Omit<SearchResult, 'score'>[] = [
    { id: '1', type: 'page', title: 'Dashboard', path: '/', description: 'Main control center' },
    { id: '2', type: 'page', title: 'Chat', path: '/chat', description: 'AI conversation interface' },
    { id: '3', type: 'page', title: 'Council', path: '/council', description: 'Multi-perspective deliberation' },
    { id: '4', type: 'page', title: 'Memory Explorer', path: '/memory-explorer', description: 'Browse stored memories' },
    { id: '5', type: 'page', title: 'Workflows', path: '/workflows', description: 'Automation pipelines' },
    { id: '6', type: 'page', title: 'Agents', path: '/agents', description: 'Manage AI agents' },
    { id: '7', type: 'page', title: 'GOD MODE', path: '/god-mode', description: 'Supreme command mode' },
    { id: '8', type: 'page', title: 'APEX Control', path: '/apex', description: 'Advanced pattern execution' },
    { id: '9', type: 'page', title: 'Swarm', path: '/swarm', description: 'Distributed agent swarm' },
    { id: '10', type: 'page', title: 'Settings', path: '/settings', description: 'Configure BAEL' },
    { id: '11', type: 'command', title: 'New Chat', action: () => {}, description: 'Start a new conversation' },
    { id: '12', type: 'command', title: 'Toggle Theme', action: () => document.documentElement.classList.toggle('light'), description: 'Switch between dark/light mode' },
  ];

  const lowerQuery = query.toLowerCase();
  const results = allItems
    .map(item => ({
      ...item,
      score: (
        (item.title.toLowerCase().includes(lowerQuery) ? 10 : 0) +
        (item.description?.toLowerCase().includes(lowerQuery) ? 5 : 0)
      )
    }))
    .filter(item => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 8);

  return results;
}

export function GlobalSearch() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { recentSearches, addSearch } = useRecentSearches();

  // Debounced search
  const handleSearch = useCallback(async (value: string) => {
    setQuery(value);
    if (value.trim().length < 2) {
      setResults([]);
      return;
    }

    setIsLoading(true);
    try {
      const searchResults = await performSearch(value);
      setResults(searchResults);
      setSelectedIndex(0);
    } catch (e) {
      console.error('Search failed:', e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleSelect = (result: SearchResult) => {
    addSearch(query);
    if (result.path) {
      navigate(result.path);
    } else if (result.action) {
      result.action();
    }
    setIsOpen(false);
    setQuery('');
    setResults([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(i => Math.min(i + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(i => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && results[selectedIndex]) {
      e.preventDefault();
      handleSelect(results[selectedIndex]);
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  // Open on Cmd+K
  React.useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(true);
        setTimeout(() => inputRef.current?.focus(), 100);
      }
    };
    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, []);

  const typeIcons: Record<string, React.ElementType> = {
    page: Hash,
    memory: Sparkles,
    chat: Sparkles,
    workflow: Sparkles,
    command: Sparkles,
  };

  return (
    <>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-bael-bg border border-bael-border rounded-lg text-sm text-bael-muted hover:text-bael-text hover:border-bael-primary/50 transition-colors"
      >
        <Search className="w-4 h-4" />
        <span>Search everywhere...</span>
        <kbd className="ml-2 px-1.5 py-0.5 bg-bael-border rounded text-xs">⌘K</kbd>
      </button>

      {/* Search Modal */}
      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50"
              onClick={() => setIsOpen(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: -20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -20 }}
              className="fixed left-1/2 top-[15%] -translate-x-1/2 w-full max-w-2xl bg-bael-surface border border-bael-border rounded-xl shadow-2xl z-50 overflow-hidden"
            >
              {/* Search Input */}
              <div className="flex items-center gap-3 px-4 py-4 border-b border-bael-border">
                <Search className={`w-5 h-5 ${isLoading ? 'animate-pulse text-bael-primary' : 'text-bael-muted'}`} />
                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={(e) => handleSearch(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Search pages, memories, commands..."
                  className="flex-1 bg-transparent text-bael-text text-lg placeholder:text-bael-muted outline-none"
                  autoFocus
                />
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-1.5 text-bael-muted hover:text-bael-text hover:bg-bael-border rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Results */}
              <div className="max-h-[400px] overflow-y-auto">
                {query.trim().length < 2 && recentSearches.length > 0 && (
                  <div className="p-2">
                    <p className="px-3 py-2 text-xs text-bael-muted uppercase tracking-wide">Recent Searches</p>
                    {recentSearches.slice(0, 5).map((search, i) => (
                      <button
                        key={i}
                        onClick={() => handleSearch(search)}
                        className="w-full flex items-center gap-3 px-3 py-2 text-sm text-bael-text hover:bg-bael-border/50 rounded-lg transition-colors"
                      >
                        <Clock className="w-4 h-4 text-bael-muted" />
                        {search}
                      </button>
                    ))}
                  </div>
                )}

                {results.length > 0 && (
                  <div className="p-2">
                    {results.map((result, i) => {
                      const Icon = typeIcons[result.type] || Hash;
                      return (
                        <button
                          key={result.id}
                          onClick={() => handleSelect(result)}
                          className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg transition-colors text-left ${
                            selectedIndex === i
                              ? 'bg-bael-primary/20 border-l-2 border-bael-primary'
                              : 'hover:bg-bael-border/50'
                          }`}
                        >
                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                            selectedIndex === i ? 'bg-bael-primary/20' : 'bg-bael-bg'
                          }`}>
                            <Icon className={`w-4 h-4 ${selectedIndex === i ? 'text-bael-primary' : 'text-bael-muted'}`} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-bael-text">{result.title}</p>
                            {result.description && (
                              <p className="text-xs text-bael-muted truncate">{result.description}</p>
                            )}
                          </div>
                          <ArrowRight className="w-4 h-4 text-bael-muted" />
                        </button>
                      );
                    })}
                  </div>
                )}

                {query.trim().length >= 2 && results.length === 0 && !isLoading && (
                  <div className="flex flex-col items-center justify-center py-12 text-bael-muted">
                    <Search className="w-12 h-12 mb-3 opacity-20" />
                    <p className="text-sm">No results for "{query}"</p>
                    <p className="text-xs mt-1">Try a different search term</p>
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="px-4 py-2 border-t border-bael-border bg-bael-bg/50 flex items-center gap-4 text-xs text-bael-muted">
                <span><kbd className="px-1 py-0.5 bg-bael-border rounded mx-1">↑↓</kbd> Navigate</span>
                <span><kbd className="px-1 py-0.5 bg-bael-border rounded mx-1">↵</kbd> Select</span>
                <span><kbd className="px-1 py-0.5 bg-bael-border rounded mx-1">esc</kbd> Close</span>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

export default GlobalSearch;
