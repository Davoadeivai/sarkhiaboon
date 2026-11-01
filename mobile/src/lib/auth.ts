import { create } from 'zustand';

import { storage } from './storage';
import type { AuthResponse, User } from './types';

const ACCESS = 'sk.access';
const REFRESH = 'sk.refresh';
const USER = 'sk.user';

interface AuthState {
  ready: boolean;
  access: string | null;
  refresh: string | null;
  user: User | null;
  /** Load the saved session from secure storage (called once at launch). */
  hydrate: () => Promise<void>;
  setSession: (res: AuthResponse) => Promise<void>;
  setAccess: (access: string) => Promise<void>;
  setUser: (user: User) => Promise<void>;
  clear: () => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  ready: false,
  access: null,
  refresh: null,
  user: null,

  async hydrate() {
    const [access, refresh, user] = await Promise.all([storage.get(ACCESS), storage.get(REFRESH), storage.get(USER)]);
    let parsed: User | null = null;
    try {
      parsed = user ? (JSON.parse(user) as User) : null;
    } catch {
      parsed = null;
    }
    set({ access, refresh, user: parsed, ready: true });
  },

  async setSession(res) {
    await Promise.all([
      storage.set(ACCESS, res.access),
      storage.set(REFRESH, res.refresh),
      storage.set(USER, JSON.stringify(res.user)),
    ]);
    set({ access: res.access, refresh: res.refresh, user: res.user });
  },

  async setAccess(access) {
    await storage.set(ACCESS, access);
    set({ access });
  },

  async setUser(user) {
    await storage.set(USER, JSON.stringify(user));
    set({ user });
  },

  async clear() {
    await Promise.all([storage.remove(ACCESS), storage.remove(REFRESH), storage.remove(USER)]);
    set({ access: null, refresh: null, user: null });
  },
}));

export const isGuest = (user: User | null) => !user || user.is_guest;
