import { api } from './api';
import type { BirthChart } from '../types/stellar';

export interface BirthChartRequest {
  player_id: string;
  birth_date: string;
  birth_time?: string;
  latitude: number;
  longitude: number;
}

export function fetchBirthChart(req: BirthChartRequest) {
  return api.post<BirthChart>('/api/stellar/birth-chart', {
    player_id: req.player_id,
    birth_date: req.birth_date,
    birth_time: req.birth_time,
    latitude: req.latitude,
    longitude: req.longitude,
  });
}
