import { api } from './api';
import type { DailyMission } from '../types/stellar';

export function fetchDailyMission(playerId: string) {
  return api.get<DailyMission>(`/api/stellar/daily-mission?player_id=${encodeURIComponent(playerId)}`);
}

export function submitGameResult(playerId: string, gameId: string, score: number) {
  return api.post<Record<string, unknown>>(`/api/stellar/mini-game/${gameId}/score`, {
    player_id: playerId,
    score,
  });
}
