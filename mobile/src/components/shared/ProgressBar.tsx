import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';

interface ProgressBarProps {
  value: number; // 0-1
  label?: string;
  barColor?: string;
}

export function ProgressBar({ value, label, barColor = colors.amber }: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(1, value));
  return (
    <View style={styles.container}>
      {label && <Text style={styles.label}>{label}</Text>}
      <View style={styles.track}>
        <View style={[styles.fill, { width: `${clamped * 100}%`, backgroundColor: barColor }]} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginVertical: spacing.xs,
  },
  label: {
    ...typography.caption,
    color: colors.textMuted,
    marginBottom: 2,
  },
  track: {
    height: 6,
    backgroundColor: colors.cardBg,
    borderWidth: 1,
    borderColor: colors.panelBg,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
  },
});
