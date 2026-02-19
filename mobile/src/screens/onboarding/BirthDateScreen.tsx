import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import { useDraft } from '../../context/OnboardingDraftContext';
import type { OnboardingStackProps } from '../../navigation/types';

export function BirthDateScreen({ navigation }: OnboardingStackProps<'BirthDate'>) {
  const { draft, update } = useDraft();
  const [year, setYear] = useState(draft.birthYear ?? '');
  const [month, setMonth] = useState(draft.birthMonth ?? '');
  const [day, setDay] = useState(draft.birthDay ?? '');

  const isValid =
    year.length === 4 &&
    month.length >= 1 && month.length <= 2 &&
    day.length >= 1 && day.length <= 2 &&
    Number(month) >= 1 && Number(month) <= 12 &&
    Number(day) >= 1 && Number(day) <= 31 &&
    Number(year) >= 1900 && Number(year) <= new Date().getFullYear();

  const onNext = () => {
    update({
      birthYear: year,
      birthMonth: month.padStart(2, '0'),
      birthDay: day.padStart(2, '0'),
    });
    navigation.navigate('BirthTime');
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.header}>
        <Text style={styles.step}>STEP 1 OF 5</Text>
        <Text style={styles.title}>BIRTH DATE</Text>
        <Text style={styles.subtitle}>
          Your natal chart requires an accurate date of birth.
          This data stays on your device only.
        </Text>
      </View>

      <View style={styles.inputRow}>
        <View style={styles.inputGroup}>
          <Text style={styles.label}>YEAR</Text>
          <TextInput
            style={styles.input}
            value={year}
            onChangeText={setYear}
            placeholder="1990"
            placeholderTextColor={colors.muted}
            keyboardType="number-pad"
            maxLength={4}
            returnKeyType="next"
          />
        </View>
        <View style={styles.inputGroup}>
          <Text style={styles.label}>MONTH</Text>
          <TextInput
            style={styles.input}
            value={month}
            onChangeText={setMonth}
            placeholder="06"
            placeholderTextColor={colors.muted}
            keyboardType="number-pad"
            maxLength={2}
            returnKeyType="next"
          />
        </View>
        <View style={styles.inputGroup}>
          <Text style={styles.label}>DAY</Text>
          <TextInput
            style={styles.input}
            value={day}
            onChangeText={setDay}
            placeholder="15"
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
    justifyContent: 'space-between',
    gap: spacing.md,
  },
  inputGroup: {
    flex: 1,
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
  footer: {
    paddingBottom: spacing.xxl,
    alignItems: 'center',
  },
  button: {
    borderWidth: 1,
    borderColor: colors.amber,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.xxl,
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
});
