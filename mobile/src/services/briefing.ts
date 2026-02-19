import { api } from './api';
import { cache, TTL } from './cache';
import { DailyBriefing } from '../types/stellar';

export interface BriefingRequest {
  player_id: string;
  birth_date: string;    // "YYYY-MM-DD"
  birth_time?: string;   // "HH:MM"
  latitude: number;
  longitude: number;
  transit_date?: string;  // defaults to today
}

export async function fetchDailyBriefing(req: BriefingRequest): Promise<DailyBriefing> {
  const cacheKey = `briefing:${req.player_id}`;
  try {
    const data = await api.post<DailyBriefing>('/api/stellar/briefing', {
      player_id: req.player_id,
      birth_date: req.birth_date,
      birth_time: req.birth_time,
      latitude: req.latitude,
      longitude: req.longitude,
      transit_date: req.transit_date,
    });
    await cache.set(cacheKey, data, TTL.BRIEFING);
    return data;
  } catch (err) {
    const stale = await cache.getStale<DailyBriefing>(cacheKey);
    if (stale) return stale.data;
    throw err;
  }
}

export async function fetchSkyToday(lat: number, lng: number) {
  const cacheKey = `sky:${Math.round(lat)},${Math.round(lng)}`;
  try {
    const data = await api.post<Record<string, unknown>>('/api/stellar/sky-today', {
      latitude: lat,
      longitude: lng,
    });
    await cache.set(cacheKey, data, TTL.BRIEFING);
    return data;
  } catch (err) {
    const stale = await cache.getStale<Record<string, unknown>>(cacheKey);
    if (stale) return stale.data;
    throw err;
  }
}
