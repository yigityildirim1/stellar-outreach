import AsyncStorage from '@react-native-async-storage/async-storage';
import { api } from './api';
import type { NotificationPayload } from '../components/shared/InAppNotification';

const LAST_NOTIF_KEY = '@nexus_notifications:last_shown';
const MIN_INTERVAL_MS = 20 * 60 * 60 * 1000; // 20 hours between reminders

interface NotificationRecord {
  type: string;
  shownAt: number;
}

export const notificationService = {
  /**
   * Check if the user is due for a daily briefing reminder or streak nudge.
   * Returns a payload to show as an in-app notification, or null if nothing to show.
   */
  async checkForPendingNotification(
    playerId: string,
    latitude: number,
    longitude: number,
  ): Promise<NotificationPayload | null> {
    try {
      // Enforce minimum interval between notifications
      const raw = await AsyncStorage.getItem(LAST_NOTIF_KEY);
      if (raw) {
        const record: NotificationRecord = JSON.parse(raw);
        if (Date.now() - record.shownAt < MIN_INTERVAL_MS) return null;
      }

      // Ask backend for a morning briefing notification
      const res = await api.post<{
        ok: boolean;
        notification?: { title: string; body: string; notification_type?: string };
      }>('/api/stellar/notifications/morning', {
        player_id: playerId,
        latitude,
        longitude,
      });

      if (!res.ok || !res.notification) return null;

      // Record that we showed it
      const record: NotificationRecord = { type: 'morning', shownAt: Date.now() };
      await AsyncStorage.setItem(LAST_NOTIF_KEY, JSON.stringify(record));

      return {
        title: res.notification.title,
        body: res.notification.body,
        icon: '◉',
      };
    } catch {
      return null;
    }
  },

  /** Mark a notification as dismissed without counting it against the interval. */
  async markDismissed(): Promise<void> {
    try {
      await AsyncStorage.removeItem(LAST_NOTIF_KEY);
    } catch {}
  },
};
