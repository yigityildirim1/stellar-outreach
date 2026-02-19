import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import { ProgressBar } from '../shared/ProgressBar';
import { ActionButton } from '../shared/ActionButton';
import type { NpcSummary } from '../../types/stellar';

interface NpcCardProps {
  npc: NpcSummary;
  onInteract: (npcId: string) => void;
}

export function NpcCard({ npc, onInteract }: NpcCardProps) {
  const xpPct = npc.xp_to_next > 0 ? npc.xp / npc.xp_to_next : 1;
  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <View style={styles.info}>
          <Text style={styles.name}>{npc.name}</Text>
          <Text style={styles.role}>{npc.role}</Text>
        </View>
        <Text style={styles.level}>LVL {npc.level}</Text>
      </View>
      <ProgressBar value={xpPct} label={`Relationship ${npc.xp}/${npc.xp_to_next}`} />
      <View style={styles.buttonRow}>
        <ActionButton title="INTERACT" onPress={() => onInteract(npc.npc_id)} />
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
    marginBottom: spacing.sm,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: spacing.xs,
  },
  info: { flex: 1 },
  name: {
    ...typography.monoSmall,
    color: colors.cream,
  },
  role: {
    ...typography.caption,
    color: colors.brass,
    marginTop: 2,
  },
  level: {
    ...typography.monoSmall,
    color: colors.amber,
  },
  buttonRow: {
    marginTop: spacing.sm,
  },
});
