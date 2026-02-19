import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  ActivityIndicator,
  StyleSheet,
  RefreshControl,
} from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { colors, typography, spacing } from '../../theme';
import { useAuth } from '../../context/AuthContext';
import { fetchDailyMission } from '../../services/miniGames';
import { fetchStreaks, streakCheckin } from '../../services/progression';
import type { DailyMission, StreakData } from '../../types/stellar';
import { StationHeader } from '../../components/shared/StationHeader';
import { SectionCard } from '../../components/shared/SectionCard';
import { DailyMissionCard } from '../../components/missions/DailyMissionCard';
import { StreakPanel } from '../../components/missions/StreakPanel';
import { GameLauncherCard } from '../../components/missions/GameLauncherCard';
import { OfflineBanner } from '../../components/shared/OfflineBanner';
import { analytics } from '../../services/analytics';

const GAMES = [
  { name: 'Star Pattern', description: 'Connect constellations from memory', icon: '✦' },
  { name: 'Circuit Repair', description: 'Fix station wiring under time pressure', icon: '⚡' },
  { name: 'Asteroid Deflection', description: 'Calculate trajectories to save the station', icon: '☄' },
  { name: 'Crew Diplomacy', description: 'Navigate crew conflicts with dialogue', icon: '🤝' },
  { name: 'Signal Decode', description: 'Decrypt incoming transmissions', icon: '📡' },
  { name: 'Cosmic Harvest', description: 'Manage resource collection cycles', icon: '🌾' },
  { name: 'Sky Scanner', description: 'Identify celestial objects in real-time', icon: '🔭' },
];

export function MissionsScreen() {
  const { player } = useAuth();
  const playerId = player?.player_id ?? '';
  const [mission, setMission] = useState<DailyMission | null>(null);
  const [streak, setStreak] = useState<StreakData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [checking, setChecking] = useState(false);

  const loadData = async () => {
    try {
      setError(null);
      const [missionRes, streakRes] = await Promise.allSettled([
        fetchDailyMission(playerId),
        fetchStreaks(playerId),
      ]);
      if (missionRes.status === 'fulfilled') setMission(missionRes.value);
      if (streakRes.status === 'fulfilled') setStreak(streakRes.value);
      if (missionRes.status === 'rejected' && streakRes.status === 'rejected') {
        throw new Error('Failed to load mission data');
      }
    } catch (e: any) {
      setError(e.message ?? 'Unknown error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  const onCheckin = async () => {
    setChecking(true);
    try {
      const updated = await streakCheckin(playerId);
      setStreak(updated);
      analytics.track('streak_checkin', { player_id: playerId, streak: updated.current_streak });
    } catch (_) {}
    setChecking(false);
  };

  if (loading) {
    return (
      <LinearGradient colors={['#1A0A0A', '#0A0A0A']} style={styles.center}>
        <ActivityIndicator size="large" color={colors.amber} />
        <Text style={styles.loadingText}>LOADING MISSIONS...</Text>
      </LinearGradient>
    );
  }

  if (error) {
    return (
      <LinearGradient colors={['#1A0A0A', '#0A0A0A']} style={styles.center}>
        <Text style={styles.errorIcon}>◉</Text>
        <Text style={styles.errorTitle}>SIGNAL LOST</Text>
        <Text style={styles.errorMsg}>{error}</Text>
        <Text style={styles.retryHint}>Pull down to retry</Text>
      </LinearGradient>
    );
  }

  return (
    <LinearGradient colors={['#1A0A0A', '#0A0A0A']} style={styles.flex}>
      <StationHeader title="MISSION CONTROL" />
      <OfflineBanner />
      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={colors.amber}
          />
        }
      >
        {mission && <DailyMissionCard mission={mission} />}
        {streak && (
          <StreakPanel streak={streak} onCheckin={onCheckin} checking={checking} />
        )}
        <SectionCard label="MINI-GAMES" rightLabel={`${GAMES.length} AVAILABLE`}>
          {GAMES.map((g) => (
            <GameLauncherCard key={g.name} name={g.name} description={g.description} icon={g.icon} />
          ))}
        </SectionCard>
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    ...typography.monoSmall,
    color: colors.amber,
    marginTop: spacing.md,
  },
  errorIcon: {
    fontSize: 48,
    color: colors.error,
    marginBottom: spacing.md,
  },
  errorTitle: {
    ...typography.monoLarge,
    color: colors.error,
    marginBottom: spacing.sm,
  },
  errorMsg: {
    ...typography.bodySmall,
    color: colors.textMuted,
    textAlign: 'center',
    paddingHorizontal: spacing.xl,
    marginBottom: spacing.md,
  },
  retryHint: {
    ...typography.caption,
    color: colors.textMuted,
  },
  scrollContent: {
    paddingTop: spacing.md,
    paddingBottom: spacing.xxl,
  },
});
