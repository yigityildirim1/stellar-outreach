import { api } from './api';
import type { PassStatus, SeasonProgress } from '../types/stellar';

export function fetchPassStatus(playerId: string) {
  return api.get<PassStatus>(`/api/stellar/pass/status?player_id=${encodeURIComponent(playerId)}`);
}

export function fetchSeasonProgress(playerId: string) {
  return api.get<SeasonProgress>(`/api/stellar/pass/progress?player_id=${encodeURIComponent(playerId)}`);
}

export function claimPassReward(playerId: string, tier: number) {
  return api.post<Record<string, unknown>>('/api/stellar/pass/claim', { player_id: playerId, tier });
}
