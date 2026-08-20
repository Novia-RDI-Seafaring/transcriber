// Mirrors transcriber/ui/colors.py so the React frontend, the Python
// renderer, and any persisted screenshots stay visually consistent.

export const PALETTE = [
  "#60a5fa", // blue-400
  "#fb923c", // orange-400
  "#34d399", // emerald-400
  "#f87171", // red-400
  "#a78bfa", // violet-400
  "#f472b6", // pink-400
  "#facc15", // yellow-400
  "#22d3ee", // cyan-400
  "#fbbf24", // amber-400
  "#a3e635", // lime-400
  "#818cf8", // indigo-400
  "#fda4af", // rose-300
  "#86efac", // green-300
  "#7dd3fc", // sky-300
  "#c4b5fd", // violet-300
  "#fcd34d", // amber-300
  "#67e8f9", // cyan-300
  "#bef264", // lime-300
  "#a5b4fc", // indigo-300
  "#fdba74", // orange-300
];

export const FALLBACK_COLOR = "#71717a"; // zinc-500

export function assignColors(labels: string[]): Record<string, string> {
  const mapping: Record<string, string> = {};
  let next = 0;
  for (const label of labels) {
    if (label in mapping) continue;
    mapping[label] = next < PALETTE.length ? PALETTE[next++] : FALLBACK_COLOR;
  }
  return mapping;
}
