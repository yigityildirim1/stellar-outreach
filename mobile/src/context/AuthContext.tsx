import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY = '@nexus_player';

export interface PlayerIdentity {
  player_id: string;
  birth_date: string;
  birth_time?: string;
  latitude: number;
  longitude: number;
}

interface AuthState {
  isLoading: boolean;
  isOnboarded: boolean;
  player: PlayerIdentity | null;
}

interface AuthContextValue extends AuthState {
  completeOnboarding: (player: PlayerIdentity) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    isLoading: true,
    isOnboarded: false,
    player: null,
  });

  useEffect(() => {
    (async () => {
      try {
        const raw = await AsyncStorage.getItem(STORAGE_KEY);
        if (raw) {
          const player: PlayerIdentity = JSON.parse(raw);
          setState({ isLoading: false, isOnboarded: true, player });
        } else {
          setState({ isLoading: false, isOnboarded: false, player: null });
        }
      } catch {
        setState({ isLoading: false, isOnboarded: false, player: null });
      }
    })();
  }, []);

  const completeOnboarding = useCallback(async (player: PlayerIdentity) => {
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(player));
    setState({ isLoading: false, isOnboarded: true, player });
  }, []);

  const signOut = useCallback(async () => {
    await AsyncStorage.removeItem(STORAGE_KEY);
    setState({ isLoading: false, isOnboarded: false, player: null });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, completeOnboarding, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>');
  return ctx;
}
