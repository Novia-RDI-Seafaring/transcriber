import { Link2, Upload, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { createJob, uploadJob } from "../api";
import { useStore } from "../store";

type Tab = "url" | "upload";

interface Props {
  onClose: () => void;
}

export function NewJobDialog({ onClose }: Props) {
  const upsertJob = useStore((s) => s.upsertJob);
  const setCurrentJobId = useStore((s) => s.setCurrentJobId);

  const [tab, setTab] = useState<Tab>("url");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [backend, setBackend] = useState<"openai" | "local">("openai");
  const [language, setLanguage] = useState("en");
  const [participants, setParticipants] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dialogRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function submit() {
    setError(null);
    const p = participants.trim() ? Number(participants) : null;
    setSubmitting(true);
    try {
      let job;
      if (tab === "url") {
        const trimmed = url.trim();
        if (!trimmed) throw new Error("Enter a URL or local path");
        job = await createJob({
          source: trimmed,
          backend,
          language,
          participants: p,
        });
      } else {
        if (!file) throw new Error("Choose a file");
        job = await uploadJob(file, { backend, language, participants: p });
      }
      upsertJob(job);
      setCurrentJobId(job.id);
      window.location.hash = `#/jobs/${job.id}`;
      onClose();
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        className="w-full max-w-lg rounded-xl border border-zinc-800 bg-zinc-900 shadow-2xl"
        role="dialog"
        aria-modal="true"
      >
        <div className="flex items-center justify-between border-b border-zinc-800 px-5 py-3">
          <h2 className="text-sm font-semibold text-zinc-100">New job</h2>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-200"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex border-b border-zinc-800 px-5">
          <TabButton active={tab === "url"} onClick={() => setTab("url")}>
            <Link2 className="h-3.5 w-3.5" /> URL or path
          </TabButton>
          <TabButton active={tab === "upload"} onClick={() => setTab("upload")}>
            <Upload className="h-3.5 w-3.5" /> Upload file
          </TabButton>
        </div>

        <div className="space-y-4 px-5 py-4">
          {tab === "url" ? (
            <div>
              <label className="mb-1 block text-xs uppercase tracking-wider text-zinc-400">
                YouTube URL or local audio path
              </label>
              <input
                autoFocus
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submit()}
                placeholder="https://www.youtube.com/watch?v=… or /path/to/file.mp3"
                className="h-9 w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-zinc-500 focus:outline-none"
              />
              <p className="mt-2 text-xs text-zinc-500">
                YouTube URLs are downloaded once via yt-dlp and reused. Local
                paths must exist on the server's filesystem.
              </p>
            </div>
          ) : (
            <UploadField file={file} onFile={setFile} />
          )}

          <div className="grid grid-cols-3 gap-3">
            <Field label="Backend">
              <select
                value={backend}
                onChange={(e) => setBackend(e.target.value as "openai" | "local")}
                className="h-9 w-full rounded-md border border-zinc-700 bg-zinc-950 px-2 text-sm text-zinc-100 focus:border-zinc-500 focus:outline-none"
              >
                <option value="openai">OpenAI Whisper</option>
                <option value="local">Local (faster-whisper)</option>
              </select>
            </Field>
            <Field label="Language">
              <input
                type="text"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                placeholder="en"
                className="h-9 w-full rounded-md border border-zinc-700 bg-zinc-950 px-2 text-sm text-zinc-100 focus:border-zinc-500 focus:outline-none"
              />
            </Field>
            <Field label="Speakers">
              <input
                type="number"
                min={1}
                value={participants}
                onChange={(e) => setParticipants(e.target.value)}
                placeholder="auto"
                className="h-9 w-full rounded-md border border-zinc-700 bg-zinc-950 px-2 text-sm text-zinc-100 focus:border-zinc-500 focus:outline-none"
              />
            </Field>
          </div>

          {error && (
            <div className="rounded-md border border-rose-900 bg-rose-950/40 px-3 py-2 text-xs text-rose-300">
              {error}
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-zinc-800 px-5 py-3">
          <button
            onClick={onClose}
            className="h-8 rounded-md border border-zinc-700 px-3 text-xs text-zinc-300 hover:bg-zinc-800"
            disabled={submitting}
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={submitting}
            className="h-8 rounded-md bg-zinc-100 px-3 text-xs font-medium text-zinc-900 hover:bg-white disabled:cursor-wait disabled:opacity-50"
          >
            {submitting ? "Submitting…" : "Start job"}
          </button>
        </div>
      </div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={
        "flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-medium transition " +
        (active
          ? "border-zinc-100 text-zinc-100"
          : "border-transparent text-zinc-500 hover:text-zinc-300")
      }
    >
      {children}
    </button>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <div className="mb-1 text-xs uppercase tracking-wider text-zinc-400">
        {label}
      </div>
      {children}
    </label>
  );
}

function UploadField({
  file,
  onFile,
}: {
  file: File | null;
  onFile: (f: File | null) => void;
}) {
  const [drag, setDrag] = useState(false);
  return (
    <div>
      <div className="mb-1 text-xs uppercase tracking-wider text-zinc-400">
        Audio or video file
      </div>
      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          const f = e.dataTransfer.files[0];
          if (f) onFile(f);
        }}
        className={
          "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed py-8 text-center transition " +
          (drag
            ? "border-zinc-100 bg-zinc-800/50"
            : "border-zinc-700 bg-zinc-950 hover:border-zinc-500")
        }
      >
        <Upload className="mb-2 h-5 w-5 text-zinc-500" />
        {file ? (
          <>
            <div className="text-sm font-medium text-zinc-100">{file.name}</div>
            <div className="text-xs text-zinc-500">
              {(file.size / 1_000_000).toFixed(1)} MB
            </div>
          </>
        ) : (
          <>
            <div className="text-sm text-zinc-300">
              Drag & drop or click to choose
            </div>
            <div className="mt-0.5 text-xs text-zinc-500">
              MP3, MP4, WAV, M4A — anything ffmpeg can read
            </div>
          </>
        )}
        <input
          type="file"
          className="hidden"
          accept="audio/*,video/*,.mp3,.mp4,.wav,.m4a,.webm,.ogg,.flac"
          onChange={(e) => onFile(e.target.files?.[0] ?? null)}
        />
      </label>
    </div>
  );
}
