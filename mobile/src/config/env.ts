import { Platform } from 'react-native';

// Android emulator uses 10.0.2.2 to reach host localhost
export const API_BASE_URL =
  Platform.OS === 'android'
    ? 'http://10.0.2.2:8080'
    : 'http://localhost:8080';
