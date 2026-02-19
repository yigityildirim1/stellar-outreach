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
import { fetchBirthChart } from '../../services/birthChart';
import { fetchAtlas, fetchPassport } from '../../services/progression';
import { fetchSeasonProgress } from '../../services/pass';
import { fetchWallet } from '../../services/store';
import type { BirthChart, AtlasData, CosmicPassport, SeasonProgress, Wallet } from '../../types/stellar';
import { StationHeader } from '../../components/shared/StationHeader';
import { BirthChartSummary } from '../../components/profile/BirthChartSummary';
import { OfflineBanner } from '../../components/shared/OfflineBanner';
import { ElementBadge } from '../../components/profile/ElementBadge';
import { AtlasCompletionCard } from '../../components/profile/AtlasCompletionCard';
import { CosmicPassportCard } from '../../components/profile/CosmicPassportCard';
import { SeasonPassCard } from '../../components/profile/SeasonPassCard';

export function ProfileScreen() {
  const { player } = useAuth();
  const [chart, setChart] = useState<BirthChart | null>(null);
  const [atlas, setAtlas] = useState<AtlasData | null>(null);
  const [passport, setPassport] = useState<CosmicPassport | null>(null);
  const [season, setSeason] = useState<SeasonProgress | null>(null);
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async () => {
    if (!player) return;
    try {
      setError(null);
      const [chartRes, atlasRes, passportRes, seasonRes, walletRes] = await Promise.allSettled([
        fetchBirthChart({
          player_id: player.player_id,
          birth_date: player.birth_date,
          birth_time: player.birth_time,
          latitude: player.latitude,
          longitude: player.longitude,
        }),
        fetchAtlas(player.player_id),
        fetchPassport(player.player_id),
        fetchSeasonProgress(player.player_id),
        fetchWallet(player.player_id),
      ]);
      if (chartRes.status === 'fulfilled') setChart(chartRes.value);
      if (atlasRes.status === 'fulfilled') setAtlas(atlasRes.value);
      if (passportRes.status === 'fulfilled') setPassport(passportRes.value);
      if (seasonRes.status === 'fulfilled') setSeason(seasonRes.value);
      if (walletRes.status === 'fulfilled') setWallet(walletRes.value);
      // Only show error if all fetches failed
      const allFailed = [chartRes, atlasRes, passportRes, seasonRes, walletRes]
        .every((r) => r.status === 'rejected');
      if (allFailed) throw new Error('Failed to load profile data');
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

  if (loading) {
    return (
      <LinearGradient colors={['#1A0A1A', '#0A0A0A']} style={styles.center}>
        <ActivityIndicator size="large" color={colors.amber} />
        <Text style={styles.loadingText}>LOADING PROFILE...</Text>
      </LinearGradient>
    );
  }

  if (error) {
    return (
      <LinearGradient colors={['#1A0A1A', '#0A0A0A']} style={styles.center}>
        <Text style={styles.errorIcon}>◉</Text>
        <Text style={styles.errorTitle}>SIGNAL LOST</Text>
        <Text style={styles.errorMsg}>{error}</Text>
        <Text style={styles.retryHint}>Pull down to retry</Text>
      </LinearGradient>
    );
  }

  return (
    <LinearGradient colors={['#1A0A1A', '#0A0A0A']} style={styles.flex}>
      <StationHeader title="COMMANDER PROFILE" />
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
        {chart && <BirthChartSummary chart={chart} />}
        {chart && (
          <ElementBadge
            dominantElement={chart.dominant_element}
            balance={chart.element_balance}
          />
        )}
        {atlas && <AtlasCompletionCard atlas={atlas} />}
        {passport && <CosmicPassportCard passport={passport} />}
        {season && <SeasonPassCard season={season} />}
        {wallet && (
          <View style={styles.walletCard}>
            <Text style={styles.walletLabel}>WALLET</Text>
            <View style={styles.walletRow}>
              <View style={styles.walletCol}>
                <Text style={styles.walletValue}>{wallet.stardust}</Text>
                <Text style={styles.walletKey}>STARDUST</Text>
              </View>
              <View style={styles.walletCol}>
                <Text style={styles.walletValue}>{wallet.gems}</Text>
                <Text style={styles.walletKey}>GEMS</Text>
              </View>
            </View>
          </View>
        )}
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
  walletCard: {
    backgroundColor: colors.cardBg,
    borderWidth: 1,
    borderColor: colors.panelBg,
    padding: spacing.md,
    marginHorizontal: spacing.md,
    marginBottom: spacing.md,
  },
  walletLabel: {
    ...typography.monoSmall,
    color: colors.amber,
    marginBottom: spacing.sm,
  },
  walletRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  walletCol: {
    alignItems: 'center',
  },
  walletValue: {
    ...typography.monoLarge,
    color: colors.cream,
  },
  walletKey: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: 2,
  },
});
