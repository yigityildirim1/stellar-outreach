import { api } from './api';
import type { RegisterResponse, AuthCheckResponse } from '../types/stellar';

export function registerPlayer(): Promise<RegisterResponse> {
  return api.post<RegisterResponse>('/api/auth/register', {});
}

export function completeOnboarding(playerId: string): Promise<RegisterResponse> {
  return api.post<RegisterResponse>('/api/auth/complete', {
    player_id: playerId,
  });
}

export function checkPlayer(playerId: string): Promise<AuthCheckResponse> {
  return api.get<AuthCheckResponse>(`/api/auth/check?player_id=${playerId}`);
}
