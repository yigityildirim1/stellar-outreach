import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import type { ModuleAlert } from '../../types/stellar';

interface ResourceSummaryProps {
  resources: Record<string, number>;
  alerts: ModuleAlert[];
  stationLevel: number;
}

export function ResourceSummary({ resources, alerts, stationLevel }: ResourceSummaryProps) {
  const entries = Object.entries(resources);

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.label}>RESOURCES</Text>
        <Text style={styles.level}>LVL {stationLevel}</Text>
      </View>
      <View style={styles.grid}>
        {entries.map(([key, val]) => (
          <View key={key} style={styles.cell}>
            <Text style={styles.value}>{val}</Text>
            <Text style={styles.key}>{key.toUpperCase()}</Text>
          </View>
        ))}
      </View>
      {alerts.length > 0 && (
        <View style={styles.alertSection}>
          {alerts.map((a, i) => (
            <Text key={i} style={styles.alert}>
              ! {a.module}: {a.alert}
            </Text>
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
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.sm,
  },
  label: {
    ...typography.monoSmall,
    color: colors.amber,
  },
  level: {
    ...typography.monoSmall,
    color: colors.brass,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  cell: {
    width: '33%',
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },
  value: {
    ...typography.monoMedium,
    color: colors.cream,
  },
  key: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: 2,
  },
  alertSection: {
    marginTop: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.panelBg,
    paddingTop: spacing.sm,
  },
  alert: {
    ...typography.caption,
    color: colors.error,
    marginBottom: 2,
  },
});
