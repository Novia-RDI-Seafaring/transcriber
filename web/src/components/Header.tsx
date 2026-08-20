import { Download, Search } from "lucide-react";
import { useMemo } from "react";
import { transcriptUrl } from "../api";
import { assignColors } from "../colors";
import { useStore } from "../store";
import { SpeakerChips } from "./SpeakerChips";

export function Header() {
  const result = useStore((s) => s.result);
  const speakers = useStore((s) => s.speakers);
  const search = useStore((s) => s.search);
  const setSearch = useStore((s) => s.setSearch);

  const colorMap = useMemo(() => assignColors(speakers), [speakers]);
  const uniqueSpeakers = useMemo(
    () => Array.from(new Set(speakers)),
    [speakers],
  );

  return (
    <header className="flex shrink-0 items-center gap-4 border-b border-zinc-800 bg-zinc-900/50 px-5 py-3 backdrop-blur">
      <div className="flex min-w-0 flex-col">
        <div className="text-xs uppercase tracking-wider text-zinc-500">
          Transcriber
        </div>
        <div className="truncate text-sm font-medium text-zinc-100">
          {result?.audio_name ?? "—"}
        </div>
      </div>

      <SpeakerChips uniqueSpeakers={uniqueSpeakers} colorMap={colorMap} />

      <div className="ml-auto flex items-center gap-2">
        <div className="relative">
          <Search className="pointer-events-none absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
          <input
            type="text"
            placeholder="Search transcript…  (/)"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8 w-64 rounded-md border border-zinc-800 bg-zinc-900 pl-8 pr-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-zinc-600 focus:outline-none"
            id="transcript-search"
          />
        </div>
        <ExportMenu jobId={result?.job_id ?? null} />
      </div>
    </header>
  );
}

function ExportMenu({ jobId }: { jobId: string | null }) {
  if (!jobId) return null;
  return (
    <div className="flex items-center overflow-hidden rounded-md border border-zinc-800">
      {(["txt", "vtt", "srt"] as const).map((fmt) => (
        <a
          key={fmt}
          href={transcriptUrl(jobId, fmt)}
          download={`transcript.${fmt}`}
          className="flex h-8 items-center gap-1.5 border-r border-zinc-800 bg-zinc-900 px-2.5 text-xs uppercase text-zinc-300 last:border-r-0 hover:bg-zinc-800"
          title={`Download ${fmt.toUpperCase()}`}
        >
          <Download className="h-3.5 w-3.5" />
          {fmt}
        </a>
      ))}
    </div>
  );
}
