import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import { ActionButton } from '../shared/ActionButton';

interface ResourcePanelProps {
  resources: Record<string, number>;
  onCollect: () => void;
  collecting: boolean;
}

export function ResourcePanel({ resources, onCollect, collecting }: ResourcePanelProps) {
  const entries = Object.entries(resources);
  return (
    <View style={styles.card}>
      <Text style={styles.label}>RESOURCES</Text>
      <View style={styles.grid}>
        {entries.map(([key, val]) => (
          <View key={key} style={styles.cell}>
            <Text style={styles.value}>{val}</Text>
            <Text style={styles.key}>{key.toUpperCase()}</Text>
          </View>
        ))}
      </View>
      <View style={styles.buttonRow}>
        <ActionButton title="COLLECT RESOURCES" onPress={onCollect} loading={collecting} />
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
  label: {
    ...typography.monoSmall,
    color: colors.amber,
    marginBottom: spacing.sm,
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
  buttonRow: {
    marginTop: spacing.sm,
  },
});
