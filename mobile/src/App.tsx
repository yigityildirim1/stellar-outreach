import React, { useCallback, useEffect, useRef, useState } from 'react';
import { StatusBar } from 'react-native';
import { NavigationContainer, NavigationState } from '@react-navigation/native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { AuthProvider, useAuth } from './context/AuthContext';
import { NetworkProvider } from './context/NetworkContext';
import { RootNavigator } from './navigation/RootNavigator';
import { ErrorBoundary } from './components/shared/ErrorBoundary';
import { InAppNotification, NotificationPayload } from './components/shared/InAppNotification';
import { analytics } from './services/analytics';
import { notificationService } from './services/notifications';
import { colors } from './theme';

function getActiveRouteName(state: NavigationState | undefined): string {
  if (!state) return 'Unknown';
  const route = state.routes[state.index];
  if (route.state) return getActiveRouteName(route.state as NavigationState);
  return route.name;
}

function AppInner() {
  const { player } = useAuth();
  const [notification, setNotification] = useState<NotificationPayload | null>(null);
  const routeNameRef = useRef<string>('');

  // Init analytics when player is known
  useEffect(() => {
    if (player?.player_id) {
      analytics.init(player.player_id);
    }
  }, [player?.player_id]);

  // Check for pending in-app notifications on mount
  useEffect(() => {
    if (!player?.player_id || !player.latitude || !player.longitude) return;
    notificationService
      .checkForPendingNotification(player.player_id, player.latitude, player.longitude)
      .then(payload => {
        if (payload) setNotification(payload);
      });
  }, [player?.player_id]);

  const onNavigationReady = useCallback(() => {
    // No-op: routeNameRef initialized on first state change
  }, []);

  const onStateChange = useCallback(
    (state: NavigationState | undefined) => {
      const currentRoute = getActiveRouteName(state);
      if (currentRoute !== routeNameRef.current) {
        analytics.screenView(currentRoute);
        routeNameRef.current = currentRoute;
      }
    },
    [],
  );

  return (
    <>
      <NavigationContainer
        theme={{
          dark: true,
          colors: {
            primary: colors.amber,
            background: colors.darkBg,
            card: colors.darkBg,
            text: colors.textPrimary,
            border: colors.panelBg,
            notification: colors.amber,
          },
          fonts: {
            regular: { fontFamily: 'System', fontWeight: '400' },
            medium: { fontFamily: 'System', fontWeight: '500' },
            bold: { fontFamily: 'System', fontWeight: '700' },
            heavy: { fontFamily: 'System', fontWeight: '900' },
          },
        }}
        onReady={onNavigationReady}
        onStateChange={onStateChange}
      >
        <RootNavigator />
      </NavigationContainer>
      <InAppNotification
        notification={notification}
        onDismiss={() => setNotification(null)}
      />
    </>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <NetworkProvider>
        <AuthProvider>
          <SafeAreaProvider>
            <StatusBar barStyle="light-content" backgroundColor={colors.darkBg} />
            <AppInner />
          </SafeAreaProvider>
        </AuthProvider>
      </NetworkProvider>
    </ErrorBoundary>
  );
}
