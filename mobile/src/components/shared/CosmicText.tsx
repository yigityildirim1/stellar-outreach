import React from 'react';
import { Text, TextProps, StyleSheet } from 'react-native';
import { colors, typography } from '../../theme';

interface CosmicTextProps extends TextProps {
  variant?: 'mono' | 'serif' | 'body';
  size?: 'large' | 'medium' | 'small';
  color?: string;
}

export function CosmicText({
  variant = 'body',
  size = 'medium',
  color = colors.textPrimary,
  style,
  ...props
}: CosmicTextProps) {
  const key = `${variant === 'body' ? 'body' : variant}${size.charAt(0).toUpperCase() + size.slice(1)}` as keyof typeof typography;
  return (
    <Text
      style={[typography[key], { color }, style]}
      {...props}
    />
  );
}
