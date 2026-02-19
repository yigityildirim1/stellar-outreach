import React, {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';
import { AppState, AppStateStatus } from 'react-native';
import { checkConnectivity } from '../services/network';

interface NetworkState {
  isOnline: boolean;
  lastChecked: Date | null;
  recheck: () => Promise<void>;
}

const NetworkContext = createContext<NetworkState>({
  isOnline: true,
  lastChecked: null,
  recheck: async () => {},
});

const POLL_INTERVAL_MS = 30_000;

export function NetworkProvider({ children }: { children: React.ReactNode }) {
  const [isOnline, setIsOnline] = useState(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const recheck = async () => {
    const online = await checkConnectivity();
    setIsOnline(online);
    setLastChecked(new Date());
  };

  useEffect(() => {
    recheck();
    intervalRef.current = setInterval(recheck, POLL_INTERVAL_MS);

    const sub = AppState.addEventListener('change', (state: AppStateStatus) => {
      if (state === 'active') recheck();
    });

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      sub.remove();
    };
  }, []);

  return (
    <NetworkContext.Provider value={{ isOnline, lastChecked, recheck }}>
      {children}
    </NetworkContext.Provider>
  );
}

export function useNetwork(): NetworkState {
  return useContext(NetworkContext);
}
