import type {
  CreateJobRequest,
  JobDTO,
  LabelsState,
  LabelsUpdate,
  ResultDTO,
} from "./types";

const BASE = "";

async function asJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json();
}

export async function listJobs(): Promise<JobDTO[]> {
  return asJson<JobDTO[]>(await fetch(`${BASE}/api/jobs`));
}

export async function getJob(id: string): Promise<JobDTO> {
  return asJson<JobDTO>(await fetch(`${BASE}/api/jobs/${id}`));
}

export async function createJob(req: CreateJobRequest): Promise<JobDTO> {
  return asJson<JobDTO>(
    await fetch(`${BASE}/api/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    }),
  );
}

export async function uploadJob(
  file: File,
  opts: { backend?: string; language?: string; participants?: number | null } = {},
): Promise<JobDTO> {
  const fd = new FormData();
  fd.append("file", file);
  if (opts.backend) fd.append("backend", opts.backend);
  if (opts.language) fd.append("language", opts.language);
  if (opts.participants != null)
    fd.append("participants", String(opts.participants));
  return asJson<JobDTO>(
    await fetch(`${BASE}/api/jobs/upload`, { method: "POST", body: fd }),
  );
}

export async function deleteJob(id: string): Promise<void> {
  const res = await fetch(`${BASE}/api/jobs/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
}

export async function fetchResult(jobId: string): Promise<ResultDTO> {
  return asJson<ResultDTO>(await fetch(`${BASE}/api/jobs/${jobId}/result`));
}

export async function postLabels(
  jobId: string,
  update: LabelsUpdate,
): Promise<LabelsState> {
  return asJson<LabelsState>(
    await fetch(`${BASE}/api/jobs/${jobId}/labels`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(update),
    }),
  );
}

export function transcriptUrl(
  jobId: string,
  fmt: "txt" | "vtt" | "srt",
): string {
  return `${BASE}/api/jobs/${jobId}/transcripts/${fmt}`;
}
