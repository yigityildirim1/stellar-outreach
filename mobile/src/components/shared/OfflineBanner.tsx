import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useNetwork } from '../../context/NetworkContext';
import { colors, typography, spacing } from '../../theme';

export function OfflineBanner() {
  const { isOnline, lastChecked, recheck } = useNetwork();

  if (isOnline) return null;

  const since = lastChecked
    ? lastChecked.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '—';

  return (
    <View style={styles.banner}>
      <Text style={styles.icon}>◈</Text>
      <Text style={styles.text}>OFFLINE — Cached data as of {since}</Text>
      <TouchableOpacity onPress={recheck} style={styles.retryBtn}>
        <Text style={styles.retryText}>RETRY</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    backgroundColor: '#4A2F00',
    borderBottomWidth: 1,
    borderBottomColor: colors.amber,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    gap: spacing.xs,
  },
  icon: {
    color: colors.amber,
    fontSize: 14,
  },
  text: {
    color: colors.amber,
    ...typography.monoSmall,
    fontSize: 11,
    flex: 1,
    letterSpacing: 0.5,
  },
  retryBtn: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderWidth: 1,
    borderColor: colors.amber,
    borderRadius: 2,
  },
  retryText: {
    color: colors.amber,
    ...typography.monoSmall,
    fontSize: 10,
    letterSpacing: 1,
  },
});
