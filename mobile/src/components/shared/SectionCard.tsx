import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';

interface SectionCardProps {
  label: string;
  rightLabel?: string;
  children: React.ReactNode;
}

export function SectionCard({ label, rightLabel, children }: SectionCardProps) {
  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.label}>{label}</Text>
        {rightLabel && <Text style={styles.rightLabel}>{rightLabel}</Text>}
      </View>
      {children}
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
  rightLabel: {
    ...typography.monoSmall,
    color: colors.brass,
  },
});
