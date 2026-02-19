// Matches briefing_to_dict() at cosmic_briefing.py:691-708

export interface ModuleStatus {
  module: string;
  status: string;       // "POWER" | "TROUBLE" | "PRESSURE" etc.
  description: string;
  transit_aspect: string;
}

export interface ModuleAlert {
  module: string;
  alert: string;
  severity: string;
}

export interface Archetype {
  sun_sign: string;
  moon_sign: string;
  rising_sign: string;
  element: string;
  modality: string;
  archetype_name: string;
  archetype_description: string;
}

export interface ElementColor {
  primary: string;
  secondary: string;
  accent: string;
  bg_gradient_start: string;
  bg_gradient_end: string;
}

export interface DiscoveryCard {
  title: string;
  date: string;
  explanation: string;
  url: string;
  media_type: string;
  hdurl?: string;
  copyright?: string;
}

export interface DailyBriefing {
  player_id: string;
  date: string;
  station_name: string;
  cosmic_briefing_text: string;
  daily_dispatch: string;
  module_statuses: ModuleStatus[];
  overall_mood: string;
  station_level: number;
  resources: Record<string, number>;
  resources_collected: Record<string, number>;
  module_alerts: ModuleAlert[];
  archetype: Archetype;
  element_color: ElementColor;
  discovery_card: DiscoveryCard;
  generated_at: string;
  is_cached: boolean;
}

// ─── Station (TASK-020) ──────────────────────────────────────

export interface StationModule {
  name: string;
  level: number;
  xp: number;
  xp_to_next: number;
  status: string;
  health: number;
  description: string;
  upgrade_cost?: Record<string, number>;
}

export interface Station {
  player_id: string;
  station_name: string;
  station_level: number;
  resources: Record<string, number>;
  modules: StationModule[];
  created_at?: string;
}

export interface CollectResult {
  collected: Record<string, number>;
  resources: Record<string, number>;
  next_collect_at?: string;
}

// ─── Missions ────────────────────────────────────────────────

export interface DailyMission {
  mission_id: string;
  title: string;
  description: string;
  difficulty: number;
  rewards: Record<string, number>;
  game_type?: string;
  expires_at?: string;
}

// ─── Streaks ─────────────────────────────────────────────────

export interface StreakData {
  player_id: string;
  current_streak: number;
  longest_streak: number;
  last_checkin?: string;
  can_checkin: boolean;
  freeze_count: number;
  next_milestone?: number;
  next_milestone_reward?: Record<string, number>;
}

// ─── NPC Crew ────────────────────────────────────────────────

export interface NpcSummary {
  npc_id: string;
  name: string;
  role: string;
  level: number;
  xp: number;
  xp_to_next: number;
  backstory?: string;
}

// ─── Friends ─────────────────────────────────────────────────

export interface FriendEntry {
  friend_id: string;
  since?: string;
  last_gift_sent?: string;
  last_gift_received?: string;
}

export interface FriendsList {
  player_id: string;
  friends: FriendEntry[];
  friend_count: number;
}

// ─── Guild ───────────────────────────────────────────────────

export interface GuildResponse {
  guild_id: string;
  name: string;
  element?: string;
  member_count: number;
  members?: Array<{ player_id: string; role: string }>;
  weekly_challenge?: {
    challenge_id: string;
    description: string;
    progress: number;
    target: number;
  };
}

// ─── Star Atlas ──────────────────────────────────────────────

export interface AtlasData {
  player_id: string;
  discovered: string[];
  total_objects: number;
  completion_pct: number;
  categories: Record<string, { discovered: number; total: number }>;
  recent_discoveries?: string[];
}

export interface CosmicPassport {
  player_id: string;
  stamps: PassportStamp[];
  total_stamps: number;
}

export interface PassportStamp {
  sign: string;
  collected: boolean;
  discovered_at?: string;
}

// ─── Season Pass ─────────────────────────────────────────────

export interface SeasonProgress {
  season_id: string;
  season_name: string;
  current_tier: number;
  max_tier: number;
  current_xp: number;
  xp_to_next: number;
  days_remaining: number;
  is_premium: boolean;
}

export interface PassStatus {
  has_premium: boolean;
  subscription_type?: string;
  expires_at?: string;
  benefits: string[];
}

// ─── Birth Chart ─────────────────────────────────────────────

export interface BirthChart {
  player_id: string;
  sun_sign: string;
  moon_sign: string;
  rising_sign: string;
  dominant_element: string;
  planets: Array<{
    planet: string;
    sign: string;
    degree: number;
    house?: number;
  }>;
  element_balance: Record<string, number>;
}

// ─── Wallet ──────────────────────────────────────────────────

export interface Wallet {
  player_id: string;
  stardust: number;
  gems: number;
}

// ─── Auth (TASK-021) ────────────────────────────────────────

export interface RegisterResponse {
  player_id: string;
  created_at: string;
  onboarded: boolean;
}

export interface AuthCheckResponse {
  exists: boolean;
  player_id: string;
  created_at?: string;
  onboarded?: boolean;
  onboarded_at?: string;
}
