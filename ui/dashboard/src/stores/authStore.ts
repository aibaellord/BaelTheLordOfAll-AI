import { create } from "zustand";
import { persist } from "zustand/middleware";

interface User {
  id: string;
  name: string;
  email: string;
  role: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setUser: (user: User) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      login: async (email: string, password: string) => {
        // Simulate API call
        await new Promise((resolve) => setTimeout(resolve, 500));

        // Mock authentication - replace with real API call
        if (email && password) {
          const user = {
            id: "1",
            name: "Admin User",
            email,
            role: "admin",
          };
          const token = "mock_token_" + Date.now();

          set({ user, token, isAuthenticated: true });
        } else {
          throw new Error("Invalid credentials");
        }
      },

      logout: () => {
        set({ user: null, token: null, isAuthenticated: false });
      },

      setUser: (user: User) => {
        set({ user, isAuthenticated: true });
      },
    }),
    {
      name: "bael-auth",
    },
  ),
);
