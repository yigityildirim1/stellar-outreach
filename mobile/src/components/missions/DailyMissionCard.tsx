import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import { ActionButton } from '../shared/ActionButton';
import type { DailyMission } from '../../types/stellar';

interface DailyMissionCardProps {
  mission: DailyMission;
}

export function DailyMissionCard({ mission }: DailyMissionCardProps) {
  const pips = Array.from({ length: 5 }, (_, i) => (i < mission.difficulty ? '■' : '□')).join('');
  const rewardStr = Object.entries(mission.rewards).map(([k, v]) => `+${v} ${k}`).join('  ');

  return (
    <View style={styles.card}>
      <Text style={styles.label}>DAILY MISSION</Text>
      <Text style={styles.title}>{mission.title}</Text>
      <Text style={styles.desc}>{mission.description}</Text>
      <View style={styles.metaRow}>
        <Text style={styles.difficulty}>DIFFICULTY {pips}</Text>
        <Text style={styles.rewards}>{rewardStr}</Text>
      </View>
      {mission.game_type && (
        <View style={styles.buttonRow}>
          <ActionButton title="LAUNCH MISSION" onPress={() => {}} />
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
  label: {
    ...typography.monoSmall,
    color: colors.amber,
    marginBottom: spacing.xs,
  },
  title: {
    ...typography.monoMedium,
    color: colors.cream,
    marginBottom: spacing.xs,
  },
  desc: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    marginBottom: spacing.sm,
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  difficulty: {
    ...typography.caption,
    color: colors.amber,
  },
  rewards: {
    ...typography.caption,
    color: colors.success,
  },
  buttonRow: {
    marginTop: spacing.sm,
  },
});
