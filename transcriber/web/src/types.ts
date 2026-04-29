export interface SegmentDTO {
  index: number;
  start: number;
  end: number;
  text: string;
  speaker: string;
  x: number;
  y: number;
  clip_url: string;
}

export interface ResultDTO {
  job_id: string;
  audio_name: string;
  audio_url: string | null;
  duration: number;
  n_speakers: number;
  speakers: string[];
  segments: SegmentDTO[];
}

export interface LabelsState {
  speakers: string[];
}

export interface LabelsUpdate {
  mapping: Record<string, string>;
  per_index: Record<number, string>;
}

export type JobStatus = "pending" | "running" | "complete" | "failed";

export interface JobDTO {
  id: string;
  source: string;
  title: string;
  backend: string;
  language: string;
  participants: number | null;
  status: JobStatus;
  stage: string | null;
  error: string | null;
  duration_seconds: number | null;
  n_segments: number | null;
  n_speakers: number | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface CreateJobRequest {
  source: string;
  title?: string;
  backend?: string;
  language?: string;
  participants?: number | null;
}
