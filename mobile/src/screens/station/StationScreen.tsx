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
import { fetchStation, collectResources, upgradeModule } from '../../services/station';
import type { Station } from '../../types/stellar';
import { StationHeader } from '../../components/shared/StationHeader';
import { OfflineBanner } from '../../components/shared/OfflineBanner';
import { ResourcePanel } from '../../components/station/ResourcePanel';
import { ModuleCard } from '../../components/station/ModuleCard';
import { analytics } from '../../services/analytics';

export function StationScreen() {
  const { player } = useAuth();
  const playerId = player?.player_id ?? '';
  const [station, setStation] = useState<Station | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [collecting, setCollecting] = useState(false);
  const [upgradingModule, setUpgradingModule] = useState<string | null>(null);

  const loadStation = async () => {
    try {
      setError(null);
      const data = await fetchStation(playerId);
      setStation(data);
    } catch (e: any) {
      setError(e.message ?? 'Unknown error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadStation();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    loadStation();
  };

  const onCollect = async () => {
    setCollecting(true);
    try {
      await collectResources(playerId);
      analytics.track('resource_collected', { player_id: playerId });
      await loadStation();
    } catch (_) {}
    setCollecting(false);
  };

  const onUpgrade = async (moduleName: string) => {
    setUpgradingModule(moduleName);
    try {
      await upgradeModule(playerId, moduleName);
      analytics.track('module_upgraded', { player_id: playerId, module: moduleName });
      await loadStation();
    } catch (_) {}
    setUpgradingModule(null);
  };

  if (loading) {
    return (
      <LinearGradient colors={['#0A1A0A', '#0A0A0A']} style={styles.center}>
        <ActivityIndicator size="large" color={colors.amber} />
        <Text style={styles.loadingText}>LOADING STATION...</Text>
      </LinearGradient>
    );
  }

  if (error) {
    return (
      <LinearGradient colors={['#0A1A0A', '#0A0A0A']} style={styles.center}>
        <Text style={styles.errorIcon}>◉</Text>
        <Text style={styles.errorTitle}>SIGNAL LOST</Text>
        <Text style={styles.errorMsg}>{error}</Text>
        <Text style={styles.retryHint}>Pull down to retry</Text>
      </LinearGradient>
    );
  }

  if (!station) return null;

  return (
    <LinearGradient colors={['#0A1A0A', '#0A0A0A']} style={styles.flex}>
      <StationHeader
        title="STATION"
        subtitle={`${station.station_name} — LVL ${station.station_level}`}
      />
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
        <ResourcePanel
          resources={station.resources}
          onCollect={onCollect}
          collecting={collecting}
        />
        {station.modules.map((mod) => (
          <ModuleCard
            key={mod.name}
            module={mod}
            onUpgrade={onUpgrade}
            upgrading={upgradingModule === mod.name}
          />
        ))}
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
