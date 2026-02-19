import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Text } from 'react-native';
import { colors } from '../theme';
import type { MainTabParamList } from './types';
import { BriefingScreen } from '../screens/briefing/BriefingScreen';
import { StationScreen } from '../screens/station/StationScreen';
import { MissionsScreen } from '../screens/missions/MissionsScreen';
import { SocialScreen } from '../screens/social/SocialScreen';
import { ProfileScreen } from '../screens/profile/ProfileScreen';

const Tab = createBottomTabNavigator<MainTabParamList>();

const tabIcons: Record<keyof MainTabParamList, string> = {
  Briefing: '◉',
  Station: '⬡',
  Missions: '△',
  Social: '◇',
  Profile: '☆',
};

export function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarStyle: {
          backgroundColor: colors.tabBarBg,
          borderTopColor: colors.tabBarBorder,
          borderTopWidth: 1,
          height: 80,
          paddingBottom: 20,
          paddingTop: 8,
        },
        tabBarActiveTintColor: colors.tabActive,
        tabBarInactiveTintColor: colors.tabInactive,
        tabBarLabelStyle: {
          fontFamily: 'Menlo',
          fontSize: 10,
          letterSpacing: 0.5,
        },
        tabBarIcon: ({ color }) => (
          <Text style={{ color, fontSize: 20 }}>
            {tabIcons[route.name]}
          </Text>
        ),
      })}
    >
      <Tab.Screen name="Briefing" component={BriefingScreen} />
      <Tab.Screen name="Station" component={StationScreen} />
      <Tab.Screen name="Missions" component={MissionsScreen} />
      <Tab.Screen name="Social" component={SocialScreen} />
      <Tab.Screen name="Profile" component={ProfileScreen} />
    </Tab.Navigator>
  );
}
