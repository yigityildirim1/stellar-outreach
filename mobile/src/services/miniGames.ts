import { api } from './api';
import type { DailyMission } from '../types/stellar';

export function fetchDailyMission(playerId: string) {
  return api.get<DailyMission>(`/api/stellar/daily-mission?player_id=${encodeURIComponent(playerId)}`);
}

// ─── Game generation ────────────────────────────────────────

export function fetchDiplomacy(playerId: string) {
  return api.post<any>('/api/stellar/mini-game/diplomacy', { player_id: playerId });
}

export function fetchSignalDecode(playerId: string) {
  return api.post<any>('/api/stellar/mini-game/signal-decode', { player_id: playerId });
}

export function fetchStarPattern(playerId: string) {
  return api.post<any>('/api/stellar/mini-game/star-pattern', { player_id: playerId });
}

export function fetchCircuitRepair(playerId: string) {
  return api.post<any>('/api/stellar/mini-game/repair', { player_id: playerId });
}

export function fetchAsteroidDeflection(playerId: string) {
  return api.post<any>('/api/stellar/mini-game/asteroid', { player_id: playerId });
}

export function fetchHarvest(playerId: string) {
  return api.post<any>('/api/stellar/mini-game/harvest', { player_id: playerId });
}

export function fetchSkyScanner(playerId: string) {
  return api.post<any>('/api/stellar/mini-game/sky-scanner', { player_id: playerId });
}

// ─── Score submission ───────────────────────────────────────

export function scoreDiplomacy(payload: Record<string, unknown>) {
  return api.post<any>('/api/stellar/mini-game/diplomacy/score', payload);
}

export function scoreSignalDecode(payload: Record<string, unknown>) {
  return api.post<any>('/api/stellar/mini-game/signal-decode/score', payload);
}

export function scoreStarPattern(payload: Record<string, unknown>) {
  return api.post<any>('/api/stellar/mini-game/star-pattern/score', payload);
}

export function scoreCircuitRepair(payload: Record<string, unknown>) {
  return api.post<any>('/api/stellar/mini-game/repair/score', payload);
}

export function scoreAsteroidDeflection(payload: Record<string, unknown>) {
  return api.post<any>('/api/stellar/mini-game/asteroid/score', payload);
}

export function scoreHarvest(payload: Record<string, unknown>) {
  return api.post<any>('/api/stellar/mini-game/harvest/score', payload);
}

export function scoreSkyScanner(payload: Record<string, unknown>) {
  return api.post<any>('/api/stellar/mini-game/sky-scanner/score', payload);
}
