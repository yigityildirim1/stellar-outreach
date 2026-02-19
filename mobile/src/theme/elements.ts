// Element color palettes — sourced from cosmic_briefing.py:81-110
export const elementColors = {
  Fire: {
    primary: '#DC2626',
    secondary: '#F59E0B',
    accent: '#FCD34D',
    bg_gradient_start: '#1A0A0A',
    bg_gradient_end: '#0A0A0A',
  },
  Earth: {
    primary: '#059669',
    secondary: '#92400E',
    accent: '#A16207',
    bg_gradient_start: '#0A1A0A',
    bg_gradient_end: '#0A0A0A',
  },
  Air: {
    primary: '#3B82F6',
    secondary: '#9CA3AF',
    accent: '#A78BFA',
    bg_gradient_start: '#0A0A1A',
    bg_gradient_end: '#0A0A0A',
  },
  Water: {
    primary: '#0891B2',
    secondary: '#0D9488',
    accent: '#E0E7FF',
    bg_gradient_start: '#0A0A1A',
    bg_gradient_end: '#0A0A0A',
  },
} as const;

export type Element = keyof typeof elementColors;
