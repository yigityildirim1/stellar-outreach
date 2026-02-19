import AsyncStorage from '@react-native-async-storage/async-storage';

const NS = '@nexus_cache:';

interface CacheEntry<T> {
  data: T;
  cachedAt: number; // ms epoch
  ttl: number;      // ms
}

export const cache = {
  async get<T>(key: string): Promise<T | null> {
    try {
      const raw = await AsyncStorage.getItem(NS + key);
      if (!raw) return null;
      const entry: CacheEntry<T> = JSON.parse(raw);
      if (Date.now() - entry.cachedAt > entry.ttl) {
        await AsyncStorage.removeItem(NS + key);
        return null;
      }
      return entry.data;
    } catch {
      return null;
    }
  },

  async getStale<T>(key: string): Promise<{ data: T; age: number } | null> {
    try {
      const raw = await AsyncStorage.getItem(NS + key);
      if (!raw) return null;
      const entry: CacheEntry<T> = JSON.parse(raw);
      return { data: entry.data, age: Date.now() - entry.cachedAt };
    } catch {
      return null;
    }
  },

  async set<T>(key: string, data: T, ttlMs: number): Promise<void> {
    try {
      const entry: CacheEntry<T> = { data, cachedAt: Date.now(), ttl: ttlMs };
      await AsyncStorage.setItem(NS + key, JSON.stringify(entry));
    } catch {
      // storage full or unavailable — silently skip
    }
  },

  async clear(key: string): Promise<void> {
    try {
      await AsyncStorage.removeItem(NS + key);
    } catch {}
  },

  async clearAll(): Promise<void> {
    try {
      const keys = await AsyncStorage.getAllKeys();
      const ours = keys.filter(k => k.startsWith(NS));
      if (ours.length) await AsyncStorage.multiRemove(ours);
    } catch {}
  },
};

// TTL constants (ms)
export const TTL = {
  BRIEFING:    60 * 60 * 1000,  // 1 hour  — changes daily
  STATION:      5 * 60 * 1000,  // 5 min   — collect/upgrade cycles
  SOCIAL:       5 * 60 * 1000,  // 5 min
  PROGRESSION:  5 * 60 * 1000,  // 5 min
  PROFILE:     30 * 60 * 1000,  // 30 min  — atlas, passport
};
