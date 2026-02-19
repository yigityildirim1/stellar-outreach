import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import { ProgressBar } from '../shared/ProgressBar';
import type { SeasonProgress } from '../../types/stellar';

interface SeasonPassCardProps {
  season: SeasonProgress;
}

export function SeasonPassCard({ season }: SeasonPassCardProps) {
  const tierPct = season.max_tier > 0 ? season.current_tier / season.max_tier : 0;

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <Text style={styles.label}>SEASON PASS</Text>
        {season.is_premium && <Text style={styles.premium}>PREMIUM</Text>}
      </View>
      <Text style={styles.seasonName}>{season.season_name}</Text>
      <ProgressBar value={tierPct} label={`Tier ${season.current_tier}/${season.max_tier}`} />
      <View style={styles.metaRow}>
        <Text style={styles.meta}>XP: {season.current_xp}/{season.xp_to_next}</Text>
        <Text style={styles.meta}>{season.days_remaining} DAYS LEFT</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.cardBg,
    borderWidth: 1,
    borderColor: colors.panelBg,
    padding: spacing.md,
    marginHorizontal: spacing.md,
    marginBottom: spacing.md,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.xs,
  },
  label: {
    ...typography.monoSmall,
    color: colors.amber,
  },
  premium: {
    ...typography.monoSmall,
    color: colors.success,
  },
  seasonName: {
    ...typography.monoMedium,
    color: colors.cream,
    marginBottom: spacing.sm,
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: spacing.xs,
  },
  meta: {
    ...typography.caption,
    color: colors.textMuted,
  },
});
