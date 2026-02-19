import { Platform, TextStyle } from 'react-native';

const mono = Platform.select({ ios: 'Menlo', android: 'monospace' }) ?? 'monospace';
const serif = Platform.select({ ios: 'Georgia', android: 'serif' }) ?? 'serif';

export const typography: Record<string, TextStyle> = {
  // Monospace — terminal readouts, data, headers
  monoLarge: { fontFamily: mono, fontSize: 20, letterSpacing: 1.2 },
  monoMedium: { fontFamily: mono, fontSize: 16, letterSpacing: 0.8 },
  monoSmall: { fontFamily: mono, fontSize: 12, letterSpacing: 0.6 },

  // Serif — narrative text, dispatches
  serifLarge: { fontFamily: serif, fontSize: 20, lineHeight: 28 },
  serifMedium: { fontFamily: serif, fontSize: 16, lineHeight: 24 },
  serifSmall: { fontFamily: serif, fontSize: 14, lineHeight: 20 },

  // System — body, labels
  bodyLarge: { fontSize: 18, lineHeight: 26 },
  bodyMedium: { fontSize: 15, lineHeight: 22 },
  bodySmall: { fontSize: 13, lineHeight: 18 },
  caption: { fontSize: 11, lineHeight: 14, letterSpacing: 0.4 },
} as const;
