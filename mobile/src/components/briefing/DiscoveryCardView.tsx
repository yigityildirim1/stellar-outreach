import React from 'react';
import { View, Text, Image, StyleSheet, Linking, TouchableOpacity } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import type { DiscoveryCard } from '../../types/stellar';

interface DiscoveryCardViewProps {
  card: DiscoveryCard;
}

export function DiscoveryCardView({ card }: DiscoveryCardViewProps) {
  return (
    <View style={styles.card}>
      <Text style={styles.label}>DISCOVERY CARD — NASA APOD</Text>
      {card.media_type === 'image' && card.url ? (
        <Image
          source={{ uri: card.url }}
          style={styles.image}
          resizeMode="cover"
        />
      ) : (
        <View style={styles.placeholder}>
          <Text style={styles.placeholderText}>[ VIDEO ]</Text>
        </View>
      )}
      <Text style={styles.title}>{card.title}</Text>
      <Text style={styles.explanation} numberOfLines={4}>
        {card.explanation}
      </Text>
      {card.copyright && (
        <Text style={styles.copyright}>{card.copyright}</Text>
      )}
      <TouchableOpacity onPress={() => Linking.openURL(card.url)}>
        <Text style={styles.link}>VIEW FULL IMAGE</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.cardBg,
    borderWidth: 1,
    borderColor: colors.brass,
    padding: spacing.md,
    marginHorizontal: spacing.md,
    marginBottom: spacing.md,
  },
  label: {
    ...typography.monoSmall,
    color: colors.amber,
    marginBottom: spacing.sm,
  },
  image: {
    width: '100%',
    height: 200,
    marginBottom: spacing.sm,
  },
  placeholder: {
    width: '100%',
    height: 200,
    backgroundColor: colors.panelBg,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  placeholderText: {
    ...typography.monoSmall,
    color: colors.textMuted,
  },
  title: {
    ...typography.serifMedium,
    color: colors.cream,
    marginBottom: spacing.xs,
  },
  explanation: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    marginBottom: spacing.xs,
  },
  copyright: {
    ...typography.caption,
    color: colors.textMuted,
    marginBottom: spacing.xs,
  },
  link: {
    ...typography.monoSmall,
    color: colors.amber,
    marginTop: spacing.xs,
  },
});
