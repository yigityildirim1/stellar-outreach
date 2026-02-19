import React from 'react';
import { TouchableOpacity, Text, ActivityIndicator, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';

interface ActionButtonProps {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
}

export function ActionButton({ title, onPress, disabled, loading }: ActionButtonProps) {
  return (
    <TouchableOpacity
      style={[styles.button, disabled && styles.disabled]}
      onPress={onPress}
      disabled={disabled || loading}
      activeOpacity={0.7}
    >
      {loading ? (
        <ActivityIndicator size="small" color={colors.amber} />
      ) : (
        <Text style={[styles.text, disabled && styles.disabledText]}>{title}</Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    borderWidth: 1,
    borderColor: colors.amber,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 40,
  },
  disabled: {
    borderColor: colors.textMuted,
    opacity: 0.5,
  },
  text: {
    ...typography.monoSmall,
    color: colors.amber,
  },
  disabledText: {
    color: colors.textMuted,
  },
});
