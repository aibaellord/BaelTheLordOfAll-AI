import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Keyboard, X, Command, Search, MessageSquare, Home, Settings, HelpCircle } from 'lucide-react';

interface ShortcutGroup {
  title: string;
  shortcuts: Array<{
    keys: string[];
    description: string;
    icon?: React.ReactNode;
  }>;
}

const shortcutGroups: ShortcutGroup[] = [
  {
    title: 'Navigation',
    shortcuts: [
      { keys: ['⌘', 'K'], description: 'Open command palette', icon: <Search className="w-4 h-4" /> },
      { keys: ['⌘', 'H'], description: 'Go to Home/Dashboard', icon: <Home className="w-4 h-4" /> },
      { keys: ['⌘', 'J'], description: 'Open Chat', icon: <MessageSquare className="w-4 h-4" /> },
      { keys: ['⌘', ','], description: 'Open Settings', icon: <Settings className="w-4 h-4" /> },
      { keys: ['?'], description: 'Show this help', icon: <HelpCircle className="w-4 h-4" /> },
    ]
  },
  {
    title: 'Chat',
    shortcuts: [
      { keys: ['Enter'], description: 'Send message' },
      { keys: ['Shift', 'Enter'], description: 'New line in message' },
      { keys: ['⌘', '↑'], description: 'Edit last message' },
      { keys: ['Escape'], description: 'Cancel editing / Close' },
    ]
  },
  {
    title: 'General',
    shortcuts: [
      { keys: ['⌘', 'S'], description: 'Save current state' },
      { keys: ['⌘', 'R'], description: 'Refresh data' },
      { keys: ['⌘', 'B'], description: 'Toggle sidebar' },
      { keys: ['Escape'], description: 'Close modal / Cancel' },
    ]
  }
];

export function KeyboardShortcutsModal() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // '?' to show shortcuts (without modifiers)
      if (e.key === '?' && !e.metaKey && !e.ctrlKey && !e.altKey) {
        e.preventDefault();
        setIsOpen(prev => !prev);
      }
      // Escape to close
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
          onClick={() => setIsOpen(false)}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.9, opacity: 0, y: 20 }}
            className="w-full max-w-2xl bg-bael-surface border border-bael-border rounded-2xl overflow-hidden"
            onClick={e => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-bael-border">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center">
                  <Keyboard className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white">Keyboard Shortcuts</h2>
                  <p className="text-xs text-bael-muted">Quick access to BAEL features</p>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-2 text-bael-muted hover:text-white hover:bg-bael-border rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="p-4 max-h-[60vh] overflow-y-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {shortcutGroups.map((group, idx) => (
                  <div key={idx} className="space-y-2">
                    <h3 className="text-sm font-semibold text-white px-2">{group.title}</h3>
                    <div className="space-y-1">
                      {group.shortcuts.map((shortcut, sIdx) => (
                        <div
                          key={sIdx}
                          className="flex items-center justify-between p-2 rounded-lg hover:bg-bael-bg transition-colors"
                        >
                          <div className="flex items-center gap-2">
                            {shortcut.icon && (
                              <span className="text-bael-muted">{shortcut.icon}</span>
                            )}
                            <span className="text-sm text-bael-text">{shortcut.description}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            {shortcut.keys.map((key, kIdx) => (
                              <React.Fragment key={kIdx}>
                                <kbd className="min-w-[24px] px-2 py-1 text-xs font-medium bg-bael-bg border border-bael-border rounded text-bael-text text-center">
                                  {key}
                                </kbd>
                                {kIdx < shortcut.keys.length - 1 && (
                                  <span className="text-bael-muted text-xs">+</span>
                                )}
                              </React.Fragment>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Footer */}
            <div className="px-4 py-3 border-t border-bael-border bg-bael-bg/50 text-center">
              <p className="text-xs text-bael-muted">
                Press <kbd className="px-1.5 py-0.5 bg-bael-surface rounded border border-bael-border mx-1">?</kbd>
                anytime to toggle this help
              </p>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// Hook to enable global shortcuts throughout the app
export function useGlobalShortcuts() {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // ⌘+K - Open command palette (handled by CommandPalette)
      // ⌘+H - Go to Home
      if ((e.metaKey || e.ctrlKey) && e.key === 'h') {
        e.preventDefault();
        window.location.href = '/';
      }
      // ⌘+J - Open Chat
      if ((e.metaKey || e.ctrlKey) && e.key === 'j') {
        e.preventDefault();
        window.location.href = '/chat';
      }
      // ⌘+, - Open Settings
      if ((e.metaKey || e.ctrlKey) && e.key === ',') {
        e.preventDefault();
        window.location.href = '/settings';
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);
}

export default KeyboardShortcutsModal;
