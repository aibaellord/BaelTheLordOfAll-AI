import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  Plus,
  MessageSquare,
  Brain,
  Zap,
  Upload,
  Search,
  Settings,
  X,
  Sparkles,
  Workflow,
  Database,
  Terminal,
  FileText
} from 'lucide-react';

interface QuickAction {
  id: string;
  label: string;
  icon: React.ElementType;
  color: string;
  action: () => void;
  shortcut?: string;
}

export function QuickActionsFAB() {
  const [isOpen, setIsOpen] = useState(false);
  const [isVisible, setIsVisible] = useState(true);
  const navigate = useNavigate();

  const actions: QuickAction[] = [
    {
      id: 'new-chat',
      label: 'New Chat',
      icon: MessageSquare,
      color: 'from-purple-500 to-purple-600',
      action: () => navigate('/chat'),
      shortcut: '⌘J'
    },
    {
      id: 'council',
      label: 'Council',
      icon: Brain,
      color: 'from-blue-500 to-blue-600',
      action: () => navigate('/council'),
    },
    {
      id: 'workflow',
      label: 'New Workflow',
      icon: Workflow,
      color: 'from-green-500 to-green-600',
      action: () => navigate('/workflow-designer'),
    },
    {
      id: 'search-memory',
      label: 'Search Memory',
      icon: Database,
      color: 'from-amber-500 to-amber-600',
      action: () => navigate('/memory'),
    },
    {
      id: 'terminal',
      label: 'Terminal',
      icon: Terminal,
      color: 'from-gray-500 to-gray-600',
      action: () => navigate('/terminals'),
    },
    {
      id: 'upload',
      label: 'Upload File',
      icon: Upload,
      color: 'from-pink-500 to-pink-600',
      action: () => navigate('/files'),
    },
  ];

  // Hide FAB when scrolling down, show when scrolling up
  useEffect(() => {
    let lastScrollY = window.scrollY;

    const handleScroll = () => {
      const currentScrollY = window.scrollY;
      setIsVisible(currentScrollY <= lastScrollY || currentScrollY < 100);
      lastScrollY = currentScrollY;
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Close on escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  const handleActionClick = (action: QuickAction) => {
    action.action();
    setIsOpen(false);
  };

  return (
    <>
      {/* Backdrop */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/30 backdrop-blur-sm z-40"
            onClick={() => setIsOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* FAB Container */}
      <motion.div
        initial={{ y: 100, opacity: 0 }}
        animate={{
          y: isVisible ? 0 : 100,
          opacity: isVisible ? 1 : 0
        }}
        className="fixed bottom-6 right-6 z-50 flex flex-col-reverse items-end gap-3"
      >
        {/* Action Items */}
        <AnimatePresence>
          {isOpen && actions.map((action, index) => (
            <motion.button
              key={action.id}
              initial={{ opacity: 0, y: 20, scale: 0.8 }}
              animate={{
                opacity: 1,
                y: 0,
                scale: 1,
                transition: { delay: index * 0.05 }
              }}
              exit={{
                opacity: 0,
                y: 20,
                scale: 0.8,
                transition: { delay: (actions.length - index) * 0.03 }
              }}
              onClick={() => handleActionClick(action)}
              className="flex items-center gap-3 group"
            >
              {/* Label */}
              <motion.span
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0, transition: { delay: index * 0.05 + 0.1 } }}
                className="px-3 py-1.5 bg-bael-surface border border-bael-border rounded-lg text-sm text-bael-text shadow-lg whitespace-nowrap"
              >
                {action.label}
                {action.shortcut && (
                  <kbd className="ml-2 px-1.5 py-0.5 bg-bael-bg rounded text-xs text-bael-muted">
                    {action.shortcut}
                  </kbd>
                )}
              </motion.span>

              {/* Icon Button */}
              <div className={`w-12 h-12 rounded-full bg-gradient-to-br ${action.color} flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform`}>
                <action.icon className="w-5 h-5 text-white" />
              </div>
            </motion.button>
          ))}
        </AnimatePresence>

        {/* Main FAB Button */}
        <motion.button
          onClick={() => setIsOpen(!isOpen)}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className={`w-14 h-14 rounded-full bg-gradient-to-br from-bael-primary to-bael-secondary flex items-center justify-center shadow-xl hover:shadow-bael-primary/30 transition-shadow ${isOpen ? 'rotate-45' : ''}`}
          style={{ transform: isOpen ? 'rotate(45deg)' : 'rotate(0deg)', transition: 'transform 0.2s ease' }}
        >
          {isOpen ? (
            <X className="w-6 h-6 text-white" />
          ) : (
            <Plus className="w-6 h-6 text-white" />
          )}
        </motion.button>
      </motion.div>
    </>
  );
}

export default QuickActionsFAB;
