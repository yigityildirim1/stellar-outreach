import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import type { OnboardingStackProps } from '../../navigation/types';

export function OnboardingSplashScreen({ navigation }: OnboardingStackProps<'OnboardingSplash'>) {
  return (
    <View style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.logo}>◉</Text>
        <Text style={styles.title}>NEXUS STATION</Text>
        <Text style={styles.subtitle}>STELLAR OUTREACH</Text>
        <Text style={styles.tagline}>Deep Space Research Institute{'\n'}L2 Lagrange Point</Text>
      </View>

      <TouchableOpacity
        style={styles.button}
        onPress={() => navigation.navigate('BirthDate')}
        activeOpacity={0.7}
      >
        <Text style={styles.buttonText}>[ BEGIN REGISTRATION ]</Text>
      </TouchableOpacity>

      <Text style={styles.version}>v0.2.0 — ONBOARDING</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.darkBg,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xl,
  },
  content: {
    alignItems: 'center',
    marginBottom: spacing.xxl,
  },
  logo: {
    fontSize: 64,
    color: colors.amber,
    marginBottom: spacing.lg,
  },
  title: {
    ...typography.monoLarge,
    color: colors.amber,
    marginBottom: spacing.xs,
  },
  subtitle: {
    ...typography.monoSmall,
    color: colors.brass,
    marginBottom: spacing.lg,
  },
  tagline: {
    ...typography.serifMedium,
    color: colors.textMuted,
    textAlign: 'center',
  },
  button: {
    borderWidth: 1,
    borderColor: colors.amber,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.xl,
    marginBottom: spacing.xxl,
  },
  buttonText: {
    ...typography.monoMedium,
    color: colors.amber,
  },
  version: {
    ...typography.caption,
    color: colors.textMuted,
    position: 'absolute',
    bottom: spacing.xxl,
  },
});
