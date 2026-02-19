import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import { useDraft } from '../../context/OnboardingDraftContext';
import type { OnboardingStackProps } from '../../navigation/types';

export function ConsentScreen({ navigation }: OnboardingStackProps<'Consent'>) {
  const { update } = useDraft();
  const [accepted, setAccepted] = useState(false);

  const onNext = () => {
    update({ consentGiven: true });
    navigation.navigate('Tutorial');
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.step}>STEP 4 OF 5</Text>
        <Text style={styles.title}>DATA DISCLOSURE</Text>
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
        <Text style={styles.sectionTitle}>YOUR DATA, YOUR CONTROL</Text>
        <Text style={styles.body}>
          NEXUS STATION is designed with your privacy at its core.
          Here is exactly how your data is handled:
        </Text>

        <Text style={styles.bullet}>
          {'\u2022'} Your birth date, time, and location are stored ONLY on this device.
        </Text>
        <Text style={styles.bullet}>
          {'\u2022'} This data is NEVER uploaded to our servers or shared with third parties.
        </Text>
        <Text style={styles.bullet}>
          {'\u2022'} Your player ID (an anonymous UUID) is the only identifier stored server-side.
        </Text>
        <Text style={styles.bullet}>
          {'\u2022'} Natal chart calculations happen by sending coordinates to the backend,
          but these are not persisted.
        </Text>
        <Text style={styles.bullet}>
          {'\u2022'} You can delete all data at any time from the Profile screen.
        </Text>

        <Text style={styles.sectionTitle}>WHAT WE COLLECT</Text>
        <Text style={styles.body}>
          Only your anonymous player UUID and gameplay progress (station level, resources,
          streaks, etc.) are stored on the server. No personal information is retained.
        </Text>
      </ScrollView>

      <View style={styles.footer}>
        <TouchableOpacity
          style={styles.checkRow}
          onPress={() => setAccepted(!accepted)}
          activeOpacity={0.7}
        >
          <View style={[styles.checkbox, accepted && styles.checkboxChecked]}>
            {accepted && <Text style={styles.checkmark}>{'✓'}</Text>}
          </View>
          <Text style={styles.checkLabel}>
            I understand and consent to the data usage described above
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.button, !accepted && styles.buttonDisabled]}
          onPress={onNext}
          disabled={!accepted}
          activeOpacity={0.7}
        >
          <Text style={[styles.buttonText, !accepted && styles.buttonTextDisabled]}>
            [ PROCEED ]
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.darkBg,
    padding: spacing.xl,
  },
  header: {
    paddingTop: spacing.xxl,
    marginBottom: spacing.md,
  },
  step: {
    ...typography.monoSmall,
    color: colors.amberDim,
    marginBottom: spacing.sm,
  },
  title: {
    ...typography.monoLarge,
    color: colors.amber,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: spacing.lg,
  },
  sectionTitle: {
    ...typography.monoSmall,
    color: colors.amber,
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },
  body: {
    ...typography.serifMedium,
    color: colors.cream,
    marginBottom: spacing.sm,
  },
  bullet: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    paddingLeft: spacing.md,
    marginBottom: spacing.xs,
  },
  footer: {
    paddingBottom: spacing.xxl,
    alignItems: 'center',
  },
  checkRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.lg,
  },
  checkbox: {
    width: 24,
    height: 24,
    borderWidth: 1,
    borderColor: colors.brass,
    marginRight: spacing.sm,
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkboxChecked: {
    borderColor: colors.amber,
    backgroundColor: colors.cardBg,
  },
  checkmark: {
    color: colors.amber,
    fontSize: 16,
  },
  checkLabel: {
    ...typography.bodySmall,
    color: colors.cream,
    flex: 1,
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
