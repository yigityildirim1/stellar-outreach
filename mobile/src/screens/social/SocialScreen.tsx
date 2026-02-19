import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  ActivityIndicator,
  StyleSheet,
  RefreshControl,
} from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { colors, typography, spacing } from '../../theme';
import { useAuth } from '../../context/AuthContext';
import { fetchNpcList, interactWithNpc } from '../../services/progression';
import { fetchFriends, sendGift, fetchGuild } from '../../services/social';
import type { NpcSummary, FriendsList, GuildResponse } from '../../types/stellar';
import { StationHeader } from '../../components/shared/StationHeader';
import { SegmentTabs } from '../../components/shared/SegmentTabs';
import { OfflineBanner } from '../../components/shared/OfflineBanner';
import { NpcCard } from '../../components/social/NpcCard';
import { FriendCard } from '../../components/social/FriendCard';
import { GuildPanel } from '../../components/social/GuildPanel';

const TABS = ['CREW', 'FRIENDS', 'GUILD'];

export function SocialScreen() {
  const { player } = useAuth();
  const playerId = player?.player_id ?? '';
  const [activeTab, setActiveTab] = useState(0);
  const [npcs, setNpcs] = useState<NpcSummary[] | null>(null);
  const [friends, setFriends] = useState<FriendsList | null>(null);
  const [guild, setGuild] = useState<GuildResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async () => {
    try {
      setError(null);
      const [npcRes, friendRes, guildRes] = await Promise.allSettled([
        fetchNpcList(playerId),
        fetchFriends(playerId),
        fetchGuild(playerId),
      ]);
      if (npcRes.status === 'fulfilled') setNpcs(npcRes.value);
      if (friendRes.status === 'fulfilled') setFriends(friendRes.value);
      if (guildRes.status === 'fulfilled') setGuild(guildRes.value);
      if (npcRes.status === 'rejected' && friendRes.status === 'rejected' && guildRes.status === 'rejected') {
        throw new Error('Failed to load social data');
      }
    } catch (e: any) {
      setError(e.message ?? 'Unknown error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  const onInteractNpc = async (npcId: string) => {
    try {
      await interactWithNpc(playerId, npcId);
      await loadData();
    } catch (_) {}
  };

  const onSendGift = async (friendId: string) => {
    try {
      await sendGift(playerId, friendId);
      await loadData();
    } catch (_) {}
  };

  if (loading) {
    return (
      <LinearGradient colors={['#0A0A1A', '#0A0A0A']} style={styles.center}>
        <ActivityIndicator size="large" color={colors.amber} />
        <Text style={styles.loadingText}>SCANNING FREQUENCIES...</Text>
      </LinearGradient>
    );
  }

  if (error) {
    return (
      <LinearGradient colors={['#0A0A1A', '#0A0A0A']} style={styles.center}>
        <Text style={styles.errorIcon}>◉</Text>
        <Text style={styles.errorTitle}>SIGNAL LOST</Text>
        <Text style={styles.errorMsg}>{error}</Text>
        <Text style={styles.retryHint}>Pull down to retry</Text>
      </LinearGradient>
    );
  }

  return (
    <LinearGradient colors={['#0A0A1A', '#0A0A0A']} style={styles.flex}>
      <StationHeader title="COMMUNICATIONS" />
      <OfflineBanner />
      <SegmentTabs tabs={TABS} activeIndex={activeTab} onTabPress={setActiveTab} />
      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={colors.amber}
          />
        }
      >
        {activeTab === 0 && (
          <View style={styles.section}>
            {npcs && npcs.length > 0 ? (
              npcs.map((npc) => (
                <NpcCard key={npc.npc_id} npc={npc} onInteract={onInteractNpc} />
              ))
            ) : (
              <Text style={styles.emptyText}>NO CREW DATA AVAILABLE</Text>
            )}
          </View>
        )}
        {activeTab === 1 && (
          <View style={styles.section}>
            {friends && friends.friends.length > 0 ? (
              friends.friends.map((f) => (
                <FriendCard key={f.friend_id} friend={f} onSendGift={onSendGift} />
              ))
            ) : (
              <Text style={styles.emptyText}>NO CONTACTS</Text>
            )}
          </View>
        )}
        {activeTab === 2 && (
          <View style={styles.section}>
            {guild ? (
              <GuildPanel guild={guild} onContribute={() => {}} />
            ) : (
              <Text style={styles.emptyText}>NO GUILD</Text>
            )}
          </View>
        )}
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    ...typography.monoSmall,
    color: colors.amber,
    marginTop: spacing.md,
  },
  errorIcon: {
    fontSize: 48,
    color: colors.error,
    marginBottom: spacing.md,
  },
  errorTitle: {
    ...typography.monoLarge,
    color: colors.error,
    marginBottom: spacing.sm,
  },
  errorMsg: {
    ...typography.bodySmall,
    color: colors.textMuted,
    textAlign: 'center',
    paddingHorizontal: spacing.xl,
    marginBottom: spacing.md,
  },
  retryHint: {
    ...typography.caption,
    color: colors.textMuted,
  },
  scrollContent: {
    paddingBottom: spacing.xxl,
  },
  section: {
    paddingHorizontal: spacing.md,
  },
  emptyText: {
    ...typography.monoSmall,
    color: colors.textMuted,
    textAlign: 'center',
    paddingVertical: spacing.xl,
  },
});
