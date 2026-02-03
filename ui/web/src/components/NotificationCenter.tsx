import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bell,
  X,
  Check,
  AlertCircle,
  Info,
  AlertTriangle,
  Trash2,
  CheckCheck,
  Clock
} from 'lucide-react';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Notification types
interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  timestamp: number;
  read: boolean;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface NotificationStore {
  notifications: Notification[];
  unreadCount: number;
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  removeNotification: (id: string) => void;
  clearAll: () => void;
}

// Zustand store for notifications
export const useNotificationStore = create<NotificationStore>()(
  persist(
    (set, get) => ({
      notifications: [],
      unreadCount: 0,

      addNotification: (notification) => {
        const newNotification: Notification = {
          ...notification,
          id: `notif-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          timestamp: Date.now(),
          read: false,
        };
        set((state) => ({
          notifications: [newNotification, ...state.notifications].slice(0, 50), // Keep last 50
          unreadCount: state.unreadCount + 1,
        }));
      },

      markAsRead: (id) => {
        set((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id && !n.read ? { ...n, read: true } : n
          ),
          unreadCount: Math.max(0, state.unreadCount - (state.notifications.find(n => n.id === id && !n.read) ? 1 : 0)),
        }));
      },

      markAllAsRead: () => {
        set((state) => ({
          notifications: state.notifications.map((n) => ({ ...n, read: true })),
          unreadCount: 0,
        }));
      },

      removeNotification: (id) => {
        set((state) => {
          const notification = state.notifications.find((n) => n.id === id);
          return {
            notifications: state.notifications.filter((n) => n.id !== id),
            unreadCount: notification && !notification.read ? state.unreadCount - 1 : state.unreadCount,
          };
        });
      },

      clearAll: () => {
        set({ notifications: [], unreadCount: 0 });
      },
    }),
    {
      name: 'bael-notifications',
      partialize: (state) => ({
        notifications: state.notifications.slice(0, 20), // Only persist last 20
      }),
    }
  )
);

// Icon map
const iconMap = {
  success: Check,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

const colorMap = {
  success: 'text-green-400 bg-green-400/10',
  error: 'text-red-400 bg-red-400/10',
  warning: 'text-amber-400 bg-amber-400/10',
  info: 'text-blue-400 bg-blue-400/10',
};

// Time ago helper
function timeAgo(timestamp: number): string {
  const seconds = Math.floor((Date.now() - timestamp) / 1000);

  if (seconds < 60) return 'Just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

// Notification Center component
export function NotificationCenter() {
  const [isOpen, setIsOpen] = useState(false);
  const { notifications, unreadCount, markAsRead, markAllAsRead, removeNotification, clearAll } = useNotificationStore();

  const toggleOpen = useCallback(() => {
    setIsOpen((prev) => !prev);
  }, []);

  return (
    <div className="relative">
      {/* Bell Button */}
      <motion.button
        onClick={toggleOpen}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className="relative p-2 text-bael-muted hover:text-bael-text hover:bg-bael-border rounded-lg transition-colors"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </motion.button>

      {/* Notification Panel */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
              className="fixed inset-0 z-40"
            />

            {/* Panel */}
            <motion.div
              initial={{ opacity: 0, y: -10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              className="absolute right-0 top-full mt-2 w-96 bg-bael-surface border border-bael-border rounded-xl shadow-2xl overflow-hidden z-50"
            >
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-bael-border bg-bael-bg/50">
                <div className="flex items-center gap-2">
                  <Bell className="w-4 h-4 text-bael-primary" />
                  <span className="text-sm font-medium text-bael-text">Notifications</span>
                  {unreadCount > 0 && (
                    <span className="px-2 py-0.5 text-xs bg-bael-primary/20 text-bael-primary rounded-full">
                      {unreadCount} new
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  {unreadCount > 0 && (
                    <button
                      onClick={markAllAsRead}
                      className="p-1.5 text-bael-muted hover:text-bael-text hover:bg-bael-border rounded-lg transition-colors"
                      title="Mark all as read"
                    >
                      <CheckCheck className="w-4 h-4" />
                    </button>
                  )}
                  {notifications.length > 0 && (
                    <button
                      onClick={clearAll}
                      className="p-1.5 text-bael-muted hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
                      title="Clear all"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>

              {/* Notifications List */}
              <div className="max-h-[400px] overflow-y-auto">
                {notifications.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-bael-muted">
                    <Bell className="w-12 h-12 mb-3 opacity-20" />
                    <p className="text-sm">No notifications</p>
                  </div>
                ) : (
                  <div className="divide-y divide-bael-border">
                    {notifications.map((notification) => {
                      const Icon = iconMap[notification.type];
                      return (
                        <motion.div
                          key={notification.id}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: 20 }}
                          onClick={() => markAsRead(notification.id)}
                          className={`p-4 hover:bg-bael-bg/50 cursor-pointer transition-colors ${
                            !notification.read ? 'bg-bael-primary/5' : ''
                          }`}
                        >
                          <div className="flex gap-3">
                            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${colorMap[notification.type]}`}>
                              <Icon className="w-4 h-4" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-start justify-between gap-2">
                                <p className="text-sm font-medium text-bael-text">
                                  {notification.title}
                                </p>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    removeNotification(notification.id);
                                  }}
                                  className="p-1 text-bael-muted hover:text-red-400 hover:bg-red-400/10 rounded transition-colors"
                                >
                                  <X className="w-3 h-3" />
                                </button>
                              </div>
                              {notification.message && (
                                <p className="text-xs text-bael-muted mt-1 line-clamp-2">
                                  {notification.message}
                                </p>
                              )}
                              <div className="flex items-center justify-between mt-2">
                                <span className="flex items-center gap-1 text-xs text-bael-muted">
                                  <Clock className="w-3 h-3" />
                                  {timeAgo(notification.timestamp)}
                                </span>
                                {notification.action && (
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      notification.action?.onClick();
                                    }}
                                    className="text-xs text-bael-primary hover:text-bael-primary/80"
                                  >
                                    {notification.action.label}
                                  </button>
                                )}
                              </div>
                              {!notification.read && (
                                <div className="absolute right-4 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-bael-primary" />
                              )}
                            </div>
                          </div>
                        </motion.div>
                      );
                    })}
                  </div>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

// Hook to add notifications easily
export function useNotifications() {
  const addNotification = useNotificationStore((s) => s.addNotification);

  return {
    success: (title: string, message?: string) => addNotification({ type: 'success', title, message }),
    error: (title: string, message?: string) => addNotification({ type: 'error', title, message }),
    warning: (title: string, message?: string) => addNotification({ type: 'warning', title, message }),
    info: (title: string, message?: string) => addNotification({ type: 'info', title, message }),
    notify: addNotification,
  };
}

export default NotificationCenter;
