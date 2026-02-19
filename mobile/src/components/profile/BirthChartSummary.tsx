import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import type { BirthChart } from '../../types/stellar';

interface BirthChartSummaryProps {
  chart: BirthChart;
}

export function BirthChartSummary({ chart }: BirthChartSummaryProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <View style={styles.card}>
      <Text style={styles.label}>BIRTH CHART</Text>
      <View style={styles.bigThree}>
        <View style={styles.signCol}>
          <Text style={styles.signLabel}>SUN</Text>
          <Text style={styles.signValue}>{chart.sun_sign}</Text>
        </View>
        <View style={styles.signCol}>
          <Text style={styles.signLabel}>MOON</Text>
          <Text style={styles.signValue}>{chart.moon_sign}</Text>
        </View>
        <View style={styles.signCol}>
          <Text style={styles.signLabel}>RISING</Text>
          <Text style={styles.signValue}>{chart.rising_sign}</Text>
        </View>
      </View>
      <TouchableOpacity onPress={() => setExpanded(!expanded)} activeOpacity={0.7}>
        <Text style={styles.toggle}>{expanded ? '▾ HIDE PLANETS' : '▸ SHOW ALL PLANETS'}</Text>
      </TouchableOpacity>
      {expanded && (
        <View style={styles.planetTable}>
          {chart.planets.map((p) => (
            <View key={p.planet} style={styles.planetRow}>
              <Text style={styles.planetName}>{p.planet}</Text>
              <Text style={styles.planetSign}>{p.sign}</Text>
              <Text style={styles.planetDeg}>{p.degree.toFixed(1)}°</Text>
            </View>
          ))}
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
    marginBottom: spacing.sm,
  },
  bigThree: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: spacing.sm,
  },
  signCol: {
    alignItems: 'center',
  },
  signLabel: {
    ...typography.caption,
    color: colors.textMuted,
  },
  signValue: {
    ...typography.monoMedium,
    color: colors.cream,
    marginTop: 2,
  },
  toggle: {
    ...typography.monoSmall,
    color: colors.brass,
    marginTop: spacing.xs,
  },
  planetTable: {
    marginTop: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.panelBg,
    paddingTop: spacing.sm,
  },
  planetRow: {
    flexDirection: 'row',
    paddingVertical: 2,
  },
  planetName: {
    ...typography.caption,
    color: colors.textMuted,
    width: 80,
  },
  planetSign: {
    ...typography.caption,
    color: colors.cream,
    flex: 1,
  },
  planetDeg: {
    ...typography.caption,
    color: colors.brass,
    width: 50,
    textAlign: 'right',
  },
});
