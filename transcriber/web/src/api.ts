import type { LabelsState, LabelsUpdate, ResultDTO } from "./types";

const BASE = "";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json();
}

export async function fetchResult(): Promise<ResultDTO> {
  return json<ResultDTO>(await fetch(`${BASE}/api/result`));
}

export async function postLabels(update: LabelsUpdate): Promise<LabelsState> {
  return json<LabelsState>(
    await fetch(`${BASE}/api/labels`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(update),
    }),
  );
}

export function transcriptUrl(fmt: "txt" | "vtt" | "srt"): string {
  return `${BASE}/api/transcripts/${fmt}`;
}
