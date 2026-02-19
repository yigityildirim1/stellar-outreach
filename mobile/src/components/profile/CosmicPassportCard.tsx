import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import type { CosmicPassport } from '../../types/stellar';

interface CosmicPassportCardProps {
  passport: CosmicPassport;
}

export function CosmicPassportCard({ passport }: CosmicPassportCardProps) {
  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <Text style={styles.label}>COSMIC PASSPORT</Text>
        <Text style={styles.count}>
          {passport.stamps.filter((s) => s.collected).length}/{passport.total_stamps}
        </Text>
      </View>
      <View style={styles.grid}>
        {passport.stamps.map((stamp) => (
          <View key={stamp.sign} style={styles.stampCell}>
            <Text style={[styles.stampSign, stamp.collected && styles.stampCollected]}>
              {stamp.sign}
            </Text>
          </View>
        ))}
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
    marginHorizontal: spacing.md,
    marginBottom: spacing.md,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.sm,
  },
  label: {
    ...typography.monoSmall,
    color: colors.amber,
  },
  count: {
    ...typography.monoSmall,
    color: colors.cream,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  stampCell: {
    width: '25%',
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },
  stampSign: {
    ...typography.monoSmall,
    color: colors.textMuted,
    opacity: 0.4,
  },
  stampCollected: {
    color: colors.amber,
    opacity: 1,
  },
});
