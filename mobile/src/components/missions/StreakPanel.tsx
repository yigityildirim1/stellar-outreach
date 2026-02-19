import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import { ActionButton } from '../shared/ActionButton';
import type { StreakData } from '../../types/stellar';

interface StreakPanelProps {
  streak: StreakData;
  onCheckin: () => void;
  checking: boolean;
}

export function StreakPanel({ streak, onCheckin, checking }: StreakPanelProps) {
  return (
    <View style={styles.card}>
      <Text style={styles.label}>STREAK</Text>
      <View style={styles.row}>
        <View style={styles.bigNum}>
          <Text style={styles.count}>{streak.current_streak}</Text>
          <Text style={styles.unit}>DAYS</Text>
        </View>
        <View style={styles.details}>
          <Text style={styles.stat}>LONGEST: {streak.longest_streak}</Text>
          <Text style={styles.stat}>FREEZES: {streak.freeze_count}</Text>
          {streak.next_milestone != null && (
            <Text style={styles.milestone}>NEXT: {streak.next_milestone} days</Text>
          )}
        </View>
      </View>
      <ActionButton
        title={streak.can_checkin ? 'CHECK IN' : 'CHECKED IN TODAY'}
        onPress={onCheckin}
        disabled={!streak.can_checkin}
        loading={checking}
      />
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
    marginBottom: spacing.sm,
  },
  bigNum: {
    alignItems: 'center',
    marginRight: spacing.lg,
  },
  count: {
    ...typography.monoLarge,
    fontSize: 36,
    color: colors.amber,
  },
  unit: {
    ...typography.caption,
    color: colors.textMuted,
  },
  details: {
    justifyContent: 'center',
  },
  stat: {
    ...typography.monoSmall,
    color: colors.cream,
    marginBottom: 2,
  },
  milestone: {
    ...typography.caption,
    color: colors.brass,
    marginTop: spacing.xs,
  },
});
