import { useMemo } from "react";
import { assignColors } from "../colors";
import { useStore } from "../store";

const HEIGHT = 56;
const PAD_LEFT = 12;
const PAD_RIGHT = 12;
const TICK_HEIGHT = 14;

function fmtTime(s: number): string {
  const m = Math.floor(s / 60);
  const ss = Math.floor(s % 60).toString().padStart(2, "0");
  return `${m}:${ss}`;
}

export function Timeline() {
  const result = useStore((s) => s.result);
  const speakers = useStore((s) => s.speakers);
  const highlighted = useStore((s) => s.highlighted);
  const hovered = useStore((s) => s.hovered);
  const playSegment = useStore((s) => s.playSegment);
  const setHovered = useStore((s) => s.setHovered);

  const colorMap = useMemo(() => assignColors(speakers), [speakers]);

  if (!result) return null;
  const total = result.duration || 1;
  const highlightedIdx = highlighted ?? hovered ?? null;

  // Render in a viewBox so it scales with the container.
  return (
    <div className="select-none">
      <svg
        width="100%"
        viewBox={`0 0 1000 ${HEIGHT + TICK_HEIGHT}`}
        preserveAspectRatio="none"
        className="block"
        style={{ height: HEIGHT + TICK_HEIGHT }}
      >
        <rect
          x={0}
          y={0}
          width={1000}
          height={HEIGHT}
          fill="rgb(24 24 27)"
        />
        {result.segments.map((seg, i) => {
          const x = PAD_LEFT + ((1000 - PAD_LEFT - PAD_RIGHT) * seg.start) / total;
          const w = Math.max(
            1.5,
            ((1000 - PAD_LEFT - PAD_RIGHT) * (seg.end - seg.start)) / total,
          );
          const isHl = i === highlightedIdx;
          return (
            <rect
              key={i}
              x={x}
              y={isHl ? 4 : 8}
              width={w}
              height={isHl ? HEIGHT - 8 : HEIGHT - 16}
              fill={colorMap[speakers[i]]}
              opacity={isHl ? 1 : 0.85}
              stroke={isHl ? "#fafafa" : "transparent"}
              strokeWidth={isHl ? 1.5 : 0}
              style={{ cursor: "pointer", transition: "opacity 80ms" }}
              onClick={() => playSegment(i)}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
            >
              <title>
                {speakers[i]} • {fmtTime(seg.start)}–{fmtTime(seg.end)}
              </title>
            </rect>
          );
        })}

        {/* Time ticks */}
        {tickPositions(total).map((t) => {
          const x = PAD_LEFT + ((1000 - PAD_LEFT - PAD_RIGHT) * t) / total;
          return (
            <g key={t}>
              <line
                x1={x}
                x2={x}
                y1={HEIGHT}
                y2={HEIGHT + 4}
                stroke="rgb(82 82 91)"
              />
              <text
                x={x}
                y={HEIGHT + 12}
                fill="rgb(161 161 170)"
                fontSize={9}
                textAnchor="middle"
              >
                {fmtTime(t)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function tickPositions(total: number): number[] {
  // Aim for ~8 ticks; round to nice intervals.
  const candidates = [5, 10, 15, 30, 60, 120, 300, 600, 900, 1800];
  const target = total / 8;
  const step = candidates.find((c) => c >= target) ?? candidates[candidates.length - 1];
  const out: number[] = [];
  for (let t = 0; t <= total; t += step) out.push(t);
  return out;
}
