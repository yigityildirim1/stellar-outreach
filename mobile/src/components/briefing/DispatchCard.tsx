import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';

interface DispatchCardProps {
  dispatch: string;
  mood: string;
  date: string;
}

const moodLabel: Record<string, string> = {
  positive: 'FAVORABLE',
  challenging: 'TURBULENT',
  mixed: 'VARIABLE',
  neutral: 'STEADY',
};

export function DispatchCard({ dispatch, mood, date }: DispatchCardProps) {
  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.label}>DAILY DISPATCH</Text>
        <Text style={styles.date}>{date}</Text>
      </View>
      <Text style={styles.dispatch}>{dispatch}</Text>
      <View style={styles.footer}>
        <Text style={styles.mood}>CONDITIONS: {moodLabel[mood] ?? mood.toUpperCase()}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.cardBg,
    borderWidth: 1,
    borderColor: colors.brass,
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
  date: {
    ...typography.monoSmall,
    color: colors.textMuted,
  },
  dispatch: {
    ...typography.serifMedium,
    color: colors.cream,
  },
  footer: {
    marginTop: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.panelBg,
    paddingTop: spacing.xs,
  },
  mood: {
    ...typography.caption,
    color: colors.brass,
  },
});
