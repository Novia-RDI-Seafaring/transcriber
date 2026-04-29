import { lazy, Suspense, useEffect } from "react";
import { fetchResult, getJob, listJobs } from "./api";
import { AudioPlayer } from "./components/AudioPlayer";
import { EmptyState } from "./components/EmptyState";
import { Header } from "./components/Header";
import { Sidebar } from "./components/Sidebar";
import { Timeline } from "./components/Timeline";
import { Transcript } from "./components/Transcript";
import { useKeyboardNav } from "./hooks/useKeyboardNav";
import { useStore } from "./store";

// Plotly is large (~3MB minified). Code-split it so the rest of the UI
// renders instantly while the chart bundle streams in.
const Scatter = lazy(() =>
  import("./components/Scatter").then((m) => ({ default: m.Scatter })),
);

function jobIdFromHash(): string | null {
  const m = window.location.hash.match(/^#\/jobs\/([\w-]+)/);
  return m ? m[1] : null;
}

export default function App() {
  const jobs = useStore((s) => s.jobs);
  const setJobs = useStore((s) => s.setJobs);
  const upsertJob = useStore((s) => s.upsertJob);
  const currentJobId = useStore((s) => s.currentJobId);
  const setCurrentJobId = useStore((s) => s.setCurrentJobId);
  const result = useStore((s) => s.result);
  const setResult = useStore((s) => s.setResult);

  // 1. Initial load: fetch jobs + react to hash routing.
  useEffect(() => {
    let cancelled = false;
    listJobs()
      .then((js) => {
        if (cancelled) return;
        setJobs(js);
        const fromHash = jobIdFromHash();
        const target =
          fromHash && js.some((j) => j.id === fromHash)
            ? fromHash
            : js.find((j) => j.status === "complete")?.id ?? null;
        if (target) setCurrentJobId(target);
      })
      .catch((err) => console.error("failed to load jobs", err));
    return () => {
      cancelled = true;
    };
  }, [setJobs, setCurrentJobId]);

  // 2. Hash navigation between jobs.
  useEffect(() => {
    function onHashChange() {
      const id = jobIdFromHash();
      if (id) setCurrentJobId(id);
    }
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, [setCurrentJobId]);

  // 3. Whenever the current job changes (and is complete), load the result.
  useEffect(() => {
    if (!currentJobId) {
      setResult(null);
      return;
    }
    const job = jobs.find((j) => j.id === currentJobId);
    if (!job || job.status !== "complete") {
      setResult(null);
      return;
    }
    let cancelled = false;
    fetchResult(currentJobId)
      .then((r) => {
        if (!cancelled) setResult(r);
      })
      .catch((err) => console.error("failed to load result", err));
    return () => {
      cancelled = true;
    };
  }, [currentJobId, jobs, setResult]);

  // 4. Poll any in-progress jobs every 2s.
  useEffect(() => {
    const inProgress = jobs.filter(
      (j) => j.status === "pending" || j.status === "running",
    );
    if (inProgress.length === 0) return;
    const interval = window.setInterval(async () => {
      const updated = await Promise.all(
        inProgress.map((j) =>
          getJob(j.id).catch(() => null),
        ),
      );
      for (const j of updated) if (j) upsertJob(j);
    }, 2000);
    return () => window.clearInterval(interval);
  }, [jobs, upsertJob]);

  // 5. Cmd/Ctrl+B toggles the sidebar.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "b") {
        e.preventDefault();
        useStore.getState().toggleSidebar();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useKeyboardNav();

  const job = jobs.find((j) => j.id === currentJobId) ?? null;

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-100">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        {result && job?.status === "complete" ? (
          <>
            <Header />
            <div className="flex flex-1 overflow-hidden">
              <div className="flex w-3/5 flex-col border-r border-zinc-800">
                <div className="flex-1 overflow-hidden">
                  <Suspense
                    fallback={
                      <div className="grid h-full place-items-center text-xs text-zinc-500">
                        Loading scatter…
                      </div>
                    }
                  >
                    <Scatter />
                  </Suspense>
                </div>
                <div className="border-t border-zinc-800">
                  <AudioPlayer />
                </div>
                <div className="border-t border-zinc-800">
                  <Timeline />
                </div>
              </div>
              <div className="w-2/5 overflow-hidden">
                <Transcript />
              </div>
            </div>
          </>
        ) : (
          <EmptyState job={job} />
        )}
      </div>
    </div>
  );
}
