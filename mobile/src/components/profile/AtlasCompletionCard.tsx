import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import { ProgressBar } from '../shared/ProgressBar';
import type { AtlasData } from '../../types/stellar';

interface AtlasCompletionCardProps {
  atlas: AtlasData;
}

export function AtlasCompletionCard({ atlas }: AtlasCompletionCardProps) {
  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <Text style={styles.label}>STAR ATLAS</Text>
        <Text style={styles.stat}>{atlas.discovered.length}/{atlas.total_objects}</Text>
      </View>
      <ProgressBar value={atlas.completion_pct / 100} label={`${atlas.completion_pct.toFixed(1)}% complete`} />
      {atlas.recent_discoveries && atlas.recent_discoveries.length > 0 && (
        <View style={styles.recentSection}>
          <Text style={styles.recentLabel}>RECENT DISCOVERIES</Text>
          {atlas.recent_discoveries.slice(0, 3).map((d) => (
            <Text key={d} style={styles.discovery}>{d}</Text>
          ))}
        </View>
      )}
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
    marginBottom: spacing.sm,
  },
  label: {
    ...typography.monoSmall,
    color: colors.amber,
  },
  stat: {
    ...typography.monoSmall,
    color: colors.cream,
  },
  recentSection: {
    marginTop: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.panelBg,
    paddingTop: spacing.sm,
  },
  recentLabel: {
    ...typography.caption,
    color: colors.brass,
    marginBottom: spacing.xs,
  },
  discovery: {
    ...typography.caption,
    color: colors.cream,
    marginBottom: 2,
  },
});
