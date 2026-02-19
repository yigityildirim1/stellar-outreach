import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import { elementColors, type Element } from '../../theme/elements';
import { ProgressBar } from '../shared/ProgressBar';

interface ElementBadgeProps {
  dominantElement: string;
  balance: Record<string, number>;
}

export function ElementBadge({ dominantElement, balance }: ElementBadgeProps) {
  const elColor = elementColors[dominantElement as Element]?.primary ?? colors.amber;
  const total = Object.values(balance).reduce((a, b) => a + b, 0) || 1;

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <Text style={styles.label}>DOMINANT ELEMENT</Text>
        <Text style={[styles.element, { color: elColor }]}>{dominantElement.toUpperCase()}</Text>
      </View>
      {Object.entries(balance).map(([el, val]) => (
        <ProgressBar
          key={el}
          value={val / total}
          label={el}
          barColor={elementColors[el as Element]?.primary ?? colors.amber}
        />
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
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.sm,
  },
  label: {
    ...typography.monoSmall,
    color: colors.amber,
  },
  element: {
    ...typography.monoMedium,
  },
});
