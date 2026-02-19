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
import { elementColors, type Element } from '../../theme/elements';
import { fetchDailyBriefing } from '../../services/briefing';
import type { DailyBriefing } from '../../types/stellar';
import { StationHeader } from '../../components/shared/StationHeader';
import { DispatchCard } from '../../components/briefing/DispatchCard';
import { ModuleStatusCard } from '../../components/briefing/ModuleStatusCard';
import { ResourceSummary } from '../../components/briefing/ResourceSummary';
import { DiscoveryCardView } from '../../components/briefing/DiscoveryCardView';
import { OfflineBanner } from '../../components/shared/OfflineBanner';
import { useAuth } from '../../context/AuthContext';

export function BriefingScreen() {
  const { player } = useAuth();
  const [briefing, setBriefing] = useState<DailyBriefing | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadBriefing = async () => {
    if (!player) return;
    try {
      setError(null);
      const data = await fetchDailyBriefing(player);
      setBriefing(data);
    } catch (e: any) {
      setError(e.message ?? 'Unknown error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadBriefing();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    loadBriefing();
  };

  // Determine gradient from element
  const element = (briefing?.archetype?.element ?? 'Fire') as Element;
  const elColors = elementColors[element] ?? elementColors.Fire;

  if (loading) {
    return (
      <LinearGradient
        colors={[elColors.bg_gradient_start, elColors.bg_gradient_end]}
        style={styles.center}
      >
        <ActivityIndicator size="large" color={colors.amber} />
        <Text style={styles.loadingText}>CALCULATING TRANSITS...</Text>
      </LinearGradient>
    );
  }

  if (error) {
    return (
      <LinearGradient
        colors={[elColors.bg_gradient_start, elColors.bg_gradient_end]}
        style={styles.center}
      >
        <Text style={styles.errorIcon}>◉</Text>
        <Text style={styles.errorTitle}>SIGNAL LOST</Text>
        <Text style={styles.errorMsg}>{error}</Text>
        <Text style={styles.retryHint}>Pull down to retry</Text>
      </LinearGradient>
    );
  }

  if (!briefing) return null;

  return (
    <LinearGradient
      colors={[elColors.bg_gradient_start, elColors.bg_gradient_end]}
      style={styles.flex}
    >
      <StationHeader
        title={briefing.station_name}
        subtitle={`${briefing.archetype?.archetype_name ?? 'Unknown'} — ${element}`}
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
        {/* Cosmic Briefing Text */}
        <View style={styles.briefingTextCard}>
          <Text style={styles.briefingLabel}>COSMIC WEATHER</Text>
          <Text style={styles.briefingText}>{briefing.cosmic_briefing_text}</Text>
        </View>

        {/* Daily Dispatch */}
        <DispatchCard
          dispatch={briefing.daily_dispatch}
          mood={briefing.overall_mood}
          date={briefing.date}
        />

        {/* Module Statuses */}
        {briefing.module_statuses.length > 0 && (
          <ModuleStatusCard statuses={briefing.module_statuses} />
        )}

        {/* Resources */}
        <ResourceSummary
          resources={briefing.resources}
          alerts={briefing.module_alerts}
          stationLevel={briefing.station_level}
        />

        {/* Discovery Card (NASA APOD) */}
        {briefing.discovery_card && (
          <DiscoveryCardView card={briefing.discovery_card} />
        )}

        {/* Metadata footer */}
        <View style={styles.metaFooter}>
          <Text style={styles.metaText}>
            Generated: {briefing.generated_at}
            {briefing.is_cached ? ' (cached)' : ''}
          </Text>
        </View>
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
  briefingTextCard: {
    backgroundColor: colors.cardBg,
    borderWidth: 1,
    borderColor: colors.panelBg,
    padding: spacing.md,
    marginHorizontal: spacing.md,
    marginBottom: spacing.md,
  },
  briefingLabel: {
    ...typography.monoSmall,
    color: colors.amber,
    marginBottom: spacing.sm,
  },
  briefingText: {
    ...typography.serifMedium,
    color: colors.cream,
  },
  metaFooter: {
    paddingHorizontal: spacing.md,
    paddingTop: spacing.md,
    alignItems: 'center',
  },
  metaText: {
    ...typography.caption,
    color: colors.textMuted,
  },
});
