import { Pause, Play } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import WaveSurfer from "wavesurfer.js";
import RegionsPlugin, {
  type Region,
} from "wavesurfer.js/dist/plugins/regions.esm.js";
import { assignColors } from "../colors";
import { useStore } from "../store";
import type { SegmentDTO } from "../types";

const PLAYBACK_RATES = [0.75, 1, 1.25, 1.5, 2] as const;
type PlaybackRate = (typeof PLAYBACK_RATES)[number];

const NORMAL_OPACITY = 0.25;
const HIGHLIGHTED_OPACITY = 0.55;
const EMPHASIS_OPACITY = 1;
const EMPHASIS_DURATION_MS = 450;

export function AudioPlayer() {
  const result = useStore((s) => s.result);
  const speakers = useStore((s) => s.speakers);
  const highlighted = useStore((s) => s.highlighted);
  const setHighlighted = useStore((s) => s.setHighlighted);

  const containerRef = useRef<HTMLDivElement | null>(null);
  const wsRef = useRef<WaveSurfer | null>(null);
  const regionsPluginRef = useRef<ReturnType<typeof RegionsPlugin.create> | null>(
    null,
  );
  const regionByIndexRef = useRef<Map<number, Region>>(new Map());
  const lastSegmentIndexRef = useRef<number | null>(null);
  const emphasisTimeoutRef = useRef<number | null>(null);
  const isReadyRef = useRef(false);
  const pendingSeekRef = useRef<{ index: number; play: boolean } | null>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [position, setPosition] = useState(0);
  const [rate, setRate] = useState<PlaybackRate>(1);
  const [loadError, setLoadError] = useState(false);
  const [isReady, setIsReady] = useState(false);

  const segments = result?.segments ?? null;
  const audioUrl = result?.audio_url ?? null;

  const colorMap = useMemo(() => assignColors(speakers), [speakers]);

  const segment: SegmentDTO | null =
    highlighted != null && segments ? segments[highlighted] ?? null : null;
  const speaker =
    highlighted != null && speakers[highlighted] != null
      ? speakers[highlighted]
      : null;

  // Initialize WaveSurfer once.
  useEffect(() => {
    if (!containerRef.current) return;
    const regionsPlugin = RegionsPlugin.create();
    const ws = WaveSurfer.create({
      container: containerRef.current,
      height: 64,
      waveColor: "#3f3f46",
      progressColor: "#a1a1aa",
      cursorColor: "#fafafa",
      cursorWidth: 1,
      barWidth: 2,
      barGap: 1,
      barRadius: 2,
    });
    ws.registerPlugin(regionsPlugin);
    wsRef.current = ws;
    regionsPluginRef.current = regionsPlugin;

    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);
    const onFinish = () => setIsPlaying(false);
    const onReady = () => {
      isReadyRef.current = true;
      setIsReady(true);
      setDuration(ws.getDuration());
      const pending = pendingSeekRef.current;
      if (pending) {
        pendingSeekRef.current = null;
        seekToSegment(pending.index, pending.play);
      }
    };
    const onAudioProcess = () => {
      const t = ws.getCurrentTime();
      setPosition(t);
      const segs = segmentsRef.current;
      if (!segs || segs.length === 0) return;
      const idx = findSegmentIndex(segs, t);
      if (idx !== null && idx !== lastSegmentIndexRef.current) {
        lastSegmentIndexRef.current = idx;
        if (idx !== currentHighlightedRef.current) {
          setHighlightedRef.current(idx);
        }
      }
    };
    const onSeeking = () => setPosition(ws.getCurrentTime());

    ws.on("play", onPlay);
    ws.on("pause", onPause);
    ws.on("finish", onFinish);
    ws.on("ready", onReady);
    ws.on("audioprocess", onAudioProcess);
    ws.on("seeking", onSeeking);

    return () => {
      isReadyRef.current = false;
      if (emphasisTimeoutRef.current != null) {
        window.clearTimeout(emphasisTimeoutRef.current);
        emphasisTimeoutRef.current = null;
      }
      ws.destroy();
      wsRef.current = null;
      regionsPluginRef.current = null;
      regionByIndexRef.current.clear();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Refs to give the audioprocess listener access to current store/segment state
  // without re-creating the WaveSurfer instance.
  const segmentsRef = useRef<SegmentDTO[] | null>(null);
  const currentHighlightedRef = useRef<number | null>(null);
  const setHighlightedRef = useRef(setHighlighted);
  useEffect(() => {
    segmentsRef.current = segments;
  }, [segments]);
  useEffect(() => {
    currentHighlightedRef.current = highlighted;
  }, [highlighted]);
  useEffect(() => {
    setHighlightedRef.current = setHighlighted;
  }, [setHighlighted]);

  // Load the full audio when audio_url changes.
  useEffect(() => {
    const ws = wsRef.current;
    if (!ws) return;
    if (!audioUrl) return;
    isReadyRef.current = false;
    setIsReady(false);
    setLoadError(false);
    setPosition(0);
    setDuration(0);
    lastSegmentIndexRef.current = null;
    let cancelled = false;
    ws.load(audioUrl).catch(() => {
      // Ignore aborts caused by a fast unmount/remount in React StrictMode.
      if (!cancelled) setLoadError(true);
    });
    return () => {
      cancelled = true;
    };
  }, [audioUrl]);

  // (Re)render regions whenever segments or speakers (relabeling) change.
  useEffect(() => {
    const regionsPlugin = regionsPluginRef.current;
    if (!regionsPlugin) return;
    if (!isReady) return;
    if (!segments || segments.length === 0) {
      regionsPlugin.clearRegions();
      regionByIndexRef.current.clear();
      return;
    }
    regionsPlugin.clearRegions();
    regionByIndexRef.current.clear();
    const highlightedIdx = currentHighlightedRef.current;
    segments.forEach((seg, i) => {
      const speakerLabel = speakers[i] ?? seg.speaker;
      const baseColor = colorMap[speakerLabel] ?? "#71717a";
      const opacity = i === highlightedIdx ? HIGHLIGHTED_OPACITY : NORMAL_OPACITY;
      const region = regionsPlugin.addRegion({
        id: `seg-${i}`,
        start: seg.start,
        end: seg.end,
        color: hexToRgba(baseColor, opacity),
        drag: false,
        resize: false,
        content: speakerLabel,
      });
      regionByIndexRef.current.set(i, region);
      const handler = () => {
        if (currentHighlightedRef.current === i) {
          const ws = wsRef.current;
          if (!ws) return;
          if (ws.isPlaying()) ws.pause();
          else void ws.play();
        } else {
          setHighlightedRef.current(i);
        }
      };
      region.on("click", handler);
    });
  }, [segments, speakers, colorMap, isReady]);

  // React to highlighted changes: seek + emphasize + play.
  useEffect(() => {
    if (highlighted == null) return;
    if (!segments || !segments[highlighted]) return;
    const ws = wsRef.current;
    if (!ws) return;
    if (!isReadyRef.current) {
      pendingSeekRef.current = { index: highlighted, play: true };
      return;
    }
    seekToSegment(highlighted, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [highlighted, segments]);

  // Update region opacities when highlighted changes (without rebuilding).
  useEffect(() => {
    const map = regionByIndexRef.current;
    if (map.size === 0) return;
    map.forEach((region, i) => {
      const speakerLabel = speakers[i] ?? "";
      const baseColor = colorMap[speakerLabel] ?? "#71717a";
      const opacity =
        i === highlighted ? HIGHLIGHTED_OPACITY : NORMAL_OPACITY;
      region.setOptions({ color: hexToRgba(baseColor, opacity) });
    });
  }, [highlighted, speakers, colorMap]);

  function seekToSegment(index: number, play: boolean): void {
    const ws = wsRef.current;
    if (!ws) return;
    const segs = segmentsRef.current;
    if (!segs) return;
    const seg = segs[index];
    if (!seg) return;
    const dur = ws.getDuration();
    if (dur > 0) {
      const ratio = Math.max(0, Math.min(1, seg.start / dur));
      ws.seekTo(ratio);
    }
    lastSegmentIndexRef.current = index;
    emphasizeRegion(index);
    if (play) {
      // If the user clicks the same segment that's already highlighted, the
      // upstream caller decides toggle vs restart. Here we just play.
      void ws.play().catch(() => {
        /* autoplay block: ignore */
      });
    }
  }

  function emphasizeRegion(index: number): void {
    const region = regionByIndexRef.current.get(index);
    if (!region) return;
    const speakerLabel = speakers[index] ?? "";
    const baseColor = colorMap[speakerLabel] ?? "#71717a";
    region.setOptions({ color: hexToRgba(baseColor, EMPHASIS_OPACITY) });
    if (emphasisTimeoutRef.current != null) {
      window.clearTimeout(emphasisTimeoutRef.current);
    }
    emphasisTimeoutRef.current = window.setTimeout(() => {
      emphasisTimeoutRef.current = null;
      const r = regionByIndexRef.current.get(index);
      if (!r) return;
      const opacity =
        currentHighlightedRef.current === index
          ? HIGHLIGHTED_OPACITY
          : NORMAL_OPACITY;
      r.setOptions({ color: hexToRgba(baseColor, opacity) });
    }, EMPHASIS_DURATION_MS);
  }

  function togglePlay(): void {
    const ws = wsRef.current;
    if (!ws) return;
    if (loadError) return;
    if (ws.isPlaying()) {
      ws.pause();
      return;
    }
    if (highlighted != null && segments?.[highlighted]) {
      const t = ws.getCurrentTime();
      const seg = segments[highlighted];
      if (t < seg.start || t > seg.end) {
        seekToSegment(highlighted, true);
        return;
      }
    }
    void ws.play().catch(() => {
      /* autoplay block: ignore */
    });
  }

  function changeRate(next: PlaybackRate): void {
    setRate(next);
    const ws = wsRef.current;
    if (!ws) return;
    ws.setPlaybackRate(next);
  }

  const playDisabled = !audioUrl || loadError || !isReady;
  const playTitle = !audioUrl
    ? "No audio available for this transcript"
    : loadError
      ? "Audio failed to load"
      : isPlaying
        ? "Pause (space)"
        : "Play (space)";

  return (
    <div className="flex flex-col gap-2 bg-zinc-950 px-4 py-3">
      <div className="flex items-center gap-3">
        <button
          onClick={togglePlay}
          disabled={playDisabled}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-zinc-100 text-zinc-900 transition hover:bg-white disabled:cursor-not-allowed disabled:bg-zinc-700 disabled:text-zinc-500"
          title={playTitle}
        >
          {isPlaying ? (
            <Pause className="h-4 w-4" />
          ) : (
            <Play className="h-4 w-4 translate-x-px" />
          )}
        </button>

        <div className="flex min-w-0 flex-1 items-center gap-2 text-xs">
          <div className="min-w-0 flex-1 truncate text-zinc-300">
            {speaker ? (
              <>
                <span className="font-medium">{speaker}</span>
                <span className="mx-1.5 text-zinc-600">·</span>
                <span className="text-zinc-500">
                  {segment?.text.slice(0, 90) ?? ""}
                </span>
              </>
            ) : loadError ? (
              <span className="text-zinc-500">
                Audio unavailable for this transcript
              </span>
            ) : (
              <span className="text-zinc-500">
                Click a point, bar, or transcript line to play
              </span>
            )}
          </div>
          <div className="shrink-0 text-zinc-500 tabular-nums">
            {fmt(position)} / {fmt(duration)}
          </div>
          <RateSelector value={rate} onChange={changeRate} disabled={playDisabled} />
        </div>
      </div>

      <div ref={containerRef} className="w-full" />
    </div>
  );
}

interface RateSelectorProps {
  value: PlaybackRate;
  onChange: (rate: PlaybackRate) => void;
  disabled: boolean;
}

function RateSelector({ value, onChange, disabled }: RateSelectorProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(Number(e.target.value) as PlaybackRate)}
      disabled={disabled}
      className="h-7 rounded-md border border-zinc-800 bg-zinc-900 px-1.5 text-xs text-zinc-300 hover:border-zinc-600 focus:border-zinc-500 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
      title="Playback speed"
    >
      {PLAYBACK_RATES.map((r) => (
        <option key={r} value={r}>
          {r}x
        </option>
      ))}
    </select>
  );
}

function findSegmentIndex(segments: SegmentDTO[], t: number): number | null {
  // Binary search for the segment whose [start, end] contains t.
  let lo = 0;
  let hi = segments.length - 1;
  while (lo <= hi) {
    const mid = (lo + hi) >>> 1;
    const s = segments[mid];
    if (t < s.start) hi = mid - 1;
    else if (t > s.end) lo = mid + 1;
    else return mid;
  }
  // No exact hit (gap between segments) — pick the closest preceding segment
  // so the UI still updates as playback walks across silence.
  const idx = Math.max(0, Math.min(segments.length - 1, hi));
  return idx;
}

function fmt(s: number): string {
  if (!isFinite(s) || s < 0) return "0:00";
  const m = Math.floor(s / 60);
  const ss = Math.floor(s % 60)
    .toString()
    .padStart(2, "0");
  return `${m}:${ss}`;
}

function hexToRgba(hex: string, alpha: number): string {
  const cleaned = hex.replace("#", "");
  const full =
    cleaned.length === 3
      ? cleaned
          .split("")
          .map((c) => c + c)
          .join("")
      : cleaned;
  const r = parseInt(full.slice(0, 2), 16);
  const g = parseInt(full.slice(2, 4), 16);
  const b = parseInt(full.slice(4, 6), 16);
  if (isNaN(r) || isNaN(g) || isNaN(b)) return `rgba(113, 113, 122, ${alpha})`;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
