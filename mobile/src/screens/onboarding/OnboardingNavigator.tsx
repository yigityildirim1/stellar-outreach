import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import type { OnboardingStackParamList } from '../../navigation/types';
import { OnboardingDraftProvider } from '../../context/OnboardingDraftContext';
import { OnboardingSplashScreen } from './OnboardingSplashScreen';
import { BirthDateScreen } from './BirthDateScreen';
import { BirthTimeScreen } from './BirthTimeScreen';
import { BirthLocationScreen } from './BirthLocationScreen';
import { ConsentScreen } from './ConsentScreen';
import { TutorialScreen } from './TutorialScreen';

const Stack = createNativeStackNavigator<OnboardingStackParamList>();

export function OnboardingNavigator() {
  return (
    <OnboardingDraftProvider>
      <Stack.Navigator screenOptions={{ headerShown: false, animation: 'slide_from_right' }}>
        <Stack.Screen name="OnboardingSplash" component={OnboardingSplashScreen} />
        <Stack.Screen name="BirthDate" component={BirthDateScreen} />
        <Stack.Screen name="BirthTime" component={BirthTimeScreen} />
        <Stack.Screen name="BirthLocation" component={BirthLocationScreen} />
        <Stack.Screen name="Consent" component={ConsentScreen} />
        <Stack.Screen name="Tutorial" component={TutorialScreen} />
      </Stack.Navigator>
    </OnboardingDraftProvider>
  );
}
