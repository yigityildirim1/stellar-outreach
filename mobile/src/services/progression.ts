import { api } from './api';
import { cache, TTL } from './cache';
import type { StreakData, NpcSummary, AtlasData, CosmicPassport } from '../types/stellar';

export async function fetchStreaks(playerId: string): Promise<StreakData> {
  const cacheKey = `streaks:${playerId}`;
  try {
    const data = await api.get<StreakData>(`/api/stellar/streak?player_id=${encodeURIComponent(playerId)}`);
    await cache.set(cacheKey, data, TTL.PROGRESSION);
    return data;
  } catch (err) {
    const stale = await cache.getStale<StreakData>(cacheKey);
    if (stale) return stale.data;
    throw err;
  }
}

export async function streakCheckin(playerId: string): Promise<StreakData> {
  const result = await api.post<StreakData>('/api/stellar/streak/checkin', { player_id: playerId });
  await cache.clear(`streaks:${playerId}`);
  return result;
}

export async function purchaseFreeze(playerId: string): Promise<StreakData> {
  const result = await api.post<StreakData>('/api/stellar/streak/freeze', { player_id: playerId });
  await cache.clear(`streaks:${playerId}`);
  return result;
}

export async function fetchNpcList(playerId: string): Promise<NpcSummary[]> {
  const cacheKey = `npcs:${playerId}`;
  try {
    const data = await api.get<NpcSummary[]>(`/api/stellar/npc/list?player_id=${encodeURIComponent(playerId)}`);
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
    const data = await api.get<AtlasData>(`/api/stellar/atlas?player_id=${encodeURIComponent(playerId)}`);
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
    const data = await api.get<CosmicPassport>(`/api/stellar/atlas/passport?player_id=${encodeURIComponent(playerId)}`);
    await cache.set(cacheKey, data, TTL.PROFILE);
    return data;
  } catch (err) {
    const stale = await cache.getStale<CosmicPassport>(cacheKey);
    if (stale) return stale.data;
    throw err;
  }
}
