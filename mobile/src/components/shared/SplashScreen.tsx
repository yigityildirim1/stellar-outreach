import React from 'react';
import { View, Text, ActivityIndicator, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';

export function SplashScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.logo}>◉</Text>
      <ActivityIndicator size="large" color={colors.amber} />
      <Text style={styles.text}>INITIALIZING SYSTEMS...</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.darkBg,
    justifyContent: 'center',
    alignItems: 'center',
  },
  logo: {
    fontSize: 48,
    color: colors.amber,
    marginBottom: spacing.lg,
  },
  text: {
    ...typography.monoSmall,
    color: colors.amberDim,
    marginTop: spacing.md,
  },
});
