import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import { ProgressBar } from '../shared/ProgressBar';
import { ActionButton } from '../shared/ActionButton';
import type { GuildResponse } from '../../types/stellar';

interface GuildPanelProps {
  guild: GuildResponse;
  onContribute: () => void;
}

export function GuildPanel({ guild, onContribute }: GuildPanelProps) {
  const challenge = guild.weekly_challenge;
  const progress = challenge ? challenge.progress / challenge.target : 0;

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <Text style={styles.name}>{guild.name}</Text>
        <Text style={styles.members}>{guild.member_count} MEMBERS</Text>
      </View>
      {guild.element && <Text style={styles.element}>Element: {guild.element}</Text>}
      {challenge && (
        <View style={styles.challengeSection}>
          <Text style={styles.challengeLabel}>WEEKLY CHALLENGE</Text>
          <Text style={styles.challengeDesc}>{challenge.description}</Text>
          <ProgressBar
            value={progress}
            label={`${challenge.progress}/${challenge.target}`}
          />
        </View>
      )}
      <View style={styles.buttonRow}>
        <ActionButton title="CONTRIBUTE RESOURCES" onPress={onContribute} />
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
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.xs,
  },
  name: {
    ...typography.monoMedium,
    color: colors.amber,
  },
  members: {
    ...typography.monoSmall,
    color: colors.brass,
  },
  element: {
    ...typography.caption,
    color: colors.textMuted,
    marginBottom: spacing.sm,
  },
  challengeSection: {
    marginTop: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.panelBg,
    paddingTop: spacing.sm,
  },
  challengeLabel: {
    ...typography.monoSmall,
    color: colors.amber,
    marginBottom: spacing.xs,
  },
  challengeDesc: {
    ...typography.bodySmall,
    color: colors.cream,
    marginBottom: spacing.xs,
  },
  buttonRow: {
    marginTop: spacing.sm,
  },
});
