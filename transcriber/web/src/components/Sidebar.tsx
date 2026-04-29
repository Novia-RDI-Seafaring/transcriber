import { ChevronLeft, ChevronRight, Plus } from "lucide-react";
import { useState } from "react";
import { useStore } from "../store";
import { JobsList } from "./JobsList";
import { NewJobDialog } from "./NewJobDialog";

export function Sidebar() {
  const open = useStore((s) => s.sidebarOpen);
  const toggle = useStore((s) => s.toggleSidebar);
  const [dialogOpen, setDialogOpen] = useState(false);

  if (!open) {
    return (
      <button
        onClick={toggle}
        title="Show jobs (⌘B)"
        className="flex h-full w-9 shrink-0 flex-col items-center border-r border-zinc-800 bg-zinc-950 text-zinc-500 transition hover:bg-zinc-900 hover:text-zinc-200"
      >
        <ChevronRight className="mt-3 h-4 w-4" />
        <span className="mt-2 [writing-mode:vertical-rl] text-xs uppercase tracking-widest">
          Jobs
        </span>
      </button>
    );
  }

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col border-r border-zinc-800 bg-zinc-950">
      <div className="flex shrink-0 items-center justify-between border-b border-zinc-800 px-4 py-3">
        <div className="text-xs font-semibold uppercase tracking-widest text-zinc-400">
          Jobs
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setDialogOpen(true)}
            title="New job"
            className="flex h-7 items-center gap-1 rounded-md bg-zinc-100 px-2 text-xs font-medium text-zinc-900 transition hover:bg-white"
          >
            <Plus className="h-3.5 w-3.5" />
            New
          </button>
          <button
            onClick={toggle}
            title="Hide sidebar (⌘B)"
            className="flex h-7 w-7 items-center justify-center rounded-md text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <JobsList onNew={() => setDialogOpen(true)} />
      </div>

      {dialogOpen && <NewJobDialog onClose={() => setDialogOpen(false)} />}
    </aside>
  );
}
