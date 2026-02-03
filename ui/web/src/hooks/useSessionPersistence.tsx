import { useState, useEffect, useCallback, useMemo } from 'react';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Session state interface
interface SessionState {
  // Navigation state
  lastVisitedPage: string;
  recentPages: string[];

  // Chat state
  lastChatId: string | null;
  chatDraft: string;

  // UI preferences
  sidebarCollapsed: boolean;
  activePanel: string | null;

  // Workflow state
  lastWorkflowId: string | null;
  workflowDraft: any | null;

  // Search state
  recentSearches: string[];
  searchFilters: Record<string, any>;

  // Session metadata
  sessionStartTime: number;
  lastActivityTime: number;

  // Actions
  setLastVisitedPage: (page: string) => void;
  addRecentPage: (page: string) => void;
  setLastChatId: (id: string | null) => void;
  setChatDraft: (draft: string) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setActivePanel: (panel: string | null) => void;
  setLastWorkflowId: (id: string | null) => void;
  setWorkflowDraft: (draft: any) => void;
  addRecentSearch: (search: string) => void;
  setSearchFilters: (filters: Record<string, any>) => void;
  updateActivity: () => void;
  clearSession: () => void;
}

// Zustand store with persistence
export const useSessionStore = create<SessionState>()(
  persist(
    (set, get) => ({
      // Initial state
      lastVisitedPage: '/',
      recentPages: [],
      lastChatId: null,
      chatDraft: '',
      sidebarCollapsed: false,
      activePanel: null,
      lastWorkflowId: null,
      workflowDraft: null,
      recentSearches: [],
      searchFilters: {},
      sessionStartTime: Date.now(),
      lastActivityTime: Date.now(),

      // Actions
      setLastVisitedPage: (page) => {
        set({ lastVisitedPage: page, lastActivityTime: Date.now() });
        get().addRecentPage(page);
      },

      addRecentPage: (page) => {
        set((state) => {
          const pages = state.recentPages.filter(p => p !== page);
          return {
            recentPages: [page, ...pages].slice(0, 10), // Keep last 10
            lastActivityTime: Date.now()
          };
        });
      },

      setLastChatId: (id) => set({ lastChatId: id, lastActivityTime: Date.now() }),

      setChatDraft: (draft) => set({ chatDraft: draft, lastActivityTime: Date.now() }),

      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

      setActivePanel: (panel) => set({ activePanel: panel }),

      setLastWorkflowId: (id) => set({ lastWorkflowId: id, lastActivityTime: Date.now() }),

      setWorkflowDraft: (draft) => set({ workflowDraft: draft, lastActivityTime: Date.now() }),

      addRecentSearch: (search) => {
        set((state) => {
          const searches = state.recentSearches.filter(s => s !== search);
          return {
            recentSearches: [search, ...searches].slice(0, 20), // Keep last 20
            lastActivityTime: Date.now()
          };
        });
      },

      setSearchFilters: (filters) => set({ searchFilters: filters }),

      updateActivity: () => set({ lastActivityTime: Date.now() }),

      clearSession: () => set({
        lastVisitedPage: '/',
        recentPages: [],
        lastChatId: null,
        chatDraft: '',
        sidebarCollapsed: false,
        activePanel: null,
        lastWorkflowId: null,
        workflowDraft: null,
        recentSearches: [],
        searchFilters: {},
        sessionStartTime: Date.now(),
        lastActivityTime: Date.now(),
      }),
    }),
    {
      name: 'bael-session',
      partialize: (state) => ({
        lastVisitedPage: state.lastVisitedPage,
        recentPages: state.recentPages,
        lastChatId: state.lastChatId,
        chatDraft: state.chatDraft,
        sidebarCollapsed: state.sidebarCollapsed,
        activePanel: state.activePanel,
        lastWorkflowId: state.lastWorkflowId,
        workflowDraft: state.workflowDraft,
        recentSearches: state.recentSearches,
        searchFilters: state.searchFilters,
      }),
    }
  )
);

// Hook for page tracking
export function usePageTracking(currentPage: string) {
  const setLastVisitedPage = useSessionStore(s => s.setLastVisitedPage);

  useEffect(() => {
    setLastVisitedPage(currentPage);
  }, [currentPage, setLastVisitedPage]);
}

// Hook for chat draft auto-save
export function useChatDraft() {
  const chatDraft = useSessionStore(s => s.chatDraft);
  const setChatDraft = useSessionStore(s => s.setChatDraft);

  const saveDraft = useCallback((draft: string) => {
    setChatDraft(draft);
  }, [setChatDraft]);

  const clearDraft = useCallback(() => {
    setChatDraft('');
  }, [setChatDraft]);

  return { chatDraft, saveDraft, clearDraft };
}

// Hook for recent searches
export function useRecentSearches() {
  const recentSearches = useSessionStore(s => s.recentSearches);
  const addRecentSearch = useSessionStore(s => s.addRecentSearch);

  const addSearch = useCallback((search: string) => {
    if (search.trim()) {
      addRecentSearch(search.trim());
    }
  }, [addRecentSearch]);

  return { recentSearches, addSearch };
}

// Hook for session duration
export function useSessionDuration() {
  const sessionStartTime = useSessionStore(s => s.sessionStartTime);
  const lastActivityTime = useSessionStore(s => s.lastActivityTime);
  const updateActivity = useSessionStore(s => s.updateActivity);

  const [duration, setDuration] = useState('0m');

  useEffect(() => {
    const updateDuration = () => {
      const now = Date.now();
      const diff = now - sessionStartTime;
      const minutes = Math.floor(diff / 60000);
      const hours = Math.floor(minutes / 60);

      if (hours > 0) {
        setDuration(`${hours}h ${minutes % 60}m`);
      } else {
        setDuration(`${minutes}m`);
      }
    };

    updateDuration();
    const interval = setInterval(updateDuration, 60000);
    return () => clearInterval(interval);
  }, [sessionStartTime]);

  // Update activity on user interaction
  useEffect(() => {
    const events = ['mousedown', 'keydown', 'scroll', 'touchstart'];
    const handler = () => updateActivity();

    events.forEach(event => window.addEventListener(event, handler, { passive: true }));
    return () => events.forEach(event => window.removeEventListener(event, handler));
  }, [updateActivity]);

  const isActive = useMemo(() => {
    return Date.now() - lastActivityTime < 5 * 60 * 1000; // Active if activity in last 5 minutes
  }, [lastActivityTime]);

  return { duration, isActive };
}

// Hook for sidebar state
export function useSidebarState() {
  const sidebarCollapsed = useSessionStore(s => s.sidebarCollapsed);
  const setSidebarCollapsed = useSessionStore(s => s.setSidebarCollapsed);

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed(!sidebarCollapsed);
  }, [sidebarCollapsed, setSidebarCollapsed]);

  return { sidebarCollapsed, setSidebarCollapsed, toggleSidebar };
}

// Auto-save hook for any data
export function useAutoSave<T>(
  key: string,
  data: T,
  delay: number = 2000
) {
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);

  useEffect(() => {
    setIsSaving(true);
    const timeout = setTimeout(() => {
      try {
        localStorage.setItem(`bael-autosave-${key}`, JSON.stringify(data));
        setLastSaved(new Date());
      } catch (e) {
        console.error('Auto-save failed:', e);
      } finally {
        setIsSaving(false);
      }
    }, delay);

    return () => clearTimeout(timeout);
  }, [key, data, delay]);

  const loadSaved = useCallback((): T | null => {
    try {
      const saved = localStorage.getItem(`bael-autosave-${key}`);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  }, [key]);

  const clearSaved = useCallback(() => {
    localStorage.removeItem(`bael-autosave-${key}`);
  }, [key]);

  return { isSaving, lastSaved, loadSaved, clearSaved };
}

export default useSessionStore;
