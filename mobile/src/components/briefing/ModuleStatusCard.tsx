import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import type { ModuleStatus } from '../../types/stellar';

interface ModuleStatusCardProps {
  statuses: ModuleStatus[];
}

const statusColor: Record<string, string> = {
  POWER: '#22C55E',
  TROUBLE: '#EF4444',
  PRESSURE: '#F59E0B',
  STEADY: '#6B7280',
};

export function ModuleStatusCard({ statuses }: ModuleStatusCardProps) {
  return (
    <View style={styles.card}>
      <Text style={styles.label}>MODULE STATUS</Text>
      {statuses.map((s, i) => (
        <View key={i} style={styles.row}>
          <View style={styles.nameCol}>
            <Text style={styles.moduleName}>{s.module}</Text>
          </View>
          <Text style={[styles.status, { color: statusColor[s.status] ?? colors.textMuted }]}>
            {s.status}
          </Text>
        </View>
      ))}
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
  label: {
    ...typography.monoSmall,
    color: colors.amber,
    marginBottom: spacing.sm,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.xs,
    borderBottomWidth: 1,
    borderBottomColor: colors.panelBg,
  },
  nameCol: {
    flex: 1,
  },
  moduleName: {
    ...typography.monoSmall,
    color: colors.cream,
  },
  status: {
    ...typography.monoSmall,
    fontWeight: '700',
  },
});
