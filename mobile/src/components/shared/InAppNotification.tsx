import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Animated,
  TouchableOpacity,
} from 'react-native';
import { colors, typography, spacing } from '../../theme';

export interface NotificationPayload {
  title: string;
  body: string;
  icon?: string;
}

interface Props {
  notification: NotificationPayload | null;
  onDismiss: () => void;
  durationMs?: number;
}

export function InAppNotification({ notification, onDismiss, durationMs = 4500 }: Props) {
  const slideY = useRef(new Animated.Value(-120)).current;
  const opacity = useRef(new Animated.Value(0)).current;
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!notification) return;

    // Slide in
    Animated.parallel([
      Animated.spring(slideY, {
        toValue: 0,
        tension: 60,
        friction: 10,
        useNativeDriver: true,
      }),
      Animated.timing(opacity, {
        toValue: 1,
        duration: 250,
        useNativeDriver: true,
      }),
    ]).start();

    timerRef.current = setTimeout(dismiss, durationMs);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [notification]);

  const dismiss = () => {
    Animated.parallel([
      Animated.timing(slideY, { toValue: -120, duration: 300, useNativeDriver: true }),
      Animated.timing(opacity, { toValue: 0, duration: 300, useNativeDriver: true }),
    ]).start(() => onDismiss());
  };

  if (!notification) return null;

  return (
    <Animated.View style={[styles.container, { transform: [{ translateY: slideY }], opacity }]}>
      <TouchableOpacity onPress={dismiss} activeOpacity={0.9} style={styles.card}>
        <Text style={styles.icon}>{notification.icon ?? '◈'}</Text>
        <View style={styles.textWrap}>
          <Text style={styles.title} numberOfLines={1}>{notification.title}</Text>
          <Text style={styles.body} numberOfLines={2}>{notification.body}</Text>
        </View>
        <Text style={styles.dismiss}>✕</Text>
      </TouchableOpacity>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 9999,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.lg,
  },
  card: {
    backgroundColor: '#1A1400',
    borderWidth: 1,
    borderColor: colors.amber,
    borderRadius: 4,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    gap: spacing.sm,
    shadowColor: colors.amber,
    shadowOpacity: 0.3,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 8,
  },
  icon: {
    color: colors.amber,
    fontSize: 20,
    width: 24,
    textAlign: 'center',
  },
  textWrap: {
    flex: 1,
  },
  title: {
    color: colors.amber,
    ...typography.monoSmall,
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 0.5,
    marginBottom: 2,
  },
  body: {
    color: colors.textSecondary,
    ...typography.monoSmall,
    lineHeight: 16,
  },
  dismiss: {
    color: colors.textMuted,
    fontSize: 12,
    paddingLeft: spacing.xs,
  },
});
