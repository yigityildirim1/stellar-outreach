import { Platform } from 'react-native';

// Android emulator: 10.0.2.2 reaches host localhost
// iOS physical device: use Mac's local WiFi IP
// iOS simulator: localhost works fine
export const API_BASE_URL =
  Platform.OS === 'android'
    ? 'http://10.0.2.2:8080'
    : 'http://192.168.1.105:8080';
