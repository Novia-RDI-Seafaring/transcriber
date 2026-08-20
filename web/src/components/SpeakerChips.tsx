import { Pencil } from "lucide-react";
import { useState } from "react";
import { postLabels } from "../api";
import { useStore } from "../store";

interface Props {
  uniqueSpeakers: string[];
  colorMap: Record<string, string>;
}

export function SpeakerChips({ uniqueSpeakers, colorMap }: Props) {
  const speakers = useStore((s) => s.speakers);
  const setSpeakers = useStore((s) => s.setSpeakers);
  const jobId = useStore((s) => s.result?.job_id ?? null);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");

  async function commit(oldName: string) {
    const next = draft.trim();
    if (!next || next === oldName || !jobId) {
      setEditing(null);
      return;
    }
    const optimistic = speakers.map((s) => (s === oldName ? next : s));
    setSpeakers(optimistic);
    setEditing(null);
    try {
      const updated = await postLabels(jobId, {
        mapping: { [oldName]: next },
        per_index: {},
      });
      setSpeakers(updated.speakers);
    } catch (err) {
      console.error(err);
      setSpeakers(speakers);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {uniqueSpeakers.map((name) => {
        const count = speakers.filter((s) => s === name).length;
        if (editing === name) {
          return (
            <input
              key={name}
              autoFocus
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onBlur={() => commit(name)}
              onKeyDown={(e) => {
                if (e.key === "Enter") commit(name);
                if (e.key === "Escape") setEditing(null);
              }}
              className="h-6 w-32 rounded-full border border-zinc-700 bg-zinc-900 px-2 text-xs text-zinc-100 focus:outline-none"
            />
          );
        }
        return (
          <button
            key={name}
            onClick={() => {
              setEditing(name);
              setDraft(name);
            }}
            className="group inline-flex h-6 items-center gap-1.5 rounded-full border border-zinc-700/70 bg-zinc-900 pl-1.5 pr-2 text-xs text-zinc-200 hover:border-zinc-500"
            title="Click to rename this speaker everywhere"
          >
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: colorMap[name] }}
            />
            <span className="font-medium">{name}</span>
            <span className="text-[10px] text-zinc-500">{count}</span>
            <Pencil className="h-3 w-3 opacity-0 transition group-hover:opacity-100" />
          </button>
        );
      })}
    </div>
  );
}
