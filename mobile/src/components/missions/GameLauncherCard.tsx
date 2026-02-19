import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import { ActionButton } from '../shared/ActionButton';

interface GameLauncherCardProps {
  name: string;
  description: string;
  icon: string;
}

export function GameLauncherCard({ name, description, icon }: GameLauncherCardProps) {
  return (
    <View style={styles.card}>
      <View style={styles.row}>
        <Text style={styles.icon}>{icon}</Text>
        <View style={styles.info}>
          <Text style={styles.name}>{name}</Text>
          <Text style={styles.desc}>{description}</Text>
        </View>
        <ActionButton title="PLAY" onPress={() => {}} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.cardBg,
    borderWidth: 1,
    borderColor: colors.panelBg,
    padding: spacing.sm,
    marginBottom: spacing.xs,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  icon: {
    fontSize: 24,
    marginRight: spacing.sm,
  },
  info: {
    flex: 1,
    marginRight: spacing.sm,
  },
  name: {
    ...typography.monoSmall,
    color: colors.cream,
  },
  desc: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: 2,
  },
});
