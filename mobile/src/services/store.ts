import { api } from './api';
import type { Wallet } from '../types/stellar';

export function fetchWallet(playerId: string) {
  return api.get<Wallet>(`/api/stellar/store/wallet?player_id=${encodeURIComponent(playerId)}`);
}

export function fetchStoreCatalog(playerId: string) {
  return api.get<Record<string, unknown>>(`/api/stellar/store/catalog?player_id=${encodeURIComponent(playerId)}`);
}

export function purchaseItem(playerId: string, itemId: string) {
  return api.post<Record<string, unknown>>('/api/stellar/store/purchase', { player_id: playerId, item_id: itemId });
}
