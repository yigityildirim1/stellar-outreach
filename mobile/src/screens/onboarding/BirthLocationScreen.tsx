import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  KeyboardAvoidingView, Platform, ActivityIndicator, PermissionsAndroid,
} from 'react-native';
import { colors, typography, spacing } from '../../theme';
import { useDraft } from '../../context/OnboardingDraftContext';
import type { OnboardingStackProps } from '../../navigation/types';

async function requestGPS(): Promise<{ latitude: number; longitude: number } | null> {
  if (Platform.OS === 'android') {
    const granted = await PermissionsAndroid.request(
      PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
    );
    if (granted !== PermissionsAndroid.RESULTS.GRANTED) return null;
  }
  // iOS: location permission is declared in Info.plist (NSLocationWhenInUseUsageDescription)
  // and automatically prompted by the OS on first getCurrentPosition call.
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
      (_err) => resolve(null),
      { enableHighAccuracy: false, timeout: 15000 },
    );
  });
}

export function BirthLocationScreen({ navigation }: OnboardingStackProps<'BirthLocation'>) {
  const { draft, update } = useDraft();
  const [lat, setLat] = useState(draft.latitude?.toString() ?? '');
  const [lon, setLon] = useState(draft.longitude?.toString() ?? '');
  const [gpsLoading, setGpsLoading] = useState(false);

  const latNum = parseFloat(lat);
  const lonNum = parseFloat(lon);
  const isValid =
    !isNaN(latNum) && !isNaN(lonNum) &&
    latNum >= -90 && latNum <= 90 &&
    lonNum >= -180 && lonNum <= 180;

  const onGPS = async () => {
    setGpsLoading(true);
    const coords = await requestGPS();
    if (coords) {
      setLat(coords.latitude.toFixed(4));
      setLon(coords.longitude.toFixed(4));
    }
    setGpsLoading(false);
  };

  const onNext = () => {
    update({ latitude: latNum, longitude: lonNum });
    navigation.navigate('Consent');
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.header}>
        <Text style={styles.step}>STEP 3 OF 5</Text>
        <Text style={styles.title}>BIRTH LOCATION</Text>
        <Text style={styles.subtitle}>
          Location enables precise house placements and local sky calculations.
          Use GPS for your current location, or enter coordinates manually.
        </Text>
      </View>

      <View style={styles.body}>
        <TouchableOpacity style={styles.gpsButton} onPress={onGPS} activeOpacity={0.7} disabled={gpsLoading}>
          {gpsLoading ? (
            <ActivityIndicator color={colors.amber} size="small" />
          ) : (
            <Text style={styles.gpsText}>[ USE CURRENT LOCATION ]</Text>
          )}
        </TouchableOpacity>

        <Text style={styles.orText}>— OR ENTER MANUALLY —</Text>

        <View style={styles.inputRow}>
          <View style={styles.inputGroup}>
            <Text style={styles.label}>LATITUDE</Text>
            <TextInput
              style={styles.input}
              value={lat}
              onChangeText={setLat}
              placeholder="41.0082"
              placeholderTextColor={colors.muted}
              keyboardType="numeric"
              returnKeyType="next"
            />
          </View>
          <View style={styles.inputGroup}>
            <Text style={styles.label}>LONGITUDE</Text>
            <TextInput
              style={styles.input}
              value={lon}
              onChangeText={setLon}
              placeholder="28.9784"
              placeholderTextColor={colors.muted}
              keyboardType="numeric"
              returnKeyType="done"
            />
          </View>
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
  body: {
    alignItems: 'center',
  },
  gpsButton: {
    borderWidth: 1,
    borderColor: colors.amber,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.xl,
    marginBottom: spacing.md,
    minWidth: 240,
    alignItems: 'center',
  },
  gpsText: {
    ...typography.monoSmall,
    color: colors.amber,
  },
  orText: {
    ...typography.caption,
    color: colors.textMuted,
    marginVertical: spacing.md,
  },
  inputRow: {
    flexDirection: 'row',
    gap: spacing.md,
    width: '100%',
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
