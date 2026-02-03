import React, { createContext, useContext, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

interface ProgressTask {
  id: string;
  label: string;
  status: 'pending' | 'running' | 'success' | 'error';
  progress?: number; // 0-100
  message?: string;
}

interface ProgressContextType {
  tasks: ProgressTask[];
  startTask: (id: string, label: string) => void;
  updateTask: (id: string, updates: Partial<ProgressTask>) => void;
  completeTask: (id: string, success?: boolean, message?: string) => void;
  removeTask: (id: string) => void;
  clearAll: () => void;
}

const ProgressContext = createContext<ProgressContextType | null>(null);

export function useProgress() {
  const context = useContext(ProgressContext);
  if (!context) {
    throw new Error('useProgress must be used within ProgressProvider');
  }
  return context;
}

export function ProgressProvider({ children }: { children: React.ReactNode }) {
  const [tasks, setTasks] = useState<ProgressTask[]>([]);

  const startTask = useCallback((id: string, label: string) => {
    setTasks(prev => [...prev.filter(t => t.id !== id), { id, label, status: 'running' }]);
  }, []);

  const updateTask = useCallback((id: string, updates: Partial<ProgressTask>) => {
    setTasks(prev => prev.map(t => t.id === id ? { ...t, ...updates } : t));
  }, []);

  const completeTask = useCallback((id: string, success = true, message?: string) => {
    setTasks(prev => prev.map(t =>
      t.id === id ? { ...t, status: success ? 'success' : 'error', message, progress: 100 } : t
    ));
    // Auto-remove after delay
    setTimeout(() => {
      setTasks(prev => prev.filter(t => t.id !== id));
    }, 3000);
  }, []);

  const removeTask = useCallback((id: string) => {
    setTasks(prev => prev.filter(t => t.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setTasks([]);
  }, []);

  return (
    <ProgressContext.Provider value={{ tasks, startTask, updateTask, completeTask, removeTask, clearAll }}>
      {children}
    </ProgressContext.Provider>
  );
}

// Progress Overlay Component - exported for use in App.tsx
export function ProgressOverlay() {
  const context = useContext(ProgressContext);
  const tasks = context?.tasks || [];

  if (tasks.length === 0) return null;

  return (
    <div className="fixed bottom-20 left-6 z-40 space-y-2 max-w-sm">
      <AnimatePresence>
        {tasks.map(task => (
          <motion.div
            key={task.id}
            initial={{ opacity: 0, x: -50, scale: 0.9 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: -50, scale: 0.9 }}
            className="bg-bael-surface border border-bael-border rounded-xl p-4 shadow-xl"
          >
            <div className="flex items-center gap-3">
              {/* Status Icon */}
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                task.status === 'running' ? 'bg-blue-500/20' :
                task.status === 'success' ? 'bg-green-500/20' :
                task.status === 'error' ? 'bg-red-500/20' : 'bg-gray-500/20'
              }`}>
                {task.status === 'running' && <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />}
                {task.status === 'success' && <CheckCircle className="w-4 h-4 text-green-400" />}
                {task.status === 'error' && <XCircle className="w-4 h-4 text-red-400" />}
                {task.status === 'pending' && <AlertTriangle className="w-4 h-4 text-gray-400" />}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-bael-text truncate">{task.label}</p>
                {task.message && (
                  <p className="text-xs text-bael-muted truncate">{task.message}</p>
                )}
              </div>
            </div>

            {/* Progress Bar */}
            {task.status === 'running' && task.progress !== undefined && (
              <div className="mt-3 h-1.5 bg-bael-border rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${task.progress}%` }}
                  className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full"
                />
              </div>
            )}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

// Standalone progress bar component
interface ProgressBarProps {
  value: number;
  max?: number;
  label?: string;
  showPercentage?: boolean;
  size?: 'sm' | 'md' | 'lg';
  color?: 'primary' | 'success' | 'warning' | 'error';
}

export function ProgressBar({
  value,
  max = 100,
  label,
  showPercentage = true,
  size = 'md',
  color = 'primary'
}: ProgressBarProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  const sizeClasses = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3'
  };

  const colorClasses = {
    primary: 'from-bael-primary to-purple-500',
    success: 'from-green-500 to-emerald-500',
    warning: 'from-yellow-500 to-amber-500',
    error: 'from-red-500 to-rose-500'
  };

  return (
    <div className="w-full">
      {(label || showPercentage) && (
        <div className="flex items-center justify-between mb-1">
          {label && <span className="text-sm text-bael-muted">{label}</span>}
          {showPercentage && <span className="text-sm font-medium text-bael-text">{Math.round(percentage)}%</span>}
        </div>
      )}
      <div className={`w-full bg-bael-border rounded-full overflow-hidden ${sizeClasses[size]}`}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
          className={`h-full bg-gradient-to-r ${colorClasses[color]} rounded-full`}
        />
      </div>
    </div>
  );
}

export default ProgressProvider;
