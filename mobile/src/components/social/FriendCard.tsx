import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import { ActionButton } from '../shared/ActionButton';
import type { FriendEntry } from '../../types/stellar';

interface FriendCardProps {
  friend: FriendEntry;
  onSendGift: (friendId: string) => void;
}

export function FriendCard({ friend, onSendGift }: FriendCardProps) {
  return (
    <View style={styles.card}>
      <View style={styles.row}>
        <View style={styles.info}>
          <Text style={styles.id}>{friend.friend_id}</Text>
          {friend.last_gift_sent && (
            <Text style={styles.meta}>Last gift sent: {friend.last_gift_sent}</Text>
          )}
        </View>
        <ActionButton title="GIFT" onPress={() => onSendGift(friend.friend_id)} />
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
  info: {
    flex: 1,
    marginRight: spacing.sm,
  },
  id: {
    ...typography.monoSmall,
    color: colors.cream,
  },
  meta: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: 2,
  },
});
