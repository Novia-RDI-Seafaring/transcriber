import { Trash2 } from "lucide-react";
import { deleteJob } from "../api";
import { useStore } from "../store";
import type { JobDTO, JobStatus } from "../types";

interface Props {
  onNew: () => void;
}

export function JobsList({ onNew }: Props) {
  const jobs = useStore((s) => s.jobs);
  const currentJobId = useStore((s) => s.currentJobId);
  const setCurrentJobId = useStore((s) => s.setCurrentJobId);
  const removeJob = useStore((s) => s.removeJob);

  if (jobs.length === 0) {
    return (
      <div className="px-4 py-8 text-center text-xs text-zinc-500">
        <div className="mb-2">No jobs yet.</div>
        <button
          onClick={onNew}
          className="text-zinc-300 underline-offset-2 hover:underline"
        >
          Add a YouTube URL or audio file
        </button>{" "}
        to get started.
      </div>
    );
  }

  async function onDelete(e: React.MouseEvent, id: string) {
    e.stopPropagation();
    if (!window.confirm("Delete this job? Pipeline cache stays but the entry goes away.")) return;
    try {
      await deleteJob(id);
      removeJob(id);
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <ul className="flex flex-col">
      {jobs.map((job) => {
        const active = job.id === currentJobId;
        return (
          <li key={job.id}>
            <button
              onClick={() => {
                setCurrentJobId(job.id);
                window.location.hash = `#/jobs/${job.id}`;
              }}
              className={
                "group flex w-full items-start gap-2 border-l-2 px-3 py-2.5 text-left transition " +
                (active
                  ? "border-zinc-100 bg-zinc-900"
                  : "border-transparent hover:border-zinc-700 hover:bg-zinc-900/50")
              }
            >
              <StatusDot status={job.status} />
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium text-zinc-100">
                  {job.title}
                </div>
                <JobMeta job={job} />
              </div>
              <button
                onClick={(e) => onDelete(e, job.id)}
                title="Delete job"
                className="opacity-0 transition group-hover:opacity-100"
              >
                <Trash2 className="h-3.5 w-3.5 text-zinc-500 hover:text-rose-400" />
              </button>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

function StatusDot({ status }: { status: JobStatus }) {
  const cls = {
    pending: "bg-zinc-500",
    running: "bg-amber-400 animate-pulse",
    complete: "bg-emerald-400",
    failed: "bg-rose-500",
  }[status];
  return (
    <span
      title={status}
      className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${cls}`}
    />
  );
}

function JobMeta({ job }: { job: JobDTO }) {
  const bits: string[] = [];
  if (job.status === "running" && job.stage) bits.push(job.stage);
  if (job.status === "failed" && job.error) bits.push(job.error);
  if (job.status === "complete") {
    if (job.n_speakers != null) bits.push(`${job.n_speakers} sp`);
    if (job.n_segments != null) bits.push(`${job.n_segments} seg`);
    if (job.duration_seconds != null) bits.push(fmtDuration(job.duration_seconds));
  }
  if (bits.length === 0) bits.push(job.status);
  return (
    <div className="mt-0.5 truncate text-xs text-zinc-500">
      {bits.join(" · ")}
    </div>
  );
}

function fmtDuration(s: number): string {
  const m = Math.floor(s / 60);
  const ss = Math.floor(s % 60).toString().padStart(2, "0");
  return `${m}:${ss}`;
}
