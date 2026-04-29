import { lazy, Suspense, useEffect } from "react";
import { fetchResult } from "./api";
import { Header } from "./components/Header";
import { Timeline } from "./components/Timeline";
import { Transcript } from "./components/Transcript";
import { AudioPlayer } from "./components/AudioPlayer";
import { useKeyboardNav } from "./hooks/useKeyboardNav";
import { useStore } from "./store";

// Plotly is large (~3MB minified). Code-split it so the rest of the UI
// renders instantly while the chart bundle streams in.
const Scatter = lazy(() =>
  import("./components/Scatter").then((m) => ({ default: m.Scatter })),
);

export default function App() {
  const result = useStore((s) => s.result);
  const setResult = useStore((s) => s.setResult);

  useEffect(() => {
    fetchResult()
      .then(setResult)
      .catch((err) => console.error("failed to load result", err));
  }, [setResult]);

  useKeyboardNav();

  if (!result) {
    return (
      <div className="grid h-screen place-items-center text-zinc-400">
        <div className="flex flex-col items-center gap-3">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-500 border-t-zinc-100" />
          <div>Loading transcript…</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-zinc-950 text-zinc-100">
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
    </div>
  );
}
