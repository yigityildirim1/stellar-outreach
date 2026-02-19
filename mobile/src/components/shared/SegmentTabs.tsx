import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';

interface SegmentTabsProps {
  tabs: string[];
  activeIndex: number;
  onTabPress: (index: number) => void;
}

export function SegmentTabs({ tabs, activeIndex, onTabPress }: SegmentTabsProps) {
  return (
    <View style={styles.container}>
      {tabs.map((tab, i) => (
        <TouchableOpacity
          key={tab}
          style={[styles.tab, i === activeIndex && styles.activeTab]}
          onPress={() => onTabPress(i)}
          activeOpacity={0.7}
        >
          <Text style={[styles.text, i === activeIndex && styles.activeText]}>{tab}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    marginHorizontal: spacing.md,
    marginBottom: spacing.md,
    borderWidth: 1,
    borderColor: colors.panelBg,
  },
  tab: {
    flex: 1,
    paddingVertical: spacing.sm,
    alignItems: 'center',
    backgroundColor: colors.cardBg,
  },
  activeTab: {
    backgroundColor: colors.panelBg,
    borderBottomWidth: 2,
    borderBottomColor: colors.amber,
  },
  text: {
    ...typography.monoSmall,
    color: colors.textMuted,
  },
  activeText: {
    color: colors.amber,
  },
});
