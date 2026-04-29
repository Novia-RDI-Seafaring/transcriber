import { useEffect, useMemo, useRef, useState } from "react";
import Plotly from "plotly.js-basic-dist";
import type { Data, Layout, PlotMouseEvent, PlotSelectionEvent } from "plotly.js";
import { postLabels } from "../api";
import { assignColors } from "../colors";
import { useStore } from "../store";

// Plotly's CJS package + the official react-plotly.js wrapper choke on
// Vite's interop layer (the wrapper relies on a CJS factory that the
// browser sees as `{ default: fn }`). We bypass it and call Plotly
// directly — it's a thin imperative API on a div.

const LAYOUT: Partial<Layout> = {
  dragmode: "lasso",
  margin: { l: 8, r: 8, t: 8, b: 8 },
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  xaxis: { showgrid: false, zeroline: false, showticklabels: false },
  yaxis: { showgrid: false, zeroline: false, showticklabels: false },
  hoverlabel: {
    bgcolor: "#18181b",
    bordercolor: "#3f3f46",
    font: { color: "#fafafa", family: "ui-sans-serif" },
  },
  font: { color: "#a1a1aa", family: "ui-sans-serif" },
  autosize: true,
};

interface PlotlyDiv extends HTMLDivElement {
  on: (event: string, cb: (e: unknown) => void) => void;
}

export function Scatter() {
  const result = useStore((s) => s.result);
  const speakers = useStore((s) => s.speakers);
  const highlighted = useStore((s) => s.highlighted);
  const hovered = useStore((s) => s.hovered);
  const selected = useStore((s) => s.selected);
  const setHighlighted = useStore((s) => s.setHighlighted);
  const setHovered = useStore((s) => s.setHovered);
  const setSelected = useStore((s) => s.setSelected);
  const setSpeakers = useStore((s) => s.setSpeakers);

  const containerRef = useRef<HTMLDivElement | null>(null);
  const lassoIndices = useRef<number[]>([]);
  const handlersRef = useRef<{
    setHighlighted: typeof setHighlighted;
    setHovered: typeof setHovered;
    setSelected: typeof setSelected;
    openRename: (idx: number[]) => void;
  }>({
    setHighlighted,
    setHovered,
    setSelected,
    openRename: () => {},
  });

  const [renameOpen, setRenameOpen] = useState(false);
  const [draft, setDraft] = useState("");

  const colorMap = useMemo(() => assignColors(speakers), [speakers]);
  const segments = result?.segments ?? null;
  const highlightedIdx = highlighted ?? hovered ?? null;

  // Initialize the plot once.
  useEffect(() => {
    const node = containerRef.current as PlotlyDiv | null;
    if (!node || !segments) return;

    const colors = speakers.map((s) => colorMap[s]);
    const data: Partial<Data>[] = [
      {
        type: "scatter",
        mode: "markers",
        x: segments.map((s) => s.x),
        y: segments.map((s) => s.y),
        hovertext: segments.map((s) => `${s.speaker}: ${s.text.slice(0, 40)}…`),
        hoverinfo: "text",
        marker: {
          size: 9,
          color: colors,
          opacity: 0.9,
          line: { width: 0, color: "#fafafa" },
        },
        showlegend: false,
      },
    ];

    Plotly.newPlot(node, data, LAYOUT, {
      displayModeBar: false,
      responsive: true,
    });

    const onClick = (e: unknown) => {
      const ev = e as PlotMouseEvent;
      const point = ev.points?.[0];
      const idx = point?.pointIndex;
      if (typeof idx === "number") handlersRef.current.setHighlighted(idx);
    };
    const onHover = (e: unknown) => {
      const ev = e as PlotMouseEvent;
      const point = ev.points?.[0];
      const idx = point?.pointIndex;
      if (typeof idx === "number") handlersRef.current.setHovered(idx);
    };
    const onUnhover = () => handlersRef.current.setHovered(null);
    const onSelected = (e: unknown) => {
      const ev = e as PlotSelectionEvent | undefined;
      if (!ev || !ev.points) {
        handlersRef.current.setSelected(new Set());
        return;
      }
      const idx = ev.points
        .map((p) => p.pointIndex)
        .filter((p): p is number => typeof p === "number");
      handlersRef.current.setSelected(new Set(idx));
      if (idx.length > 0) handlersRef.current.openRename(idx);
    };

    node.on("plotly_click", onClick);
    node.on("plotly_hover", onHover);
    node.on("plotly_unhover", onUnhover);
    node.on("plotly_selected", onSelected);

    return () => {
      Plotly.purge(node);
    };
    // We rebuild only when the segment list itself changes (length / x-y).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [segments?.length]);

  // Keep handler ref fresh without re-initializing the plot.
  useEffect(() => {
    handlersRef.current = {
      setHighlighted,
      setHovered,
      setSelected,
      openRename: (idx) => {
        lassoIndices.current = idx;
        setRenameOpen(true);
        setDraft("");
      },
    };
  }, [setHighlighted, setHovered, setSelected]);

  // Restyle on highlighted / selected / labels changes — cheaper than rebuilding.
  useEffect(() => {
    const node = containerRef.current as PlotlyDiv | null;
    if (!node || !segments) return;
    const colors = speakers.map((s) => colorMap[s]);
    const sizes = segments.map((_, i) => {
      if (i === highlightedIdx) return 18;
      if (selected.has(i)) return 13;
      return 9;
    });
    const lineWidths = segments.map((_, i) => {
      if (i === highlightedIdx) return 2.5;
      if (selected.has(i)) return 1.5;
      return 0;
    });
    // Plotly's restyle signature is loose enough that the typed wrapper
    // disagrees with the dotted-path keys we need here.
    void (Plotly.restyle as unknown as (
      node: HTMLDivElement,
      update: Record<string, unknown>,
      traces: number[],
    ) => unknown)(
      node,
      {
        "marker.color": [colors],
        "marker.size": [sizes],
        "marker.line.width": [lineWidths],
      },
      [0],
    );
  }, [segments, speakers, colorMap, highlightedIdx, selected]);

  async function commitRename() {
    const name = draft.trim();
    setRenameOpen(false);
    if (!name) return;
    const indices = lassoIndices.current;
    if (!indices.length) return;
    const jobId = useStore.getState().result?.job_id;
    if (!jobId) return;
    const next = [...speakers];
    for (const i of indices) next[i] = name;
    setSpeakers(next);
    try {
      const per_index: Record<number, string> = {};
      for (const i of indices) per_index[i] = name;
      const updated = await postLabels(jobId, { mapping: {}, per_index });
      setSpeakers(updated.speakers);
    } catch (err) {
      console.error(err);
    }
  }

  if (!result) return null;

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />

      {renameOpen && (
        <div className="absolute left-1/2 top-4 z-10 -translate-x-1/2 rounded-lg border border-zinc-800 bg-zinc-900/95 p-3 shadow-xl backdrop-blur">
          <div className="mb-2 text-xs text-zinc-400">
            Rename {lassoIndices.current.length} segment(s) to…
          </div>
          <div className="flex gap-2">
            <input
              autoFocus
              type="text"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") commitRename();
                if (e.key === "Escape") setRenameOpen(false);
              }}
              placeholder="e.g. Tony Hawk"
              className="h-8 w-56 rounded-md border border-zinc-700 bg-zinc-950 px-2 text-sm focus:border-zinc-500 focus:outline-none"
            />
            <button
              onClick={commitRename}
              className="h-8 rounded-md bg-zinc-100 px-3 text-xs font-medium text-zinc-900 hover:bg-white"
            >
              Apply
            </button>
            <button
              onClick={() => setRenameOpen(false)}
              className="h-8 rounded-md border border-zinc-700 px-3 text-xs text-zinc-300 hover:bg-zinc-800"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
