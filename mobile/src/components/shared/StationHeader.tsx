import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors, typography, spacing } from '../../theme';

interface StationHeaderProps {
  title: string;
  subtitle?: string;
}

export function StationHeader({ title, subtitle }: StationHeaderProps) {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.container, { paddingTop: insets.top + spacing.sm }]}>
      <Text style={styles.title}>{title}</Text>
      {subtitle && <Text style={styles.subtitle}>{subtitle}</Text>}
      <View style={styles.rule} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.darkBg,
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.sm,
  },
  title: {
    ...typography.monoMedium,
    color: colors.amber,
  },
  subtitle: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: 2,
  },
  rule: {
    height: 1,
    backgroundColor: colors.amber,
    opacity: 0.3,
    marginTop: spacing.sm,
  },
});
