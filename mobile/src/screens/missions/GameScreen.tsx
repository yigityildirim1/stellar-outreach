import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { colors, spacing, typography } from '../../theme';
import { useAuth } from '../../context/AuthContext';
import type { RootStackProps } from '../../navigation/types';
import {
  fetchAsteroidDeflection,
  fetchCircuitRepair,
  fetchDiplomacy,
  fetchHarvest,
  fetchSignalDecode,
  fetchSkyScanner,
  fetchStarPattern,
  scoreAsteroidDeflection,
  scoreCircuitRepair,
  scoreDiplomacy,
  scoreHarvest,
  scoreSignalDecode,
  scoreSkyScanner,
  scoreStarPattern,
} from '../../services/miniGames';

// ─── FETCH MAP ──────────────────────────────────────────────────────────────

const FETCH_MAP: Record<string, (id: string) => Promise<any>> = {
  diplomacy: fetchDiplomacy,
  'signal-decode': fetchSignalDecode,
  'star-pattern': fetchStarPattern,
  repair: fetchCircuitRepair,
  asteroid: fetchAsteroidDeflection,
  harvest: fetchHarvest,
  'sky-scanner': fetchSkyScanner,
};

// ─── RESULT OVERLAY ─────────────────────────────────────────────────────────

interface ResultOverlayProps {
  result: any;
  gameName: string;
  onClose: () => void;
}

function ResultOverlay({ result, gameName, onClose }: ResultOverlayProps) {
  const stardust = result?.stardust_earned ?? result?.reward?.stardust ?? 0;
  const xp = result?.xp_earned ?? result?.reward?.xp ?? 0;
  const success = result?.success ?? result?.correct ?? true;

  return (
    <View style={styles.overlay}>
      <View style={styles.resultCard}>
        <Text style={styles.resultIcon}>{success ? '✦' : '◉'}</Text>
        <Text style={styles.resultTitle}>{success ? 'MISSION COMPLETE' : 'MISSION FAILED'}</Text>
        <Text style={styles.resultGame}>{gameName.toUpperCase()}</Text>
        <View style={styles.rewardRow}>
          {stardust > 0 && (
            <View style={styles.rewardBadge}>
              <Text style={styles.rewardValue}>+{stardust}</Text>
              <Text style={styles.rewardLabel}>STARDUST</Text>
            </View>
          )}
          {xp > 0 && (
            <View style={styles.rewardBadge}>
              <Text style={styles.rewardValue}>+{xp}</Text>
              <Text style={styles.rewardLabel}>XP</Text>
            </View>
          )}
        </View>
        <TouchableOpacity style={styles.closeBtn} onPress={onClose}>
          <Text style={styles.closeBtnText}>RETURN TO STATION</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

// ─── DIPLOMACY GAME ──────────────────────────────────────────────────────────

function DiplomacyGame({
  data,
  playerId,
  onComplete,
}: {
  data: any;
  playerId: string;
  onComplete: (result: any) => void;
}) {
  const startTime = useRef(Date.now());
  const [submitting, setSubmitting] = useState(false);

  const scenario = data?.scenario ?? 'A crew conflict requires mediation.';
  const characters = data?.characters ?? [];
  const choices: string[] = data?.choices ?? data?.options ?? [];
  const scenarioId = data?.scenario_id ?? data?.id ?? 'default';

  const handleChoice = async (index: number) => {
    setSubmitting(true);
    try {
      const result = await scoreDiplomacy({
        player_id: playerId,
        scenario_id: scenarioId,
        choice_index: index,
        time_taken: Math.round((Date.now() - startTime.current) / 1000),
      });
      onComplete(result);
    } catch {
      onComplete({ success: false, stardust_earned: 0 });
    }
    setSubmitting(false);
  };

  return (
    <ScrollView style={styles.gameContainer} contentContainerStyle={styles.gameContent}>
      <Text style={styles.gameLabel}>CREW DIPLOMACY</Text>
      <View style={styles.scenarioBox}>
        {characters.length > 0 && (
          <Text style={styles.scenarioChars}>
            {characters.join(' • ')}
          </Text>
        )}
        <Text style={styles.scenarioText}>{scenario}</Text>
      </View>
      <Text style={styles.choicePrompt}>SELECT YOUR RESPONSE:</Text>
      {choices.map((choice: string, i: number) => (
        <TouchableOpacity
          key={i}
          style={styles.choiceBtn}
          onPress={() => handleChoice(i)}
          disabled={submitting}
        >
          <Text style={styles.choiceIndex}>{String.fromCharCode(65 + i)}</Text>
          <Text style={styles.choiceText}>{choice}</Text>
        </TouchableOpacity>
      ))}
      {submitting && <ActivityIndicator color={colors.amber} style={{ marginTop: spacing.lg }} />}
    </ScrollView>
  );
}

// ─── SIGNAL DECODE GAME ──────────────────────────────────────────────────────

function SignalDecodeGame({
  data,
  playerId,
  onComplete,
}: {
  data: any;
  playerId: string;
  onComplete: (result: any) => void;
}) {
  const startTime = useRef(Date.now());
  const [answer, setAnswer] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const encoded = data?.encoded_message ?? data?.signal ?? '--- ... ---';
  const clue = data?.clue ?? data?.hint ?? 'Decode the transmission.';
  const signalId = data?.signal_id ?? data?.id ?? 'default';

  // Parse into segments for display
  const segments = encoded.split(' ');

  const handleSubmit = async () => {
    if (!answer.trim()) return;
    setSubmitting(true);
    try {
      const result = await scoreSignalDecode({
        player_id: playerId,
        signal_id: signalId,
        decoded_answer: answer.trim().toUpperCase(),
        time_taken: Math.round((Date.now() - startTime.current) / 1000),
      });
      onComplete(result);
    } catch {
      onComplete({ success: false, stardust_earned: 0 });
    }
    setSubmitting(false);
  };

  return (
    <ScrollView style={styles.gameContainer} contentContainerStyle={styles.gameContent}>
      <Text style={styles.gameLabel}>SIGNAL DECODE</Text>
      <View style={styles.scenarioBox}>
        <Text style={styles.signalDisplay}>{segments.join('  ')}</Text>
        <Text style={styles.scenarioText}>{clue}</Text>
      </View>
      <Text style={styles.choicePrompt}>ENTER DECODED MESSAGE:</Text>
      <View style={styles.inputRow}>
        {/* Simulated keyboard input via letter buttons */}
        <View style={styles.answerDisplay}>
          <Text style={styles.answerText}>{answer || '_'}</Text>
        </View>
      </View>
      {/* Alphabet pad */}
      <View style={styles.alphaPad}>
        {'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').map((ch) => (
          <TouchableOpacity
            key={ch}
            style={styles.alphaKey}
            onPress={() => setAnswer((a) => a + ch)}
            disabled={submitting}
          >
            <Text style={styles.alphaKeyText}>{ch}</Text>
          </TouchableOpacity>
        ))}
        <TouchableOpacity
          style={[styles.alphaKey, styles.alphaDelete]}
          onPress={() => setAnswer((a) => a.slice(0, -1))}
          disabled={submitting}
        >
          <Text style={styles.alphaKeyText}>⌫</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.alphaKey, styles.alphaSpace]}
          onPress={() => setAnswer((a) => a + ' ')}
          disabled={submitting}
        >
          <Text style={styles.alphaKeyText}>SPACE</Text>
        </TouchableOpacity>
      </View>
      <TouchableOpacity
        style={[styles.submitBtn, !answer.trim() && styles.submitBtnDisabled]}
        onPress={handleSubmit}
        disabled={!answer.trim() || submitting}
      >
        <Text style={styles.submitBtnText}>
          {submitting ? 'TRANSMITTING...' : 'TRANSMIT ANSWER'}
        </Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

// ─── STAR PATTERN GAME ───────────────────────────────────────────────────────

function StarPatternGame({
  data,
  playerId,
  onComplete,
}: {
  data: any;
  playerId: string;
  onComplete: (result: any) => void;
}) {
  const startTime = useRef(Date.now());
  const [selected, setSelected] = useState<number[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const constellation = data?.constellation ?? data?.name ?? 'UNKNOWN';
  const stars: Array<{ id: number; x: number; y: number }> =
    data?.stars ?? Array.from({ length: 9 }, (_, i) => ({ id: i, x: i % 3, y: Math.floor(i / 3) }));
  const patternId = data?.pattern_id ?? data?.id ?? 'default';
  const targetLength: number = data?.pattern?.length ?? stars.length;

  const toggleStar = (id: number) => {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((s) => s !== id);
      if (prev.length >= targetLength) return prev;
      return [...prev, id];
    });
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const result = await scoreStarPattern({
        player_id: playerId,
        pattern_id: patternId,
        selected_sequence: selected,
        time_taken: Math.round((Date.now() - startTime.current) / 1000),
      });
      onComplete(result);
    } catch {
      onComplete({ success: false, stardust_earned: 0 });
    }
    setSubmitting(false);
  };

  // Arrange stars in a grid (max 5 cols)
  const COLS = 5;
  const rows: typeof stars[] = [];
  for (let i = 0; i < stars.length; i += COLS) {
    rows.push(stars.slice(i, i + COLS));
  }

  return (
    <ScrollView style={styles.gameContainer} contentContainerStyle={styles.gameContent}>
      <Text style={styles.gameLabel}>STAR PATTERN</Text>
      <View style={styles.scenarioBox}>
        <Text style={styles.constellationName}>{constellation}</Text>
        <Text style={styles.scenarioText}>
          Select {targetLength} stars in the correct sequence to form the constellation.
        </Text>
      </View>
      <View style={styles.starGrid}>
        {rows.map((row, ri) => (
          <View key={ri} style={styles.starRow}>
            {row.map((star) => {
              const selIdx = selected.indexOf(star.id);
              const isSel = selIdx !== -1;
              return (
                <TouchableOpacity
                  key={star.id}
                  style={[styles.starBtn, isSel && styles.starBtnSelected]}
                  onPress={() => toggleStar(star.id)}
                  disabled={submitting}
                >
                  <Text style={[styles.starBtnText, isSel && styles.starBtnTextSelected]}>
                    {isSel ? String(selIdx + 1) : '✦'}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>
        ))}
      </View>
      <Text style={styles.selectionCount}>
        {selected.length}/{targetLength} STARS SELECTED
      </Text>
      <TouchableOpacity
        style={[styles.submitBtn, selected.length < targetLength && styles.submitBtnDisabled]}
        onPress={handleSubmit}
        disabled={selected.length < targetLength || submitting}
      >
        <Text style={styles.submitBtnText}>
          {submitting ? 'COMPUTING...' : 'LOCK CONSTELLATION'}
        </Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

// ─── CIRCUIT REPAIR GAME ─────────────────────────────────────────────────────

function CircuitRepairGame({
  data,
  playerId,
  onComplete,
}: {
  data: any;
  playerId: string;
  onComplete: (result: any) => void;
}) {
  const startTime = useRef(Date.now());
  const [repairsMade, setRepairsMade] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  const damagedNodes: number = data?.damaged_nodes ?? data?.node_count ?? 5;
  const circuitId = data?.circuit_id ?? data?.id ?? 'default';
  const description = data?.description ?? 'Station circuits are damaged. Repair all nodes.';

  const handleRepair = () => {
    if (repairsMade < damagedNodes) {
      setRepairsMade((r) => r + 1);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const result = await scoreCircuitRepair({
        player_id: playerId,
        circuit_id: circuitId,
        repairs_made: repairsMade,
        time_taken: Math.round((Date.now() - startTime.current) / 1000),
      });
      onComplete(result);
    } catch {
      onComplete({ success: false, stardust_earned: 0 });
    }
    setSubmitting(false);
  };

  const progress = damagedNodes > 0 ? repairsMade / damagedNodes : 0;

  return (
    <View style={styles.gameContainer}>
      <View style={styles.gameContent}>
        <Text style={styles.gameLabel}>CIRCUIT REPAIR</Text>
        <View style={styles.scenarioBox}>
          <Text style={styles.scenarioText}>{description}</Text>
        </View>
        {/* Circuit diagram */}
        <View style={styles.circuitPanel}>
          {Array.from({ length: damagedNodes }).map((_, i) => {
            const repaired = i < repairsMade;
            return (
              <View key={i} style={[styles.circuitNode, repaired && styles.circuitNodeRepaired]}>
                <Text style={styles.circuitNodeText}>{repaired ? '■' : '□'}</Text>
                <Text style={styles.circuitNodeLabel}>NODE {i + 1}</Text>
              </View>
            );
          })}
        </View>
        {/* Progress bar */}
        <View style={styles.progressBarBg}>
          <View style={[styles.progressBarFill, { width: `${progress * 100}%` }]} />
        </View>
        <Text style={styles.selectionCount}>
          {repairsMade}/{damagedNodes} NODES REPAIRED
        </Text>
        <TouchableOpacity
          style={[styles.repairBtn, repairsMade >= damagedNodes && styles.repairBtnDone]}
          onPress={handleRepair}
          disabled={repairsMade >= damagedNodes || submitting}
        >
          <Text style={styles.submitBtnText}>
            {repairsMade >= damagedNodes ? 'ALL REPAIRED' : 'REPAIR NODE'}
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.submitBtn, repairsMade === 0 && styles.submitBtnDisabled]}
          onPress={handleSubmit}
          disabled={repairsMade === 0 || submitting}
        >
          <Text style={styles.submitBtnText}>
            {submitting ? 'PROCESSING...' : 'SUBMIT REPAIRS'}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

// ─── ASTEROID DEFLECTION GAME ────────────────────────────────────────────────

function AsteroidGame({
  data,
  playerId,
  onComplete,
}: {
  data: any;
  playerId: string;
  onComplete: (result: any) => void;
}) {
  const startTime = useRef(Date.now());
  const [submitting, setSubmitting] = useState(false);

  const trajectory = data?.trajectory ?? data?.description ?? 'Incoming asteroid on collision course.';
  const options: Array<{ angle: number; label: string }> =
    data?.options ??
    [15, 30, 45, 60].map((a) => ({ angle: a, label: `${a}°` }));
  const asteroidId = data?.asteroid_id ?? data?.id ?? 'default';

  const handleSelect = async (angle: number) => {
    setSubmitting(true);
    try {
      const result = await scoreAsteroidDeflection({
        player_id: playerId,
        asteroid_id: asteroidId,
        selected_angle: angle,
        time_taken: Math.round((Date.now() - startTime.current) / 1000),
      });
      onComplete(result);
    } catch {
      onComplete({ success: false, stardust_earned: 0 });
    }
    setSubmitting(false);
  };

  return (
    <ScrollView style={styles.gameContainer} contentContainerStyle={styles.gameContent}>
      <Text style={styles.gameLabel}>ASTEROID DEFLECTION</Text>
      <View style={styles.scenarioBox}>
        <Text style={styles.scenarioText}>{trajectory}</Text>
      </View>
      <Text style={styles.choicePrompt}>SELECT DEFLECTION ANGLE:</Text>
      {options.map((opt, i) => {
        const angle = typeof opt === 'number' ? opt : opt.angle;
        const label = typeof opt === 'object' ? (opt.label ?? `${angle}°`) : `${opt}°`;
        return (
          <TouchableOpacity
            key={i}
            style={styles.choiceBtn}
            onPress={() => handleSelect(angle)}
            disabled={submitting}
          >
            <Text style={styles.choiceIndex}>{String.fromCharCode(65 + i)}</Text>
            <Text style={styles.choiceText}>{label}</Text>
          </TouchableOpacity>
        );
      })}
      {submitting && <ActivityIndicator color={colors.amber} style={{ marginTop: spacing.lg }} />}
    </ScrollView>
  );
}

// ─── HARVEST GAME ────────────────────────────────────────────────────────────

function HarvestGame({
  data,
  playerId,
  onComplete,
}: {
  data: any;
  playerId: string;
  onComplete: (result: any) => void;
}) {
  const startTime = useRef(Date.now());
  const [harvested, setHarvested] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);

  // Backend returns resource_grid as object like {A1: 'stardust', B2: 'crystal', ...}
  const resourceGrid: Record<string, string> = data?.resource_grid ?? {};
  const harvestId = data?.harvest_id ?? data?.id ?? 'default';
  const cells = Object.keys(resourceGrid);

  const toggleCell = (cell: string) => {
    setHarvested((prev) => {
      const next = new Set(prev);
      if (next.has(cell)) next.delete(cell);
      else next.add(cell);
      return next;
    });
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const result = await scoreHarvest({
        player_id: playerId,
        harvest_id: harvestId,
        cells_harvested: Array.from(harvested),
        time_taken: Math.round((Date.now() - startTime.current) / 1000),
      });
      onComplete(result);
    } catch {
      onComplete({ success: false, stardust_earned: 0 });
    }
    setSubmitting(false);
  };

  // Build grid rows (assume cell names like A1, A2 ... B1, B2)
  const COLS = 4;
  const rows: string[][] = [];
  for (let i = 0; i < cells.length; i += COLS) {
    rows.push(cells.slice(i, i + COLS));
  }

  return (
    <ScrollView style={styles.gameContainer} contentContainerStyle={styles.gameContent}>
      <Text style={styles.gameLabel}>COSMIC HARVEST</Text>
      <View style={styles.scenarioBox}>
        <Text style={styles.scenarioText}>
          Tap resource cells to harvest. Collect as many as you can.
        </Text>
      </View>
      <View style={styles.harvestGrid}>
        {rows.map((row, ri) => (
          <View key={ri} style={styles.harvestRow}>
            {row.map((cell) => {
              const resource = resourceGrid[cell];
              const isHarvested = harvested.has(cell);
              return (
                <TouchableOpacity
                  key={cell}
                  style={[styles.harvestCell, isHarvested && styles.harvestCellActive]}
                  onPress={() => toggleCell(cell)}
                  disabled={submitting}
                >
                  <Text style={styles.harvestCellResource}>
                    {resource === 'stardust' ? '✦' : resource === 'crystal' ? '◆' : '●'}
                  </Text>
                  <Text style={styles.harvestCellId}>{cell}</Text>
                </TouchableOpacity>
              );
            })}
          </View>
        ))}
      </View>
      <Text style={styles.selectionCount}>
        {harvested.size}/{cells.length} CELLS HARVESTED
      </Text>
      <TouchableOpacity
        style={[styles.submitBtn, harvested.size === 0 && styles.submitBtnDisabled]}
        onPress={handleSubmit}
        disabled={harvested.size === 0 || submitting}
      >
        <Text style={styles.submitBtnText}>
          {submitting ? 'TRANSMITTING...' : 'COLLECT HARVEST'}
        </Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

// ─── SKY SCANNER GAME ────────────────────────────────────────────────────────

function SkyScannerGame({
  data,
  playerId,
  onComplete,
}: {
  data: any;
  playerId: string;
  onComplete: (result: any) => void;
}) {
  const startTime = useRef(Date.now());
  const [submitting, setSubmitting] = useState(false);

  const objectData = data?.object_data ?? {};
  const description = objectData?.description ?? data?.description ?? 'Unknown celestial object detected.';
  const clues: string[] = objectData?.clues ?? data?.clues ?? [];
  const candidates: string[] = data?.candidates ?? data?.options ?? [];
  const scanId = data?.scan_id ?? data?.id ?? 'default';

  const handleSelect = async (selected: string) => {
    setSubmitting(true);
    try {
      const result = await scoreSkyScanner({
        player_id: playerId,
        scan_id: scanId,
        selected_object: selected,
        time_taken: Math.round((Date.now() - startTime.current) / 1000),
      });
      onComplete(result);
    } catch {
      onComplete({ success: false, stardust_earned: 0 });
    }
    setSubmitting(false);
  };

  return (
    <ScrollView style={styles.gameContainer} contentContainerStyle={styles.gameContent}>
      <Text style={styles.gameLabel}>SKY SCANNER</Text>
      <View style={styles.scenarioBox}>
        <Text style={styles.scenarioText}>{description}</Text>
        {clues.length > 0 && (
          <View style={{ marginTop: spacing.sm }}>
            {clues.map((clue, i) => (
              <Text key={i} style={styles.clueText}>• {clue}</Text>
            ))}
          </View>
        )}
      </View>
      <Text style={styles.choicePrompt}>IDENTIFY THE OBJECT:</Text>
      {candidates.map((candidate, i) => (
        <TouchableOpacity
          key={i}
          style={styles.choiceBtn}
          onPress={() => handleSelect(candidate)}
          disabled={submitting}
        >
          <Text style={styles.choiceIndex}>{String.fromCharCode(65 + i)}</Text>
          <Text style={styles.choiceText}>{candidate}</Text>
        </TouchableOpacity>
      ))}
      {submitting && <ActivityIndicator color={colors.amber} style={{ marginTop: spacing.lg }} />}
    </ScrollView>
  );
}

// ─── GAME RENDERER ───────────────────────────────────────────────────────────

function renderGame(
  gameId: string,
  data: any,
  playerId: string,
  onComplete: (result: any) => void,
) {
  switch (gameId) {
    case 'diplomacy':
      return <DiplomacyGame data={data} playerId={playerId} onComplete={onComplete} />;
    case 'signal-decode':
      return <SignalDecodeGame data={data} playerId={playerId} onComplete={onComplete} />;
    case 'star-pattern':
      return <StarPatternGame data={data} playerId={playerId} onComplete={onComplete} />;
    case 'repair':
      return <CircuitRepairGame data={data} playerId={playerId} onComplete={onComplete} />;
    case 'asteroid':
      return <AsteroidGame data={data} playerId={playerId} onComplete={onComplete} />;
    case 'harvest':
      return <HarvestGame data={data} playerId={playerId} onComplete={onComplete} />;
    case 'sky-scanner':
      return <SkyScannerGame data={data} playerId={playerId} onComplete={onComplete} />;
    default:
      return <Text style={{ color: colors.textMuted, padding: spacing.lg }}>Unknown game: {gameId}</Text>;
  }
}

// ─── MAIN SCREEN ─────────────────────────────────────────────────────────────

type GameScreenProps = RootStackProps<'Game'>;

export function GameScreen({ route, navigation }: GameScreenProps) {
  const { gameId, gameName } = route.params;
  const { player } = useAuth();
  const playerId = player?.player_id ?? '';

  const [gameData, setGameData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    const fetchFn = FETCH_MAP[gameId];
    if (!fetchFn) {
      setError(`Unknown game: ${gameId}`);
      setLoading(false);
      return;
    }
    fetchFn(playerId)
      .then((data) => {
        setGameData(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err?.message ?? 'Failed to load game');
        setLoading(false);
      });
  }, [gameId, playerId]);

  const handleComplete = (res: any) => {
    setResult(res);
  };

  const handleClose = () => {
    navigation.goBack();
  };

  return (
    <LinearGradient colors={['#1A0A0A', '#0A0A0A']} style={styles.flex}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={handleClose}>
          <Text style={styles.backBtnText}>← ABORT</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>{gameName.toUpperCase()}</Text>
        <View style={styles.backBtn} />
      </View>

      {/* Content */}
      {loading && (
        <View style={styles.centerState}>
          <ActivityIndicator size="large" color={colors.amber} />
          <Text style={styles.loadingText}>INITIALIZING GAME...</Text>
        </View>
      )}

      {!loading && error && (
        <View style={styles.centerState}>
          <Text style={styles.errorIcon}>◉</Text>
          <Text style={styles.errorTitle}>SYSTEM ERROR</Text>
          <Text style={styles.errorMsg}>{error}</Text>
          <TouchableOpacity style={styles.submitBtn} onPress={handleClose}>
            <Text style={styles.submitBtnText}>RETURN TO STATION</Text>
          </TouchableOpacity>
        </View>
      )}

      {!loading && !error && gameData && !result &&
        renderGame(gameId, gameData, playerId, handleComplete)}

      {result && (
        <ResultOverlay result={result} gameName={gameName} onClose={handleClose} />
      )}
    </LinearGradient>
  );
}

// ─── STYLES ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  flex: { flex: 1 },

  // Header
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    paddingTop: spacing.xl,
    paddingBottom: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.panelBg,
  },
  backBtn: {
    width: 80,
  },
  backBtnText: {
    ...typography.monoSmall,
    color: colors.amber,
  },
  headerTitle: {
    flex: 1,
    ...typography.monoSmall,
    color: colors.cream,
    textAlign: 'center',
    letterSpacing: 2,
  },

  // Loading / Error
  centerState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xl,
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
    marginBottom: spacing.lg,
  },

  // Game container
  gameContainer: {
    flex: 1,
  },
  gameContent: {
    padding: spacing.md,
    paddingBottom: spacing.xxl,
  },
  gameLabel: {
    ...typography.caption,
    color: colors.amber,
    letterSpacing: 3,
    marginBottom: spacing.md,
  },

  // Scenario box
  scenarioBox: {
    backgroundColor: colors.cardBg,
    borderWidth: 1,
    borderColor: colors.panelBg,
    padding: spacing.md,
    marginBottom: spacing.lg,
  },
  scenarioChars: {
    ...typography.caption,
    color: colors.amber,
    marginBottom: spacing.xs,
    letterSpacing: 1,
  },
  scenarioText: {
    ...typography.bodySmall,
    color: colors.cream,
    lineHeight: 20,
  },

  // Choices
  choicePrompt: {
    ...typography.caption,
    color: colors.textMuted,
    letterSpacing: 2,
    marginBottom: spacing.sm,
  },
  choiceBtn: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: colors.cardBg,
    borderWidth: 1,
    borderColor: colors.panelBg,
    padding: spacing.sm,
    marginBottom: spacing.xs,
  },
  choiceIndex: {
    ...typography.monoSmall,
    color: colors.amber,
    width: 24,
    marginRight: spacing.xs,
  },
  choiceText: {
    ...typography.bodySmall,
    color: colors.cream,
    flex: 1,
  },

  // Signal decode
  signalDisplay: {
    ...typography.monoSmall,
    color: colors.amber,
    letterSpacing: 4,
    fontSize: 16,
    marginBottom: spacing.sm,
    textAlign: 'center',
  },
  inputRow: {
    marginBottom: spacing.sm,
  },
  answerDisplay: {
    backgroundColor: colors.panelBg,
    padding: spacing.sm,
    borderWidth: 1,
    borderColor: colors.amber,
    alignItems: 'center',
  },
  answerText: {
    ...typography.monoSmall,
    color: colors.amber,
    fontSize: 18,
    letterSpacing: 3,
  },
  alphaPad: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    marginBottom: spacing.md,
    gap: 4,
  },
  alphaKey: {
    width: 36,
    height: 36,
    backgroundColor: colors.cardBg,
    borderWidth: 1,
    borderColor: colors.panelBg,
    justifyContent: 'center',
    alignItems: 'center',
  },
  alphaDelete: {
    width: 50,
    backgroundColor: colors.panelBg,
  },
  alphaSpace: {
    width: 80,
  },
  alphaKeyText: {
    ...typography.caption,
    color: colors.cream,
    fontSize: 11,
  },
  clueText: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: 4,
  },

  // Star pattern
  constellationName: {
    ...typography.monoLarge,
    color: colors.amber,
    marginBottom: spacing.xs,
    textAlign: 'center',
  },
  starGrid: {
    marginBottom: spacing.md,
  },
  starRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginBottom: spacing.xs,
  },
  starBtn: {
    width: 52,
    height: 52,
    margin: 4,
    backgroundColor: colors.cardBg,
    borderWidth: 1,
    borderColor: colors.panelBg,
    justifyContent: 'center',
    alignItems: 'center',
  },
  starBtnSelected: {
    backgroundColor: colors.amber,
    borderColor: colors.amber,
  },
  starBtnText: {
    ...typography.monoSmall,
    color: colors.textMuted,
    fontSize: 16,
  },
  starBtnTextSelected: {
    color: '#1A0A0A',
  },
  selectionCount: {
    ...typography.caption,
    color: colors.textMuted,
    textAlign: 'center',
    marginBottom: spacing.md,
    letterSpacing: 1,
  },

  // Circuit repair
  circuitPanel: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    marginBottom: spacing.md,
    gap: spacing.sm,
  },
  circuitNode: {
    width: 64,
    height: 64,
    backgroundColor: colors.cardBg,
    borderWidth: 1,
    borderColor: colors.error,
    justifyContent: 'center',
    alignItems: 'center',
    margin: 4,
  },
  circuitNodeRepaired: {
    borderColor: colors.amber,
    backgroundColor: '#1A1200',
  },
  circuitNodeText: {
    fontSize: 24,
    color: colors.cream,
  },
  circuitNodeLabel: {
    ...typography.caption,
    color: colors.textMuted,
    fontSize: 9,
    marginTop: 2,
  },
  progressBarBg: {
    height: 4,
    backgroundColor: colors.panelBg,
    marginBottom: spacing.sm,
    marginHorizontal: spacing.md,
  },
  progressBarFill: {
    height: 4,
    backgroundColor: colors.amber,
  },
  repairBtn: {
    backgroundColor: colors.amber,
    padding: spacing.md,
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  repairBtnDone: {
    backgroundColor: colors.panelBg,
  },

  // Harvest
  harvestGrid: {
    marginBottom: spacing.md,
  },
  harvestRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginBottom: spacing.xs,
  },
  harvestCell: {
    width: 64,
    height: 64,
    margin: 4,
    backgroundColor: colors.cardBg,
    borderWidth: 1,
    borderColor: colors.panelBg,
    justifyContent: 'center',
    alignItems: 'center',
  },
  harvestCellActive: {
    backgroundColor: '#1A1200',
    borderColor: colors.amber,
  },
  harvestCellResource: {
    fontSize: 20,
    color: colors.amber,
  },
  harvestCellId: {
    ...typography.caption,
    color: colors.textMuted,
    fontSize: 9,
    marginTop: 2,
  },

  // Submit button
  submitBtn: {
    backgroundColor: colors.panelBg,
    borderWidth: 1,
    borderColor: colors.amber,
    padding: spacing.md,
    alignItems: 'center',
    marginTop: spacing.sm,
  },
  submitBtnDisabled: {
    opacity: 0.4,
  },
  submitBtnText: {
    ...typography.monoSmall,
    color: colors.amber,
    letterSpacing: 2,
  },

  // Result overlay
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.85)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xl,
  },
  resultCard: {
    backgroundColor: colors.cardBg,
    borderWidth: 1,
    borderColor: colors.amber,
    padding: spacing.xl,
    width: '100%',
    alignItems: 'center',
  },
  resultIcon: {
    fontSize: 48,
    color: colors.amber,
    marginBottom: spacing.md,
  },
  resultTitle: {
    ...typography.monoLarge,
    color: colors.amber,
    marginBottom: spacing.xs,
    letterSpacing: 3,
  },
  resultGame: {
    ...typography.caption,
    color: colors.textMuted,
    letterSpacing: 2,
    marginBottom: spacing.lg,
  },
  rewardRow: {
    flexDirection: 'row',
    gap: spacing.md,
    marginBottom: spacing.xl,
  },
  rewardBadge: {
    alignItems: 'center',
    backgroundColor: colors.panelBg,
    padding: spacing.md,
    minWidth: 80,
  },
  rewardValue: {
    ...typography.monoLarge,
    color: colors.amber,
  },
  rewardLabel: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: 2,
    letterSpacing: 1,
  },
  closeBtn: {
    backgroundColor: colors.amber,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.xl,
  },
  closeBtnText: {
    ...typography.monoSmall,
    color: '#1A0A0A',
    letterSpacing: 2,
  },
});
