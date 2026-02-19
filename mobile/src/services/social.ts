import { api } from './api';
import { cache, TTL } from './cache';
import type { FriendsList, GuildResponse } from '../types/stellar';

export async function fetchFriends(playerId: string): Promise<FriendsList> {
  const cacheKey = `friends:${playerId}`;
  try {
    const data = await api.get<FriendsList>(`/api/stellar/friends?player_id=${encodeURIComponent(playerId)}`);
    await cache.set(cacheKey, data, TTL.SOCIAL);
    return data;
  } catch (err) {
    const stale = await cache.getStale<FriendsList>(cacheKey);
    if (stale) return stale.data;
    throw err;
  }
}

export function sendGift(playerId: string, friendId: string) {
  return api.post<Record<string, unknown>>('/api/stellar/friends/gift', {
    player_id: playerId,
    friend_id: friendId,
  });
}

export async function fetchGuild(playerId: string): Promise<GuildResponse> {
  const cacheKey = `guild:${playerId}`;
  try {
    const data = await api.get<GuildResponse>(`/api/stellar/guild?player_id=${encodeURIComponent(playerId)}`);
    await cache.set(cacheKey, data, TTL.SOCIAL);
    return data;
  } catch (err) {
    const stale = await cache.getStale<GuildResponse>(cacheKey);
    if (stale) return stale.data;
    throw err;
  }
}

export function contributeToGuild(playerId: string, resource: string, amount: number) {
  return api.post<Record<string, unknown>>('/api/stellar/guild/contribute', {
    player_id: playerId,
    resource,
    amount,
  });
}
