import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { BottomTabScreenProps } from '@react-navigation/bottom-tabs';

export type RootStackParamList = {
  Onboarding: undefined;
  MainTabs: undefined;
  Game: { gameId: string; gameName: string };
};

export type OnboardingStackParamList = {
  OnboardingSplash: undefined;
  BirthDate: undefined;
  BirthTime: undefined;
  BirthLocation: undefined;
  Consent: undefined;
  Tutorial: undefined;
};

export type MainTabParamList = {
  Briefing: undefined;
  Station: undefined;
  Missions: undefined;
  Social: undefined;
  Profile: undefined;
};

export type RootStackProps<T extends keyof RootStackParamList> =
  NativeStackScreenProps<RootStackParamList, T>;

export type OnboardingStackProps<T extends keyof OnboardingStackParamList> =
  NativeStackScreenProps<OnboardingStackParamList, T>;

export type MainTabProps<T extends keyof MainTabParamList> =
  BottomTabScreenProps<MainTabParamList, T>;
