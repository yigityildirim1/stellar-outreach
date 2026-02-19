import React, { useState, useRef } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet,
  ScrollView, Dimensions, ActivityIndicator,
  NativeSyntheticEvent, NativeScrollEvent,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { colors, typography, spacing } from '../../theme';
import { useDraft } from '../../context/OnboardingDraftContext';
import { useAuth } from '../../context/AuthContext';
import { registerPlayer, completeOnboarding } from '../../services/auth';
import type { RootStackParamList } from '../../navigation/types';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

const PAGES = [
  {
    icon: '◉',
    title: 'YOUR COSMIC BRIEFING',
    body: 'Every day, NEXUS calculates your personal cosmic weather based on real planetary transits against your natal chart.',
  },
  {
    icon: '⬡',
    title: 'YOUR STATION',
    body: 'Manage 7 station modules powered by planetary energies. Collect resources, upgrade systems, and expand your deep space outpost.',
  },
  {
    icon: '✦',
    title: 'MISSIONS & GAMES',
    body: 'Complete daily missions, play mini-games, and maintain your check-in streak to earn rewards and level up.',
  },
  {
    icon: '◈',
    title: 'SOCIAL & CREW',
    body: 'Build relationships with NPC crew members, connect with friends via synastry, and join elemental guilds.',
  },
  {
    icon: '☆',
    title: 'DISCOVER THE COSMOS',
    body: 'Explore the Star Atlas, collect NASA discovery cards, track your cosmic passport, and unlock seasonal rewards.',
  },
];

export function TutorialScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const { draft } = useDraft();
  const { completeOnboarding: finishAuth } = useAuth();
  const [page, setPage] = useState(0);
  const [initializing, setInitializing] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);
  const scrollRef = useRef<ScrollView>(null);

  const isLastPage = page === PAGES.length - 1;

  const onScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const idx = Math.round(e.nativeEvent.contentOffset.x / SCREEN_WIDTH);
    if (idx !== page) setPage(idx);
  };

  const onInitialize = async () => {
    setInitializing(true);
    setInitError(null);
    try {
      // 1. Register player on backend
      const reg = await registerPlayer();
      if (!reg?.player_id) throw new Error('Server returned invalid response. Try again.');

      // 2. Complete onboarding on backend
      await completeOnboarding(reg.player_id);

      // 3. Build birth date string
      const birthDate = `${draft.birthYear}-${draft.birthMonth}-${draft.birthDay}`;
      const birthTime = draft.birthTimeSkipped
        ? undefined
        : `${draft.birthHour}:${draft.birthMinute}`;

      // 4. Persist to AsyncStorage via AuthContext
      await finishAuth({
        player_id: reg.player_id,
        birth_date: birthDate,
        birth_time: birthTime,
        latitude: draft.latitude ?? 0,
        longitude: draft.longitude ?? 0,
      });

      // Navigation will auto-switch to MainTabs via RootNavigator's isOnboarded check
    } catch (e: any) {
      setInitializing(false);
      const msg = e?.message ?? '';
      if (msg.includes('Network request failed') || msg.includes('fetch')) {
        setInitError('Cannot reach server. Make sure your Mac backend is running and phone is on the same WiFi.');
      } else {
        setInitError(msg || 'Initialization failed. Tap to retry.');
      }
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.step}>STEP 5 OF 5</Text>
        <Text style={styles.title}>STATION TOUR</Text>
      </View>

      <ScrollView
        ref={scrollRef}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onMomentumScrollEnd={onScroll}
        style={styles.carousel}
      >
        {PAGES.map((p, i) => (
          <View key={i} style={styles.page}>
            <Text style={styles.pageIcon}>{p.icon}</Text>
            <Text style={styles.pageTitle}>{p.title}</Text>
            <Text style={styles.pageBody}>{p.body}</Text>
          </View>
        ))}
      </ScrollView>

      {/* Page indicators */}
      <View style={styles.dots}>
        {PAGES.map((_, i) => (
          <View key={i} style={[styles.dot, i === page && styles.dotActive]} />
        ))}
      </View>

      <View style={styles.footer}>
        {initError && (
          <Text style={styles.errorText}>{initError}</Text>
        )}
        {isLastPage ? (
          <TouchableOpacity
            style={styles.initButton}
            onPress={onInitialize}
            disabled={initializing}
            activeOpacity={0.7}
          >
            {initializing ? (
              <ActivityIndicator color={colors.darkBg} size="small" />
            ) : (
              <Text style={styles.initButtonText}>[ INITIALIZE STATION ]</Text>
            )}
          </TouchableOpacity>
        ) : (
          <TouchableOpacity
            style={styles.nextButton}
            onPress={() => {
              scrollRef.current?.scrollTo({ x: (page + 1) * SCREEN_WIDTH, animated: true });
            }}
            activeOpacity={0.7}
          >
            <Text style={styles.nextButtonText}>[ NEXT ]</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.darkBg,
  },
  header: {
    paddingTop: spacing.xxl,
    paddingHorizontal: spacing.xl,
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
  carousel: {
    flex: 1,
  },
  page: {
    width: SCREEN_WIDTH,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: spacing.xxl,
  },
  pageIcon: {
    fontSize: 64,
    color: colors.amber,
    marginBottom: spacing.lg,
  },
  pageTitle: {
    ...typography.monoMedium,
    color: colors.cream,
    marginBottom: spacing.md,
    textAlign: 'center',
  },
  pageBody: {
    ...typography.serifMedium,
    color: colors.textMuted,
    textAlign: 'center',
  },
  dots: {
    flexDirection: 'row',
    justifyContent: 'center',
    paddingVertical: spacing.md,
    gap: spacing.sm,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.muted,
  },
  dotActive: {
    backgroundColor: colors.amber,
  },
  footer: {
    paddingBottom: spacing.xxl,
    alignItems: 'center',
    paddingHorizontal: spacing.xl,
  },
  nextButton: {
    borderWidth: 1,
    borderColor: colors.amber,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.xxl,
  },
  nextButtonText: {
    ...typography.monoMedium,
    color: colors.amber,
  },
  initButton: {
    backgroundColor: colors.amber,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.xxl,
    minWidth: 240,
    alignItems: 'center',
  },
  initButtonText: {
    ...typography.monoMedium,
    color: colors.darkBg,
  },
  errorText: {
    ...typography.monoSmall,
    color: colors.error,
    textAlign: 'center',
    marginBottom: spacing.sm,
    paddingHorizontal: spacing.md,
  },
});
