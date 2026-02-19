import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import { useDraft } from '../../context/OnboardingDraftContext';
import type { OnboardingStackProps } from '../../navigation/types';

export function BirthTimeScreen({ navigation }: OnboardingStackProps<'BirthTime'>) {
  const { draft, update } = useDraft();
  const [hour, setHour] = useState(draft.birthHour ?? '');
  const [minute, setMinute] = useState(draft.birthMinute ?? '');

  const isValid =
    hour.length >= 1 && hour.length <= 2 &&
    minute.length >= 1 && minute.length <= 2 &&
    Number(hour) >= 0 && Number(hour) <= 23 &&
    Number(minute) >= 0 && Number(minute) <= 59;

  const onNext = () => {
    update({
      birthHour: hour.padStart(2, '0'),
      birthMinute: minute.padStart(2, '0'),
      birthTimeSkipped: false,
    });
    navigation.navigate('BirthLocation');
  };

  const onSkip = () => {
    update({ birthTimeSkipped: true, birthHour: undefined, birthMinute: undefined });
    navigation.navigate('BirthLocation');
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.header}>
        <Text style={styles.step}>STEP 2 OF 5</Text>
        <Text style={styles.title}>BIRTH TIME</Text>
        <Text style={styles.subtitle}>
          Exact birth time enables rising sign and house calculations.
          If unknown, you can skip this step.
        </Text>
      </View>

      <View style={styles.inputRow}>
        <View style={styles.inputGroup}>
          <Text style={styles.label}>HOUR (0-23)</Text>
          <TextInput
            style={styles.input}
            value={hour}
            onChangeText={setHour}
            placeholder="14"
            placeholderTextColor={colors.muted}
            keyboardType="number-pad"
            maxLength={2}
            returnKeyType="next"
          />
        </View>
        <Text style={styles.colon}>:</Text>
        <View style={styles.inputGroup}>
          <Text style={styles.label}>MINUTE</Text>
          <TextInput
            style={styles.input}
            value={minute}
            onChangeText={setMinute}
            placeholder="30"
            placeholderTextColor={colors.muted}
            keyboardType="number-pad"
            maxLength={2}
            returnKeyType="done"
          />
        </View>
      </View>

      <View style={styles.footer}>
        <TouchableOpacity
          style={[styles.button, !isValid && styles.buttonDisabled]}
          onPress={onNext}
          disabled={!isValid}
          activeOpacity={0.7}
        >
          <Text style={[styles.buttonText, !isValid && styles.buttonTextDisabled]}>
            [ NEXT ]
          </Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={onSkip} activeOpacity={0.7} style={styles.skipButton}>
          <Text style={styles.skipText}>SKIP — I DON'T KNOW MY BIRTH TIME</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.darkBg,
    padding: spacing.xl,
    justifyContent: 'space-between',
  },
  header: {
    paddingTop: spacing.xxl,
  },
  step: {
    ...typography.monoSmall,
    color: colors.amberDim,
    marginBottom: spacing.sm,
  },
  title: {
    ...typography.monoLarge,
    color: colors.amber,
    marginBottom: spacing.sm,
  },
  subtitle: {
    ...typography.serifMedium,
    color: colors.textMuted,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'center',
    gap: spacing.md,
  },
  inputGroup: {
    flex: 1,
    maxWidth: 120,
  },
  label: {
    ...typography.monoSmall,
    color: colors.brass,
    marginBottom: spacing.xs,
  },
  input: {
    ...typography.monoMedium,
    color: colors.cream,
    borderWidth: 1,
    borderColor: colors.brass,
    padding: spacing.md,
    textAlign: 'center',
  },
  colon: {
    ...typography.monoLarge,
    color: colors.amber,
    marginBottom: spacing.md,
  },
  footer: {
    paddingBottom: spacing.xxl,
    alignItems: 'center',
  },
  button: {
    borderWidth: 1,
    borderColor: colors.amber,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.xxl,
    marginBottom: spacing.md,
  },
  buttonDisabled: {
    borderColor: colors.muted,
  },
  buttonText: {
    ...typography.monoMedium,
    color: colors.amber,
  },
  buttonTextDisabled: {
    color: colors.muted,
  },
  skipButton: {
    padding: spacing.sm,
  },
  skipText: {
    ...typography.caption,
    color: colors.textMuted,
  },
});
