import { api } from './api';
import { cache, TTL } from './cache';
import type { Station, CollectResult } from '../types/stellar';

export async function fetchStation(playerId: string): Promise<Station> {
  const cacheKey = `station:${playerId}`;
  try {
    const raw = await api.get<any>(`/api/stellar/station?player_id=${encodeURIComponent(playerId)}`);
    // Backend returns modules as a dict {id: module}, but Station type expects StationModule[]
    const data: Station = {
      ...raw,
      modules: raw.modules
        ? Object.values(raw.modules).map((m: any) => ({
            ...m,
            status: m.status ?? m.cosmic_status ?? 'NOMINAL',
          }))
        : [],
    };
    await cache.set(cacheKey, data, TTL.STATION);
    return data;
  } catch (err) {
    const stale = await cache.getStale<Station>(cacheKey);
    if (stale) return stale.data;
    throw err;
  }
}

export function createStation(playerId: string, stationName: string) {
  return api.post<Station>('/api/stellar/station', { player_id: playerId, station_name: stationName });
}

export async function collectResources(playerId: string): Promise<CollectResult> {
  const result = await api.post<CollectResult>('/api/stellar/station/collect', { player_id: playerId });
  // Bust cache after mutation
  await cache.clear(`station:${playerId}`);
  return result;
}

export async function upgradeModule(playerId: string, moduleName: string): Promise<Station> {
  const result = await api.post<Station>('/api/stellar/station/upgrade', {
    player_id: playerId,
    module_name: moduleName,
  });
  await cache.clear(`station:${playerId}`);
  return result;
}
