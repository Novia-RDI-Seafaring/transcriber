import { AudioLines, Loader2, TriangleAlert } from "lucide-react";
import type { JobDTO } from "../types";

export function EmptyState({ job }: { job: JobDTO | null }) {
  if (job?.status === "running" || job?.status === "pending") {
    return (
      <div className="grid flex-1 place-items-center bg-zinc-950 px-6 text-center">
        <div className="flex flex-col items-center gap-3 text-zinc-400">
          <Loader2 className="h-6 w-6 animate-spin text-zinc-300" />
          <div>
            <div className="text-sm font-medium text-zinc-200">{job.title}</div>
            <div className="text-xs text-zinc-500">
              {job.stage ? `Stage: ${job.stage}` : "Queued"}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (job?.status === "failed") {
    return (
      <div className="grid flex-1 place-items-center bg-zinc-950 px-6 text-center">
        <div className="max-w-md">
          <TriangleAlert className="mx-auto mb-3 h-8 w-8 text-rose-400" />
          <div className="mb-1 text-sm font-medium text-zinc-100">Job failed</div>
          <div className="break-words text-xs text-rose-300">
            {job.error ?? "Unknown error."}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="grid flex-1 place-items-center bg-zinc-950 px-6 text-center">
      <div className="max-w-md">
        <AudioLines className="mx-auto mb-3 h-8 w-8 text-zinc-500" />
        <div className="mb-1 text-sm font-medium text-zinc-100">
          No transcript loaded
        </div>
        <div className="text-xs text-zinc-500">
          Click <span className="font-medium text-zinc-300">+ New</span> in the
          sidebar to add a YouTube URL, paste a local audio path, or upload an
          audio/video file. Completed jobs appear in the sidebar — click one to
          open it.
        </div>
      </div>
    </div>
  );
}
