import { api } from './api';
import type { Wallet } from '../types/stellar';

export async function fetchWallet(playerId: string): Promise<Wallet> {
  const raw = await api.get<any>(`/api/stellar/store/wallet?player_id=${encodeURIComponent(playerId)}`);
  // Backend uses "stellar_gems" not "gems"; no stardust balance exposed (only total_stardust_spent)
  return {
    player_id: raw.player_id ?? playerId,
    stardust: raw.stardust ?? 0,
    gems: raw.stellar_gems ?? raw.gems ?? 0,
  };
}

export function fetchStoreCatalog(playerId: string) {
  return api.get<Record<string, unknown>>(`/api/stellar/store/catalog?player_id=${encodeURIComponent(playerId)}`);
}

export function purchaseItem(playerId: string, itemId: string) {
  return api.post<Record<string, unknown>>('/api/stellar/store/purchase', { player_id: playerId, item_id: itemId });
}
