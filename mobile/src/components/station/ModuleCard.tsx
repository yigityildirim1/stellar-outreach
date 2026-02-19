import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import { ProgressBar } from '../shared/ProgressBar';
import { ActionButton } from '../shared/ActionButton';
import type { StationModule } from '../../types/stellar';

interface ModuleCardProps {
  module: StationModule;
  onUpgrade: (name: string) => void;
  upgrading: boolean;
}

export function ModuleCard({ module, onUpgrade, upgrading }: ModuleCardProps) {
  const xpPct = module.xp_to_next > 0 ? module.xp / module.xp_to_next : 1;
  const costStr = module.upgrade_cost
    ? Object.entries(module.upgrade_cost).map(([k, v]) => `${v} ${k}`).join(', ')
    : null;

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <View style={styles.nameCol}>
          <Text style={styles.name}>{module.name.toUpperCase()}</Text>
          <Text style={styles.desc}>{module.description}</Text>
        </View>
        <View style={styles.levelCol}>
          <Text style={styles.level}>LVL {module.level}</Text>
          <Text style={[styles.status, module.health < 50 && styles.statusWarn]}>
            {module.status} ({module.health}%)
          </Text>
        </View>
      </View>
      <ProgressBar value={xpPct} label={`XP ${module.xp}/${module.xp_to_next}`} />
      {costStr && (
        <View style={styles.upgradeRow}>
          <Text style={styles.costText}>UPGRADE: {costStr}</Text>
          <ActionButton
            title="UPGRADE"
            onPress={() => onUpgrade(module.name)}
            loading={upgrading}
          />
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
    marginBottom: spacing.sm,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.xs,
  },
  nameCol: { flex: 1 },
  name: {
    ...typography.monoSmall,
    color: colors.amber,
  },
  desc: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: 2,
  },
  levelCol: {
    alignItems: 'flex-end',
  },
  level: {
    ...typography.monoSmall,
    color: colors.cream,
  },
  status: {
    ...typography.caption,
    color: colors.success,
    marginTop: 2,
  },
  statusWarn: {
    color: colors.error,
  },
  upgradeRow: {
    marginTop: spacing.sm,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  costText: {
    ...typography.caption,
    color: colors.brass,
    flex: 1,
    marginRight: spacing.sm,
  },
});
