import { create } from "zustand";
import type { JobDTO, ResultDTO, SegmentDTO } from "./types";

interface State {
  // sidebar
  jobs: JobDTO[];
  sidebarOpen: boolean;
  // selection
  currentJobId: string | null;
  // currently loaded result for currentJobId (null while loading or on error)
  result: ResultDTO | null;
  speakers: string[];
  // viewport interactivity
  highlighted: number | null;
  hovered: number | null;
  selected: Set<number>;
  search: string;
  // setters
  setJobs: (jobs: JobDTO[]) => void;
  upsertJob: (job: JobDTO) => void;
  removeJob: (id: string) => void;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setCurrentJobId: (id: string | null) => void;
  setResult: (r: ResultDTO | null) => void;
  setSpeakers: (s: string[]) => void;
  setHighlighted: (i: number | null) => void;
  setHovered: (i: number | null) => void;
  setSelected: (s: Set<number>) => void;
  clearSelected: () => void;
  setSearch: (q: string) => void;
}

export const useStore = create<State>((set) => ({
  jobs: [],
  sidebarOpen: true,
  currentJobId: null,
  result: null,
  speakers: [],
  highlighted: null,
  hovered: null,
  selected: new Set(),
  search: "",
  setJobs: (jobs) => set({ jobs }),
  upsertJob: (job) =>
    set((s) => {
      const existing = s.jobs.findIndex((j) => j.id === job.id);
      if (existing < 0) return { jobs: [job, ...s.jobs] };
      const next = s.jobs.slice();
      next[existing] = job;
      return { jobs: next };
    }),
  removeJob: (id) =>
    set((s) => ({
      jobs: s.jobs.filter((j) => j.id !== id),
      currentJobId: s.currentJobId === id ? null : s.currentJobId,
      result: s.currentJobId === id ? null : s.result,
    })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setCurrentJobId: (id) => set({ currentJobId: id }),
  setResult: (r) =>
    set({ result: r, speakers: r ? r.speakers : [], highlighted: null, selected: new Set() }),
  setSpeakers: (speakers) => set({ speakers }),
  setHighlighted: (i) => set({ highlighted: i }),
  setHovered: (i) => set({ hovered: i }),
  setSelected: (s) => set({ selected: s }),
  clearSelected: () => set({ selected: new Set() }),
  setSearch: (q) => set({ search: q }),
}));

export function getSegment(i: number): SegmentDTO | undefined {
  return useStore.getState().result?.segments[i];
}
