import { api } from './api';
import type { BirthChart } from '../types/stellar';

export interface BirthChartRequest {
  player_id: string;
  birth_date: string;
  birth_time?: string;
  latitude: number;
  longitude: number;
}

export async function fetchBirthChart(req: BirthChartRequest): Promise<BirthChart> {
  const raw = await api.post<any>('/api/stellar/birth-chart', {
    player_id: req.player_id,
    birth_date: req.birth_date,
    birth_time: req.birth_time,
    latitude: req.latitude,
    longitude: req.longitude,
  });
  // Backend response is nested: natal_chart.planets, archetype.sign/element, elemental_balance
  const planets: any[] = raw.natal_chart?.planets ?? [];
  const moonSign = planets.find((p: any) => p.planet === 'Moon')?.sign ?? '';
  return {
    player_id: req.player_id,
    sun_sign: raw.archetype?.sign ?? '',
    moon_sign: moonSign,
    rising_sign: raw.natal_chart?.ascendant_sign ?? '',
    dominant_element: raw.archetype?.element ?? '',
    planets,
    element_balance: raw.elemental_balance ?? {},
  };
}
