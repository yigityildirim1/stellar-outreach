import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '../../theme';
import { analytics } from '../../services/analytics';

interface State {
  hasError: boolean;
  message: string | null;
}

interface Props {
  children: React.ReactNode;
  fallbackLabel?: string;
}

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false, message: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    analytics.track('error_boundary', {
      message: error.message,
      component: info.componentStack?.split('\n')[1]?.trim() ?? 'unknown',
    });
  }

  handleReset = () => {
    this.setState({ hasError: false, message: null });
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <View style={styles.container}>
        <Text style={styles.icon}>◉</Text>
        <Text style={styles.title}>SUBSYSTEM FAULT</Text>
        <Text style={styles.subtitle}>{this.props.fallbackLabel ?? 'A rendering error occurred.'}</Text>
        {this.state.message && (
          <Text style={styles.detail} numberOfLines={3}>{this.state.message}</Text>
        )}
        <TouchableOpacity onPress={this.handleReset} style={styles.btn}>
          <Text style={styles.btnText}>REINITIALIZE</Text>
        </TouchableOpacity>
      </View>
    );
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.darkBg,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xl,
  },
  icon: {
    color: colors.amber,
    fontSize: 48,
    marginBottom: spacing.md,
    opacity: 0.6,
  },
  title: {
    color: colors.amber,
    ...typography.monoSmall,
    fontSize: 18,
    letterSpacing: 2,
    marginBottom: spacing.sm,
  },
  subtitle: {
    color: colors.textSecondary,
    ...typography.monoSmall,
    fontSize: 13,
    textAlign: 'center',
    marginBottom: spacing.sm,
  },
  detail: {
    color: colors.textMuted,
    ...typography.monoSmall,
    fontSize: 11,
    textAlign: 'center',
    marginBottom: spacing.lg,
    opacity: 0.7,
  },
  btn: {
    borderWidth: 1,
    borderColor: colors.amber,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderRadius: 2,
  },
  btnText: {
    color: colors.amber,
    fontSize: 12,
    ...typography.monoSmall,
    letterSpacing: 1.5,
  },
});
