import { create } from "zustand";
import type { ResultDTO, SegmentDTO } from "./types";

interface State {
  result: ResultDTO | null;
  speakers: string[]; // mutable: speakers[i] is the current label for segment i
  highlighted: number | null;
  hovered: number | null;
  selected: Set<number>; // bulk selection from the scatter lasso
  search: string;
  setResult: (r: ResultDTO) => void;
  setSpeakers: (s: string[]) => void;
  setHighlighted: (i: number | null) => void;
  setHovered: (i: number | null) => void;
  setSelected: (s: Set<number>) => void;
  clearSelected: () => void;
  setSearch: (q: string) => void;
}

export const useStore = create<State>((set) => ({
  result: null,
  speakers: [],
  highlighted: null,
  hovered: null,
  selected: new Set(),
  search: "",
  setResult: (r) => set({ result: r, speakers: r.speakers }),
  setSpeakers: (s) => set({ speakers: s }),
  setHighlighted: (i) => set({ highlighted: i }),
  setHovered: (i) => set({ hovered: i }),
  setSelected: (s) => set({ selected: s }),
  clearSelected: () => set({ selected: new Set() }),
  setSearch: (q) => set({ search: q }),
}));

export function getSegment(i: number): SegmentDTO | undefined {
  return useStore.getState().result?.segments[i];
}
