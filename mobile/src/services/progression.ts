import { api } from './api';
import { cache, TTL } from './cache';
import type { StreakData, NpcSummary, AtlasData, CosmicPassport } from '../types/stellar';

export async function fetchStreaks(playerId: string): Promise<StreakData> {
  const cacheKey = `streaks:${playerId}`;
  try {
    const raw = await api.get<any>(`/api/stellar/streak?player_id=${encodeURIComponent(playerId)}`);
    const data = normalizeStreak(raw);
    await cache.set(cacheKey, data, TTL.PROGRESSION);
    return data;
  } catch (err) {
    const stale = await cache.getStale<StreakData>(cacheKey);
    if (stale) return stale.data;
    throw err;
  }
}

function normalizeStreak(raw: any): StreakData {
  const today = new Date().toISOString().slice(0, 10);
  return {
    ...raw,
    freeze_count: raw.freezes_available ?? 0,
    can_checkin: raw.last_checkin_date !== today,
    next_milestone: raw.next_milestone?.days ?? undefined,
  };
}

export async function streakCheckin(playerId: string): Promise<StreakData> {
  const raw = await api.post<any>('/api/stellar/streak/checkin', { player_id: playerId });
  await cache.clear(`streaks:${playerId}`);
  return normalizeStreak(raw);
}

export async function purchaseFreeze(playerId: string): Promise<StreakData> {
  const raw = await api.post<any>('/api/stellar/streak/freeze', { player_id: playerId });
  await cache.clear(`streaks:${playerId}`);
  return normalizeStreak(raw);
}

export async function fetchNpcList(playerId: string): Promise<NpcSummary[]> {
  const cacheKey = `npcs:${playerId}`;
  try {
    const raw = await api.get<any>(`/api/stellar/npc/list?player_id=${encodeURIComponent(playerId)}`);
    // Backend returns {"npcs": [...]} wrapper
    const data: NpcSummary[] = Array.isArray(raw) ? raw : (raw.npcs ?? []);
    await cache.set(cacheKey, data, TTL.PROGRESSION);
    return data;
  } catch (err) {
    const stale = await cache.getStale<NpcSummary[]>(cacheKey);
    if (stale) return stale.data;
    throw err;
  }
}

export function interactWithNpc(playerId: string, npcId: string) {
  return api.post<Record<string, unknown>>('/api/stellar/npc/interact', {
    player_id: playerId,
    npc_id: npcId,
  });
}

export async function fetchAtlas(playerId: string): Promise<AtlasData> {
  const cacheKey = `atlas:${playerId}`;
  try {
    const raw = await api.get<any>(`/api/stellar/atlas?player_id=${encodeURIComponent(playerId)}`);
    // Backend wraps stats in a nested "stats" object and uses "completion_percent" not "completion_pct"
    const stats = raw.stats ?? {};
    const recentRaw: any[] = raw.recent_discoveries ?? [];
    const data: AtlasData = {
      player_id: playerId,
      // Represent discovered as an array of the right length (only length is used in UI)
      discovered: new Array(stats.total_discovered ?? 0).fill(''),
      total_objects: stats.total_objects ?? 0,
      completion_pct: stats.completion_percent ?? 0,
      categories: stats.categories ?? {},
      recent_discoveries: recentRaw.map((d) =>
        typeof d === 'string' ? d : (d.name ?? d.object_id ?? ''),
      ),
    };
    await cache.set(cacheKey, data, TTL.PROFILE);
    return data;
  } catch (err) {
    const stale = await cache.getStale<AtlasData>(cacheKey);
    if (stale) return stale.data;
    throw err;
  }
}

export async function fetchPassport(playerId: string): Promise<CosmicPassport> {
  const cacheKey = `passport:${playerId}`;
  try {
    const raw = await api.get<any>(`/api/stellar/atlas/passport?player_id=${encodeURIComponent(playerId)}`);
    // Backend returns "total" not "total_stamps"
    const data: CosmicPassport = {
      player_id: playerId,
      stamps: raw.stamps ?? [],
      total_stamps: raw.total ?? 12,
    };
    await cache.set(cacheKey, data, TTL.PROFILE);
    return data;
  } catch (err) {
    const stale = await cache.getStale<CosmicPassport>(cacheKey);
    if (stale) return stale.data;
    throw err;
  }
}
