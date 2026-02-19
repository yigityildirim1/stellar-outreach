import { api } from './api';
import type { PassStatus, SeasonProgress } from '../types/stellar';

export function fetchPassStatus(playerId: string) {
  return api.get<PassStatus>(`/api/stellar/pass/status?player_id=${encodeURIComponent(playerId)}`);
}

export async function fetchSeasonProgress(playerId: string): Promise<SeasonProgress> {
  const raw = await api.get<any>(`/api/stellar/pass/progress?player_id=${encodeURIComponent(playerId)}`);
  // Backend returns "total_tiers", "season_xp", "xp_to_next_tier" — normalize to type names
  return {
    ...raw,
    max_tier: raw.total_tiers ?? raw.max_tier ?? 30,
    current_xp: raw.season_xp ?? raw.current_xp ?? 0,
    xp_to_next: raw.xp_to_next_tier ?? raw.xp_to_next ?? 0,
  };
}

export function claimPassReward(playerId: string, tier: number) {
  return api.post<Record<string, unknown>>('/api/stellar/pass/claim', { player_id: playerId, tier });
}
