import AsyncStorage from '@react-native-async-storage/async-storage';
import { api } from './api';

const QUEUE_KEY = '@nexus_analytics:queue';
const MAX_QUEUE_SIZE = 100;
const FLUSH_ENDPOINT = '/api/analytics/events';

export interface AnalyticsEvent {
  event: string;
  ts: number;
  props?: Record<string, unknown>;
}

let _playerId: string | null = null;
let _flushTimer: ReturnType<typeof setTimeout> | null = null;
const FLUSH_DEBOUNCE_MS = 5_000;

export const analytics = {
  init(playerId: string) {
    _playerId = playerId;
    // Flush any queued events from previous sessions
    scheduleFlush(1_000);
  },

  track(event: string, props?: Record<string, unknown>) {
    const entry: AnalyticsEvent = { event, ts: Date.now(), props };
    enqueue(entry);
    scheduleFlush(FLUSH_DEBOUNCE_MS);
  },

  screenView(screenName: string) {
    this.track('screen_view', { screen: screenName });
  },

  async flush() {
    if (!_playerId) return;
    try {
      const raw = await AsyncStorage.getItem(QUEUE_KEY);
      if (!raw) return;
      const queue: AnalyticsEvent[] = JSON.parse(raw);
      if (!queue.length) return;

      await api.post(FLUSH_ENDPOINT, {
        player_id: _playerId,
        events: queue,
      });
      await AsyncStorage.removeItem(QUEUE_KEY);
    } catch {
      // Network error — keep queue, try next time
    }
  },
};

async function enqueue(entry: AnalyticsEvent) {
  try {
    const raw = await AsyncStorage.getItem(QUEUE_KEY);
    const queue: AnalyticsEvent[] = raw ? JSON.parse(raw) : [];
    queue.push(entry);
    // Cap queue size to avoid unbounded growth when offline
    if (queue.length > MAX_QUEUE_SIZE) queue.splice(0, queue.length - MAX_QUEUE_SIZE);
    await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
  } catch {}
}

function scheduleFlush(delayMs: number) {
  if (_flushTimer) clearTimeout(_flushTimer);
  _flushTimer = setTimeout(() => analytics.flush(), delayMs);
}
