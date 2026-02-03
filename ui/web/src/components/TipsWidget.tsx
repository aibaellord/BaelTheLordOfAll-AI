import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Lightbulb,
  X,
  ChevronRight,
  ChevronLeft,
  Keyboard,
  Zap,
  Brain,
  Sparkles,
  MessageSquare,
  Target
} from 'lucide-react';

interface Tip {
  id: string;
  icon: React.ElementType;
  title: string;
  description: string;
  shortcut?: string;
  category: 'navigation' | 'productivity' | 'features' | 'power';
}

const tips: Tip[] = [
  {
    id: 'cmd-k',
    icon: Keyboard,
    title: 'Quick Command Palette',
    description: 'Press ⌘K to instantly search anything - pages, commands, memories, and more.',
    shortcut: '⌘K',
    category: 'navigation'
  },
  {
    id: 'god-mode',
    icon: Zap,
    title: 'GOD MODE',
    description: 'Access the supreme command interface for unrestricted AI capabilities.',
    category: 'power'
  },
  {
    id: 'council',
    icon: Brain,
    title: 'Council Deliberation',
    description: 'Get multiple AI perspectives on complex problems with the Council feature.',
    category: 'features'
  },
  {
    id: 'quick-settings',
    icon: Sparkles,
    title: 'Quick Settings',
    description: 'Press ⌘⇧S to open quick settings without leaving your current page.',
    shortcut: '⌘⇧S',
    category: 'productivity'
  },
  {
    id: 'chat-draft',
    icon: MessageSquare,
    title: 'Auto-saved Drafts',
    description: 'Your chat messages are automatically saved as you type. Never lose your thoughts!',
    category: 'productivity'
  },
  {
    id: 'favorites',
    icon: Target,
    title: 'Pin Favorites',
    description: 'Star frequently used pages to access them quickly from the sidebar.',
    category: 'navigation'
  },
  {
    id: 'shortcuts-help',
    icon: Keyboard,
    title: 'Keyboard Shortcuts',
    description: 'Press ? at any time to view all available keyboard shortcuts.',
    shortcut: '?',
    category: 'navigation'
  },
];

export function TipsWidget() {
  const [isVisible, setIsVisible] = useState(false);
  const [currentTipIndex, setCurrentTipIndex] = useState(0);
  const [dismissedTips, setDismissedTips] = useState<Set<string>>(new Set());

  // Load dismissed tips from localStorage
  useEffect(() => {
    const stored = localStorage.getItem('bael-dismissed-tips');
    if (stored) {
      setDismissedTips(new Set(JSON.parse(stored)));
    }

    // Show tip after a delay
    const timer = setTimeout(() => {
      const lastShown = localStorage.getItem('bael-last-tip-shown');
      const now = Date.now();
      // Show tip if not shown in last hour
      if (!lastShown || now - parseInt(lastShown) > 60 * 60 * 1000) {
        setIsVisible(true);
        localStorage.setItem('bael-last-tip-shown', now.toString());
      }
    }, 10000); // Show after 10 seconds

    return () => clearTimeout(timer);
  }, []);

  const availableTips = tips.filter(tip => !dismissedTips.has(tip.id));
  const currentTip = availableTips[currentTipIndex % availableTips.length];

  const dismissTip = () => {
    if (currentTip) {
      const newDismissed = new Set(dismissedTips).add(currentTip.id);
      setDismissedTips(newDismissed);
      localStorage.setItem('bael-dismissed-tips', JSON.stringify([...newDismissed]));
    }
    setIsVisible(false);
  };

  const nextTip = () => {
    setCurrentTipIndex(i => (i + 1) % availableTips.length);
  };

  const prevTip = () => {
    setCurrentTipIndex(i => (i - 1 + availableTips.length) % availableTips.length);
  };

  if (!currentTip || availableTips.length === 0) return null;

  const Icon = currentTip.icon;

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.95 }}
          className="fixed bottom-20 right-4 z-40 w-80"
        >
          <div className="bg-gradient-to-br from-bael-surface to-bael-bg border border-bael-border rounded-xl shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 bg-bael-primary/10 border-b border-bael-border">
              <div className="flex items-center gap-2">
                <Lightbulb className="w-4 h-4 text-amber-400" />
                <span className="text-sm font-medium text-bael-text">Quick Tip</span>
              </div>
              <button
                onClick={dismissTip}
                className="p-1 text-bael-muted hover:text-bael-text hover:bg-bael-border rounded-lg transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Content */}
            <div className="p-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-bael-primary/20 flex items-center justify-center">
                  <Icon className="w-5 h-5 text-bael-primary" />
                </div>
                <div className="flex-1">
                  <h4 className="font-medium text-bael-text">{currentTip.title}</h4>
                  <p className="text-sm text-bael-muted mt-1">{currentTip.description}</p>
                  {currentTip.shortcut && (
                    <kbd className="inline-block mt-2 px-2 py-1 bg-bael-bg border border-bael-border rounded text-xs font-mono text-bael-text">
                      {currentTip.shortcut}
                    </kbd>
                  )}
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between px-4 py-2 border-t border-bael-border bg-bael-bg/50">
              <div className="flex items-center gap-2">
                <button
                  onClick={prevTip}
                  className="p-1 text-bael-muted hover:text-bael-text hover:bg-bael-border rounded transition-colors"
                  title="Previous tip"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-xs text-bael-muted">
                  {currentTipIndex + 1} / {availableTips.length}
                </span>
                <button
                  onClick={nextTip}
                  className="p-1 text-bael-muted hover:text-bael-text hover:bg-bael-border rounded transition-colors"
                  title="Next tip"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
              <button
                onClick={dismissTip}
                className="text-xs text-bael-muted hover:text-bael-text"
              >
                Got it, don't show again
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default TipsWidget;
