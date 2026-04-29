import { useEffect, useMemo, useRef } from "react";
import { assignColors } from "../colors";
import { useStore } from "../store";

const ROW_HEIGHT = 78;

export function Transcript() {
  const result = useStore((s) => s.result);
  const speakers = useStore((s) => s.speakers);
  const highlighted = useStore((s) => s.highlighted);
  const hovered = useStore((s) => s.hovered);
  const search = useStore((s) => s.search);
  const setHighlighted = useStore((s) => s.setHighlighted);
  const setHovered = useStore((s) => s.setHovered);

  const containerRef = useRef<HTMLDivElement | null>(null);
  const colorMap = useMemo(() => assignColors(speakers), [speakers]);
  const highlightIdx = highlighted ?? hovered ?? null;

  const filteredIndices = useMemo(() => {
    if (!result) return [];
    const q = search.trim().toLowerCase();
    if (!q) return result.segments.map((_, i) => i);
    return result.segments
      .map((s, i) => ({ s, i }))
      .filter(
        ({ s, i }) =>
          s.text.toLowerCase().includes(q) ||
          (speakers[i] ?? "").toLowerCase().includes(q),
      )
      .map(({ i }) => i);
  }, [result, search, speakers]);

  useEffect(() => {
    if (highlighted == null || !containerRef.current || !result) return;
    const visiblePos = filteredIndices.indexOf(highlighted);
    if (visiblePos < 0) return;
    const top = visiblePos * ROW_HEIGHT;
    const c = containerRef.current;
    const within = top >= c.scrollTop && top + ROW_HEIGHT <= c.scrollTop + c.clientHeight;
    if (!within) {
      c.scrollTo({
        top: Math.max(0, top - c.clientHeight / 2 + ROW_HEIGHT / 2),
        behavior: "smooth",
      });
    }
  }, [highlighted, filteredIndices, result]);

  if (!result) return null;

  return (
    <div ref={containerRef} className="h-full overflow-y-auto px-5 py-4">
      {filteredIndices.length === 0 ? (
        <div className="py-12 text-center text-sm text-zinc-500">
          No segments match “{search}”
        </div>
      ) : (
        filteredIndices.map((i) => {
          const seg = result.segments[i];
          const speaker = speakers[i];
          const isHl = i === highlightIdx;
          return (
            <div
              key={i}
              data-segment-index={i}
              onClick={() => setHighlighted(i)}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
              className={
                "group cursor-pointer rounded-md px-3 py-2 transition " +
                (isHl
                  ? "bg-zinc-800/80 ring-1 ring-zinc-700"
                  : "hover:bg-zinc-900")
              }
            >
              <div className="mb-1 flex items-center gap-2 text-xs">
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: colorMap[speaker] }}
                />
                <span className="font-semibold text-zinc-200">{speaker}</span>
                <span className="text-zinc-500">{fmtRange(seg.start, seg.end)}</span>
              </div>
              <div className="text-sm leading-relaxed text-zinc-300">
                <Highlight text={seg.text} term={search} />
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}

function fmtRange(start: number, end: number): string {
  return `${fmt(start)} – ${fmt(end)}`;
}
function fmt(s: number): string {
  const m = Math.floor(s / 60);
  const ss = Math.floor(s % 60).toString().padStart(2, "0");
  return `${m}:${ss}`;
}

function Highlight({ text, term }: { text: string; term: string }) {
  const q = term.trim();
  if (!q) return <>{text}</>;
  const re = new RegExp(`(${escapeRegExp(q)})`, "gi");
  const parts = text.split(re);
  return (
    <>
      {parts.map((p, i) =>
        re.test(p) ? (
          <mark key={i} className="rounded bg-yellow-500/30 px-0.5 text-zinc-100">
            {p}
          </mark>
        ) : (
          <span key={i}>{p}</span>
        ),
      )}
    </>
  );
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
