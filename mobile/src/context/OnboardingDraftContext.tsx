import React, { createContext, useContext, useState, useCallback } from 'react';

export interface OnboardingDraft {
  birthYear?: string;
  birthMonth?: string;
  birthDay?: string;
  birthHour?: string;
  birthMinute?: string;
  birthTimeSkipped?: boolean;
  latitude?: number;
  longitude?: number;
  locationLabel?: string;
  consentGiven?: boolean;
}

interface DraftContextValue {
  draft: OnboardingDraft;
  update: (partial: Partial<OnboardingDraft>) => void;
  reset: () => void;
}

const DraftContext = createContext<DraftContextValue | null>(null);

export function OnboardingDraftProvider({ children }: { children: React.ReactNode }) {
  const [draft, setDraft] = useState<OnboardingDraft>({});

  const update = useCallback((partial: Partial<OnboardingDraft>) => {
    setDraft((prev) => ({ ...prev, ...partial }));
  }, []);

  const reset = useCallback(() => setDraft({}), []);

  return (
    <DraftContext.Provider value={{ draft, update, reset }}>
      {children}
    </DraftContext.Provider>
  );
}

export function useDraft(): DraftContextValue {
  const ctx = useContext(DraftContext);
  if (!ctx) throw new Error('useDraft must be used within <OnboardingDraftProvider>');
  return ctx;
}
