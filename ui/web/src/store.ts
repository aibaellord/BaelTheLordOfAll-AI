import { create } from "zustand";
import { persist } from "zustand/middleware";

// Types - exported for use in components
export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  persona?: string;
}

export interface Terminal {
  id: string;
  name: string;
  active: boolean;
}

export interface CouncilMember {
  id: string;
  name: string;
  persona: string;
  status: "idle" | "thinking" | "speaking";
  lastMessage?: string;
  color?: string;
  role?: string;
  active?: boolean;
}

export interface SystemStatus {
  connected: boolean;
  llmProvider: string | null;
  activeModel: string | null;
  memory: {
    working: number;
    episodic: number;
    semantic: number;
  };
  tools: number;
  mcpServers: number;
}

interface AppState {
  // UI State
  sidebarOpen: boolean;
  activeView: string;
  theme: "dark" | "light";

  // Chat State
  messages: Message[];
  currentPersona: string | null;
  isStreaming: boolean;

  // Terminals
  terminals: Terminal[];
  activeTerminalId: string | null;

  // Council
  councilMembers: CouncilMember[];
  councilActive: boolean;
  councilTopic: string | null;

  // System
  status: SystemStatus;

  // Settings
  settings: {
    llm: {
      provider: string;
      model: string;
      temperature: number;
      maxTokens: number;
    };
    memory: {
      enabled: boolean;
      workingSize: number;
    };
    ui: {
      fontSize: number;
      showTimestamps: boolean;
      compactMode: boolean;
    };
  };

  // Actions
  initialize: () => Promise<void>;
  toggleSidebar: () => void;
  setActiveView: (view: string) => void;

  // Chat actions
  addMessage: (message: Omit<Message, "id" | "timestamp">) => void;
  clearMessages: () => void;
  setPersona: (persona: string | null) => void;
  setStreaming: (streaming: boolean) => void;

  // Terminal actions
  addTerminal: (name?: string) => string;
  removeTerminal: (id: string) => void;
  setActiveTerminal: (id: string) => void;

  // Council actions
  startCouncil: (topic: string, members: string[]) => void;
  endCouncil: () => void;
  updateMemberStatus: (
    id: string,
    status: CouncilMember["status"],
    message?: string,
  ) => void;
  updateCouncilMember: (id: string, updates: Partial<CouncilMember>) => void;
  setCouncilMembers: (members: CouncilMember[]) => void;

  // Settings actions
  updateSettings: (path: string, value: any) => void;

  // System actions
  updateStatus: (status: Partial<SystemStatus>) => void;
}

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Initial state
      sidebarOpen: true,
      activeView: "dashboard",
      theme: "dark",

      messages: [],
      currentPersona: null,
      isStreaming: false,

      terminals: [],
      activeTerminalId: null,

      councilMembers: [],
      councilActive: false,
      councilTopic: null,

      status: {
        connected: false,
        llmProvider: null,
        activeModel: null,
        memory: { working: 0, episodic: 0, semantic: 0 },
        tools: 0,
        mcpServers: 0,
      },

      settings: {
        llm: {
          provider: "openrouter",
          model: "anthropic/claude-3.5-sonnet",
          temperature: 0.7,
          maxTokens: 4096,
        },
        memory: {
          enabled: true,
          workingSize: 20,
        },
        ui: {
          fontSize: 14,
          showTimestamps: true,
          compactMode: false,
        },
      },

      // Actions
      initialize: async () => {
        try {
          // Check API connection
          const response = await fetch("/api/v1/status");
          if (response.ok) {
            const data = await response.json();
            set({
              status: {
                connected: true,
                llmProvider: data.llm_provider,
                activeModel: data.active_model,
                memory: data.memory || { working: 0, episodic: 0, semantic: 0 },
                tools: data.tools || 0,
                mcpServers: data.mcp_servers || 0,
              },
            });
          }
        } catch (error) {
          console.error("Failed to initialize:", error);
          set({ status: { ...get().status, connected: false } });
        }
      },

      toggleSidebar: () =>
        set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setActiveView: (view) => set({ activeView: view }),

      // Chat
      addMessage: (message) =>
        set((state) => ({
          messages: [
            ...state.messages,
            {
              ...message,
              id: crypto.randomUUID(),
              timestamp: new Date(),
            },
          ],
        })),
      clearMessages: () => set({ messages: [] }),
      setPersona: (persona) => set({ currentPersona: persona }),
      setStreaming: (streaming) => set({ isStreaming: streaming }),

      // Terminals
      addTerminal: (name) => {
        const id = crypto.randomUUID();
        const terminalName = name || `Terminal ${get().terminals.length + 1}`;
        set((state) => ({
          terminals: [
            ...state.terminals,
            { id, name: terminalName, active: true },
          ],
          activeTerminalId: id,
        }));
        return id;
      },
      removeTerminal: (id) =>
        set((state) => {
          const newTerminals = state.terminals.filter((t) => t.id !== id);
          return {
            terminals: newTerminals,
            activeTerminalId:
              state.activeTerminalId === id
                ? newTerminals[0]?.id || null
                : state.activeTerminalId,
          };
        }),
      setActiveTerminal: (id) => set({ activeTerminalId: id }),

      // Council
      startCouncil: (topic, members) => {
        const councilMembers: CouncilMember[] = members.map((name, i) => ({
          id: `member-${i}`,
          name,
          persona: name.toLowerCase(),
          status: "idle" as const,
        }));
        set({ councilActive: true, councilTopic: topic, councilMembers });
      },
      endCouncil: () =>
        set({ councilActive: false, councilTopic: null, councilMembers: [] }),
      updateMemberStatus: (id, status, message) =>
        set((state) => ({
          councilMembers: state.councilMembers.map((m) =>
            m.id === id
              ? { ...m, status, lastMessage: message || m.lastMessage }
              : m,
          ),
        })),

      updateCouncilMember: (id, updates) =>
        set((state) => ({
          councilMembers: state.councilMembers.map((m) =>
            m.id === id ? { ...m, ...updates } : m,
          ),
        })),

      setCouncilMembers: (members) => set({ councilMembers: members }),

      // Settings
      updateSettings: (path, value) =>
        set((state) => {
          const parts = path.split(".");
          const newSettings = { ...state.settings };
          let current: any = newSettings;

          for (let i = 0; i < parts.length - 1; i++) {
            current[parts[i]] = { ...current[parts[i]] };
            current = current[parts[i]];
          }
          current[parts[parts.length - 1]] = value;

          return { settings: newSettings };
        }),

      // System
      updateStatus: (statusUpdate) =>
        set((state) => ({
          status: { ...state.status, ...statusUpdate },
        })),
    }),
    {
      name: "bael-storage",
      partialize: (state) => ({
        settings: state.settings,
        theme: state.theme,
      }),
    },
  ),
);
